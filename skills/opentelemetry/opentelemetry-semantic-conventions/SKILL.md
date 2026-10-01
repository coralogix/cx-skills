---
name: opentelemetry-semantic-conventions
description: >
  Use when a Coralogix/OpenTelemetry issue depends on telemetry semantics:
  resource/span/metric/log attribute names, values, scopes, schemas,
  generated metric labels, or collection topology affecting product
  behavior. Trigger for missing or empty APM Service Catalog,
  Transactions, Error/API Error Tracking, Database Catalog/DB Monitoring,
  Span Metrics RED metrics, Infrastructure Explorer/Resource Catalog,
  Custom Metrics, or logs/serverless metadata, especially with
  service.name, http.route, http.response.status_code, db.system /
  db.system.name, db.namespace, k8s.*, host.*, cloud.*, resource_ttl,
  interval, otel.entity.interval, url.full, service.instance.id,
  label/cardinality, or temporality questions. Do not use for pure OTTL
  syntax, collector/Helm wiring, SDK install,
  cx.application.name/cx.subsystem.name routing, dashboards, Jira,
  version-upgrade planning, or AI Center / gen_ai.* spans (use
  ai-app-instrumentation).
license: Apache-2.0
metadata:
  version: "0.2.0"
  integration: opentelemetry
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
      Load when Coralogix/OpenTelemetry product behavior depends on telemetry
      attributes, semantic conventions, scope, generated metric labels,
      cardinality, temporality, or collection topology. Covers missing or
      empty APM, DB Monitoring, Span Metrics, Infra/Resource Catalog,
      Custom Metrics, and logs/serverless metadata; skip pure OTTL,
      collector, SDK, cx app/subsystem routing implementation, and AI
      Center / GenAI (ai-app-instrumentation).
    always: false
    file_patterns:
      - "**/*instrumentation*.py"
      - "**/*instrumentation*.js"
      - "**/*instrumentation*.ts"
      - "**/*instrumentation*.java"
      - "**/*instrumentation*.cs"
      - "**/*instrumentation*.go"
      - "**/otel-collector*.yaml"
      - "**/values*.yaml"
    config_keys:
      - "resource.attributes"
      - "service.name"
      - "db.system"
      - "spanmetrics"
      - "aggregation_cardinality_limit"
      - "k8sattributes"
    keywords:
      - semantic conventions
      - semconv
      - coralogix opentelemetry
      - resource attribute
      - span attribute
      - metric attribute
      - log record attribute
      - cardinality
      - service.name
      - db.system
      - http.route
      - span kind
      - cgx.transaction
      - infrastructure explorer
      - database monitoring
      - service catalog
      - span metrics
      - custom metrics
      - otel_metric_overflow
      - otel.metric.overflow
  docs: https://coralogix.com/docs/user-guides/apm/getting-started/aligning-coralogix-and-otel-naming-conventions/
  upstream: https://opentelemetry.io/docs/specs/semconv/
  repo: https://github.com/open-telemetry/semantic-conventions
---

# OpenTelemetry Semantic Conventions for Coralogix

Map Coralogix product behavior to the resource/span/metric/log attributes
it consumes. This top-level file routes to focused references and gives the
cross-product triage workflow; detailed product rules live in `references/`.

## Reference Map and Scope

| Use case | What to do |
|---|---|
| Pick attributes for a new HTTP / DB / RPC / messaging span | [apm-service-catalog.md](references/apm-service-catalog.md) — what each Coralogix APM feature reads; for stable/current/new HTTP metrics use `http.request.method` |
| Diagnose a missing operation in APM Service Catalog | [apm-service-catalog.md](references/apm-service-catalog.md) — service.name + span kind + operation-name attribute checklist |
| Diagnose a missing database in Database Monitoring | [database-monitoring.md](references/database-monitoring.md) — target span attributes are `db.system`, `db.name`, `db.operation`, `db.statement`, `net.peer.name`; newer names are bridge inputs |
| Handle new DB semantic-convention names such as `db.system.name` / `db.query.text` | [database-monitoring.md](references/database-monitoring.md) and [spanmetrics.md](references/spanmetrics.md) — DB bridge: `db.name` first, then `server.address`, `network.peer.name`, `net.peer.name`, `network.peer.address`, final `db.system`; include `db_calls_total` vs `calls_total` / `db_namespace` symptoms |
| Diagnose recurring cross-product gotchas | [high-signal-rules.md](references/high-signal-rules.md) — common scope, topology, cardinality, and product-path rules |
| Answer a specific "which fields / exact names" question | Always read [final-answer-checklists.md](references/final-answer-checklists.md) first — short-answer anchors that must not be inferred or paraphrased away |
| Triage a new OTel semantic-convention breaking change after an SDK / Collector upgrade | [triage-workflow.md](references/triage-workflow.md) — classify attribute-name, attribute-value, metric data-point, scope, or topology changes before choosing a bridge |
| Configure Span Metrics labels or cardinality | [spanmetrics.md](references/spanmetrics.md) — minimum labels include `span_name`, `service_name`, `span_kind`, `status_code`, `collector_instance_id`, `http_method`, `host_name`, `k8s_cluster_name`, `cgx.transaction`, `cgx.transaction.root`, `db_namespace`, `db_operation_name`, `db_collection_name`, `db_system`, `application_name`, `cx_subsystem_name`; use `k8s.pod.name` only for collision cases, not blanket defaults |
| Diagnose Span Metrics writer identity or topology | [spanmetrics.md](references/spanmetrics.md) and [associated-boundaries.md](references/associated-boundaries.md) — restore `service.instance.id` for resource-key collisions; for gateways name traceID / trace ID load balancing |
| Diagnose `otel.metric.overflow="true"` / `otel_metric_overflow="true"` series | [spanmetrics.md](references/spanmetrics.md) — expected overflow fallback, not a bug; raw OTLP vs PromQL labels; reduce source cardinality; qualify `aggregation_cardinality_limit: 0` vs Helm v0.0.203+ 100,000 default |
| Diagnose missing pods / hosts in Infrastructure Explorer | [infrastructure-explorer.md](references/infrastructure-explorer.md) — resource-scope `k8s.cluster.name`, `k8s.namespace.name`, `k8s.pod.name`, `k8s.node.name`, `k8s.container.name`, `service.name`, plus owner `k8s.deployment.name` / `k8s.statefulset.name` / `k8s.daemonset.name` / `k8s.job.name` / `k8s.cronjob.name` / `k8s.replicaset.name`; EC2 tag target is `host.name` |
| Diagnose resource metadata lifetime / Resource Catalog inventory issues | [infrastructure-explorer.md](references/infrastructure-explorer.md) — `resource_ttl`, `interval`, `otel.entity.interval`, `schema_url`, `coralogix/resource_catalog`, `x-coralogix-ingress: metadata-as-otlp-logs/v1` |
| AI Center: missing LLM rows, `gen_ai.*` attributes, prompts, cost | Not this skill — hand off to `ai-app-instrumentation`, which owns GenAI span shape, detection, and AI Center verification |
| Diagnose custom metric temporality, duplicate labels, or `_1_total` names | [custom-metrics.md](references/custom-metrics.md) — `delta` temporality, writer identity, Prometheus normalization, and low-cardinality labels |
| Diagnose Lambda/log metadata scope or EC2 tag enrichment | [logs-serverless.md](references/logs-serverless.md) — log-record vs resource scope, `cx_metadata.*`, dashboard/correlation warning, and host identity enrichment |
| Decide when semconv should hand off to another skill | [associated-boundaries.md](references/associated-boundaries.md) — `core` owns `cx.application.name` / `cx.subsystem.name`; Javaagent setup including `OTEL_RESOURCE_ATTRIBUTES` and JMX receiver belongs to instrumentation; exact `set(...)` / where / context belongs to `opentelemetry-ottl` |
| Decide whether an attribute belongs on resource, span, or metric | [Attribute placement](#attribute-placement) below |

## Attribute placement

Scope mismatches are a common reason Coralogix features stay empty while
telemetry is flowing.

| Level | Use for | Examples |
|---|---|---|
| **Resource** | producer identity / environment | `service.name`, `service.instance.id`, `deployment.environment.name`, `host.name`, `k8s.pod.name`, `cloud.region` |
| **Span** | per-operation context | `http.route`, `db.system`, `db.operation`, `db.statement`, `net.peer.name`, `rpc.method` |
| **Metric data point** | bounded dimensions | `http.request.method`, `http.response.status_code`, `db.system`, generated labels such as `span_kind` |
| **Log record** | per-log-event fields | parsed body fields, filelog parser output, request IDs |
| **Span event** | point-in-time span details | `exception.type`, `exception.message`, `exception.stacktrace` |

Exporter `application_name_attributes` and `subsystem_name_attributes` read
resource attributes only; for exact routing answers read
[final-answer-checklists.md](references/final-answer-checklists.md).

## Common Triage Flow

Use this flow when a Coralogix surface is empty or changed after an OTel
SDK / instrumentation / Collector upgrade.

1. Identify the changed OTel version, instrumentation source, and
   `schema_url` when present.
2. Identify the affected Coralogix surface and load the matching reference
   above.
3. Inspect raw telemetry before and after transforms with the collector
   `debug` exporter.
4. Classify the break as one of:
   - attribute-name rename;
   - attribute-value / enum rename;
   - generated metric label or data-point change;
   - resource/span/metric/log-record scope mismatch;
   - collection topology or product-path gap.
5. Choose the bridge location conceptually:
   - span attributes before APM / DB / Span Metrics consume spans;
   - generated RED metric labels after `spanmetrics`;
   - resource attributes before export / Resource Catalog correlation;
   - log/resource metadata before exporter routing or serverless metadata
     processing.
6. Hand exact implementation to the owning skill:
   `opentelemetry-ottl` for transform syntax, `opentelemetry-collector` for
   pipeline/Helm/Fleet wiring, `opentelemetry-instrumentation` for SDK and
   sampler setup, `core` for Coralogix app/subsystem routing, and
   `ai-app-instrumentation` for AI Center / GenAI spans.

Minimal evidence-only collector config for step 3:

```yaml
receivers:
  otlp:
    protocols:
      grpc: {}
      http: {}
exporters:
  debug:
    verbosity: detailed
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      exporters: [debug]
    logs:
      receivers: [otlp]
      exporters: [debug]
```

Use this only to inspect raw scopes and attribute names; production pipeline
wiring still belongs to `opentelemetry-collector`.

For worked diagnosis examples, read
[triage-workflow.md](references/triage-workflow.md).

## Limitations

This skill diagnoses telemetry semantics. Hand off implementation details:

- `core`: `cx.application.name`, `cx.subsystem.name`, regional domains, and
  application/subsystem routing order.
- `opentelemetry-instrumentation`: SDK env vars, sampler chains,
  `CoralogixTransactionSampler`, and manual span code.
- `ai-app-instrumentation`: AI Center and GenAI — `gen_ai.*` span shape,
  detection, GenAI proxy/library setup, and verification in AI Center.
- `opentelemetry-ottl`: exact `set(...)`, `replace_pattern(...)`, contexts,
  and where clauses.
- `opentelemetry-collector`: collector pipeline wiring, Helm/Fleet values,
  rendered ConfigMaps, exporter queues, Resource Catalog paths, and profile
  pipeline setup.
- Product workflows: dashboard queries, SLOs, alerts, synthetics, RUM, and
  product-specific rule repair unless the root cause is one of the telemetry
  attribute shapes documented here.

## Upstream References
- [Coralogix: Aligning Coralogix and OTel naming conventions](https://coralogix.com/docs/user-guides/apm/getting-started/aligning-coralogix-and-otel-naming-conventions/)
- [OTel attribute registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/)
- [OTel semantic conventions specification](https://opentelemetry.io/docs/specs/semconv/)
- [OTel Telemetry Schemas](https://opentelemetry.io/docs/specs/otel/schemas/)
