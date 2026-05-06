# Troubleshooting: symptom → root cause

Maps recurring user symptoms to the actual root cause and the first action to take. Most issues come down to pipeline placement, exporter config, or an upstream connectivity/IAM problem masquerading as a config issue.

## Contents

- Operating rule: confirm this is a collector problem
- Symptom to root-cause table
- Debugging workflow
- Collector self-telemetry metrics
- Debug exporter isolation
- High-signal collector logs
- Scope checks and key facts

## Operating rule: is the problem even the OTel Collector?

Before editing pipelines, confirm the symptom actually belongs to the collector. "No data reaching Coralogix" is often a DNS / TLS / proxy / domain / API-key problem — not a pipeline problem. If the user has added a `transform` processor to "force data through" and it made no difference, the root cause is upstream. Say so clearly before continuing.

## Symptom → Root cause table

| Symptom | Most likely root cause | First action |
|---|---|---|
| No data of any kind reaching Coralogix | `endpoint:` used instead of `domain:`; full URL used instead of bare hostname; unbracketed `$CORALOGIX_PRIVATE_KEY` failing to expand in exporter v0.76+; or a UI hostname used as `domain:` instead of the data-ingestion hostname | Verify `domain:` is a bare `<region>.coralogix.com` hostname (see `core` for the regions and UI-vs-ingestion rules). `private_key: "${env:CORALOGIX_PRIVATE_KEY}"` (bracketed). Check egress/TLS/proxy to `*.coralogix.com:443`. |
| Collector starts, pipelines load, but exporter logs show `rpc error: code = ResourceExhausted` or `code = PermissionDenied` | Rate limit / quota / wrong API key scope | Check ingress quota on the Coralogix side; verify the `PRIVATE_KEY` is a Send-Your-Data key (see `core` for key categories). |
| Resource Catalog / Infrastructure Explorer is empty despite K8s deployment running fine | Missing `kubernetesResources` preset; or using the default `coralogix` exporter instead of `coralogix/resource_catalog`; or missing `x-coralogix-ingress: metadata-as-otlp-logs/v1` header | Enable `opentelemetry-cluster-collector.presets.kubernetesResources.enabled: true`. Ensure the dedicated `coralogix/resource_catalog` exporter has the ingress header. See `preset-kubernetes.md`. |
| APM shows traces but no error rates / p99 latencies | `spanmetrics` configured on the gateway (after `tail_sampling`) instead of the agent — metrics only see sampled spans | Move the `spanmetrics` connector to the agent, upstream of any sampling. `transactions` processor must also be upstream of `spanmetrics`. |
| Traces are incomplete across services — some spans per trace present, others missing | Tail sampling running on daemonset agents (each agent only sees its node's spans); or multiple gateway replicas without consistent-hashing loadbalancer | Put `tail_sampling` on a central gateway. Feed via `loadbalancing` exporter with routing by `trace_id` so all spans for one trace land on the same gateway replica. |
| `spanMetrics` values look double-counted | Same `spanmetrics` connector running on both agent and gateway — metrics emitted twice | Enable `spanmetrics` on agent only. Remove any `spanmetrics` connector from gateway/cluster-collector. |
| `k8sattributes` fires full extraction in 3 collectors, API server at high QPS | Triple-duplication anti-pattern — same full `extract.metadata` block in daemonset, cluster-collector, gateway | Keep `passthrough: true` on daemonset agents. Full extraction in one role only (usually gateway). |
| Collector refuses to start — `cannot start pipelines: failed to start "resourcedetection/resource_catalog" processor: can't get K8s Instance Metadata; node name is empty` | Resource Catalog detector running on a pod that is not part of the cluster-collector deployment (e.g. daemonset agent where node-name injection fails) | Keep `resourcedetection/resource_catalog` on cluster-collector only. Ensure `K8S_NODE_NAME` env is set from `spec.nodeName` on the cluster-collector pod spec. |
| `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early_total` climbing | Not enough gateway replicas / `num_traces` buffer too small / `decision_wait` too short for the trace duration | Scale gateway replicas. Increase `num_traces` (trace buffer) and `decision_wait` (how long to hold a trace before deciding). Check that spans for one trace actually reach the same replica. |
| Duplicate metric series or partial resets | `single-writer` principle violated — multiple collectors emitting the same metric with different resource attributes | Add `resourcedetection` (env/ec2/system/host) to the metrics pipeline and deduplicate the `resource.attributes` set. Each unique series should have exactly one writer. |
| Exporter logs `INVALID_ARGUMENT` on send, but with no upstream body/data error | OTTL problem (transform/filter) — wrong context, missing nil guard | See the OTTL skill's Error Decoder. `INVALID_ARGUMENT` here is a pipeline processing error before export. |
| `Exporting failed. Dropping data.` with `context deadline exceeded` | Coralogix ingress slow or client-side backpressure / timeout too aggressive | Increase `coralogix.timeout` (default 5s) to 30–120s. Add `sending_queue.enabled: true` + `storage: file_storage` for durable buffering. Investigate ingress latency metrics side of the house. |
| `opentelemetry-cluster-collector` not reporting `cx.agent.type: cluster-collector` | Values override broke the `resource/metadata` processor; or operator wiped the default `service.pipelines` | Restore default `service.pipelines` from chart defaults. Prefer `extraProcessors` hook over wholesale pipeline replacement. See `setup-kubernetes.md` "Don't override pipelines wholesale." |
| APM gateways consume massive memory, span drops in logs | Gateway sized for steady state; spike from burst traffic + `tail_sampling` buffer (`num_traces`) inflation | Size gateway memory for: `num_traces × avg spans/trace × avg span size`. Reduce `decision_wait` if traces are short-lived. |
| Windows collector CPU spikes during peak IIS traffic | Not the collector — Windows Defender scanning rotated IIS log files | Open Resource Monitor → Disk. If `msmpeng.exe` is the top consumer on the IIS log path, exclude that path from Defender real-time scan. See `setup-windows-standalone.md`. |
| UI-generated Linux host config produces traces without language icons | Host wizard strips `telemetry.sdk.*` resource attributes | Workaround: `transform` processor re-adds them on the traces pipeline until the wizard fix lands. See `setup-linux-standalone.md`. |
| `memory_limiter` fires constantly, memory doesn't seem to drop after GC | Go heap vs kernel page cache disconnect — `kubectl top` shows container RSS including page cache from `hostPath /var/log/pods` mounts | Check Go HeapAlloc via the collector's self-telemetry. If Go Sys < RSS significantly, the delta is kernel page cache (not a leak). See `ops-memory-performance.md`. |
| ECS Fargate sidecar: logs lost when app container crashes | App is `essential: true`, sidecar is `essential: false` — ECS kills task including sidecar before buffered logs drain | Add `healthCheck` to sidecar + `dependsOn: [{containerName: otel-collector, condition: HEALTHY}]` on the app. Use CDOT image (includes `/healthcheck` binary). See `setup-ecs-fargate.md`. |
| ECS EC2 daemonset: every log row attributed to the collector's container | `ecs` detector in `resourcedetection` stamps collector's own container ID onto all records | Remove `ecs` from `resourcedetection.detectors` on daemonset-mode collectors. Use the `ecsattributes/container-logs` CDOT processor for per-container attribution. See `setup-ecs-ec2.md`. |
| Fleet Manager says chart version applied, but user's values.yaml changes don't appear | `presets.fleetManagement.supervisor.enabled: true` — Fleet Manager UI overrides values.yaml config at runtime | Explain the precedence model: with supervisor enabled, config comes from Fleet Manager, not the Helm values. Edit in the UI or disable supervisor. See `preset-fleet-management.md`. |
| Collector v0.142+ crashes `CrashLoopBackOff` with older otel-integration chart versions | Upstream collector contains a breaking change not yet absorbed by the chart | Pin the collector image version (chart `image.tag`) or bump the whole chart to a matching release. Don't mix a new-image-tag override against an old chart. |

## Debugging workflow

If you see "it's broken," work through this order before editing pipelines:

### 1. Enable the collector's self-telemetry

If the collector isn't already emitting its own metrics, turn it on temporarily:

```yaml
service:
  telemetry:
    metrics:
      level: detailed
      readers:
        - periodic:
            interval: 30000
            exporter:
              otlp:
                protocol: grpc
                endpoint: "http://localhost:4317"
    logs:
      level: info
```

Metrics to read first:

| Metric | Tells you |
|---|---|
| `otelcol_receiver_accepted_*` vs `_refused_*` | whether data is entering at all |
| `otelcol_processor_batch_batch_send_size` | batch sizing; near-empty batches mean low volume or upstream drop |
| `otelcol_processor_memory_limiter_*` | back-pressure events |
| `otelcol_exporter_send_failed_*` | export failures by signal |
| `otelcol_exporter_queue_capacity` / `_queue_size` | sending_queue depth |
| `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early_total` | gateway under-sized / wrong routing |

### 2. Add a `debug` exporter, mirror the problematic signal

```yaml
exporters:
  debug:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [coralogix, debug]    # mirror
```

If `debug` sees the data but `coralogix` doesn't, the problem is the exporter / connectivity. If neither sees it, the problem is upstream (receiver, source app, network).

Only turn `verbosity: detailed` on in production for short diagnostic windows — it is expensive, especially on Windows.

### 3. Read the collector logs

Typical high-signal log lines:

- `Exporting failed. Dropping data.` + `rpc error: code = X` — exporter connectivity / auth / quota. Cross-check against `domain`, `private_key`, egress.
- `INVALID_ARGUMENT` — OTTL problem in transform/filter. Switch to the OTTL skill.
- `can't get K8s Instance Metadata; node name is empty` — `resourcedetection/resource_catalog` on wrong collector type (see table above).
- `cannot start pipelines: failed to start "X" processor` — processor on the wrong collector role, or missing env/RBAC.
- `denied by autogke-no-write-mode-hostpath` — GKE Autopilot Warden, see `setup-kubernetes.md`.

### 4. Cross-check quickly that it isn't the skill's own scope

- OTTL issues → OTTL skill.
- Fleet Management config precedence → `preset-fleet-management.md`.
- Memory / page cache → `ops-memory-performance.md`.

### 5. Only now, touch the pipeline

When you do edit pipelines, change one thing at a time and watch the self-telemetry. Batching two changes in a single apply wastes the diagnostic budget.

## Key Facts

- **Most "no data" problems are connectivity, not pipeline.** Check domain/key/egress first.
- **`coralogix` domain field is a bare hostname.** Not a URL, not `endpoint:`.
- **Enable self-telemetry before editing anything.** `otelcol_*` metrics are the highest-signal diagnostic.
- **Mirror suspect signals through a `debug` exporter** to isolate where data drops.
- **`single-writer` violations cause duplicate metrics and partial resets.** Deduplicate resource attributes across collectors.
- **If `memory_limiter` fires chronically, look upstream** — cardinality/volume — before sizing up the collector.
- **APM missing errors = spanmetrics placement.** Move to agent, upstream of sampling.
- **Incomplete cross-service traces = tail_sampling placement + loadbalancing routing.** Central gateway, `consistent_hashing` by `trace_id`.
