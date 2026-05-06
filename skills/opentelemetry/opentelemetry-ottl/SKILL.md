---
name: opentelemetry-ottl
description: >
  OpenTelemetry Transformation Language (OTTL) for OTel Collector pipelines. Use when
  writing or debugging OTTL statements in the transform processor, filter processor, or
  routing connector in any collector configuration — context selection, path expression
  mistakes (`attributes` vs `resource.attributes`), `error_mode`, cardinality reduction
  with `keep_keys`, JSON body handling with `ParseJSON`, PII redaction with `SHA256` /
  `replace_pattern`, and span naming. Not for receiver/exporter connectivity, DNS,
  pipeline wiring, or telemetry that never reaches the processor — those are infra
  problems, not OTTL problems.
license: Apache-2.0
metadata:
  version: "1.0.0"
  integration: ottl
  signals:
    - logs
    - metrics
    - traces
  deployment:
    - kubernetes
    - helm
    - docker
    - ecs
    - aws
  triggers:
    description: >
      Load when the user is writing or debugging OTTL statements — transform processor
      statements, filter processor conditions, or routing connector table entries in any
      OTel Collector configuration.
    always: false
    file_patterns:
      - "**/otel-collector*.yaml"
      - "**/collector-config*.yaml"
      - "**/otelcol*.yaml"
      - "**/*collector*.yaml"
      - "**/values*.yaml"
    config_keys:
      - "transform:"
      - "log_statements:"
      - "trace_statements:"
      - "metric_statements:"
      - "log_record:"
      - "filter:"
    keywords:
      - ottl
      - transform processor
      - filter processor
      - otel transformation
      - log_statements
      - trace_statements
      - metric_statements
      - "where resource.attributes"
      - "set(attributes"
      - redact
      - pii
      - mask
      - ParseJSON
      - SHA256
  docs: https://opentelemetry.io/docs/collector/transforming-telemetry/
  repo: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/pkg/ottl
---

# OTTL

OpenTelemetry Transformation Language (OTTL) transforms, filters, and routes telemetry inside an
OTel Collector pipeline without modifying application code. Load this skill when writing or
debugging OTTL statements in the transform processor, filter processor, or routing connector.

## When to Use This Skill

| Use case | What to do |
|---|---|
| Change values or fields conditionally | `transform` processor with the correct context |
| Drop telemetry entirely (match = drop) | `filter` processor |
| Set static resource attributes everywhere | `resource` processor — simpler than OTTL |
| Copy a resource field down to spans or logs | `transform` with the correct context |
| Route telemetry to different pipelines | `routing` connector |
| Reduce metric or trace cardinality | `transform` with `keep_keys` / `delete_matching_keys` → [references/cardinality.md](references/cardinality.md) |
| Redact or pseudonymize PII | `transform` with `SHA256` / `replace_all_patterns` → [references/redaction.md](references/redaction.md) |
| Debug no data, DNS, receiver/exporter issues, or pipeline wiring | Not an OTTL problem — say so before going further |

Reference material for each topic lives under [`references/`](references/) and is listed in the [References](#references) footer at the bottom of this file. When the question involves a specific processor, context, or function you have not recently reviewed — or when the user pastes a Collector error — consult the matching reference file before answering. One or two targeted reads beat guessing from memory.

## Key Concepts

### Contexts and path expressions

`context:` determines what `attributes` means. In `context: resource`, `attributes["k"]` is a resource attribute. In `context: log` or `context: span`, `attributes["k"]` is the record-level attribute — use `resource.attributes["k"]` to reach the resource. Wrong context = silent nil, no error. → [references/contexts.md](references/contexts.md)

| Signal | Valid contexts |
|---|---|
| logs | `resource`, `scope`, `log` |
| traces | `resource`, `scope`, `span`, `spanevent` |
| metrics | `resource`, `scope`, `metric`, `datapoint` |

Metric-level edits (name, description, unit) belong in `context: metric`; per-series label/attribute edits belong in `context: datapoint`. Mixing the two in one block means one of them silently no-ops. → [references/contexts.md](references/contexts.md)

### Error modes

| Mode | Behavior |
|---|---|
| `propagate` (default) | Any OTTL runtime error halts the pipeline — **causes data loss** |
| `ignore` | Log the error, skip the statement, continue the pipeline — **use in production** |
| `silent` | Skip the statement and suppress error logging |

Set `error_mode` explicitly on every `transform` and `filter` processor — the default
(`propagate`) halts the whole pipeline on the first runtime error (missing optional
field, wrong type, indexing a nil), silently dropping every subsequent record. The fix
for a pipeline that "goes silent after one failure" is almost always the missing
`error_mode` key:

```yaml
processors:
  transform:
    error_mode: ignore          # log, skip the statement, continue the pipeline
    log_statements:
      - context: log
        statements:
          - set(attributes["env"], resource.attributes["deployment.environment"])
```

### Error patterns

Map the Collector message to a root cause before proposing a fix:

| Collector message | Root cause | First action |
|---|---|---|
| `INVALID_ARGUMENT` | Type mismatch, invalid function input, or invalid path for the active context | Add nil/type guards; confirm active context |
| `... cannot be indexed` | Indexing a non-map value — string or empty body | Add `IsMap(body)` guard before body indexing |
| `segment "..." is not a valid path` | Wrong context or field not available in the chosen context | Switch to the correct context; check path reference |
| `one or more paths were modified to include their context prefix` | Bare `attributes[...]` where explicit prefixes are required | Rewrite with `resource.attributes`, `datapoint.attributes`, etc. |
| `statement has invalid syntax: ... invalid quoted string` | YAML + OTTL quoting collision — the string was consumed by the YAML parser before reaching OTTL | Use YAML single quotes outside and OTTL double quotes inside → [references/processors.md](references/processors.md#yaml--ottl-quoting-collision) |
| Statement loads but has no visible effect | Condition never matches, wrong signal block, or processor in the wrong pipeline stage | Surface debug attributes to prove matching; verify pipeline placement |

### Canonical pipeline shape

Full annotated example of a `transform` + `filter` pipeline (log/trace/metric
statements, `error_mode`, `conditions: [IsMap(body)]`, filter-before-transform
ordering) lives in [references/processors.md](references/processors.md).

## Common Workflows

### 1. Debug an OTTL statement

1. Confirm the problem is actually OTTL — not component choice, pipeline wiring, or infrastructure.
2. Identify the signal (logs / traces / metrics) and the specific context.
3. Match the exact error text against the **Error patterns** table above.
4. Check for missing nil or type guards (`IsMap`, `IsString`, `!= nil`).
5. Check for the wrong context prefix (`attributes` vs `resource.attributes`).
6. Check `conditions:` semantics or tail sampling policy ordering.
7. Only then propose the corrected statement and minimal YAML.

### 2. Promote a JSON log body to attributes

When the body arrives as a raw JSON string (`IsMap(body)` is false), guard with
`IsString(body)` and parse with `ParseJSON`. Prefer `IsString(body)` over
`not IsMap(body)` — it is the affirmative check and avoids matching empty/nil
bodies.

```yaml
- context: log
  conditions:
    - IsString(body)          # body is a JSON string (affirmative guard)
  statements:
    # Promote every top-level JSON field into attributes
    - merge_maps(attributes, ParseJSON(body), "insert")

    # Or lift specific fields only:
    - set(attributes["user_id"],    ParseJSON(body)["user_id"])    where ParseJSON(body)["user_id"]    != nil
    - set(attributes["request_id"], ParseJSON(body)["request_id"]) where ParseJSON(body)["request_id"] != nil
```

`ParseJSON` is a Converter — it returns a value but has no side effect of its own,
so it must be wrapped in an Editor (`set`, `merge_maps`). A standalone
`ParseJSON(body)` line loads without errors and does nothing. → [references/transformations.md](references/transformations.md)

### 3. Reduce metric cardinality

```yaml
- context: datapoint
  statements:
    - keep_keys(attributes, ["service.name", "http.route", "http.response.status_code"])
    - delete_matching_keys(attributes, "^k8s\\.pod\\.uid$")
```

Prefer `keep_keys` (allowlist) over many `delete_key` calls (blocklist). → [references/cardinality.md](references/cardinality.md)

### 4. Feed an exporter that reads resource attributes

Exporters that pick a destination from attributes — most notably the Coralogix exporter's
`application_name_attributes` and `subsystem_name_attributes` — read from **resource**
attributes, not log-record or span attributes. If the source value lives on the record,
copy it up to the resource from `context: log` (or `context: span`) with
`set(resource.attributes[...], attributes[...])`. Don't rename the field in the
application and don't change the exporter config.

Full pattern (both attribute pairs, `error_mode`, and pipeline ordering) is in
→ [references/contexts.md](references/contexts.md#exporters-that-read-from-resource-attributes).

### 5. Redact PII across attributes

```yaml
- context: log
  statements:
    - set(attributes["user.id"], SHA256(attributes["user.id"])) where attributes["user.id"] != nil
    - replace_all_patterns(attributes, "value", "(?i)bearer\\s+[a-z0-9._-]+", "bearer ***")
```

`SHA256` preserves correlation without exposing the raw identifier. `replace_all_patterns` redacts across every attribute value without listing each key. → [references/redaction.md](references/redaction.md)

## Best Practices

### Pipeline and ordering

1. **Filter before transform.** Don't spend CPU transforming records that will be dropped.
2. **Set `error_mode: ignore` explicitly.** The default `propagate` causes data loss on any runtime error.
3. **Use `conditions:` to scope a block.** Statements run when any listed condition matches (OR semantics) — cheaper than a `where` clause on every statement. For strict AND, combine with `a and b` or use per-statement `where`.

### Defensive OTTL

1. **Guard before indexing.** `IsMap(body)` before map access, `IsString(body)`
   before string operations, `where attributes["x"] != nil` before reading
   optional fields. An unguarded indexing into the wrong type raises
   `INVALID_ARGUMENT` and (with the default `error_mode`) halts the pipeline.
2. **`conditions:` is OR, not AND.** For strict AND, combine into one boolean
   (`a and b`) or add `where` on each statement.

### Authoring style

1. **Identify signal and context first.** Keep traces, metrics, and logs separate; use the context that matches the referenced fields.
2. **Prefer several short statements over one dense expression.** Show exact path prefixes when clarity matters.
3. **Prefer `keep_keys` over many `delete_key` calls.** An allowlist is shorter and self-documenting.

## Limitations

OTTL is not the fix for: receiver connectivity, exporter connectivity, DNS or Kubernetes service discovery, load balancing, gateway reachability, pipeline wiring mistakes, or telemetry that never reaches the processor. Say so before going further.

Scope fences:
- OTTL can only use fields exposed in the active signal and context model.
- The Collector sees telemetry payloads, not raw incoming requests — upstream HTTP headers are usually not available after receiver ingest.
- If a field is not in the active context, OTTL cannot infer or reconstruct it.

The OTTL function list evolves each Collector release. This skill covers patterns and common misuses — for current function signatures, consult the upstream docs in the **References** footer below.

## References

- **[references/contexts.md](references/contexts.md)** — OTTL contexts, path expressions, and the most common context mistakes
- **[references/processors.md](references/processors.md)** — `transform`, `filter`, and `routing` connector configuration
- **[references/filtering.md](references/filtering.md)** — Dropping logs, metrics, and spans with the filter processor
- **[references/transformations.md](references/transformations.md)** — Span naming, semconv migration, body operations, `ParseJSON`, fallback chains
- **[references/cardinality.md](references/cardinality.md)** — Reducing metric and trace cardinality with `keep_keys`, `delete_matching_keys`, `replace_pattern`
- **[references/redaction.md](references/redaction.md)** — PII masking, `SHA256` pseudonymization, token/card/auth header redaction

Upstream:
- [OTTL language spec](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/README.md)
- [ottlfuncs reference](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/ottlfuncs/README.md)
- [transform processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/transformprocessor)
- [filter processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/filterprocessor)
