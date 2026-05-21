# Database Monitoring — Required Attributes

Coralogix **Database Monitoring** (UI: **APM → Database Catalog**) gives
visibility into every database that instrumented services interact with —
query times, query failures, failure rates, and per-database / per-operation
drilldowns. It is built from spans whose attributes follow the OpenTelemetry
[database client semantic conventions](https://opentelemetry.io/docs/specs/semconv/database/database-spans/).

## Coralogix-supported target attributes

The Database Catalog currently needs **all five** of these
Coralogix-supported target attributes on every database client span. If
any one is missing, the corresponding row in the Databases Grid does not
populate, and the Operations / Queries drilldowns go blank.
In support answers, list these five target names first. Treat stable/newer
OTel names such as `db.system.name`, `db.namespace`, `db.operation.name`,
`db.query.text`, `server.address`, and `network.peer.address` as bridge
inputs, not as replacements for the target set.

| Attribute | Type | Description | Example |
|---|---|---|---|
| `db.system` | string | Identifier for the database management system. | `mysql`, `postgresql`, `dynamodb`, `elasticsearch` |
| `db.name` | string | The name of the database / keyspace / index being accessed. | `customers`, `main`, `ws-alerts`, `ops` |
| `db.operation` | string | The operation being executed — SQL keyword or driver command name. | `Select`, `Update`, `Upsert`, `Bulkdelete`, `findAndModify` |
| `db.statement` | string | The database statement being executed. | `SELECT * FROM wuser_table;`, `SET mykey "WuValue"` |
| `net.peer.name` | string | Hostname or IP of the remote database. | `example.com`, `192.0.2.1` |

Source: [Database Monitoring — Coralogix](https://coralogix.com/docs/apm/database-monitoring/).
For **new instrumentation**, do not create legacy-only spans. Emit the
latest stable OpenTelemetry database attributes first, then mirror them
into the Coralogix-supported target names above until Coralogix APM reads
the stable names directly.

## Current DB semconv compatibility bridge

Do not ask customers to downgrade their SDKs. Keep the stable OTel
attributes as the primary source, but mirror them into the names Coralogix
APM / Database Catalog reads today before Span Metrics consumes the spans.
A complete answer must say the newer names are inputs to the bridge: the
bridge still writes `db.system`, `db.name`, `db.operation`, `db.statement`,
and `net.peer.name` for the current Coralogix Database Catalog path.

| Stable / newer OTel source | Coralogix-supported target | Why |
|---|---|---|
| `db.system.name` | `db.system` | DBMS identifier used by Database Catalog and the `db_system` Span Metrics label |
| `db.namespace` | `db.name` | database / keyspace / index row grouping |
| `db.operation.name` | `db.operation` | operation drilldown grouping |
| `db.query.text` | `db.statement` | query drilldown and trace detail |
| `server.address` or `network.peer.address` | `net.peer.name` | database host drilldown |

### DB system value compatibility

Attribute names are not the only compatibility point. Some newer
instrumentation emits newer DBMS values under `db.system.name`, for example
`microsoft.sql_server`, while existing Coralogix UI grouping or icons may
still expect older `db.system` values such as `mssql`.

When a database row is present but icon/grouping/filter behavior is wrong:

1. Compare both the attribute name and the value.
2. Preserve the stable source attribute for future compatibility.
3. Add a temporary product compatibility mapping only where the current
   Coralogix surface requires it.
4. Prefer product/backend support for both values over asking customers to
   downgrade or delete stable semconv attributes.

Minimal OTTL shape, to be adapted by the `opentelemetry-ottl` skill:

```yaml
processors:
  transform/db_semconv_compat:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          - set(attributes["db.system"], attributes["db.system.name"]) where attributes["db.system"] == nil and attributes["db.system.name"] != nil
          - set(attributes["db.name"], attributes["db.namespace"]) where attributes["db.name"] == nil and attributes["db.namespace"] != nil
          - set(attributes["db.operation"], attributes["db.operation.name"]) where attributes["db.operation"] == nil and attributes["db.operation.name"] != nil
          - set(attributes["db.statement"], attributes["db.query.text"]) where attributes["db.statement"] == nil and attributes["db.query.text"] != nil
          - set(attributes["net.peer.name"], attributes["server.address"]) where attributes["net.peer.name"] == nil and attributes["server.address"] != nil
          - set(attributes["net.peer.name"], attributes["network.peer.address"]) where attributes["net.peer.name"] == nil and attributes["network.peer.address"] != nil
```

Put this in the traces pipeline before Span Metrics / APM derive catalog
metrics. This is current Coralogix compatibility, not broad legacy
migration coverage.

## Span shape — what the catalog reads

For each database client span:

1. Top-level span kind = `CLIENT`. Database calls instrumented with
   `INTERNAL` kind do not appear in dependency views. Do not set a span
   attribute named `span.kind`; use the SDK `SpanKind.CLIENT` / collector
   span `kind` field.
2. Stable OpenTelemetry DB attributes on the **span** for new
   instrumentation, plus the five Coralogix-supported mirror attributes
   above while Coralogix APM still requires them.
3. The standard service identity attributes on the **resource** —
   `service.name`, `service.version`, etc. (see
   [apm-service-catalog.md](apm-service-catalog.md)).

## What the catalog surfaces

- **Databases Grid** — aggregates by database name (`db.name`). Filter by
  any tag or process tag on the calling service.
- **Database Overview** — performance over time per database, per
  calling-operation, per query.
- **Database Operations** — query metrics grouped by `db.operation` and
  table.
- **Database Queries** — per-`db.statement` rows with span detail and
  trace links.

## Common reasons the catalog stays empty

| Symptom | Likely cause | Fix |
|---|---|---|
| Database does not appear at all | Span has wrong top-level span kind (often shown as `span.kind`, e.g. `INTERNAL` from a custom wrapper) | Ensure the auto-instrumentation library or manual span creation uses `CLIENT` for database calls; setting `attributes["span.kind"]` is not sufficient. |
| Database appears, but no operations | `db.operation` is missing | Verify the SDK / instrumentation library populates `db.operation`; some older instrumentations omit it. |
| Operations appear, but no queries | `db.statement` is missing | Some SDKs require explicit opt-in to emit statements (e.g. for redaction reasons). |
| Generic `unknown` host | `net.peer.name` not set | Add it via SDK config or via a `transform` processor at the collector. |
| Works with an older SDK, breaks after a newer SDK / eBPF upgrade | SDK now emits stable DB names such as `db.system.name`, `db.query.text`, `db.namespace`, `db.operation.name` without the Coralogix-supported mirror names | Add the current DB semconv compatibility bridge before Span Metrics / APM consume the spans. |
| eBPF / OBI spans exist but Database Catalog labels are blank | eBPF emits stable names such as `db.system.name` and `db.collection.name`, while the product path still reads `db.system`, `db.namespace`, or generated `db_system` labels | Bridge stable span attributes before Span Metrics and Database Catalog consume them; verify normal Span Metrics and DB-specific metrics both see the bridge. |
| .NET SqlClient or another SDK upgrade changes `db.system.name` value | New value spelling is not recognized by a Coralogix UI/backend path | Support both value spellings in the product path or use a temporary bridge until backend compatibility lands. |

## SpanMetrics dimensions used downstream

The Span Metrics connector emits these as label dimensions on the
generated metrics so the Database Catalog can aggregate them:
`db_namespace`, `db_operation_name`, `db_collection_name`, `db_system`.
See [spanmetrics.md](spanmetrics.md).

## References

- [Coralogix: Database Monitoring](https://coralogix.com/docs/apm/database-monitoring/)
- [OpenTelemetry: Database client spans](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)
- [OTel attribute registry — db.* namespace](https://opentelemetry.io/docs/specs/semconv/registry/attributes/db/)
- [apm-service-catalog.md](apm-service-catalog.md) — the resource-level
  attributes also required for any APM feature
- [spanmetrics.md](spanmetrics.md) — how db.* attributes become metric
  labels
