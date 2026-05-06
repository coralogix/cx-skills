# OTTL Processors

Three Collector components accept OTTL expressions: the `transform` processor (mutate),
the `filter` processor (drop), and the `routing` connector (split pipelines).

---

## transform processor

The `transform` processor mutates telemetry in-place. Statements are grouped by signal type
(`log_statements`, `trace_statements`, `metric_statements`) and context.

**Always set `error_mode: ignore` or `error_mode: silent`.** The default `propagate` halts
the pipeline on any runtime error, dropping all subsequent records.

- `ignore` — logs the error and continues
- `silent` — suppresses the error and continues (use when attribute-missing errors are expected)

```yaml
processors:
  transform:
    error_mode: ignore
    log_statements:
      - context: resource
        statements:
          - set(attributes["environment"], attributes["deployment.environment"])
      - context: log
        conditions:
          - IsMap(body)
        statements:
          - keep_keys(body, ["message", "level", "timestamp", "trace_id", "span_id"])

    trace_statements:
      - context: span
        conditions:
          - attributes["http.route"] != nil
        statements:
          - set(name, Concat([attributes["http.request.method"], attributes["http.route"]], " "))

    metric_statements:
      - context: metric
        statements:
          - replace_pattern(name, "_total$", "")
      - context: resource
        statements:
          - keep_keys(attributes, ["service.name", "k8s.namespace.name", "k8s.deployment.name"])
      - context: datapoint
        statements:
          - delete_key(attributes, "process.command_args")
          - delete_key(attributes, "process.command")
```

### Editor vs Converter functions

OTTL functions split into two categories with different usage rules:

- **Editors** (lowercase first letter): `set()`, `delete_key()`, `keep_keys()`, `replace_pattern()` — modify telemetry in place, used as **statements**
- **Converters** (uppercase first letter): `IsMatch()`, `SHA256()`, `ParseJSON()`, `Concat()`, `Split()`, `ExtractPatterns()` — return a value, used as **expressions** inside statements or conditions

This means `ParseJSON(body)` alone on a statement line is invalid — it returns a map but does nothing with it. Wrap it in an editor: `merge_maps(attributes, ParseJSON(body), "insert")`.

### Commonly used transform functions

For the full, always-current list see [ottlfuncs README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/ottlfuncs/README.md):

| Function | What it does |
|---|---|
| `set(target, value)` | Set a field to a value |
| `delete_key(map, key)` | Remove a single key from a map |
| `delete_matching_keys(map, pattern)` | Remove all keys matching a regex |
| `keep_keys(map, [keys])` | Remove all keys *not* in the list (allowlist) |
| `replace_pattern(target, regex, replacement)` | Replace regex matches in a string field |
| `replace_all_patterns(map, "value", regex, replacement)` | Replace pattern in all map values |
| `merge_maps(target, source, strategy)` | Merge two attribute maps |
| `truncate_all(map, limit)` | Truncate all string values to a max length |
| `limit(map, limit, [keys])` | Cap the number of keys in a map |
| `IsMatch(value, regex)` | Boolean — does value match regex |
| `IsMap(value)` | Boolean — is value a map (use to guard body access) |
| `IsString(value)` | Boolean — is value a string |
| `ParseJSON(value)` | Parse a JSON string into a map (Converter — use inside `merge_maps` or indexing) |
| `Concat(values, separator)` | Concatenate a list of strings |
| `Split(value, delimiter)` | Split string, returns list (index with `[0]`, `[1]`, ...) |
| `Substring(value, start, length)` | Extract a substring by position |
| `ExtractPatterns(value, regex)` | Extract named capture groups, returns a map |
| `SHA256(value)` | SHA-256 hash of a string (useful for pseudonymizing PII) |
| `Int(value)` | Convert to integer |
| `String(value)` | Convert to string |

---

## filter processor

The `filter` processor **drops** records that match the given OTTL condition. A match means drop.

```yaml
processors:
  filter:
    error_mode: ignore
    logs:
      log_record:
        - severity_number < SEVERITY_NUMBER_INFO                    # drop DEBUG and TRACE
        - IsMatch(body, "^.*GET /healthz.*200.*$")                  # drop health check hits
        - resource.attributes["service.name"] == "noisy-exporter"  # drop from a specific service
        - 'IsMatch(resource.attributes["service.name"], ".(ccrecognition|monitoring).") and severity_number > 9'
    metrics:
      metric:
        - name == "go.goroutines"                                   # drop by exact metric name
        - IsMatch(name, "^go\\..*")                                 # drop all Go runtime metrics
    traces:
      span:
        - attributes["http.target"] == "/healthz"                   # drop health check spans
        - attributes["db.system"] != nil                            # drop all DB spans
        - duration < 1000000                                        # drop spans under 1ms (nanoseconds)
```

**Severity number constants** (use these instead of integers):

| Constant | Severity |
|---|---|
| `SEVERITY_NUMBER_TRACE` | 1 |
| `SEVERITY_NUMBER_DEBUG` | 5 |
| `SEVERITY_NUMBER_INFO` | 9 |
| `SEVERITY_NUMBER_WARN` | 13 |
| `SEVERITY_NUMBER_ERROR` | 17 |
| `SEVERITY_NUMBER_FATAL` | 21 |

`severity_number < SEVERITY_NUMBER_INFO` drops both TRACE and DEBUG levels.

For current constants and the full field list, see the [filter processor documentation](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/filterprocessor#ottl-syntax).

---

## routing connector

The `routing` connector splits a pipeline into multiple downstream pipelines based on OTTL
conditions. Use this when different data needs different processors or exporters.

```yaml
connectors:
  routing:
    error_mode: ignore
    default_pipelines: [traces/sampled]
    table:
      - statement: route() where attributes["force_sample"] == "true"
        pipelines: [traces/full]
      - statement: route() where resource.attributes["k8s.namespace.name"] == "prod"
        pipelines: [traces/prod]

service:
  pipelines:
    traces/ingress:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [routing]
    traces/full:
      receivers: [routing]
      exporters: [otlp/backend]
    traces/prod:
      receivers: [routing]
      processors: [tail_sampling]
      exporters: [otlp/backend]
    traces/sampled:
      receivers: [routing]
      processors: [tail_sampling]
      exporters: [otlp/backend]
```

---

## Pipeline ordering

```yaml
service:
  pipelines:
    logs:
      processors: [filter, transform, batch]
```

- **filter first** — drop unwanted records before spending CPU transforming them
- **transform after filter** — only process records that will actually be exported
- **Exception**: if you need to enrich attributes before filtering on them (e.g., add `k8sattributes` before a filter that uses `k8s.namespace.name`), put enrichment processors before `filter`
- **batch last** — always the final processor

---

## When to use attributes processor instead

For simple attribute operations (add, update, delete) without conditions, the `attributes`
processor is simpler than OTTL:

```yaml
processors:
  attributes:
    actions:
      - key: sensitive_field
        action: delete
      - key: env
        value: production
        action: insert
```

Use `transform` when you need: `where` conditions, cross-context access (`resource.attributes`
from a span context), functions like `replace_pattern`/`keep_keys`, or `conditions:` blocks.

---

## YAML + OTTL quoting collision

OTTL statements embedded in YAML have to be valid on **two** parsing layers: the
YAML parser strips its own quoting and escapes first, then the OTTL parser reads
what is left as a string literal. A `replace_pattern` regex like
`"cycle-(manager|rpa-manager)\\.[0-9a-f]{8}-..."` that works in a standalone regex
tester can fail at Collector startup with:

```
statement has invalid syntax: 1:28: invalid quoted string
```

This is a syntax error, not an OTTL bug or a bad regex — the backslashes and
quotes were consumed twice. Three concrete fixes, in order of readability:

```yaml
processors:
  transform:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          # 1. YAML single quotes outside, OTTL double quotes inside — cleanest
          - 'replace_pattern(name, "cycle-(manager|rpa-manager)\\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "cleaned-span-name")'

          # 2. YAML block scalar — backslashes survive untouched, good for very long expressions
          - >-
            replace_pattern(name,
              "cycle-(manager|rpa-manager)\\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
              "cleaned-span-name")

          # 3. YAML double quotes outside — must double every backslash to survive YAML
          - "replace_pattern(name, \"cycle-(manager|rpa-manager)\\\\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\", \"cleaned-span-name\")"
```

Rule of thumb: **YAML single quotes outside, OTTL double quotes inside.** The
OTTL string literal keeps its normal double quotes and you only escape for OTTL,
not for YAML.
