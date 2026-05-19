# Common OTTL Transformations

Patterns drawn from real customer configurations for span naming, semantic convention
migration, attribute extraction, and log body manipulation.

---

## Span naming from HTTP method + route

Generic span names like `HTTP GET` or `http.request` lose HTTP context. Reconstruct from
method + route. Use `Split` to strip query strings from `http.target`:

```yaml
processors:
  transform:
    error_mode: ignore
    trace_statements:
      - context: span
        conditions:
          - attributes["span.kind"] == "server" or attributes["span.kind"] == "SPAN_KIND_SERVER"
        statements:
          # Prefer explicit http.route if present
          - set(name, Concat([attributes["http.request.method"], attributes["http.route"]], " ")) where attributes["http.route"] != nil and attributes["http.request.method"] != nil

          # Fallback: extract path from http.target (strips ?query=string)
          - set(attributes["http.route"], Split(attributes["http.target"], "?")[0]) where attributes["http.route"] == nil and attributes["http.target"] != nil
          - set(name, Concat([attributes["http.request.method"], attributes["http.route"]], " ")) where attributes["http.route"] != nil and attributes["http.request.method"] != nil

          # Old convention fallback (http.method / http.url)
          - set(name, Concat([attributes["http.method"], attributes["http.route"]], " ")) where attributes["http.route"] != nil and attributes["http.method"] != nil

          # Guard: set a meaningful fallback if name is still generic
          - set(name, attributes["http.route"]) where name == "http.request" or name == "HTTP GET" or name == "HTTP POST"
```

---

## Span name from database query summary

Replace raw database span names with a readable query summary attribute when available:

```yaml
trace_statements:
  - context: span
    conditions:
      - attributes["db.query.summary"] != nil
    statements:
      - set(name, attributes["db.query.summary"])
```

---

## Database attribute normalization (fallback chain)

Database spans from different systems (SQL, MongoDB, Redis, Cassandra, DynamoDB) use
different attribute names. Map them to `db.namespace` and `db.collection.name`:

```yaml
processors:
  transform:
    error_mode: silent
    trace_statements:
      - context: span
        conditions:
          - attributes["db.system"] != nil
        statements:
          # db.namespace: pick the first available source
          - set(attributes["db.namespace"], attributes["db.name"])         where attributes["db.namespace"] == nil and attributes["db.name"] != nil
          - set(attributes["db.namespace"], attributes["server.address"])   where attributes["db.namespace"] == nil and attributes["server.address"] != nil
          - set(attributes["db.namespace"], attributes["net.peer.name"])    where attributes["db.namespace"] == nil and attributes["net.peer.name"] != nil
          - set(attributes["db.namespace"], attributes["db.system"])        where attributes["db.namespace"] == nil

          # db.collection.name: varies by database system
          - set(attributes["db.collection.name"], attributes["db.sql.table"])                        where attributes["db.collection.name"] == nil and attributes["db.sql.table"] != nil
          - set(attributes["db.collection.name"], attributes["db.mongodb.collection"])               where attributes["db.collection.name"] == nil and attributes["db.mongodb.collection"] != nil
          - set(attributes["db.collection.name"], attributes["db.cassandra.table"])                  where attributes["db.collection.name"] == nil and attributes["db.cassandra.table"] != nil
          - set(attributes["db.collection.name"], attributes["db.elasticsearch.path_parts.index"])   where attributes["db.collection.name"] == nil
          - set(attributes["db.collection.name"], attributes["db.cosmosdb.container"])               where attributes["db.collection.name"] == nil
          - set(attributes["db.collection.name"], attributes["aws.dynamodb.table_names"])            where attributes["db.collection.name"] == nil
          - set(attributes["db.collection.name"], attributes["db.namespace"])                        where attributes["db.collection.name"] == nil and attributes["db.system"] == "redis"
```

---

## Extract table name from raw SQL statement

When `db.sql.table` is not populated, extract it from the raw SQL string using named capture groups:

```yaml
trace_statements:
  - context: span
    conditions:
      - attributes["db.sql.table"] == nil
      - attributes["db.statement"] != nil
    statements:
      - set(attributes["db.sql.table"], ExtractPatterns(attributes["db.statement"], "(?i)(?:update|insert\\s+into|delete\\s+from|select[\\s\\S]+?from)\\s+['\"]?(?P<table>[a-zA-Z_][a-zA-Z0-9_]*)['\"]?")["table"])
```

---

## HTTP semantic convention migration (v1 → v2)

OpenTelemetry HTTP semantic conventions changed in v2. Instrumentation libraries may emit
either version. Use `transform` as a compatibility shim:

```yaml
processors:
  transform:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          # Method: http.method → http.request.method
          - set(attributes["http.request.method"], attributes["http.method"]) where attributes["http.request.method"] == nil and attributes["http.method"] != nil

          # Status code: http.status_code → http.response.status_code
          - set(attributes["http.response.status_code"], attributes["http.status_code"]) where attributes["http.response.status_code"] == nil and attributes["http.status_code"] != nil

          # URL: http.url → url.full
          - set(attributes["url.full"], attributes["http.url"]) where attributes["url.full"] == nil and attributes["http.url"] != nil

          # Auto-set span status from HTTP response code
          - set(status.code, STATUS_CODE_ERROR) where attributes["http.response.status_code"] != nil and attributes["http.response.status_code"] > 399
```

---

## Prometheus metric name normalization

Remove the `_total` suffix that Prometheus adds — it becomes redundant after ingestion in
most backends:

```yaml
metric_statements:
  - context: metric
    statements:
      - replace_pattern(name, "_total$", "")
```

---

## Log body operations

**Always guard with `IsMap(body)` before indexing into log body fields.**
A non-map body (plain string, empty) causes `INVALID_ARGUMENT` without the guard.

```yaml
log_statements:
  - context: log
    conditions:
      - IsMap(body)
    statements:
      # Keep only fields needed — discard the rest
      - keep_keys(body, ["message", "level", "timestamp", "trace_id", "span_id", "error"])

      # Promote a body field to a log attribute
      - set(attributes["log.level"], body["level"]) where body["level"] != nil

      # Mask sensitive values within the body map
      - replace_pattern(body["user_email"], "^(.+)$", "[REDACTED]") where body["user_email"] != nil
```

---

## Parsing a JSON string body with ParseJSON

When the log body arrives as a **JSON string** (not an already-parsed map), `IsMap(body)` returns
false and body indexing fails. Use `ParseJSON()` to convert the string to a map first.

**Key distinction**: `IsMap(body)` guards map indexing on a pre-parsed map body. `IsString(body)` +
`ParseJSON()` handles a raw JSON string that the receiver has not yet parsed. Both patterns are
needed depending on what your log receiver produces.

```yaml
log_statements:
  - context: log
    conditions:
      - IsString(body)
    statements:
      # Merge all JSON fields from the body string into log attributes
      - merge_maps(attributes, ParseJSON(body), "insert")

  - context: log
    conditions:
      - IsMap(body)
    statements:
      # Body is already a parsed map — index directly
      - set(attributes["trace_id"], body["trace_id"]) where body["trace_id"] != nil
```

To extract a single field inline without merging the whole body:

```yaml
log_statements:
  - context: log
    statements:
      - set(attributes["trace_id"], ParseJSON(body)["trace_id"]) where IsString(body) and ParseJSON(body)["trace_id"] != nil
```

`merge_maps` strategies: `"insert"` (add only, don't overwrite), `"update"` (overwrite only existing),
`"upsert"` (add and overwrite).

---

## Parsing and setting log timestamps

OTTL can set a log record's event timestamp from `context: log`. The destination is `time`
for a `time.Time` value or `time_unix_nano` for an epoch-nanosecond integer. Do not use a
made-up `timestamp` path.

```yaml
processors:
  transform/log-time:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(time, Time(attributes["event_time"], "%Y-%m-%dT%H:%M:%S%z")) where IsString(attributes["event_time"])
```

`Time(value, format, optional_location, optional_locale)` parses a string using the format
you provide. Guard with `IsString`, set `error_mode: ignore` or `silent`, and make the
format/time zone explicit. A mismatch between the incoming timestamp string and the format,
missing time-zone data, or invalid input values will produce transform errors.

---

## Type-safe numeric comparisons

Attribute values can arrive as strings, integers, or doubles depending on the receiver and
source library. Do not compare `attributes["retries"] > 3` until you know the value is numeric
or have converted it.

```yaml
trace_statements:
  - context: span
    statements:
      - set(attributes["retry_bucket"], "high") where IsInt(attributes["retries"]) and attributes["retries"] > 3
      - set(attributes["retry_bucket"], "high") where IsString(attributes["retries"]) and Int(attributes["retries"]) > 3
```

Use `Double(...)` instead of `Int(...)` for decimal values, and keep `error_mode: ignore`
or a stricter `where` guard around conversions when malformed strings are possible.

---

## Building dynamic values with Concat and Split

```yaml
trace_statements:
  - context: span
    statements:
      # Build span name from method + route
      - set(name, Concat([attributes["http.request.method"], " ", attributes["http.route"]], ""))

      # Build a compound key
      - set(attributes["db.operation.full"], Concat([attributes["db.operation.name"], ".", attributes["db.collection.name"]], ""))

log_statements:
  - context: log
    statements:
      # Extract the path component from a full URL (strip query string)
      - set(attributes["http.path"], Split(attributes["http.url"], "?")[0]) where attributes["http.url"] != nil

      # Extract first segment of a log source path
      - set(attributes["log.source"], Split(attributes["log.file.path"], "/")[1]) where attributes["log.file.path"] != nil
```

---

## Setting span status from attributes

```yaml
trace_statements:
  - context: span
    statements:
      # Mark as error if HTTP status >= 400
      - set(status.code, STATUS_CODE_ERROR) where attributes["otel.status_code"] == nil and attributes["http.response.status_code"] != nil and attributes["http.response.status_code"] > 399
      # Mark as ok if status < 400
      - set(status.code, STATUS_CODE_OK) where attributes["otel.status_code"] == nil and attributes["http.response.status_code"] != nil and attributes["http.response.status_code"] < 400
```

Prefer the span-context enum constants `STATUS_CODE_UNSET`, `STATUS_CODE_OK`, and
`STATUS_CODE_ERROR` over raw numbers. For checks, write conditions like
`status.code == STATUS_CODE_ERROR` in `context: span`.

---

## Injecting environment variables as resource attributes

Use the `resource` processor (not transform) for static values from environment variables:

```yaml
processors:
  resource/add-env:
    attributes:
      - key: deployment.environment
        value: "${env:ENVIRONMENT}"
        action: insert
      - key: collector.instance.id
        value: "${env:HOSTNAME}"
        action: insert
```

For dynamic values that require conditions or functions, use `transform/context: resource` instead.
