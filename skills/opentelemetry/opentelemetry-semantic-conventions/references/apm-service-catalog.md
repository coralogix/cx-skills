# APM Service Catalog — Required Attributes

Coralogix APM's Service Catalog lists every service that emits traces and the
operations each service performs. The catalog is built from **Span Metrics**
([span-metrics.md](spanmetrics.md)) — every metric series corresponds to a
unique combination of the labels listed below, and an operation only appears
if the underlying span carries the right attributes.

## What the Service Catalog needs from each span

| Field / attribute | Scope | Required for | Notes |
|---|---|---|---|
| `service.name` | resource | service identity | Without it, telemetry arrives as `unknown_service`. |
| Span kind (`span.kind` in UI / derived labels) | top-level span field | edge type | `SERVER` for inbound, `CLIENT` for outbound dependencies, `PRODUCER`/`CONSUMER` for messaging. Spans defaulting to `INTERNAL` do not contribute to the catalog. Do not set a span attribute named `span.kind`; set the SDK span kind (`SpanKind.SERVER`, `SpanKind.CLIENT`, etc.) or adjust the collector span `kind` field. |
| `http.route` | span | HTTP server operation name | Without `http.route`, every URL path is a unique operation and the catalog explodes or collapses. |
| `db.operation` | span | database operation name | See [database-monitoring.md](database-monitoring.md). |
| `rpc.method` | span | RPC operation name | Used for gRPC and other RPC frameworks. |
| `messaging.operation` | span | messaging operation name | E.g. `publish`, `receive`. |
| `peer.service` *(preferred)* / `server.address` *(fallback)* | span | downstream service identity on Service Map edges | Use `peer.service` when the downstream is uninstrumented. |

`service.name` is a **resource attribute** — set it once at the SDK or via
the `resource` / `resourcedetection` processor at the collector. Setting it
on every span duplicates data and prevents the Coralogix exporter's
`application_name_attributes` chain (which reads resource scope only) from
seeing it.

`span.kind` is shorthand for the span's top-level kind field, not an
OpenTelemetry attribute in `attributes[...]`. If manual instrumentation or
an OTTL transform writes `attributes["span.kind"] = "SERVER"` while the real
span kind remains `INTERNAL`, Span Metrics and dependency views still use the
original kind and the operation can remain absent.

For HTTP spans, be explicit about direction:

- `url.full` is for **outbound HTTP client** spans.
- Inbound HTTP **server** spans should use `url.path`, `url.scheme`, and
  templated `http.route` for low-cardinality operation grouping.
- Do not repair server-side operation names by making `url.full` a Span
  Metrics dimension; that turns raw paths and query strings into
  high-cardinality metric labels.

For stable/current/new OpenTelemetry HTTP server metric data points, use
`http.request.method`. Coralogix Span Metrics is a generated-metric surface
that may still need a pre-connector bridge to legacy `http.method` because
the connector dimension reads that source internally.

## Recommended additional resource attributes

These are not strictly required, but several APM features depend on them:

| Attribute | Powers |
|---|---|
| `service.version` | grouping APM metrics by version; deployment markers |
| `service.namespace` | optional service grouping |
| `service.instance.id` | single-writer identity (one row per process). Required when multiple OTel collectors / replicas emit the same `service.name`, otherwise their metric series collide. |
| `deployment.environment.name` | environment filter in APM and Infrastructure Explorer ownership |
| `host.name` | maps spans to hosts in Infrastructure Explorer |
| `k8s.pod.name`, `k8s.namespace.name`, `k8s.cluster.name`, and the matching workload identity (`k8s.deployment.name`, `k8s.statefulset.name`, `k8s.daemonset.name`, `k8s.job.name`, `k8s.cronjob.name`, or `k8s.replicaset.name`) | maps spans to Kubernetes resources in Infrastructure Explorer (see [infrastructure-explorer.md](infrastructure-explorer.md)); use the owner-specific workload attribute, do not invent `k8s.deployment.name` for non-Deployment workloads |

## Coralogix Transactions (`cgx.transaction`)

APM Transactions group spans into business-meaningful units using two
Coralogix-proprietary attributes:

- `cgx.transaction` — transaction identifier
- `cgx.transaction.root` — root-of-transaction marker

These are populated automatically by `CoralogixTransactionSampler` in the
SDK sampler chain — do not set them by hand. Sampler wiring is owned by
the `opentelemetry-instrumentation` skill.

### Route and span-name timing

When Transactions are enabled, route-aware span identity needs to exist
before Coralogix transaction derivation. Some frameworks expose the final
route only after routing middleware runs, while the sampler or transaction
logic may have already derived `cgx.transaction`.

If APM operations or transaction names are wrong:

1. Confirm `http.route` is present on the server span.
2. Confirm the span name uses the low-cardinality route / operation name
   before export.
3. Do not assume a collector-side span-name rewrite will repair
   `cgx.transaction`; transaction fields may already have been derived in
   the application.
4. Hand SDK/framework ordering and sampler registration to
   `opentelemetry-instrumentation`.

## Error Tracking / API Error Tracking

APM Error Tracking and API Error Tracking need the same span identity as
Service Catalog plus status dimensions that classify failures.

| Field | Scope / source | Why |
|---|---|---|
| `http.response.status_code` | span attribute, then generated metric label | HTTP error grouping and API Error Tracking status filters |
| `rpc.grpc.status_code` | span attribute, then generated metric label | gRPC error grouping |
| `status.code` / span status | top-level span status / generated status label | generic span error state |
| `exception.type` | span event | only a fallback signal when no response status was produced |

Some client/server frameworks fail before a response exists, so
`http.response.status_code` may be absent even though span status is ERROR
and exception events are present. A collector transform that maps selected
exception types to synthetic HTTP status codes is a product workaround, not
standard OpenTelemetry behavior. Use it only when the customer/product owner
accepts that mapping.

Old HTTP semantic-convention bridges such as `http.status_code` to
`http.response.status_code` should run before Span Metrics or Error
Tracking consumes spans. Generated RED metric status-code compatibility
belongs after `spanmetrics`; see [spanmetrics.md](spanmetrics.md).

## APM overview dependencies

If traces arrive but APM overview panels are empty, do not stop at
`service.name`.

Check:

- `service.name` exists at resource scope.
- catalog-eligible spans have top-level `SERVER` or `CONSUMER` span kind
  when overview panels filter to inbound/consumer traffic.
- Span Metrics is generated from the spans before sampling removes them.
- Coralogix transaction enrichment exists when the panel depends on
  `cgx.transaction` labels.

Processor placement, group-by-trace, and collector topology belong to
`opentelemetry-collector`. SDK auto-injection and `OTEL_SERVICE_NAME`
belong to `opentelemetry-instrumentation`.

## Auto-instrumentation service identity

Kubernetes auto-injection can produce traces without setting
`service.name`. Those traces may be searchable while APM service grouping is
empty or collapsed into `unknown_service`.

For auto-injected workloads, verify:

- `OTEL_SERVICE_NAME` or `OTEL_RESOURCE_ATTRIBUTES=service.name=...` is set.
- The attribute appears at **resource** scope.
- The service name is stable and not a pod name, container ID, or random
  process ID.

## Coralogix exporter routing — `cx.application.name` / `cx.subsystem.name`

The Coralogix exporter routes traces (and their derived Span Metrics) to a
Coralogix application + subsystem using a prioritised list of resource
attributes (`application_name_attributes`, `subsystem_name_attributes`).
The list is checked in order; the first attribute present on the resource
is used.

These are **resource-scope only** — record / span / data-point attributes
are invisible to the exporter. Common-mode failure: a customer sets
`subsystem` on the log record and is surprised when the exporter falls
back to the static name. Fix it by setting the value at resource scope
in the SDK / `resource` processor, or copy it up with OTTL.

Full mechanics — chart-preset defaults per distribution, the
`aws.ecs.task.family` ECS gotcha, and the `NO_APP_NAME` / `NO_SUB_NAME`
fallback — live in the `core` skill.

## References

- [Coralogix: Span Metrics (concept)](https://coralogix.com/docs/user-guides/apm/getting-started/span-metrics/)
- [Coralogix: Aligning Coralogix and OTel naming conventions](https://coralogix.com/docs/user-guides/apm/getting-started/aligning-coralogix-and-otel-naming-conventions/)
- [Coralogix: APM dependencies](https://coralogix.com/docs/user-guides/apm/features/dependencies/introduction/)
- [Coralogix: APM environment filter](https://coralogix.com/docs/user-guides/apm/features/environment-filter/)
- `core` skill — `application_name_attributes` mechanics
- `opentelemetry-instrumentation` skill — `CoralogixTransactionSampler`
