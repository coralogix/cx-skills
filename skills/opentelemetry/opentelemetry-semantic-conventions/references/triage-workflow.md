# Semconv Triage Workflows

Use these workflows when a Coralogix surface changed after an OpenTelemetry
upgrade, new instrumentation, or collector topology change and the first
question is "which attribute, scope, or generated metric shape does this
product consume?"

## Triage a new OTel semconv break

1. Identify the exact version jump and the changed names / values from the
   OTel changelog, semantic-convention release notes, schema files, or
   collector component release notes. Check whether incoming OTLP carries a
   `schema_url`; it can explain which semconv version produced the signal.
2. Identify the Coralogix surface that changed: APM Service Catalog,
   Transactions, Error/API Error Tracking, Database Catalog, Span Metrics
   labels, Infrastructure Explorer / Resource Catalog, AI Center, Custom
   Metrics, or a dashboard/query built from receiver metrics.
3. Inspect a raw sample at the collector with the `debug` exporter before
   and after any transforms. Look for empty labels, rows moving to
   `unknown`, blank drilldowns, sudden cardinality drops for a dimension,
   or a dashboard query that still filters on the old label.
4. Classify the break:
   - **Attribute-name rename:** mirror old and new names at the scope the
     product reads, preserving both until Coralogix backend support is
     confirmed.
   - **Attribute-value rename:** support both enum/value spellings in
     backend code where possible; use a collector transform only as a
     temporary compatibility bridge.
   - **Metric data-point attribute / generated metric label change:** bridge
     in the metrics pipeline after the receiver or connector emits the
     metric, and update dashboards / backend filters that hard-code the
     old label.
   - **Scope mismatch:** copy the value to the scope the consumer reads
     (`resource`, `span`, `log record`, or metric data point) rather than
     renaming it in place.
   - **Topology or product-path gap:** hand exact collector, Helm, Fleet,
     or SDK implementation to the owning skill after naming the required
     placement.
5. Choose the bridge location deliberately:
   - Span attributes used by APM / DB Monitoring / Span Metrics dimensions:
     traces pipeline before `spanmetrics`.
   - Generated Span Metrics labels such as status-code labels: metrics
     pipeline after `spanmetrics`.
   - Resource attributes for Infrastructure Explorer: resource context in
     every signal pipeline before export / inventory correlation.
   - GenAI span attributes: instrumentation/proxy path before trace export
     and the AI Center trace/archive path.
   - Receiver metrics such as `system.cpu.*`: metrics pipeline after the
     receiver and before export or dashboard queries.
6. Hand exact implementation to the owning skill: `opentelemetry-ottl` for
   transform syntax, `opentelemetry-collector` for pipeline / Helm / Fleet
   wiring, `opentelemetry-instrumentation` for SDK and sampler setup, and
   `core` for Coralogix app/subsystem routing.
7. After the incident is understood, add the mapping and failure symptom to
   the relevant reference file plus a committed eval case under `evals/`, so
   the next model run recognizes the same break class.

Longer term, prefer schema-aware migrations where available. OpenTelemetry
Telemetry Schemas use `schema_url` to identify the producer schema and can
describe transformations between semconv versions. That does not remove the
need for Coralogix-side support or temporary collector bridges when a backend
still hard-codes the old shape.

## Pick attributes for a new HTTP server span

1. Set the top-level span kind to `SERVER` (`SpanKind.SERVER` in SDKs; do not
   set a span attribute named `span.kind`).
2. Always set on the span: `http.request.method`, `url.path`, `url.scheme`.
3. Set when known: `http.response.status_code`, `http.route` (the templated
   route, strongly recommended because APM operation names come from this),
   `server.address`, `server.port`, and `error.type` when status is ERROR.
4. Recommended where available: `network.protocol.version`,
   `user_agent.original`, and `client.address`.
5. Do not use `url.full` on a server span. It is for outbound HTTP client
   spans, and server-side full URLs can explode cardinality.

`http.request.method` is the current stable OpenTelemetry HTTP attribute for
new native HTTP metrics and spans. Coralogix Span Metrics still reads legacy
`http.method` as a connector source dimension, so Helm bridges
`http.request.method` to `http.method` before `spanmetrics`; self-managed
collector users need the equivalent bridge.

## Pick attributes for a new database client span

1. Set the top-level span kind to `CLIENT` (`SpanKind.CLIENT` in SDKs; do not
   set a span attribute named `span.kind`).
2. For new instrumentation, set the stable OpenTelemetry DB attributes on
   the span: `db.system.name`, `db.namespace` when available,
   `db.operation.name` when available, sanitized / parameterized
   `db.query.text` when it is safe to collect, and `server.address` or
   `network.peer.address` for the remote database host.
3. Before APM / Span Metrics consume the spans, mirror those stable source
   attributes into the current Coralogix-supported target names:
   `db.system`, `db.name`, `db.operation`, `db.statement`, and
   `net.peer.name`. All five target names are required by Coralogix Database
   Monitoring today.

## Diagnose a missing operation in APM Service Catalog

1. Confirm `service.name` is on the resource, not the span.
2. Confirm the top-level span kind is `SERVER` or `CLIENT` as appropriate,
   not `INTERNAL`. A span attribute named `span.kind` is not enough; Span
   Metrics and dependency views use the real span kind field.
3. Confirm an operation-name attribute is present:
   - HTTP server: `http.route`.
   - Database: `db.operation`.
   - RPC: `rpc.method`.
   - Messaging: `messaging.operation`.
4. If the right attributes are on the span but the catalog is still empty,
   check Span Metrics. The connector might be dropping the label, sampling
   might run before `spanmetrics`, or cardinality might be overflowing.

## Diagnose missing pods / hosts in Infrastructure Explorer

1. Confirm the Resource Catalog / Infra Explorer setup is enabled. For
   self-managed collectors, also confirm the inventory path exists:
   `k8sobjects` receiver on the cluster-collector,
   `resourcedetection/resource_catalog`, and the dedicated
   `coralogix/resource_catalog` exporter with
   `x-coralogix-ingress: metadata-as-otlp-logs/v1`.
2. Inspect a sample log / metric / span at the receiver. Confirm the required
   Kubernetes or host/cloud identity values are resource attributes, not
   span/log fields.
3. If only some signals are correlated, the processors are likely missing
   from one of the metrics / traces / logs pipelines. Apply the same
   enrichment chain across all three.
4. For hosts, check `host.name` plus `cloud.*` attributes from
   `resourcedetection`.

## Resolve a resource-scope routing mismatch

1. The Coralogix exporter reads `application_name_attributes` and
   `subsystem_name_attributes` from resource attributes only. Confirm with
   the collector `debug` exporter at detailed verbosity.
2. If the value lives on a log record / span, the best fix is to set it at
   resource scope in the SDK or with the `resource` / `resourcedetection`
   processor.
3. If a temporary copy-up is needed, diagnose the source and destination
   scope here, then hand the exact OTTL statement to `opentelemetry-ottl`.
4. If the attribute is on the resource but the exporter still falls back to
   the static name, check attribute-chain ordering in the `core` skill.

## Worked diagnosis examples

If the collector `debug` exporter shows a log record attribute
`attributes["subsystem"]="ingest"` but the Coralogix exporter reads
`subsystem_name_attributes` from resource scope, answer:

- diagnosis: scope mismatch; log-record attributes are invisible to the
  exporter routing chain;
- semantic fix: set or copy the value to `resource.attributes["subsystem"]`
  before export;
- handoff: exact `set(...)` syntax and context selection belong to
  `opentelemetry-ottl`, while pipeline placement belongs to
  `opentelemetry-collector`.

If Database Monitoring is empty and a debug span has
`db.system.name="microsoft.sql_server"` plus `db.query.text` but no
`db.system`, answer:

- diagnosis: stable OTel DB names are present, but current Coralogix paths
  still require the compatibility names;
- semantic fix: mirror `db.system.name` to `db.system`, `db.namespace` to
  `db.name`, `db.operation.name` to `db.operation`, `db.query.text` to
  `db.statement`, and `server.address` / `network.peer.address` to
  `net.peer.name`;
- handoff: exact transform syntax and placement belong to
  `opentelemetry-ottl` / `opentelemetry-collector`.

If Span Metrics emits `otel.metric.overflow="true"` or
`otel_metric_overflow="true"`, answer:

- diagnosis: expected overflow fallback after the cardinality cap, not a
  collector bug;
- semantic fix: reduce source dimensions such as raw `url.path`, UUID span
  names, blanket `k8s.pod.name`, or `k8s.pod.ip`; prefer bounded
  `http.route`;
- handoff: exact metric processor or Helm values belong to
  `opentelemetry-collector`.
