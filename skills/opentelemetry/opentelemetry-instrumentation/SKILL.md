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
  author: coralogix
  version: "0.1.0"
  workflow_type: advisory
  integration: otel-sdk-instrumentation
  argument_hint: "[language or 'review my instrumentation']"

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
    config_keys:
      - "OTEL_EXPORTER_OTLP_ENDPOINT"
      - "OTEL_EXPORTER_OTLP_HEADERS"
      - "OTEL_EXPORTER_OTLP_PROTOCOL"
      - "OTEL_RESOURCE_ATTRIBUTES"
      - "OTEL_SERVICE_NAME"
      - "OTEL_TRACES_EXPORTER"
      - "OTEL_METRICS_EXPORTER"
      - "OTEL_LOGS_EXPORTER"
      - "cx.application.name"
      - "cx.subsystem.name"
      - "CoralogixTransactionSampler"
      - "opentelemetry-javaagent"
    keywords:
      - otel sdk
      - opentelemetry instrumentation
      - coralogix apm
      - opentelemetry-javaagent
      - opentelemetry-instrument
      - coralogix-opentelemetry
      - "@coralogix/opentelemetry"
      - authorization bearer
      - cx.application.name
      - cx.subsystem.name
      - otlp exporter
      - span exporter
      - trace exporter
      - NodeSDK
      - BasicTracerProvider
      - TracerProvider
      - MeterProvider
      - AddOtlpExporter
      - otlptracegrpc
      - credentials.NewTLS
      - NODE_OPTIONS
      - CoralogixTransactionSampler
      - missing traces
      - missing metrics
      - coralogix.com

  docs: https://coralogix.com/docs/opentelemetry/
---

# OpenTelemetry SDK Instrumentation for Coralogix

Help users instrument Java, Python, Node.js, .NET, and Go applications with OpenTelemetry
SDKs and send traces, metrics, and logs to Coralogix. Use this skill when someone is adding
SDK instrumentation to their app — not when they are deploying or configuring the collector
(use `opentelemetry-collector` for that).

## When to Use This Skill

| Use case | What to do |
|---|---|
| Choose a language / decide where to start | Load `language-selector.md` first — it has the decision tree for language, signal, mode, and export path |
| Generate setup for a specific language | Load the language reference after confirming the SDK: `java.md`, `python.md`, `nodejs.md`, `dotnet.md`, `go.md` |
| Configure OTLP endpoint, region, or authentication | Load `coralogix-endpoints.md` — covers regional domains, OTLP host:port, auth header format |
| Generate a complete user-facing answer | Load `output-templates.md` — checklist structure with assumptions, code, validation steps |
| Diagnose missing traces, metrics, or logs from the SDK | Load `troubleshooting.md` — symptom → root-cause table for SDK-side failures |
| User wants to deploy or configure the OTel Collector | Not in scope — use the `opentelemetry-collector` skill |
| User wants to write OTTL transform/filter statements | Not in scope — use the `opentelemetry-ottl` skill |

## Progressive Loading Rule

1. Load `language-selector.md` first to determine language, signal, mode, and export path.
2. Load the specific language reference once that is known.
3. Load `coralogix-endpoints.md` whenever generating endpoint or region configuration.
4. Load `troubleshooting.md` only for debugging / missing telemetry requests.
5. Load `output-templates.md` whenever generating a final user-facing instrumentation answer.

## Key Concepts

### Auth, endpoint, and required attributes

Direct OTLP export to Coralogix requires `Authorization=Bearer <key>` (Send-Your-Data type)
as an OTLP header, plus `cx.application.name`, `cx.subsystem.name`, and `service.name` as
resource attributes. The HTTP/protobuf traces endpoint is
`https://ingress.<region>.coralogix.com:443/v1/traces`; logs use `/v1/logs`. For gRPC the
required format depends on the language: **Java and .NET** require the full `https://` URI
scheme (`https://ingress.<region>.coralogix.com:443`) because their OTLP exporters perform
URI parsing on the endpoint value. **Python and Node.js** examples should prefer bare
`host:port` (`ingress.<region>.coralogix.com:443`), but both SDKs also accept
`https://host:port`; do not flag that as incorrect in a user's config. **Go `WithEndpoint`**
uses bare `host:port` only. When exporting via a collector, the SDK sends unauthed to the
collector; the collector holds the key. Full region table and per-language formats:
[references/coralogix-endpoints.md](references/coralogix-endpoints.md).

### Resource attributes and Coralogix feature requirements

All three of `service.name`, `cx.application.name`, and `cx.subsystem.name` are required for
full APM functionality. Missing any one causes silent degradation — traces arrive but APM
features are incomplete or empty.

| Attribute | Required for |
|---|---|
| `service.name` | APM Service Catalog entry, service map, APM transaction grouping |
| `cx.application.name` + `cx.subsystem.name` | Data routing to team, TCO policy, APM grouping |
| `telemetry.sdk.language` | Language icon in APM — set automatically by the OTel SDK; do not strip it |
| `k8s.pod.name`, `k8s.namespace.name` | Infrastructure Explorer pod/namespace linking |
| `host.name` | Infrastructure Explorer host view |

### Coralogix transactions (APM)

APM Transactions require `CoralogixTransactionSampler` in the SDK sampler chain — available
for Python, Node.js, and Go (see each language reference file). **Node.js caveat:** bundled
auto-instrumentation (`@opentelemetry/auto-instrumentations-node` via `NODE_OPTIONS`) does
NOT support Coralogix transactions — use individual instrumentation or manual instead.

## High-Signal Answer Rules

Always include in generated answers:

- **`cx.application.name` + `cx.subsystem.name` + `service.name`.** All three are required;
  missing any one silently degrades APM features.
- **Required direct-export env vars.** Show `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME`, and `OTEL_RESOURCE_ATTRIBUTES` in every setup answer. For HTTP/protobuf traces use `https://ingress.<region>.coralogix.com:443/v1/traces`; for gRPC use `https://ingress.<region>.coralogix.com:443` (Java/.NET) or the standard Coralogix bare form `ingress.<region>.coralogix.com:443` (Python/Node.js/Go). Python and Node.js also accept `https://host:port`; Go `WithEndpoint` does not.
- **Telemetry quality checks.** Keep span names low-cardinality, avoid sensitive data in all telemetry, keep metric attributes bounded, use structured single-line logs with trace/span correlation, and include validation steps for the configured signal.
- **Official install references.** For new setup answers, link to `https://opentelemetry.io/docs/languages/<lang>/getting-started/` instead of writing install commands. Still name required package artifacts when they affect correctness.
- **Validation paths.** Traces → Coralogix UI **Explore → Tracing**. Metrics → **Grafana → Explore → Metric Browser**. Logs → **Logs**.
- **Language-specific fragile rules.** Load the relevant language reference before answering; it contains required package artifacts and runtime-specific caveats for Java, Python, Node.js, .NET, and Go.
- **Direct vs collector: present tradeoffs, never recommend.** When asked whether to send directly from the SDK or via an OTel Collector, ALWAYS present both as valid options — never make a final recommendation. Direct is simpler and good for getting started; via-collector adds enrichment, retry, and tail sampling. Present the tradeoff table and ask about the user's context. Do not say "I recommend X" or imply one path is better without knowing their scale, infra, or sampling needs.
- **Collector configuration questions are out of scope.** If asked about OTel Collector setup, batch processors, pipelines, or component config, redirect immediately to the `opentelemetry-collector` skill. Do not answer collector configuration questions even partially — this skill covers SDK instrumentation only, ending at the exporter.

## Workflow

- **New setup:** `language-selector.md` → language ref + `coralogix-endpoints.md` → generate with `output-templates.md`.
- **Code review:** language ref → review checklist in `output-templates.md`.
- **Debugging:** `troubleshooting.md` first; escalate to language ref only if SDK-side cause confirmed.

## Limitations

This skill does not cover:

- **OpenTelemetry Collector deployment, configuration, or OTTL.** SDK instrumentation ends
  at the exporter — what happens inside the collector is `opentelemetry-collector`.
- **Lambda / serverless OTel auto-instrumentation layers.** Use Coralogix Lambda telemetry
  exporter or language-specific Lambda layers — these have separate packaging and env-var
  conventions. For Node.js Lambda: `Payload Too Large` OTLP errors and response streaming
  limitations are handled at the Lambda layer level, not by the OTel SDK. Refer customers
  to the Coralogix Lambda layer documentation.
- **PHP instrumentation.** A separate docs page exists but is not covered here.
- **eBPF auto-instrumentation.** Coverage of eBPF-based zero-code instrumentation is out
  of scope for this skill.
- **Coralogix platform internals.** Data routing, index policies, APM config in the
  Coralogix UI — those are platform topics.

## Upstream references
- [Coralogix OTel instrumentation docs](https://coralogix.com/docs/opentelemetry/)
- [OpenTelemetry official docs](https://opentelemetry.io/docs/)
- [`coralogix-opentelemetry-js`](https://github.com/coralogix/coralogix-opentelemetry-js)
- [`coralogix-opentelemetry-go`](https://github.com/coralogix/coralogix-opentelemetry-go)
