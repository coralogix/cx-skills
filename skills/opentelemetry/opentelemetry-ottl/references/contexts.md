# OTTL Contexts

Each OTTL statement runs in a **context** that defines which telemetry object `attributes`
and other path expressions refer to. Choosing the wrong context is the most common OTTL mistake.

## Context Reference

| Context | Available in | What `attributes` means |
|---|---|---|
| `resource` | transform (log/trace/metric) | Resource-level attributes |
| `scope` | transform (log/trace/metric) | Instrumentation scope attributes |
| `log` | transform (log), filter (logs) | Log record attributes |
| `span` | transform (trace), filter (traces) | Span attributes |
| `spanevent` | transform (trace) | Span event attributes |
| `metric` | transform (metric), filter (metrics) | Metric-level fields (name, description, unit) |
| `datapoint` | transform (metric), filter (metrics) | Individual datapoint attributes |

For the full field list available in each context, see the [OTTL context documentation](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/contexts).

## Path Expressions

Within a context, paths navigate the telemetry structure using dot notation and bracket notation:

```
attributes["key"]              # record-level attributes (log/span/datapoint-level)
resource.attributes["key"]     # resource-level attributes (accessible from any context)
instrumentation_scope.name     # scope name
body                           # log body (log context only)
time                           # log event timestamp as time.Time (log context only)
time_unix_nano                 # log event timestamp as epoch nanoseconds (log context only)
severity_number                # log severity number (log context only)
name                           # span name (span context) or metric name (metric context)
status.code                    # span status code (span context)
duration                       # span duration in nanoseconds (span context)
```

Access nested maps with chained brackets:

```
attributes["http.request.headers"]["content-type"]
body["event"]["metadata"]["user_id"]
```

## The Number-One Mistake: Wrong Context for Attribute Access

In `context: log` or `context: span`, `attributes["key"]` refers to the **record-level** attribute.
Resource attributes live on the resource, not the record. Always use `resource.attributes["key"]`
to reach resource scope from a log or span context.

```yaml
# WRONG — in context: log, k8s.namespace.name lives on the resource, not the log record
# This silently sets environment to nil with no error
log_statements:
  - context: log
    statements:
      - set(attributes["environment"], attributes["k8s.namespace.name"])

# CORRECT — reach resource attributes from log context
log_statements:
  - context: log
    statements:
      - set(attributes["environment"], resource.attributes["k8s.namespace.name"])

# ALSO CORRECT — use context: resource to mutate resource attributes directly
log_statements:
  - context: resource
    statements:
      - set(attributes["environment"], attributes["k8s.namespace.name"])  # both are resource attrs
```

### Exporters that read from resource attributes

Some exporters pick their destination from attributes and read those keys **from the
resource, not the log record or span**. The most common example is the Coralogix exporter:

```yaml
exporters:
  coralogix:
    application_name_attributes: ["application"]  # read from resource.attributes
    subsystem_name_attributes:   ["subsystem"]    # read from resource.attributes
```

If the application emits these fields on the log record (`attributes["subsystem"]`,
`attributes["log.file.subsystem"]`, …), the exporter won't see them and the
application / subsystem arrive blank. The fix is **not** to rename the field in the
application or to change the exporter config — it's to copy the value up to resource
scope with OTTL:

```yaml
# Application sets attributes["log.file.subsystem"]; exporter expects resource.attributes["subsystem"]
processors:
  transform:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(resource.attributes["subsystem"], attributes["log.file.subsystem"]) where attributes["log.file.subsystem"] != nil
          # same pattern for application_name_attributes
          - set(resource.attributes["application"], attributes["service.namespace"]) where attributes["service.namespace"] != nil
```

Order matters: place the `transform` processor **before** the `coralogix` exporter in the
pipeline. The same pattern applies to any exporter that reads routing/destination keys
from resource attributes.

## Metric Context: metric vs datapoint vs resource

This is the second most common mistake. Metric attributes live at different levels:

| What you want to access/change | Context to use |
|---|---|
| Metric name, description, unit | `metric` |
| Per-datapoint attributes (labels) | `datapoint` |
| Resource attributes on the metric | `resource` |

```yaml
metric_statements:
  - context: metric
    statements:
      - replace_pattern(name, "_total$", "")                   # strip Prometheus suffix from name

  - context: resource
    statements:
      - keep_keys(attributes, ["service.name", "k8s.namespace.name"])  # trim resource labels

  - context: datapoint
    statements:
      - delete_key(attributes, "process.command_args")          # trim per-datapoint labels
```

## The `conditions:` Block

Use `conditions:` to scope an entire statement block. More efficient than adding
`where` to every individual statement.

**Multiple entries under `conditions:` are OR'd** — statements run if *any* listed
condition is true. This is the documented behavior in both the transform and
filter processors.

```yaml
# Single condition — statements run only when body is a map.
log_statements:
  - context: log
    conditions:
      - IsMap(body)
    statements:
      - keep_keys(body, ["message", "level", "trace_id"])
      - set(attributes["log.level"], body["level"])

# Two conditions — statements run if EITHER matches (OR). For strict AND,
# combine into a single boolean instead.
log_statements:
  - context: log
    conditions:
      - IsMap(body) and attributes["source"] == "application"
    statements:
      - keep_keys(body, ["message", "level", "trace_id"])
```

## The `where` Clause

Every OTTL statement can be individually guarded with a `where` condition:

```yaml
statements:
  - set(attributes["env"], "production")  where resource.attributes["k8s.namespace.name"] == "prod"
  - set(attributes["env"], "staging")     where resource.attributes["k8s.namespace.name"] == "staging"
  - set(attributes["env"], "unknown")     where attributes["env"] == nil
```

## Nil Safety

OTTL returns nil (not an error) when a path does not exist. A nil value silently propagates.
Guard before using a value:

```yaml
# Safe: set only if source exists
- set(attributes["db.namespace"], attributes["db.name"]) where attributes["db.name"] != nil

# Safe: fallback chain — first non-nil value wins
- set(attributes["db.namespace"], attributes["db.name"])         where attributes["db.name"] != nil
- set(attributes["db.namespace"], attributes["server.address"])  where attributes["db.namespace"] == nil and attributes["server.address"] != nil
- set(attributes["db.namespace"], attributes["net.peer.name"])   where attributes["db.namespace"] == nil and attributes["net.peer.name"] != nil
```

## Operators

| Operator | Example |
|---|---|
| Equality | `attributes["env"] == "prod"` |
| Inequality | `attributes["env"] != "dev"` |
| Comparison | `severity_number >= SEVERITY_NUMBER_WARN` |
| Nil check | `attributes["key"] == nil` |
| Logical and | `attributes["a"] == "x" and attributes["b"] == "y"` |
| Logical or | `attributes["env"] == "prod" or attributes["env"] == "staging"` |
| Logical not | `not IsMatch(body, "health.*")` |
| Pattern match | `IsMatch(attributes["url"], "^/api/v[0-9]+/.*")` |
| Type check | `IsMap(body)`, `IsString(attributes["retries"])`, `IsInt(attributes["retries"])` |
| Span status enum | `status.code == STATUS_CODE_ERROR` |

The full operator and literal reference is in the [OTTL grammar](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/README.md#grammar).

## Body Type Guards

`IsMap(body)` is required before map indexing. `IsString(body)` is required before string operations
on the body. Log bodies can be maps, strings, or empty — never assume the type.

```yaml
log_statements:
  - context: log
    statements:
      # Map indexing — guard with IsMap
      - keep_keys(body, ["message", "level", "trace_id"]) where IsMap(body)

      # String operations — guard with IsString
      - replace_pattern(body, "token=[^&]+", "token=REDACTED") where IsString(body)

      # Debugging: surface body type to verify what you're actually receiving
      - set(attributes["debug.body_type"], "map")    where IsMap(body)
      - set(attributes["debug.body_type"], "string") where IsString(body)
```

When `IsMap(body)` is false but the body is a JSON string, use `ParseJSON()` to convert it to a
map before indexing. See [transformations](transformations.md#parsing-a-json-string-body-with-parsejson)
for the full pattern.
