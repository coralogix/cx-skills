# Span Metrics — Required Labels and Cardinality Control

Coralogix's APM **Service Catalog** and **Database Catalog** are powered by
metrics derived from spans by the OpenTelemetry [Span Metrics
connector](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/connector/spanmetricsconnector/README.md).
The connector converts trace data into RED metrics (Rate, Errors, Duration)
so APM can retain request / error / latency coverage even when traces are
sampled downstream, **as long as `spanmetrics` consumes 100% of spans before
any sampling decision**.

This page lists the **labels** that must be present on Span Metrics for the
APM features to work, plus the cardinality controls that protect the
backend from runaway label combinations.

## Minimum metrics + labels (Service Catalog and DB Catalog drilldowns)

Span Metrics produces four series for each unique label combination:
`duration_ms_sum`, `duration_ms_bucket`, `calls_total`, `duration_ms_count`.
Keep this minimal label set. For Coralogix Service Catalog and Database
Catalog drilldowns, do not describe these labels as optional, and do not
remove them to reduce cardinality; reduce cardinality by normalizing
unbounded values and by removing non-required dimensions instead.

| Label | Source attribute |
|---|---|
| `span_name` | span name |
| `service_name` | resource `service.name` |
| `span_kind` | span kind (`SERVER`, `CLIENT`, etc.) |
| `status_code` | span status code |
| `collector_instance_id` | connector-generated `collector.instance.id` dimension |
| `http_method` | span `http.method` |
| `host_name` | resource `host.name` |
| `k8s_cluster_name` | resource `k8s.cluster.name` |
| `cgx.transaction` | span attribute populated by `CoralogixTransactionSampler` |
| `cgx.transaction.root` | same |
| `db_namespace` | span `db.namespace` |
| `db_operation_name` | span `db.operation.name` |
| `db_collection_name` | span `db.collection.name` |
| `db_system` | span `db.system` |
| `application_name` | resolved from the Coralogix exporter's `application_name_attributes` |
| `cx_subsystem_name` | resolved from the Coralogix exporter's `subsystem_name_attributes` |

For span/resource-derived labels, if a span lacks the source attribute,
the corresponding label is empty — which can collapse APM rows or duplicate
them depending on the feature.
Do not exclude the connector-generated `collector.instance.id` default
dimension (`collector_instance_id` after Prometheus normalization) unless
another stable writer-unique dimension is already in place; otherwise
multiple collector agents can emit colliding RED series for the same
service/span/status combination. For self-managed / upstream collectors,
verify that `collector.instance.id` is actually present in generated
metrics. Upstream contrib added this feature in `v0.136.0`; in
`v0.136.0` through `v0.151.x`, start the collector with
`--feature-gates=+connector.spanmetrics.includeCollectorInstanceID` or use
another stable writer-unique dimension. In `v0.152.0` and later, upstream
spanmetrics docs describe the feature gate as beta / enabled by default,
but it can still be disabled with
`--feature-gates=-connector.spanmetrics.includeCollectorInstanceID` or
removed with `exclude_dimensions`. For builds before `v0.136.0`, use
another writer-unique dimension or a single-writer pipeline topology.
Short answers for collector-instance safety should name both version
windows: `v0.136.0` through `v0.151.x` needs the feature gate, while
`v0.152.0+` should still be verified because `collector.instance.id` can be
disabled or excluded.

## Sampling placement and coverage

Span Metrics only has full RED coverage when the connector receives every
span before sampling. The common Coralogix topology is:

1. Generate span metrics on the agent from 100% of incoming spans.
2. Forward traces to a gateway for tail sampling.
3. Export sampled traces separately from the already-generated metrics.

If SDK head sampling drops spans before they leave the application, or a
collector `tail_sampling` processor runs before `spanmetrics`, the connector
only sees sampled spans. Say the symptom plainly in support answers: Span
Metrics is then based only on sampled spans, so generated `calls_total`,
error counts, and duration histograms **undercount real traffic** and can
distort rates, error percentages, and latency percentiles. This is not full
coverage, even if the sampled traces themselves look healthy.

Collector pipeline placement belongs to the `opentelemetry-collector` skill;
use its `config-connectors.md` guidance when a customer asks where to run
`spanmetrics` versus `tail_sampling`.

### Bridge between customer-emitted attributes and connector dimensions

For new native OpenTelemetry HTTP metric data points, use the current stable
attribute `http.request.method`. Span Metrics is a different generated-metric
surface: the connector dimensions still read legacy `http.method`, so
Coralogix bridges `http.request.method` to `http.method` before the connector
consumes spans.

The connector's `dimensions` block uses specific source-attribute names
that don't always match what customer instrumentation emits today:

| Connector dimension | Source attribute the connector reads | What modern OTel SDKs emit |
|---|---|---|
| `http_method` label | `http.method` | `http.request.method` |
| `db_namespace` label | `db.namespace` | sometimes `db.name`; if both are absent, fall back through endpoint / system attributes so the label is not blank |
| `db_operation_name` label | `db.operation.name` | sometimes `db.operation` (the name customers see in the Database Monitoring docs) |
| `db_system` label | `db.system` | `db.system.name` in stable DB semconv |

The **Coralogix Helm chart** (`coralogix/otel-integration/k8s-helm`)
includes a `transform/spanmetrics` processor that bridges these so the
labels populate regardless of which name the SDK emits. Use the
`coralogix/telemetry-shippers` chart README as the canonical reference for
the [`spanMetrics.transformStatements` values block](https://github.com/coralogix/telemetry-shippers/blob/master/otel-integration/k8s-helm/README.md#L1798-L1825)
that defines this bridge; the commented defaults live in
[`otel-integration/k8s-helm/values.yaml`](https://github.com/coralogix/telemetry-shippers/blob/master/otel-integration/k8s-helm/values.yaml#L184-L208).
In Helm values, these statements belong under the top-level
`spanMetrics.transformStatements`, not under
`spanMetrics.dbMetrics.transformStatements`. DB-metrics-only placement can
make `db_calls_total` contain `db_namespace` while the normal Span Metrics
`calls_total` series still has a blank `db_namespace`.
Short-answer anchor for DB namespace incidents: the pre-spanmetrics bridge
belongs in top-level `spanMetrics.transformStatements` / the traces pipeline
before `spanmetrics`. It must populate `db.namespace` from `db.name`, then
`server.address`, `network.peer.name`, `net.peer.name`,
`network.peer.address`, and finally `db.system`. Use the symptom wording
`db_calls_total` works but normal `calls_total` still has blank
`db_namespace` when the bridge lives only under
`spanMetrics.dbMetrics.transformStatements`.
For Fleet UI or generated values, verify the rendered collector ConfigMap,
not only the UI JSON or `values.yaml`. The same semantic bridge can be
present in the user input but missing from the actual traces pipeline if the
UI-to-Helm mapping writes a different key such as
`span_metrics.transform_statements` or a DB-only path.
The public Coralogix naming-conventions guide documents the same
`transform/spanmetrics` bridge and where it belongs in the traces pipeline.
**Self-managed collector users** must add the equivalent bridge themselves,
otherwise the labels stay empty and APM Service Catalog / Database Catalog
drilldowns appear blank. Hand off the OTTL transform authoring to the
`opentelemetry-ottl` skill — minimal example shape:

```yaml
processors:
  transform/spanmetrics_bridge:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          - set(attributes["http.method"], attributes["http.request.method"]) where attributes["http.method"] == nil and attributes["http.request.method"] != nil
          - set(attributes["db.system"], attributes["db.system.name"]) where attributes["db.system"] == nil and attributes["db.system.name"] != nil
          - set(attributes["db.namespace"], attributes["db.name"]) where attributes["db.namespace"] == nil and attributes["db.name"] != nil
          - set(attributes["db.namespace"], attributes["server.address"]) where attributes["db.namespace"] == nil and attributes["server.address"] != nil
          - set(attributes["db.namespace"], attributes["network.peer.name"]) where attributes["db.namespace"] == nil and attributes["network.peer.name"] != nil
          - set(attributes["db.namespace"], attributes["net.peer.name"]) where attributes["db.namespace"] == nil and attributes["net.peer.name"] != nil
          - set(attributes["db.namespace"], attributes["network.peer.address"]) where attributes["db.namespace"] == nil and attributes["network.peer.address"] != nil
          - set(attributes["db.namespace"], attributes["db.system"]) where attributes["db.namespace"] == nil and attributes["db.system"] != nil
          - set(attributes["db.operation.name"], attributes["db.operation"]) where attributes["db.operation.name"] == nil and attributes["db.operation"] != nil
          # Driver-specific collection/table names → db.collection.name.
          # Repeat for db.mongodb.collection, db.cassandra.table, etc. as
          # needed; full list at https://opentelemetry.io/docs/specs/semconv/registry/attributes/db/
          - set(attributes["db.collection.name"], attributes["db.sql.table"]) where attributes["db.collection.name"] == nil and attributes["db.sql.table"] != nil
```

Bridge runs in the **traces** pipeline before `spanmetrics` consumes
the spans. Hand SDK-specific fallback chains off to the
`opentelemetry-ottl` skill. If the same customer is debugging the
Database Catalog, also apply the Database Monitoring bridge for
`db.namespace` → `db.name`, `db.operation.name` → `db.operation`,
`db.query.text` → `db.statement`, and `server.address` /
`network.peer.address` → `net.peer.name`; see
[database-monitoring.md](database-monitoring.md).

### Status-code semconv on generated RED metrics

The upstream Span Metrics connector has a feature gate for the latest OTel
status-code semantic convention on generated RED metrics:
`spanmetrics.statusCodeConvention.useOtelPrefix`.

When the gate is **disabled** (upstream default at introduction), generated
OTLP metric data points use the older `status.code` attribute with raw values
`Error`, `Ok`, and `Unset`. When the gate is **enabled**, the generated
metric data points use `otel.status_code` only for error and explicit-ok spans,
with raw values `ERROR` and `OK`. Unset spans omit `otel.status_code`; there is
no `otel.status_code="UNSET"` value to match in collector-side OTTL.
Short-answer anchor: this is a generated Span Metrics / RED metric
data-point attribute change, so a compatibility bridge belongs in the
metrics pipeline after `spanmetrics`, not in trace
`spanMetrics.transformStatements`.

Prometheus-facing labels may show normalized values such as
`STATUS_CODE_ERROR` or `STATUS_CODE_OK`, or may omit the status label for
unset datapoints. An OTTL transform that runs in the collector metrics pipeline
after `spanmetrics` sees the raw OTLP datapoint values and attribute absence,
not Prometheus label renderings. Match those raw values and the missing-attribute
case in collector-side bridges.

This is different from the trace-span bridge above. The connector has
already converted spans into metrics, so any compatibility bridge belongs in
the **metrics** pipeline after `spanmetrics`, not in the traces pipeline
before it.

If a Coralogix backend path, dashboard, or alert still expects the older
metric attribute, mirror the new shape back to the old one temporarily:

```yaml
processors:
  transform/spanmetrics_status_code_compat:
    error_mode: ignore
    metric_statements:
      - context: datapoint
        statements:
          - set(attributes["status.code"], "Error") where attributes["status.code"] == nil and attributes["otel.status_code"] == "ERROR"
          - set(attributes["status.code"], "Ok") where attributes["status.code"] == nil and attributes["otel.status_code"] == "OK"
          # Scope the nil-status fallback to generated spanmetrics metrics so
          # unrelated metrics without otel.status_code do not get status.code.
          # This covers the raw OTLP metric names (`calls`, `duration`) and
          # the exposed spanmetrics series (`calls_total`, `duration_ms_*`).
          - set(attributes["status.code"], "Unset") where attributes["status.code"] == nil and attributes["otel.status_code"] == nil and IsMatch(metric.name, "(^|[._])calls(_total)?$|(^|[._])duration(_ms_(sum|bucket|count))?$") and (attributes["span.name"] != nil or attributes["span_name"] != nil) and (attributes["span.kind"] != nil or attributes["span_kind"] != nil)

service:
  pipelines:
    metrics:
      receivers: [spanmetrics]
      processors: [transform/spanmetrics_status_code_compat, batch]
      exporters: [coralogix]
```

If Coralogix has already moved to the newer shape and a customer still emits
the old one, mirror in the other direction:

```yaml
processors:
  transform/spanmetrics_status_code_to_otel:
    error_mode: ignore
    metric_statements:
      - context: datapoint
        statements:
          - set(attributes["otel.status_code"], "ERROR") where attributes["otel.status_code"] == nil and attributes["status.code"] == "Error"
          - set(attributes["otel.status_code"], "OK") where attributes["otel.status_code"] == nil and attributes["status.code"] == "Ok"
          # Do not set otel.status_code for status.code == "Unset"; the newer
          # convention represents unset by omitting otel.status_code.
```

Do not treat this as an instrumentation downgrade request. First check which
feature-gate state the collector is using, then make the Coralogix consumer
support both forms or apply a temporary metrics-pipeline bridge.

## Additional labels (per feature)

Add these to the connector's `dimensions` to enable the corresponding APM
feature:

| Add label | Enables |
|---|---|
| `rpc.grpc.status_code`, `http.response.status_code` | API-error tracking |
| `service.version` | service grouping by version |
| Owner-specific workload label: `k8s.deployment.name`, `k8s.statefulset.name`, `k8s.daemonset.name`, `k8s.job.name`, `k8s.cronjob.name`, or `k8s.replicaset.name` | service ↔ k8s correlation in the Resources Catalog; use whichever attribute matches the pod owner, do not invent `k8s.deployment.name` for non-Deployment workloads |
| `k8s.pod.name` | avoiding collisions when multiple collector agents / replicas write span metrics for the same `service_name`, including the common one-agent-per-node DaemonSet topology when a service has pods on multiple nodes. This is high-cardinality / pod-churn-sensitive; use it only for the collision case, not as a blanket default. |

## Cardinality limit (`aggregation_cardinality_limit`)

Dynamic values in span names or labels — UUIDs, full URL paths with
parameters, raw SQL, session IDs — explode the number of unique series.
The Span Metrics connector can enforce a per-service-per-metric cap and
redirect overflow to a fallback series. Raw OTLP metric datapoints carry
the attribute `otel.metric.overflow="true"`; PromQL / Prometheus-normalized
labels show the same marker as `otel_metric_overflow="true"`.

**The default depends on how the connector is deployed:**

- **Coralogix Helm chart (`coralogix/otel-integration/k8s-helm`)** —
  starting with chart `v0.0.203`, ships with the cap pre-configured at
  **100,000** via the `spanMetrics.aggregationCardinalityLimit` preset.
  Overflow protection is on by default for those chart versions. For chart
  versions before `v0.0.203`, set `spanMetrics.aggregationCardinalityLimit`
  explicitly.
- **Self-managed / upstream OpenTelemetry Collector** — the upstream
  `spanmetrics` connector ships with `aggregation_cardinality_limit: 0`,
  which **disables** the cap. Overflow protection only kicks in when the
  field is set explicitly.

If you are running your own collector, set the limit explicitly:

```yaml
connectors:
  spanmetrics:
    aggregation_cardinality_limit: 100000   # 0 (upstream default) disables the cap
```

For the Coralogix Helm chart, the equivalent preset key (already set to
100,000 starting with chart `v0.0.203`; set it explicitly on older chart
versions):

```yaml
spanMetrics:
  aggregationCardinalityLimit: 100000   # set to 0 to disable
```

When overflow happens, additional unique label combinations are aggregated
into the fallback series. Example with a limit of 3:

```prometheus
calls_total{service_name="A", span_name="uuid1"}
calls_total{service_name="A", span_name="uuid2"}
calls_total{service_name="A", span_name="uuid3"}
calls_total{service_name="A", otel_metric_overflow="true"}   # PromQL / Prometheus-normalized label
```

Before Prometheus normalization, the same fallback data point has raw OTLP
attributes like:

```text
service.name = "A"
otel.metric.overflow = "true"
```

The cardinality cache:

- is in-memory only and clears when the OpenTelemetry Collector restarts;
- on the Coralogix Helm preset (`metrics_expiration: 5m`), resets
  automatically after 5 minutes of no data for that service. The
  upstream spanmetrics connector defaults to `metrics_expiration: 0`
  (no expiration) — self-managed users must set the field explicitly
  or restart the collector to clear cardinality state.
- persists across redeploys if data flow is continuous.

### Recommended overflow alert

Use the Prometheus-normalized label form in PromQL:

```promql
sum by (service_name) (duration_ms_bucket{otel_metric_overflow="true"}) > 0
```

In the collector `debug` exporter, OTTL processors, or OTLP metrics before
Prometheus normalization, look for the raw data-point attribute
`otel.metric.overflow="true"` instead. Either form means a single service
started overflowing before the volume became significant.

## Other connector knobs

| Knob | What it does |
|---|---|
| `metrics_expiration` | how long unused metric series stay in memory before being dropped (helm default: `5m`) |
| `aggregation_temporality` | `cumulative` (totals since start) vs `delta` (changes since last interval) |
| `exemplars.enabled` | attaches trace IDs to metric points for metric-to-trace jumps; not required for RED monitoring |
| `resource_metrics_key_attributes` | resource attributes used to build the metric resource hash key. Include something that distinguishes the writer — `service.instance.id` is the canonical incoming resource attribute — when multiple collectors share a `service.name`, otherwise their counters collide. (`collector.instance.id` is generated by the connector as a metric dimension, not an incoming resource attribute, so it can't be referenced here unless you've explicitly set it as a resource attribute upstream.) |

### Helm interval terminology

Coralogix Helm and customer configs can expose both global collection
intervals and connector-specific flush intervals.

| Setting | Meaning |
|---|---|
| `global.collectionInterval` / `spanMetrics.collectionInterval` | Helm preset-level interval used by Coralogix chart rendering. |
| `metrics_flush_interval` | Upstream connector setting controlling how often Span Metrics emits generated metrics. |
| `metrics_expiration` | How long unused series stay in memory before expiration. |

When a customer is reducing volume or debugging single-writer/cardinality
behavior, use the setting that actually renders into the connector. Do not
assume a key named like an upstream field exists in the Helm values schema.

## Cardinality landmines

- **`k8s.pod.name` as a span-metric data-point dimension** — explodes
  proportional to pod churn. Keep it on the **resource** (Infrastructure
  Explorer needs it there) and include it in the connector's `dimensions`
  only when it prevents cross-writer collisions, such as one collector
  agent per Kubernetes node writing span metrics for pods of the same
  service on different nodes.
- **Raw `url.path` (with parameters)** as a metric label — use
  `http.route` (the templated form) instead.
- **`url.full` or full query strings** as a metric label — safe for trace
  detail, not for RED metric dimensions.
- **`user.id` / session IDs** — span scope only. They explode metrics.

## Product label contract

APM and Database Catalog query generated labels, not raw span attributes.
When a product tab is empty, inspect both forms:

- raw span attributes before `spanmetrics`;
- raw OTLP metric datapoint attributes after `spanmetrics`;
- Prometheus-normalized labels in query/UI paths.

Examples:

- `http.response.status_code` can become `http_response_status_code`.
- `db.system` can become `db_system`.
- `service.name` can become `service_name`.
- `otel.metric.overflow` becomes `otel_metric_overflow`.

If the raw attribute exists but the generated label is blank, the bridge is
probably in the wrong path or the connector dimensions do not include that
source.

## References

- [Coralogix: Span Metrics (Published, March 2026)](https://coralogix.com/docs/user-guides/apm/getting-started/span-metrics/)
- [Coralogix: Span Metrics — recommended configuration](https://coralogix.com/docs/user-guides/apm/getting-started/span-metrics-recommended-configuration/)
- [Coralogix: Span Metrics — cardinality limits](https://coralogix.com/docs/user-guides/apm/getting-started/span-metrics-cardinality-limits/)
- [Coralogix: Compact Span Metric](https://coralogix.com/docs/user-guides/apm/getting-started/using-compact-span-metric/)
- [Coralogix: Aligning Coralogix and OTel naming conventions](https://coralogix.com/docs/user-guides/apm/getting-started/aligning-coralogix-and-otel-naming-conventions/)
- [Coralogix telemetry-shippers: k8s Helm spanMetrics transform statements](https://github.com/coralogix/telemetry-shippers/blob/master/otel-integration/k8s-helm/README.md#L1798-L1825)
- [Coralogix telemetry-shippers: k8s Helm spanMetrics values](https://github.com/coralogix/telemetry-shippers/blob/master/otel-integration/k8s-helm/values.yaml#L184-L208)
- [Upstream OTel Span Metrics connector](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/connector/spanmetricsconnector/README.md)
- [apm-service-catalog.md](apm-service-catalog.md) — the span attributes
  these labels are derived from
- [database-monitoring.md](database-monitoring.md) — the database-specific
  span attributes
