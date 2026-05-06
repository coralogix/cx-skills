# Memory and performance

If you see "the collector is using a lot of memory" or "we keep OOMing" — most of the answer is: (a) `memory_limiter` is doing its job, (b) the numbers you're watching include kernel page cache that the collector didn't allocate, (c) the real lever is upstream volume or cardinality, not collector sizing.

## Contents

- `memory_limiter` behavior
- Go heap vs container RSS and page cache
- Throttling vs OOM
- Chronic `memory_limiter` causes
- Back-pressure with `sending_queue` and `file_storage`
- Batch processor tuning
- Per-deployment notes
- Key facts

## `memory_limiter`: what it actually does

```yaml
processors:
  memory_limiter:
    check_interval: 2s           # how often to sample process memory
    limit_mib: 512               # hard ceiling — refuse data beyond this
    spike_limit_mib: 128         # soft ceiling — start GC aggressively at limit - spike
```

- At `limit_mib`, receivers start **refusing** data. `otelcol_processor_memory_limiter_*_rejected` rises, the upstream sees send errors and retries.
- Between `limit - spike` and `limit`, the processor triggers Go GC on every check.
- `memory_limiter` must be the **first** processor in every pipeline — see `config-processors.md`. Put it anywhere else and upstream processors do work that gets shed.

`memory_limiter` is a circuit breaker, not a memory reclamation tool. It protects the collector from OOM at the cost of **upstream back-pressure** (which callers interpret as a drop or retry). That back-pressure is desirable — it keeps the collector alive during bursts.

## Sizing: Go heap vs container RSS

This is the single most common "memory leak" that isn't.

Real user case:
- `memory_limiter: limit_mib: 512`
- `kubectl top pod otel-agent-xxx`: 464 MiB
- Go runtime (via pprof): HeapAlloc ≈ 49 MB, Go Sys ≈ 117 MB

Delta: ~350 MB of container RSS that the Go runtime didn't allocate. Source: **kernel page cache** from `hostPath /var/log/pods` mount, accounted to the container cgroup because the collector reads those files.

### Debugging the disconnect

1. Emit self-telemetry (see `ops-troubleshooting.md` → step 1). Watch `process.runtime.go.mem.heap_alloc`, `process.runtime.go.mem.heap_sys`, `otelcol_process_memory_rss`.
2. If `process.runtime.go.mem.heap_alloc` is well below `limit_mib` but `kubectl top` / `process.runtime.uptime` + `otelcol_process_memory_rss` is near it, the delta is kernel page cache.
3. Page cache counts toward cgroup memory limits. `memory_limiter` samples the Go process — not the cgroup — so it fires on `heap_sys`, not RSS. If the cgroup OOM-kills the pod, that's the kernel, not the collector.

### Fixing the disconnect

- **Don't keep scaling `limit_mib` up.** That treats the symptom (cache), not the cause.
- **Don't raise the pod memory limit alone.** It just lets more cache accumulate.
- **Do** check if `filelog` is re-reading from start (unnecessary I/O spike) — `start_at: end` is usually correct.
- **Do** use `file_storage` extension to persist checkpoints — fewer re-reads after restart.
- **Do** consider `filelog`'s `max_concurrent_files` if the host has many files; high concurrency = more page-cache touching.

## Throttling vs OOM (two different things)

| Symptom | Looks like | Actually |
|---|---|---|
| OOM | container killed, pod restart, `Exit Code 137` or `OOMKilled` | kernel killed the collector for exceeding cgroup memory limit |
| Throttling | data arrives intermittently, `processor_memory_limiter_*_rejected` climbs, but no pod restart | `memory_limiter` doing its job — shedding load to stay below `limit_mib` |

Throttling is **not a bug**. If the user sees throttling and no data loss (retries drained), the collector is handling a burst correctly. If they see throttling and sustained data loss, the upstream rate is genuinely above capacity — look at the source, not the collector.

## When chronic `memory_limiter` firing means something else

`memory_limiter` shouldn't be firing in steady state. If it is, these are the causes (in order of likelihood):

### 1. Cardinality explosion in metrics

Each unique combination of resource + datapoint attributes is a series in memory. Common offenders:
- Process IDs, pod UIDs, ephemeral identifiers on resource attributes.
- SDK-specific high-cardinality attributes (`process.command_args`, `deployment.environment` typos).
- User-added labels on third-party metrics without a deny-list.

Fix: use OTTL to trim (`keep_keys`, `delete_matching_keys`, `delete_key`). See the OTTL skill's `references/cardinality.md`.

### 2. Spanmetrics `aggregation_cardinality_limit` blowup

The `spanmetrics` connector has its own cardinality ceiling:

```yaml
connectors:
  spanmetrics:
    aggregation_cardinality_limit: 100000
    dimensions:
      - name: http.method
      - name: http.status_code
      # ...
```

High-cardinality dimensions (e.g. `url.path` with IDs) blow up the series count. Trim the dimension list to low-cardinality fields or extract the pattern out of the path first (`replace_pattern`).

### 3. Tail sampling buffer sizing

Gateway memory ≈ `num_traces × avg spans per trace × avg span bytes`. If `num_traces: 500000` and avg span is 2 KB, you're reserving ~1 GB per gateway replica for trace buffering alone.

Reducing `num_traces` shrinks the buffer. Reducing `decision_wait` shrinks the time window but risks dropping late-arriving spans. Scale replicas instead when traces are actually plentiful.

### 4. Instrumentation doing more than the collector can handle

Real case: Node.js service with TypeORM auto-instrumentation created ~5x the spans of the underlying DB call volume, because the instrumentation traced every ORM-layer hop. Swapping to the narrower MySQL instrumentation dropped the span rate 80% and the collector stopped OOMing.

Fix: **look upstream.** If a microservice emits 10k traces/sec and the team didn't realize, no amount of collector tuning fixes it. Check with:
- `otelcol_receiver_accepted_spans{receiver="otlp"}` per agent
- per-service span counts from the OTel SDK's own metrics (if emitted)

## Back-pressure: `sending_queue` + `file_storage`

For bursts where the collector is fine but Coralogix ingress is momentarily slow, buffer spans/logs/metrics durably:

```yaml
extensions:
  file_storage:
    directory: /var/lib/otelcol/queue
    timeout: 10s

exporters:
  coralogix:
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 10000
      storage: file_storage
      block_on_overflow: true       # apply back-pressure upstream instead of dropping
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
    timeout: 30s

service:
  extensions: [file_storage]
```

- `storage: file_storage` writes the queue to disk — survives collector restarts.
- `block_on_overflow: true` back-pressures the pipeline (propagating to receivers) instead of dropping records at the exporter. Combined with `sending_queue` this is the right pattern for "no data loss."
- Disk path needs write access; with K8s, provision a PVC or an emptyDir (ephemeral — loses queue on pod delete).

## Batch processor tuning

`batch` amortizes export cost. Defaults are usually fine; common adjustments:

```yaml
processors:
  batch:
    timeout: 2s                   # flush at least every 2s
    send_batch_size: 1000         # trigger flush at this many records
    send_batch_max_size: 2000     # hard cap — no single export beyond this
```

- Too-small batches → exporter overhead per record dominates.
- Too-large batches → export latency, memory held longer, and some Coralogix ingestion paths have a single-request size ceiling (~2 MB default — tune `send_batch_max_size` under that).
- For logs with huge records, prefer size-based batching (`sizer: bytes`) over count-based.

## Per-deployment notes

- **K8s (otel-integration):** Chart defaults are usually sensible. Watch for custom `hostPath` mounts (page cache inflation) and per-service memory requests vs actual RSS.
- **ECS EC2 daemonset:** Host-networked, so pod-level memory limits don't apply the same way. Size the EC2 node to accommodate collector+kernel-cache.
- **ECS Fargate sidecar:** Fargate task memory is the hard ceiling. `limit_mib` at ~75% of task memory is safe; leaves headroom for the app.
- **Windows standalone:** `limit_mib` as env is fine. Windows counts memory differently — Resource Monitor is more reliable than Task Manager.

## Key Facts

- **`memory_limiter` is a circuit breaker, not a leak fixer.** Firing during bursts is the design.
- **`kubectl top` ≠ Go heap.** The delta is typically kernel page cache from file mounts; not a leak.
- **Throttling is not OOM.** Throttling = back-pressure working. OOM = cgroup killed the process.
- **Chronic firing = upstream volume or cardinality.** Look at receivers, spanmetrics dimensions, instrumentation breadth — before sizing up.
- **`sending_queue` + `file_storage` + `block_on_overflow: true`** is the no-data-loss back-pressure pattern.
- **Batch `send_batch_max_size` under 2 MB** for compatibility with some Coralogix ingestion paths.
- **Gateway memory ≈ `num_traces × avg spans × avg bytes`** — size tail-sampling buffers deliberately.
