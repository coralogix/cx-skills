# High-Signal Rules

Use these recurring rules when the topic comes up in a customer question.
For exact field lists in final answers, also read
`final-answer-checklists.md`.

| Topic | Rule |
|---|---|
| `service.name` | Resource scope only; generated labels such as `service_name` are not span attributes. Collector span filters should read `resource.attributes["service.name"]`, not `attributes["service.name"]`. |
| APM operations | Need resource `service.name`, real top-level span kind, and a low-cardinality operation attribute such as `http.route`, `db.operation`, `rpc.method`, or `messaging.operation`. |
| HTTP / Transactions | `url.full` is for outbound HTTP client spans, not inbound server spans; server spans should use `url.path` / `url.scheme` plus templated `http.route`. Route-aware names must exist before `CoralogixTransactionSampler` derives `cgx.transaction`. |
| Error Tracking | Needs status dimensions such as `http.response.status_code` / `rpc.grpc.status_code`; exception-to-status mapping is a product workaround, not generic OTel semconv. |
| Database Monitoring | Emit stable DB semconv first, but mirror into the current Coralogix compatibility names until backend support is confirmed. |
| OTel upgrades | Classify the break before OTTL: name rename, value rename, generated metric change, scope mismatch, or topology gap. |
| Helm / Fleet | The bridge must render into the path the product consumes, often top-level `spanMetrics.transformStatements` before normal Span Metrics. |
| Span Metrics | For collector-side sampling, run `spanmetrics` before the sampler for full RED coverage. SDK head sampling is source-side loss: sampled-out spans never reach the collector, so disable/raise SDK sampling or accept sampled RED metrics. Preserve required labels and writer identity, and treat overflow as expected cardinality-limit fallback behavior. |
| Span Metrics status codes | Generated RED metric label changes belong in the metrics pipeline after `spanmetrics`, not trace transforms or the traces pipeline before `spanmetrics`. |
| Infra Explorer | Needs consistent resource-scope `k8s.*`, `host.*`, and `cloud.*`; ownership labels are not the same as APM `service.name`. |
| Custom Metrics | Keep labels low-cardinality, handle OTLP temporality deliberately, and avoid conflicting dotted/underscore label identities. For multi-writer delta sums, preserve writer identity or aggregate first; use `deltatocumulative` only after identity/aggregation is correct and a cumulative path is needed. |
| AI Center | Out of scope here: hand off to `ai-app-instrumentation`, which owns GenAI span shape, detection, and AI Center verification. |
| Logs/serverless | Distinguish log-record attributes, resource attributes, and Coralogix-specific `cx_metadata.*`; removing built-in metadata can affect serverless product behavior. |
| Resource Catalog | Correlation attributes are not inventory. Inventory freshness and self-managed metadata ingestion need the dedicated Resource Catalog path. |
