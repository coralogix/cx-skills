# Output Templates

## Contents
- Template 1: New Instrumentation Setup
- Template 2: Code Review
- Template 3: Troubleshooting
- Formatting rules for all templates

Use these templates when generating a final user-facing instrumentation answer.
Choose the appropriate template based on the request type.

## Template 1: New Instrumentation Setup

Use for: "How do I instrument my X app with OpenTelemetry to send to Coralogix?"

---

**Assumptions**
- Language: `<language>`
- Signal(s): `<traces | metrics | logs | all>`
- Instrumentation mode: `<auto | programmatic | manual>`
- Export path: `<direct to Coralogix | via OTel Collector>`
- Coralogix region: `<region>` (e.g. `eu2`)
- Framework: `<framework if known>`

**Required inputs (use placeholders)**
- `<CORALOGIX_API_KEY>` — Send-Your-Data API key from Settings → API Keys
- `<SERVICE_NAME>` — your service name (appears in APM service map)
- `<CX_APPLICATION_NAME>` — Coralogix application name (groups services)
- `<CX_SUBSYSTEM_NAME>` — Coralogix subsystem name (refines routing)

**Install reference**
- Link to `https://opentelemetry.io/docs/languages/<language>/getting-started/` for SDK installation.

**Environment variables**
```bash
# All required env vars with placeholders
# HTTP/protobuf traces endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.<CORALOGIX_REGION>.coralogix.com:443/v1/traces"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
# gRPC endpoint: standard bare form for Python/Node.js/Go; Java/.NET use https://host:port
# export OTEL_EXPORTER_OTLP_ENDPOINT="ingress.<CORALOGIX_REGION>.coralogix.com:443"
# Python exception: URL-encode the space in env-var headers
# export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20<CORALOGIX_API_KEY>"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"
```

**Code / config snippet**
```language
# Minimal working example — copy, paste, replace placeholders
```

**Run command**
```bash
# How to start the instrumented application
```

**Validation steps**
1. Start the application and generate some traffic.
2. Traces → Coralogix UI **Explore → Tracing** (allow ~30s for first trace).
3. Metrics (if enabled) → **Grafana → Explore → Metric Browser**.
4. Logs (if enabled) → Coralogix UI **Logs**.

**Security reminders**
- Never commit `<CORALOGIX_API_KEY>` to source control. Use a secrets manager or env var.
- Rotate Send-Your-Data keys if they are exposed.

---

## Template 2: Code Review

Use for: "Review my OTel instrumentation code" or "What am I missing?"

---

**Review findings for `<language>` instrumentation**

| Item | Status | Notes |
|---|---|---|
| OTLP endpoint format | ✅ / ❌ | gRPC Java/.NET: `https://ingress.<region>.coralogix.com:443` (URI required); gRPC Python/Node.js: prefer `ingress.<region>.coralogix.com:443`, but `https://host:port` is accepted; Go `WithEndpoint`: bare host:port only; HTTP/proto: `https://ingress.<region>.coralogix.com:443/v1/<signal>` |
| Auth header present | ✅ / ❌ | `Authorization=Bearer <key>`; Python env vars require `Authorization=Bearer%20<key>` |
| `cx.application.name` set | ✅ / ❌ | Required resource attribute |
| `cx.subsystem.name` set | ✅ / ❌ | Required resource attribute |
| `service.name` set | ✅ / ❌ | Required for APM service map |
| CoralogixTransactionSampler | ✅ / ❌ / N/A | Required for APM Transactions view |
| Protocol matches exporter | ✅ / ❌ | gRPC vs HTTP/proto |
| No hardcoded secrets | ✅ / ❌ | Keys should be in env vars |
| Telemetry quality | ✅ / ❌ | Low-cardinality span names, bounded metric attributes, no sensitive data, structured logs with trace/span correlation |

**Issues found**
1. `<specific issue and fix>`
2. `<specific issue and fix>`

**Corrected snippet**
```language
# Corrected minimal working code
```

---

## Template 3: Troubleshooting

Use for: "I'm not seeing any traces / metrics / logs in Coralogix."

---

**Troubleshooting: missing `<signal>` from `<language>` app**

Load `troubleshooting.md` for the full symptom table. Quick checklist:

1. **Enable SDK debug logging** — see `troubleshooting.md` for per-language instructions.
2. **Verify endpoint** — is `OTEL_EXPORTER_OTLP_ENDPOINT` set to `https://ingress.<region>.coralogix.com:443/v1/traces` for HTTP/protobuf or `ingress.<region>.coralogix.com:443` for gRPC?
3. **Verify auth** — does `OTEL_EXPORTER_OTLP_HEADERS` contain `Authorization=Bearer <key>`?
4. **Verify region** — does the region match the Coralogix account's region?
5. **Check for Python URL encoding** — is the header value URL encoded (`%20` not space)?
6. **Check network** — can the app reach `ingress.<region>.coralogix.com:443`?
7. **Check signal is enabled** — are trace/metric/log exporters set (not `"none"`)?
8. **Check correlation and safety** — do logs include trace/span context, and are sensitive fields excluded?

---

## Formatting rules for all templates

- Always use code blocks with the correct language identifier.
- Replace `{{ endpoints.opentelemetry }}` template variables (from the docs source) with
  the actual regional endpoint: `https://ingress.<CORALOGIX_REGION>.coralogix.com:443/v1/traces` for
  HTTP/protobuf or `ingress.<CORALOGIX_REGION>.coralogix.com:443` for gRPC.
- Always use `<PLACEHOLDER>` style for secrets — never generate example keys.
- Use inline comments in code blocks only where the line is non-obvious.
- Include validation steps in every new instrumentation answer.
- Keep the "security reminder" section — teams often overlook secret management.
- Do not document SDK installation steps inline; link to the official OpenTelemetry language
  getting-started page.
