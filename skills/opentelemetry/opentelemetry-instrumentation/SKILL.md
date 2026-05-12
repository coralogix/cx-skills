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
| Choose a language / decide where to start | Load `language-selector.md` first — it has the decision tree for language, signal, mode, and export path |
| Generate setup for a specific language | Load the language reference after confirming the SDK: `java.md`, `python.md`, `nodejs.md`, `dotnet.md`, `go.md` |
| Configure OTLP endpoint, region, or authentication | Load `coralogix-endpoints.md` — covers regional domains, OTLP host:port, auth header format |
| Generate a complete user-facing answer | Load `output-templates.md` — checklist structure with assumptions, code, validation steps |
| Diagnose missing traces, metrics, or logs from the SDK | Load `troubleshooting.md` — symptom → root-cause table for SDK-side failures |

Load order: `language-selector.md` → language ref → `coralogix-endpoints.md` → `output-templates.md` (always last). Load `troubleshooting.md` only for debugging.

## Answer Rules

Always include in generated answers:

- **Required env vars** (direct export, HTTP/protobuf — works for all languages):
  ```bash
  export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.<region>.coralogix.com:443"
  export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
  export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer $CORALOGIX_API_KEY"
  export OTEL_SERVICE_NAME="my-service"
  export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=my-app,cx.subsystem.name=my-subsystem"
  ```
  gRPC: Java/.NET → `https://host:443`; Python/Node.js → `host:port`; Go → `host:port` only. Full table: [coralogix-endpoints.md](references/coralogix-endpoints.md).

- **Required resource attributes** — all three; missing any silently degrades APM:

  | Attribute | Required for |
  |---|---|
  | `service.name` | APM catalog, service map, transactions |
  | `cx.application.name` + `cx.subsystem.name` | Routing, TCO, APM grouping |
  | `telemetry.sdk.language` | APM language icon — auto-set; do not strip |
  | `k8s.pod.name`, `k8s.namespace.name` | Infra Explorer pod/namespace |
  | `host.name` | Infra Explorer host view |

- **Coralogix transactions.** Require `CoralogixTransactionSampler` (Python, Node.js, Go). Node.js bundled auto-instr via `NODE_OPTIONS` does NOT support transactions — use individual or manual.
- **Telemetry quality.** Low-cardinality span names, no sensitive data, bounded metric attributes, structured single-line logs with trace/span IDs, validation steps for the signal. Never approve user-scoped values (`user_id`, `tenant_id`, `request_id`, `session_id`) as metric labels — they cause unbounded cardinality and will explode metric storage.
- **Install references.** Link to `https://opentelemetry.io/docs/languages/<lang>/getting-started/`; name required packages only when they affect correctness.
- **Validation paths.** Traces → **Explore → Tracing**. Metrics → **Grafana → Explore → Metric Browser**. Logs → **Logs**.
- **Language fragile rules.** Load the language ref before answering — required packages and runtime caveats are there.
- **Direct vs collector: present tradeoffs, never recommend.** Show both; use the tradeoff table in `language-selector.md` and ask about scale, infra, and sampling needs.
- **Collector config is out of scope.** Redirect to `opentelemetry-collector` — do not partially answer pipeline or processor questions.

## Workflow

- **New setup:** `language-selector.md` → language ref + `coralogix-endpoints.md` → generate with `output-templates.md`.
- **Code review:** language ref → review checklist in `output-templates.md`.
- **Debugging:** `troubleshooting.md` first; escalate to language ref only if SDK-side cause confirmed.

## Limitations

- **OTel Collector / OTTL** — use `opentelemetry-collector` or `opentelemetry-ottl`.
- **Lambda / serverless** — use Coralogix Lambda layer docs; `Payload Too Large` OTLP errors are Lambda-layer concerns, not SDK.
- **PHP, eBPF auto-instrumentation** — not covered.
- **Coralogix platform internals** (data routing, index policies, APM UI config) — platform topics.

## Deprecated native SDKs

All native Coralogix SDKs are EOL **June 30, 2026** — redirect users to OTel instrumentation. Do not provide configuration help for these packages.

| SDK | Deprecated package |
|---|---|
| Java | `coralogix-sdk` · [Log4j](https://coralogix.com/docs/integrations/sdks/log4j/) |
| Python | `coralogix_logger` · [Python SDK](https://coralogix.com/docs/integrations/sdks/python-sdk/) |
| Node.js | `coralogix-logger` · [Node.js SDK](https://coralogix.com/docs/integrations/sdks/nodejs/) · Winston · Bunyan |
| .NET | `CoralogixCoreSDK` · [NLog](https://coralogix.com/docs/integrations/sdks/nlog/) · [Log4net](https://coralogix.com/docs/integrations/sdks/log4net/) · [Serilog](https://coralogix.com/docs/integrations/sdks/serilog/) |
| Go | `go-coralogix-sdk` · [Go SDK](https://coralogix.com/docs/integrations/sdks/go/) |

## Upstream references

Coralogix OTel instrumentation: [Java](https://coralogix.com/docs/opentelemetry/instrumentation-options/java-opentelemetry-instrumentation/) · [Python](https://coralogix.com/docs/opentelemetry/instrumentation-options/python-opentelemetry-instrumentation/) · [Node.js](https://coralogix.com/docs/opentelemetry/instrumentation-options/nodejs-opentelemetry-instrumentation/) · [.NET](https://coralogix.com/docs/opentelemetry/instrumentation-options/dotnet-opentelemetry-instrumentation/) · [Go](https://coralogix.com/docs/opentelemetry/instrumentation-options/golang-opentelemetry-instrumentation/)

[Coralogix OTel docs](https://coralogix.com/docs/opentelemetry/) · [OpenTelemetry official docs](https://opentelemetry.io/docs/)
