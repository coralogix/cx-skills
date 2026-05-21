# Data safety and cardinality

Use this reference when the user asks about PII/secrets, URL/span-name sanitization,
Span Metrics cardinality, `aggregation_cardinality_limit`, or expensive APM metrics.
The safe answer is layered: prevent bad telemetry at the source, sanitize before
metrics are generated, and use limits as guardrails.

## Rule of 100 for metric dimensions

If an attribute can have more than about 100 unique values, do not use it as a metric
dimension by default. Every distinct label combination creates a new time series, so
several individually "moderate" dimensions multiply into very large cardinality.

Good Span Metrics dimensions are bounded and useful for aggregation:

- `http.method`
- `http.response.status_code`
- `span.kind`
- `status_code`
- `http.route` when it is templated, such as `/users/{id}/orders/{order_id}`
- stable service/resource dimensions needed by Coralogix APM

Dangerous dimensions include:

- `url.full`, raw `url.path`, or URLs with query strings
- `user.id`, `session.id`, `request.id`, `trace_id`, `span_id`
- `customer.email`, IP addresses, tokens, API keys
- `k8s.pod.ip` and broad `k8s.pod.name` usage for Span Metrics
- raw `db.statement`, `db.query.text`, or SQL with literal values

When a customer says they need one of these for alerts or dashboards, do not just
approve it. Offer a lower-cardinality replacement first, then a targeted sanitization
plan if they must keep it.

## Span Metrics cardinality layers

1. **Instrumentation first.** Prefer `http.route` over raw URL paths. Keep IDs and
   per-request values on traces or logs, not metric labels.
2. **Sanitize before `spanmetrics`.** Normalize dynamic values in the traces pipeline
   before the `spanmetrics` connector consumes spans. For exact OTTL syntax, hand off
   to the `opentelemetry-ottl` skill.
3. **Trim dimensions.** Remove high-cardinality `spanmetrics` dimensions such as
   `url.full`, `k8s.pod.ip`, broad `k8s.pod.name`, and unnecessary custom labels.
4. **Tune histogram buckets.** Excessive buckets multiply `duration_ms_bucket` series.
   Keep buckets aligned to the user-facing latency questions.
5. **Add guardrails.** Use `aggregation_cardinality_limit` / Helm
   `spanMetrics.aggregationCardinalityLimit` to prevent unbounded growth. This is not a
   substitute for fixing bad dimensions.

In Coralogix Kubernetes Complete Observability, newer chart versions enable a default
Span Metrics cardinality limit. For custom collectors, older chart versions, or custom
`spanmetrics` connectors, verify the setting explicitly.

## Cardinality limit behavior

The `spanmetrics` connector's cardinality limit is a system guardrail. When the limit is
reached, new label combinations are collapsed into an overflow series rather than
continuing to create unique series. That protects the pipeline, but it also means the
high-cardinality dimension is no longer useful for precise breakdowns.

Say clearly:

- Raising the limit may restore visibility temporarily, but it increases memory and
  backend pressure.
- The durable fix is to remove, normalize, or scope the high-cardinality labels.
- The limit is in-memory collector state; restarts and metric expiration reset tracking.

## URL and span-name sanitization

For broad URL-like span names or URL attributes, `redactionprocessor` can be useful:

```yaml
processors:
  redaction/url_sanitizer:
    # Keep existing attributes while only applying URL/span-name sanitization.
    # Without allow_all_keys or allowed_keys, redactionprocessor drops keys that
    # are not explicitly allowed.
    allow_all_keys: true
    url_sanitizer:
      enabled: true
      attributes: ["url.full", "http.url", "url"]
      sanitize_span_name: true
```

Use it when the user wants a general URL sanitizer and accepts component maturity/risk
after checking the processor README. Validate representative before/after examples,
because broad sanitizers can over-sanitize domains or meaningful path segments.
When showing `redactionprocessor` examples for URL sanitization, include either
`allow_all_keys: true` for pass-through behavior or a deliberate `allowed_keys` list;
otherwise the processor is fail-closed and removes unspecified span/log/datapoint
attributes before export.

For targeted customer-specific patterns, use the OTTL `transform` processor before
`spanmetrics`, for example replacing IDs in `url.full`, stripping query strings, or
normalizing dynamic path segments. Do not put sanitization only in a metrics pipeline
after `spanmetrics`; by then the high-cardinality series have already been created.

## PII and secret redaction

Sensitive data should be removed, masked, or hashed before telemetry leaves the
collector. The collector skill should identify the pipeline placement and then route
exact statement authoring to the OTTL skill.

Common choices:

- Hash stable identifiers such as `user.id` with `SHA256` when correlation is still
  useful but raw values must not leave the environment.
- Mask credentials and Authorization headers with `replace_all_patterns`.
- Strip query parameters such as `token`, `api_key`, `secret`, and `password`.
- Delete attributes like `user.email` when they are not needed for support workflows.
- Guard transforms with `where` clauses such as `attributes["url.full"] != nil` or
  `IsString(body)` so malformed records do not break the pipeline.

Place redaction processors before `batch` and `coralogix`, and before any connector that
turns spans/logs into metrics. If the question is mostly about exact OTTL syntax,
switch to the `opentelemetry-ottl` skill and use its redaction/cardinality references.
