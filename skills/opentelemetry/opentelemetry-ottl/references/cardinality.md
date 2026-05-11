# Cardinality Reduction with OTTL

High cardinality is the most common reason customers add OTTL processors to their pipelines.
These patterns are drawn from real configurations.

---

## Metric cardinality: keep_keys (allowlist)

`keep_keys` removes every attribute NOT in the list. Safer than many `delete_key` calls when
you know exactly what you need.

```yaml
processors:
  transform:
    error_mode: ignore
    metric_statements:
      - context: resource
        statements:
          # Keep only the labels needed for dashboards/alerts; drop everything else
          - keep_keys(attributes, ["service.name", "k8s.namespace.name", "k8s.deployment.name"])

      - context: datapoint
        statements:
          # Scope to specific metrics using where — don't trim labels on all metrics
          - keep_keys(attributes, ["span.name", "service.name", "span.kind", "status_code", "http.method", "le"]) where name == "calls" or name == "duration"
```

---

## Metric cardinality: delete_matching_keys (bulk denylist)

Use when you want to remove a category of labels (e.g. all process or OS attributes)
without listing every individual key.

```yaml
processors:
  transform:
    error_mode: ignore
    metric_statements:
      - context: resource
        statements:
          # Remove all process, OS, host, telemetry SDK metadata — common cardinality sources
          - delete_matching_keys(attributes, "(?i)^(process|os|host|telemetry|container)\\.")
          - delete_matching_keys(attributes, "(?i)^(aws|azure|gcp)\\.")
          # Remove specific high-cardinality keys
          - delete_key(attributes, "service.instance.id")
          - delete_key(attributes, "service.version")
          - delete_key(attributes, "process.command_args")
          - delete_key(attributes, "process.command")

      - context: datapoint
        statements:
          # Datapoint attributes may have different keys than resource
          - delete_key(attributes, "process.command_args")
          - delete_key(attributes, "url.scheme")
          - delete_key(attributes, "network.protocol.version")
```

---

## Span/trace cardinality: normalize dynamic IDs in URLs and span names

Dynamic path segments (UUIDs, numeric IDs, MongoDB ObjectIds) cause unbounded cardinality in
span names and `http.url` / `http.target` attributes.

```yaml
processors:
  transform:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          # Replace UUIDs, MongoDB ObjectIds, and numeric IDs with a placeholder
          - replace_pattern(attributes["http.url"], "/([0-9a-fA-F]{24,32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9]+)(/|$|\\?)", "/:id$2")
          # Strip query strings from URLs entirely
          - replace_pattern(attributes["http.url"], "\\?.*$", "")
          # Replace numeric IDs in span name path segments
          - replace_pattern(name, "/[0-9]+(/|$)", "/:id$1")
```

### Delete span attributes by key prefix

Use `delete_matching_keys` when a whole family of span attributes should be removed, such as
captured request headers. Run it in `context: span` so `attributes` means span attributes, not
resource or metric datapoint attributes.

```yaml
processors:
  transform/remove-span-headers:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          - delete_matching_keys(attributes, "^http\\.request\\.header\\.")
```

### Example: GraphQL resolver cardinality

GraphQL spans produce names like `graphql.resolve User.profile.name`, `graphql.resolve User.posts[0]`.
Truncate to the first field access:

```yaml
trace_statements:
  - context: span
    statements:
      - replace_pattern(name, "^(graphql\\.resolve\\s+[a-zA-Z\\.]+).*$", "$1")
```

### When configured via the `otel-integration` Helm preset

If the customer is setting these patterns through `opentelemetry-agent.presets.spanMetrics.spanNameReplacePattern` in values.yaml rather than writing the `transform` processor directly, the same two escape rules that apply to any collector config apply here:

1. **Single-quote the regex** in YAML (or use a block scalar) so backslashes aren't consumed by YAML's double-quoted-string parser — Rule 1 above.
2. **Write `$1` / `$2` backreferences as `$$1` / `$$2`.** The collector's envprovider expands `$...` references at startup; `$$` is the literal-`$` escape. This is a collector rule, not a Helm rule — Helm passes `$` through unchanged.

Symptom when Rule 1 is wrong: `statement has invalid syntax: 1:28: invalid quoted string ... invalid syntax` on `helm upgrade`, even though the regex is valid in a tester. Symptom when Rule 2 is wrong: no startup error, but replacements produce empty output.

Verify with `helm template -f values.yaml | grep -A 20 transform/span_name` before upgrading. Worked example: `skills/opentelemetry/opentelemetry-collector/references/setup-kubernetes.md` — "Escape layers in collector config YAML".

---

## Span/trace cardinality: normalize db.query.text

Raw database query strings have near-infinite cardinality. Reduce to query type:

```yaml
processors:
  transform:
    error_mode: silent    # attribute-missing errors are expected here
    trace_statements:
      - context: span
        conditions:
          - attributes["db.query.text"] != nil
        statements:
          - set(attributes["db.query.text"], "INSERT")           where IsMatch(attributes["db.query.text"], "(?i)^insert\\s")
          - set(attributes["db.query.text"], "UPDATE")           where IsMatch(attributes["db.query.text"], "(?i)^update\\s")
          - set(attributes["db.query.text"], "DELETE")           where IsMatch(attributes["db.query.text"], "(?i)^delete\\s")
          - set(attributes["db.query.text"], "SELECT_AGGREGATE") where IsMatch(attributes["db.query.text"], "(?i)select.*(count|sum|max|min|exists)\\s*\\(")
          - set(attributes["db.query.text"], "SELECT_JOIN")      where IsMatch(attributes["db.query.text"], "(?i)select.*\\s+join\\s+")
          - set(attributes["db.query.text"], "SELECT_DISTINCT")  where IsMatch(attributes["db.query.text"], "(?i)^select\\s+distinct\\s+")
          - set(attributes["db.query.text"], "SELECT")           where IsMatch(attributes["db.query.text"], "(?i)^select\\s")
```

---

## Log body cardinality: keep only required fields

When log bodies are structured maps (e.g. JSON-parsed k8s events), keep only the fields
you need. **Always guard with `IsMap(body)`** — indexing a non-map body causes `INVALID_ARGUMENT`.

```yaml
processors:
  transform:
    error_mode: ignore
    log_statements:
      - context: log
        conditions:
          - IsMap(body)
        statements:
          - keep_keys(body, ["type", "action", "reason", "note", "metadata", "regarding", "eventTime"])
```

---

## Span metrics: limit dimensions with spanmetrics connector

OTTL `keep_keys` reduces attributes before the `spanmetrics` connector sees them. Apply in
the pipeline that feeds into spanmetrics, not after:

```yaml
processors:
  transform/pre-spanmetrics:
    error_mode: ignore
    trace_statements:
      - context: resource
        statements:
          - keep_keys(attributes, ["service.name", "k8s.deployment.name", "k8s.namespace.name"])
      - context: span
        statements:
          - keep_keys(attributes, ["http.method", "http.route", "http.response.status_code", "db.system", "span.kind", "status_code"])

service:
  pipelines:
    traces/spanmetrics:
      receivers: [forward/spans]
      processors: [transform/pre-spanmetrics]
      exporters: [spanmetrics]
```

You can also configure the `spanmetrics` connector's `dimensions:` directly to limit which
attributes become metric labels — that is the preferred approach when the connector supports it.
