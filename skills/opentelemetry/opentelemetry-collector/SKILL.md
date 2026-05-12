---
name: opentelemetry-collector
description: >
  OpenTelemetry Collector deployment, configuration, and troubleshooting for Coralogix
  users. Use when writing or debugging collector configs — the `coralogix` exporter
  (`domain:` vs `endpoint:`, `${env:CORALOGIX_PRIVATE_KEY}` bracket syntax,
  `coralogix/resource_catalog` variant), the universal processor chain, agent →
  cluster-collector → gateway topology, spanmetrics/tail_sampling/k8sattributes placement,
  and Coralogix-specific presets. Covers the `otel-integration` Helm chart (EKS/GKE/AKS/
  OpenShift, GKE Autopilot Warden, EKS Fargate), ECS EC2 daemonset, ECS Fargate sidecar,
  Linux/Windows/macOS standalone, Docker, and the universal installer. Not for OTTL
  authoring (use the `opentelemetry-ottl` skill) or OpAMP supervisor/Fleet Manager internals beyond the
  config-precedence callout.
license: Apache-2.0
metadata:
  version: "0.1.0"
  integration: otel-collector
  signals: "logs, metrics, traces"
  deployment: "kubernetes, helm, docker, ecs, aws"
  docs: https://coralogix.com/docs/opentelemetry/
  repo: https://github.com/coralogix/telemetry-shippers
  triggers:
    description: >
      Load when the user is deploying, configuring, or troubleshooting an OpenTelemetry
      Collector that ships telemetry to Coralogix — across any infrastructure (Kubernetes
      via the otel-integration Helm chart, ECS EC2/Fargate, EC2/VM standalone, Windows,
      macOS, Docker).
    always: false
    file_patterns:
      - "**/otel-collector*.yaml"
      - "**/otelcol*.yaml"
      - "**/collector-config*.yaml"
      - "**/*collector*.yaml"
      - "**/values*.yaml"
      - "**/otel-integration*.yaml"
      - "**/otel-agent*.yaml"
      - "**/task-definition*.json"
      - "**/task-definition*.yaml"
    config_keys:
      - "receivers:"
      - "exporters:"
      - "processors:"
      - "service:"
      - "pipelines:"
      - "coralogix:"
      - "opentelemetry-agent:"
      - "opentelemetry-cluster-collector:"
      - "opentelemetry-gateway:"
    keywords:
      - otel collector
      - opentelemetry collector
      - otelcol
      - otelcol-contrib
      - otel-integration
      - coralogix exporter
      - CDOT
      - CORALOGIX_PRIVATE_KEY
      - CORALOGIX_DOMAIN
      - k8sattributes
      - resource_catalog
      - tail_sampling
      - spanmetrics
      - memory_limiter
      - daemonset
      - sidecar
      - cluster-collector
      - gateway
---

# OpenTelemetry Collector

The Coralogix-flavored OpenTelemetry Collector — the `coralogix` exporter, the
`otel-integration` Helm chart for Kubernetes, CDOT for ECS, and the universal installer
for standalone hosts. Load this skill when a user is deploying, configuring, or
debugging a collector that ships to Coralogix. Most failures come down to a handful of
Coralogix-specific defaults that vanilla OpenTelemetry docs don't cover.

## When to Use This Skill

| Use case | Reference |
|---|---|
| Configure the `coralogix` exporter (domain, private key, app/subsystem) | [config-exporters.md](references/config-exporters.md) · [config-processors.md](references/config-processors.md) |
| Infrastructure Explorer / Resource Catalog | [preset-kubernetes.md](references/preset-kubernetes.md) |
| Pick a deployment mode | [setup-index.md](references/setup-index.md) |
| Kubernetes — `otel-integration` Helm chart (EKS/GKE/AKS/OpenShift/Autopilot/EKS Fargate) | [setup-kubernetes.md](references/setup-kubernetes.md) |
| OpenTelemetry Operator / Target Allocator | [setup-opentelemetry-operator.md](references/setup-opentelemetry-operator.md) |
| ECS EC2 (Linux daemonset) | [setup-ecs-ec2.md](references/setup-ecs-ec2.md) |
| ECS Fargate (sidecar) | [setup-ecs-fargate.md](references/setup-ecs-fargate.md) |
| Linux / macOS standalone | [setup-linux-standalone.md](references/setup-linux-standalone.md) |
| Windows standalone | [setup-windows-standalone.md](references/setup-windows-standalone.md) |
| Universal installer (all OS) | [setup-installer.md](references/setup-installer.md) |
| `spanmetrics`, `tail_sampling`, `k8sattributes` placement | [config-connectors.md](references/config-connectors.md) |
| Memory — `memory_limiter` firing, RSS vs Go heap | [ops-memory-performance.md](references/ops-memory-performance.md) |
| Troubleshoot "no data", "no traces", "Resource Catalog empty" | [ops-troubleshooting.md](references/ops-troubleshooting.md) |
| OpAMP supervisor / Fleet Manager config overlap | [preset-fleet-management.md](references/preset-fleet-management.md) |

## High-Signal Answer Rules

For these recurring cases, include the exact corrective detail in the final answer. These
are also the authoritative statements of Coralogix-specific defaults — do not contradict
them elsewhere in the answer.

### Exporter and routing

- **`domain:` is a bare hostname, not a URL.** `eu2.coralogix.com` — not `https://ingress.eu2.coralogix.com`, not a UI hostname.
- **Bracket env vars.** `${env:CORALOGIX_PRIVATE_KEY}`, not `$CORALOGIX_PRIVATE_KEY` — unbracketed form silently fails in v0.76+.
- **Use a dedicated `coralogix/resource_catalog` exporter for Infrastructure Explorer**
  with the `x-coralogix-ingress: metadata-as-otlp-logs/v1` header. The default
  `coralogix` exporter won't light up the entity views.
- **No data + transform/OTTL:** clearly say to stop trying OTTL; check receiver/exporter
  connectivity, DNS/TLS/proxy/egress, private key, and region/domain first.

**Minimal working exporter config:**

```yaml
exporters:
  coralogix:
    domain: "coralogix.com" # Replace with your specific Coralogix domain (e.g., coralogix.us, coralogix.in)
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    application_name: "your_application_name"
    subsystem_name: "your_subsystem_name"
```

### Pipeline placement (Kubernetes)

- **`memory_limiter` first, `batch` last.**
- **One role owns full `k8sattributes` extraction** — typically gateway; agents use `passthrough: true`.
- **`spanmetrics` on agent (before sampling), `tail_sampling` on gateway.** Run `transactions`/`groupbytrace/transactions` before `spanmetrics`; never on both agent and gateway.
- **Don't replace `service.pipelines` wholesale** — use `extraProcessors`/`extraReceivers` hooks; wholesale overrides silently break `resource/metadata` (`cx.agent.type`) and chart upgrades.

### Platform-specific rules

- **GKE Autopilot Warden:** Set `logsCollection.storeCheckpoints: false`; disable `coralogix-ebpf-profiler`, `hostMetrics`, `hostEntityEvents`, `resourceDetection` on agent; disable `resourceDetection` on cluster-collector. Use `gke-autopilot-values.yaml`.
- **ECS EC2 daemonset localhost:** Apps must target the EC2 host IP (not `localhost`); daemonset needs `networkMode: host`. Remove `ecs` from `resourcedetection.detectors` — it stamps the collector's own container ID.
- **ECS Fargate startup loss:** Add sidecar `healthCheck` + `dependsOn: [{containerName: otel-collector, condition: HEALTHY}]` on the app. Use the CDOT image.
- **Standalone installer:** Recommend `otel-installer`/one-liner with both
  `CORALOGIX_PRIVATE_KEY` and `CORALOGIX_DOMAIN`.
- **Infrastructure Explorer (Kubernetes):** `kubernetesResources` and `hostEntityEvents`
  are **enabled by default** in the chart — do not disable them. `kubernetesResources`
  must stay on the `opentelemetry-cluster-collector` only (enabling it on the agent
  crashes with `can't get K8s Instance Metadata; node name is empty`). Use a dedicated
  `coralogix/resource_catalog` exporter with `x-coralogix-ingress: metadata-as-otlp-logs/v1`.
- **Resource Catalog daemonset crash:** `resourcedetection/resource_catalog` belongs on
  the `opentelemetry-cluster-collector` Deployment only; remove it from daemonset agents.
- **Full `k8sattributes`:** Exactly one role should do full extraction; set
  `passthrough: true` on the others.
- **OpAMP supervisor endpoint:** It is different from exporter `domain:` and needs the
  full URL, e.g. `https://ingress.eu2.coralogix.com/opamp/v1`.
- **Java multiline stack traces not merging (Kubernetes):** CRI tags every log line as
  `F` (full/final) — the standard `P→F` recombine never triggers. Use `firstEntryRegex`
  on the filelog `recombine` operator to detect new entries by timestamp pattern.
- **`spanNameReplacePattern` escaping:** There are two layers: single-quote or block
  scalar for YAML/OTTL backslashes, and write backreferences as `$$1`/`$$2` because the
  collector envprovider expands `$...`; verify with `helm template`.
- **Target Allocator debugging:** Port-forward
  `svc/coralogix-opentelemetry-targetallocator` on `8080`; inspect `/jobs` and
  `/scrape_configs`; then check RBAC, selectors, and watched namespaces.

## Common Workflows

### 1. Triage a "no data reaching Coralogix" report

Work through these steps in order before touching any pipeline configuration:

**Step 1 — Prove the collector is running and exporting**
```bash
# Kubernetes: check exporter metrics
kubectl exec -n <namespace> <collector-pod> -- wget -qO- http://localhost:8888/metrics \
  | grep -E 'otelcol_exporter_(sent|send_failed|enqueue_failed|queue)'
# Success: otelcol_exporter_sent_* > 0 and climbing
# Failure indicator: otelcol_exporter_send_failed_* > 0 — proceed to Step 2
```

**Step 2 — Verify DNS and TLS reach the ingestion endpoint**
```bash
# From inside the collector pod / host
nslookup ingress.<domain>          # e.g. ingress.coralogix.com
curl -v https://ingress.<domain>   # expect 400/401, NOT a TLS or connection error
```
If DNS fails → network/VPC/proxy issue, not a collector config issue.
If TLS fails → certificate bundle or proxy MITM — check `NO_PROXY` / `HTTPS_PROXY` env vars.

**Step 3 — Confirm the private key is expanded correctly**
```bash
# Kubernetes: inspect the live env
kubectl exec -n <namespace> <collector-pod> -- env | grep CORALOGIX
# The key must appear as a 36-char UUID-like string, not the literal "${env:...}" text
# Literal text → bracket syntax wrong, or Secret not mounted
```

**Step 4 — Check the exporter `domain:` value**

In the running config (`/etc/otelcol-contrib/config.yaml` or `kubectl get cm`), verify:
- `domain:` is a bare hostname such as `eu2.coralogix.com` — no `https://` prefix, no UI hostname (`app.coralogix.com` is wrong)
- `private_key:` resolved to the actual key (Step 3)

**Step 5 — Enable debug logging for one minute**
```yaml
service:
  telemetry:
    logs:
      level: debug
```
Look for `Exporting failed` or `grpc status` lines. A `StatusUnauthenticated` confirms a key/region mismatch. A `context deadline exceeded` suggests egress/proxy or ingress-side latency — also check `coralogix.timeout` (default 5s; increase to 30s).

**Step 6 — Inspect pipeline wiring only after Steps 1–5 pass**

If export is healthy but data is missing in the Coralogix UI: check receiver connectivity, processor filters (`filter` processor dropping everything), and that the pipeline is wired in `service.pipelines`. Full symptom → root-cause table: [references/ops-troubleshooting.md](references/ops-troubleshooting.md).

### 2. Bring up a new Kubernetes cluster with `otel-integration`

Use [references/setup-kubernetes.md](references/setup-kubernetes.md) for install flow,
per-platform variants, Target Allocator, and chart-specific failure modes. Use
[references/preset-kubernetes.md](references/preset-kubernetes.md) when the question is
about Helm presets or Infrastructure Explorer.

### 3. Bring up ECS Fargate (sidecar mode)

Use [references/setup-ecs-fargate.md](references/setup-ecs-fargate.md). The fragile pieces are
sidecar health checks, `dependsOn: HEALTHY`, `essential` flags, and keeping the `ecs`
detector enabled only for sidecar mode.

### 4. Diagnose `memory_limiter` firing constantly

Use [references/ops-memory-performance.md](references/ops-memory-performance.md). Compare
Go heap metrics to RSS before changing pod limits or `memory_limiter` settings.

## Limitations

- **OTTL authoring** — use the `opentelemetry-ottl` skill.
- **OpAMP / Fleet Manager internals** — `preset-fleet-management.md` covers only the collector-config overlap (endpoint shape, values-vs-UI precedence, Windows image pitfall); deep supervisor/CDOT work is out of scope.
- **SDK instrumentation problems** — use the `opentelemetry-instrumentation` skill.
- **Upstream infrastructure** (DNS, TLS, proxies, IAM/IRSA, NAT, VPC endpoints) — diagnose to the boundary, then escalate.

## References

Upstream links:
- [Coralogix OpenTelemetry docs](https://coralogix.com/docs/opentelemetry/)
- [`telemetry-shippers` (Helm charts, ECS task defs, installer)](https://github.com/coralogix/telemetry-shippers)
- [`integration-definitions` (UI wizards)](https://github.com/coralogix/integration-definitions)
- [OpenTelemetry Collector (upstream)](https://github.com/open-telemetry/opentelemetry-collector)
- [OTel Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib)
