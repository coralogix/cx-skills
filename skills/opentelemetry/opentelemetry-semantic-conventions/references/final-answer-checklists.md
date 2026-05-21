# Final Answer Checklists

Use these when the user asks "which fields" or the issue clearly matches a
product surface. They are the short-answer anchors too: do not rely on the
model to infer these exact names from `SKILL.md` rules alone.

- **Database Monitoring:** say Database Monitoring requires all five target
  span attributes to be present: `db.system`, `db.name`, `db.operation`,
  `db.statement`, and `net.peer.name`. Treat `db.system.name`,
  `db.namespace`, `db.operation.name`, `db.query.text`, `server.address`, and
  `network.peer.address` as source/newer names that may need mirroring, not
  replacements for the target set.
- **Span Metrics DB bridge:** use top-level
  `spanMetrics.transformStatements` before `spanmetrics`, not only
  `spanMetrics.dbMetrics.transformStatements`. Include the symptom strings
  `db_calls_total`, `calls_total`, and `db_namespace`: DB-only placement can
  make `db_calls_total` get `db_namespace` while normal `calls_total` stays
  blank. The fallback chain is `db.name`, `server.address`,
  `network.peer.name`, `net.peer.name`, `network.peer.address`, then
  `db.system`.
- **Fleet transform rendering:** name both Fleet/UI
  `span_metrics.transform_statements` and rendered Helm
  `spanMetrics.transformStatements`; verify the rendered ConfigMap, not only
  values or UI JSON.
- **Span Metrics labels:** `span_name`, `service_name`, `span_kind`,
  `status_code`, `collector_instance_id` / `collector.instance.id`,
  `http_method`, `host_name`, `k8s_cluster_name`, `cgx.transaction`,
  `cgx.transaction.root`, `db_namespace`, `db_operation_name`,
  `db_collection_name`, `db_system`, `application_name`, and
  `cx_subsystem_name`.
- **Span Metrics cardinality:** avoid `url.full`, `k8s.pod.ip`, and blanket
  `k8s.pod.name` dimensions by default. Use templated `http.route` for HTTP
  grouping; add `k8s.pod.name` only for a concrete writer-collision case.
- **Span Metrics writer identity:** always include `collector.instance.id` /
  `collector_instance_id` or another writer-unique dimension. For
  collector-contrib `v0.136.0` through `v0.151.x`, name
  `--feature-gates=+connector.spanmetrics.includeCollectorInstanceID`; for
  `v0.152.0+`, verify `collector.instance.id` is emitted.
- **Span Metrics status-code bridge:** always name
  `spanmetrics.statusCodeConvention.useOtelPrefix`. This changes generated
  RED metric data points from `status.code` to `otel.status_code`, so bridge
  in the metrics pipeline after `spanmetrics`, not trace
  `spanMetrics.transformStatements` or traces before `spanmetrics`. Raw
  values are `status.code=Error/Ok/Unset` and
  `otel.status_code=ERROR/OK/missing`, including `otel.status_code=OK`; do
  not match Prometheus `STATUS_CODE_*` labels in collector-side bridges.
- **Span Metrics overflow:** `otel.metric.overflow="true"` is the raw OTLP
  data-point attribute and `otel_metric_overflow="true"` is the
  Prometheus-normalized label for the same expected fallback series, not a
  bug. Reduce source cardinality first, for example normalize UUIDs out of
  span names and prefer `http.route` over raw `url.path`; do not present
  raising the cap as the primary fix.
- **HTTP metric method:** stable/current/new OpenTelemetry HTTP server
  metric data points should use `http.request.method`; Coralogix Span
  Metrics may still need a bridge for legacy `http.method` because
  connector dimensions read that source internally.
- **Transactions timing:** `cgx.transaction` / `cgx.transaction.root` are
  derived by `CoralogixTransactionSampler`; do not set them manually as the
  fix. Route-aware span names / `http.route` must exist before that sampler;
  collector rewrites after derivation can be too late.
- **Infra Explorer pod identity:** resource-scope `k8s.cluster.name`,
  `k8s.namespace.name`, `k8s.pod.name`, `k8s.node.name`,
  `k8s.container.name`, `service.name`, and one owner such as
  `k8s.deployment.name`, `k8s.statefulset.name`, `k8s.daemonset.name`,
  `k8s.job.name`, `k8s.cronjob.name`, or `k8s.replicaset.name`.
- **EC2 Name tag:** the target identity is resource-scope `host.name`; check
  EC2 tag/resource detection in logs and Resource Catalog plus
  `ec2:DescribeTags`.
- **Lambda metadata:** `cx_metadata.*` is product metadata. Name
  `CX_LOGS_METADATA_ENABLED`, `CX_LOGS_METADATA_INCLUDE_TRACE_REF`, and
  `CX_LOGS_RESOURCE_BUILT_IN_ATTRIBUTES`; warn about serverless dashboards and
  trace/log correlation.
- **Custom metric normalized labels:** `service_instance_id` is the
  Prometheus / Target Allocator normalized spelling of `service.instance.id`,
  not a separate identity dimension to keep with different values. Choose one
  canonical service or writer identity and align or remove the duplicate
  source.
- **Exporter routing scope:** `cx.application.name` /
  `cx.subsystem.name` are Coralogix proprietary routing attributes, not
  OTel-standard semconv. `application_name_attributes` and
  `subsystem_name_attributes` read resource attributes only. If a value is at
  log-record scope, recommend setting it at resource scope with SDK /
  `resource` / `resourcedetection`, or copying it up with OTTL; exact syntax
  belongs to `opentelemetry-ottl`, while `core` owns routing configuration.
  For env-var answers name `OTEL_RESOURCE_ATTRIBUTES`. Say `core` when naming
  the routing owner.
- **Java instrumentation handoff:** if the user asks whether semconv owns full
  Java auto-instrumentation setup, answer no, and name
  `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_RESOURCE_ATTRIBUTES`, and
  `opentelemetry-instrumentation` as the setup owner.
- **Error Tracking timeout gaps:** missing `http.response.status_code` can be
  normal when no HTTP response exists. `exception.type` / span error status
  are fallback signals; mapping them to a synthetic HTTP status is a
  Coralogix/product workaround, not standard OTel semconv.
- **Resource Catalog inventory:** normal `k8sattributes` / `resource` /
  `transform` adds correlation attributes but does not create inventory.
  Self-managed inventory needs `k8sobjects`,
  `resourcedetection/resource_catalog`, `coralogix/resource_catalog`, and
  `x-coralogix-ingress: metadata-as-otlp-logs/v1`. For freshness or stale
  metadata, mention `resource_ttl`, `interval`, `otel.entity.interval`, and
  `schema_url`.
- **Pure OTTL handoff:** if the user asks for an exact `set(...)` statement,
  where clause, or OTTL context, name `opentelemetry-ottl` as owner; semconv
  only names source and destination scopes.
- **Other short answers:** Azure `cloud.platform` is a value rename
  (`azure_vm` / `azure.vm`, `azure_aks` / `azure.aks`); timeout status mapping
  from `exception.type` is a Coralogix workaround; multi-gateway tail sampling
  / `spanmetrics` needs traceID load balancing.
