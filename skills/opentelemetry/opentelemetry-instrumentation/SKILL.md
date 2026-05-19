---
name: opentelemetry-instrumentation
description: >
  Instruments Java, Python, Node.js, .NET, and Go applications with OpenTelemetry SDKs to
  send traces, metrics, and logs to Coralogix. Use for SDK-side OTel setup, OTLP exporter
  env vars, Coralogix resource attributes, APM transaction samplers, Kubernetes Operator
  injection, or debugging missing traces, metrics, logs, or no telemetry from an
  application. Not for OTel Collector config (use opentelemetry-collector), OTTL
  authoring (use opentelemetry-ottl), eBPF instrumentation, or Lambda layers.
license: Apache-2.0

metadata:
  version: "0.1.0"
  integration: otel-sdk-instrumentation
  signals:
    - logs
    - metrics
    - traces
  deployment:
    - kubernetes
    - docker
    - aws
  triggers:
    description: >
      Load when a user is adding or reviewing OpenTelemetry SDK instrumentation in an
      application — choosing a language, wiring up an exporter, setting env vars, or
      debugging missing telemetry from the SDK side (not from the collector side).
    always: false
    file_patterns:
      - "**/*instrumentation*.js"
      - "**/*instrumentation*.ts"
      - "**/*instrumentation*.py"
      - "**/*otel*.py"
      - "**/*otel*.java"
      - "**/*opentelemetry*.java"
      - "**/*opentelemetry*.cs"
      - "**/*opentelemetry*.go"
  docs: https://coralogix.com/docs/opentelemetry/
---

# OpenTelemetry SDK Instrumentation for Coralogix

## When to Use This Skill

| Use case | What to do |
|---|---|
| Choose a language / decide where to start | Load [language-selector.md](references/language-selector.md) first — it has the decision tree for language, signal, mode, and export path |
| Generate setup for a specific language | Load the language reference after confirming the SDK: [java.md](references/java.md), [python.md](references/python.md), [nodejs.md](references/nodejs.md), [dotnet.md](references/dotnet.md), [go.md](references/go.md) |
| Configure OTLP endpoint, region, or authentication | Load [coralogix-endpoints.md](references/coralogix-endpoints.md) — covers regional domains, OTLP host:port, auth header format |
| Generate a complete user-facing answer | Load [output-templates.md](references/output-templates.md) — checklist structure with assumptions, code, validation steps |
| Diagnose missing traces, metrics, or logs from the SDK | Load [troubleshooting.md](references/troubleshooting.md) — symptom → root-cause table for SDK-side failures |

Load order: [language-selector.md](references/language-selector.md) → language ref → [coralogix-endpoints.md](references/coralogix-endpoints.md) → [output-templates.md](references/output-templates.md) (always last). Load [troubleshooting.md](references/troubleshooting.md) only for debugging.

## Answer Rules

Before answering (agent mode):

- **Always call `list_references()` first, then `read_reference(...)` for the relevant files** (language selector + the target language + endpoints; add troubleshooting only when debugging). Do not answer from memory if the references could affect correctness.
- **Use the structure/checklists in [output-templates.md](references/output-templates.md)** for any user-facing response; keep your own prose minimal and actionable.

Always include in generated answers:

- **Required env vars (names only)** — include these in any “copy/paste” setup:
  `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`
  (plus `OTEL_*_EXPORTER` / `OTEL_EXPORTER_OTLP_*_PROTOCOL` when choosing signals/protocol). For exact per-language endpoint formats and the Python `%20` env-var rule, use [coralogix-endpoints.md](references/coralogix-endpoints.md).

- **Required resource attributes** — `service.name` (APM catalog/transactions), `cx.application.name` + `cx.subsystem.name` (routing, TCO, APM grouping), `telemetry.sdk.language` (auto-set; do not strip). Missing any silently degrades APM. Additional k8s/host attributes are covered in each language reference.

- **Telemetry quality.** Low-cardinality span names, no sensitive data, bounded metric attributes, structured single-line logs with trace/span IDs, validation steps for the signal. Never approve user-scoped values (`user_id`, `tenant_id`, `request_id`, `session_id`) as metric labels — they cause unbounded cardinality and will explode metric storage.
- **Direct vs collector routing rule:** Default to **direct OTLP** for dev/test environments, simple single-service production deployments, or when no collector infrastructure exists. Default to **via-collector** for Kubernetes workloads needing pod/namespace enrichment (`k8sattributes`), tail sampling, multi-service shared key management, or buffered retry/file persistence requirements. When the deployment context is unknown, show both options using the tradeoff table in [language-selector.md](references/language-selector.md).
- **Collector config is out of scope.** Redirect to `opentelemetry-collector` — do not partially answer pipeline or processor questions.

## High-Risk Gotchas (Do Not Guess)

Keep this list short and only use it when the user’s symptom matches. For details, defer to the language references.

- **Java agent:** `opentelemetry-javaagent.jar` + `JAVA_TOOL_OPTIONS="-javaagent:/path/to/opentelemetry-javaagent.jar"`.
- **Java/.NET gRPC endpoint:** must be a full URI `https://ingress.<region>.coralogix.com:443` (URI parsing breaks bare `host:port`).
- **Python auth header:** env var needs `%20` (`Authorization=Bearer%20<KEY>`); programmatic headers use a tuple sequence with lowercase key + literal space (`("authorization", f"Bearer {token}")`).
- **Node.js HTTP/proto:** exporter `url` must include `/v1/traces` (`https://ingress.<region>.coralogix.com:443/v1/traces`); gRPC doesn’t.
- **Go gRPC:** `credentials.NewTLS(nil)` and bare endpoint `ingress.<region>.coralogix.com:443` (no `https://` in `WithEndpoint`).
- **Transactions:** require `CoralogixTransactionSampler` (Node.js: `@coralogix/opentelemetry`); bundled `NODE_OPTIONS` auto-instr doesn’t support Transactions.
- **Short-lived Python scripts:** `SimpleSpanProcessor` vs `BatchSpanProcessor`; metrics need `PeriodicExportingMetricReader` flush/wait.
- **.NET Framework incoming propagation:** `OpenTelemetry.Instrumentation.AspNet` + `AddAspNetInstrumentation()`.

## Workflow

- **New setup:** [language-selector.md](references/language-selector.md) → language ref + [coralogix-endpoints.md](references/coralogix-endpoints.md) → generate with [output-templates.md](references/output-templates.md).
- **Code review:** language ref → review checklist in [output-templates.md](references/output-templates.md).
- **Debugging:** [troubleshooting.md](references/troubleshooting.md) first; escalate to language ref only if SDK-side cause confirmed.

## Limitations

- **OTel Collector / OTTL** — use `opentelemetry-collector` or `opentelemetry-ottl`.
- **Lambda / serverless** — use Coralogix Lambda layer docs; `Payload Too Large` OTLP errors are Lambda-layer concerns, not SDK.
- **PHP, eBPF auto-instrumentation** — not covered.
- **Coralogix platform internals** (data routing, index policies, APM UI config) — platform topics.

## Deprecated native SDKs

Native Coralogix SDKs are EOL **June 30, 2026** — redirect to OTel and do not provide configuration for legacy packages.

## Upstream references

Coralogix OTel instrumentation: [Java](https://coralogix.com/docs/opentelemetry/instrumentation-options/java-opentelemetry-instrumentation/) · [Python](https://coralogix.com/docs/opentelemetry/instrumentation-options/python-opentelemetry-instrumentation/) · [Node.js](https://coralogix.com/docs/opentelemetry/instrumentation-options/nodejs-opentelemetry-instrumentation/) · [.NET](https://coralogix.com/docs/opentelemetry/instrumentation-options/dotnet-opentelemetry-instrumentation/) · [Go](https://coralogix.com/docs/opentelemetry/instrumentation-options/golang-opentelemetry-instrumentation/)

[Coralogix OTel docs](https://coralogix.com/docs/opentelemetry/) · [OpenTelemetry official docs](https://opentelemetry.io/docs/)
