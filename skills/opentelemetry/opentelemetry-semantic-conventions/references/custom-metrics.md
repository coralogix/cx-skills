# Custom Metrics Semantic Shape

Custom Metrics issues often look like semantic-convention issues even when
the source is OTLP metrics data model behavior, generated Prometheus label
normalization, or multi-writer aggregation. Use this reference when the
customer is emitting application metrics directly rather than span-derived
Span Metrics.

## Metric identity and label rules

Metric labels should be bounded and stable. Good labels describe a small,
known vocabulary that a dashboard needs to slice by. Bad labels carry
per-user, per-request, raw URL, UUID, array, or process-instance values.

| Label type | Guidance |
|---|---|
| Business dimensions | Keep low-cardinality values such as `status`, `purpose_code`, `fetch_type`, tenant tier, or region. |
| Service identity | Prefer resource attributes such as `service.name`; avoid emitting both dotted and normalized copies as independent labels. |
| HTTP grouping | Prefer route-like labels such as `endpoint` or `http.route`; avoid full URLs and query strings. |
| Arrays | Emit one datapoint per element plus an aggregate metric instead of serializing arrays into a label. |
| Errors/outcomes | Use a tiny fixed vocabulary such as `success` / `failure` or a controlled `error_type`. |

If a metric has both `service.name` / `service.instance.id` and
`service_name` / `service_instance_id`, check whether two collection paths
are contributing identity differently. Coralogix and Prometheus-facing
paths normalize dotted labels into underscore labels, so mixed values can
create duplicate series even though the names appear related.

## Temporality and normalized names

OTLP `Sum` metrics have aggregation temporality. Coralogix can receive both
cumulative and delta streams, but support for delta does not remove
single-writer and aggregation requirements.

| Shape | Product-visible effect |
|---|---|
| Cumulative monotonic sum | Coralogix may expose a Prometheus-style name with `_1_total` appended; query with rate/increase as appropriate. |
| Delta sum from one stable writer | Can be accepted, but query behavior and aggregation must match customer intent. |
| Delta sum from multiple writers with the same labels | Can aggregate incorrectly unless writer identity is preserved or a real metrics aggregation step sums the intended streams before converting or exporting. |
| Gauge for current state | Use for point-in-time values such as queue depth; do not use gauges for event counts. |

When customers see a metric emitted as `consent_raised` but queried as
`consent_raised_1_total`, treat this as Coralogix/Prometheus normalization
for a cumulative OTLP sum, not necessarily as a source instrumentation bug.

## Multi-writer delta remediation

For delta metrics where multiple clients write the same label set:

1. Confirm the actual OTLP temporality with a collector `debug` exporter.
2. Identify which labels define the intended aggregate.
3. Decide whether the product should keep writers separate or collapse them:
   - To keep writer separation, preserve a stable writer-unique identity such
     as `service.instance.id`, process identity, host, pod, or another bounded
     resource key before conversion/export.
   - To collapse writers into one total, use an actual metrics aggregation
     operation that sums datapoints for the intended low-cardinality label
     set, such as a collector metric aggregation processor/operation. Do not
     treat `groupbyattrs` as the aggregation step; it re-associates attributes
     and resources but does not sum colliding datapoints.
4. Convert the corrected delta streams to cumulative with
   `deltatocumulative` only when the Coralogix/query path expects cumulative
   behavior.

Collector processor syntax belongs to `opentelemetry-collector`; exact OTTL
or transform syntax belongs to `opentelemetry-ottl`.

## Dotted versus normalized label troubleshooting

If the same concept appears in dotted and underscore forms:

- Check whether the source application emits OTel resource attributes while
  Prometheus/Target Allocator adds normalized labels.
- Decide the canonical identity for the metric series.
- Align values before export, or remove the duplicate label source.
- Do not let `service.instance.id` contain random UUIDs if the product wants
  stable service-level aggregates.

## Ownership boundary

This skill owns the telemetry semantics: temporality, label cardinality,
identity shape, and whether a metric is a counter/gauge/histogram.

Hand off:

- Processor ordering, metrics aggregation processor/operation YAML, and
  `deltatocumulative` YAML to `opentelemetry-collector`.
- Dashboard query rewrites to dashboard/query owners.
- SDK metric instrument choice to `opentelemetry-instrumentation` when code
  changes are needed.

## References

- OpenTelemetry metrics data model:
  https://opentelemetry.io/docs/specs/otel/metrics/data-model/
- [spanmetrics.md](spanmetrics.md) for span-derived RED metrics, which are
  a separate generated-metrics surface.
