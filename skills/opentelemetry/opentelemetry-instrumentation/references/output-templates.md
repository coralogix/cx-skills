# Output Templates

## Contents
- Template 1: New Instrumentation Setup
- Template 2: Code Review
- Template 3: Troubleshooting
- Complete Examples (per-language)
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
- `CORALOGIX_API_KEY` — Send-Your-Data API key from Settings → API Keys
- `<SERVICE_NAME>` — your service name (appears in APM service map)
- `<CX_APPLICATION_NAME>` — Coralogix application name (groups services)
- `<CX_SUBSYSTEM_NAME>` — Coralogix subsystem name (refines routing)

**Install reference**
- Link to `https://opentelemetry.io/docs/languages/<language>/getting-started/` for SDK installation.

**Environment variables**
```bash
# All required env vars with placeholders
# HTTP/protobuf — base URL only; SDK auto-appends /v1/traces, /v1/metrics, /v1/logs
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.<CORALOGIX_REGION>.coralogix.com:443"
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
- Never commit the `CORALOGIX_API_KEY` value to source control. Use a secrets manager or env var.
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

## Complete Examples (per-language)

Use these as the basis for Template 1 answers. Replace `eu2` with the user's actual region.
All examples send traces only (direct to Coralogix, gRPC). Enable metrics/logs by changing
the exporter env vars per the language reference.

---

### Java — auto-instrumentation, traces, EU2

```bash
export JAVA_TOOL_OPTIONS="-javaagent:/path/to/opentelemetry-javaagent.jar"
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_METRICS_EXPORTER="none"
export OTEL_LOGS_EXPORTER="none"
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL="grpc"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.eu2.coralogix.com:443"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
export OTEL_SERVICE_NAME="order-service"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=ecommerce,cx.subsystem.name=orders"
java -jar myapp.jar
```

Validation: Coralogix UI → **Explore → Tracing** (look for `[otel.javaagent ...]` log line at startup).

---

### Python — auto-instrumentation, traces, EU2

```bash
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20<CORALOGIX_API_KEY>"
export OTEL_EXPORTER_OTLP_ENDPOINT="ingress.eu2.coralogix.com:443"
export OTEL_TRACES_EXPORTER="otlp_proto_grpc"
export OTEL_SERVICE_NAME="order-service"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=ecommerce,cx.subsystem.name=orders"
opentelemetry-instrument python app.py
```

Note: `%20` in `OTEL_EXPORTER_OTLP_HEADERS` is the URL-encoded space — required for Python env var auth. Do not use `%20` in programmatic code.

Validation: Coralogix UI → **Explore → Tracing**.

---

### Node.js — individual auto-instrumentation with Coralogix transactions, EU2

`instrumentation.js`:
```js
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { CoralogixTransactionSampler } = require('@coralogix/opentelemetry');
const { AlwaysOnSampler } = require('@opentelemetry/sdk-trace-base');

const sdk = new NodeSDK({
  sampler: new CoralogixTransactionSampler(new AlwaysOnSampler()),
  instrumentations: [new HttpInstrumentation(), new ExpressInstrumentation()],
});
sdk.start();
```

```bash
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
export OTEL_EXPORTER_OTLP_ENDPOINT="ingress.eu2.coralogix.com:443"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
export OTEL_SERVICE_NAME="order-service"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=ecommerce,cx.subsystem.name=orders"
node --require ./instrumentation.js app.js
```

Validation: Coralogix UI → **Explore → Tracing**; APM → **Transactions** (requires `CoralogixTransactionSampler`).

---

### .NET — auto-instrumentation (zero-code), traces, EU2

```bash
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.eu2.coralogix.com:443"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
export OTEL_SERVICE_NAME="order-service"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=ecommerce,cx.subsystem.name=orders"
```

Run the OpenTelemetry .NET Auto-Instrumentation profiler per the [official docs](https://opentelemetry.io/docs/zero-code/dotnet/).

Validation: Coralogix UI → **Explore → Tracing**.

---

### Go — manual SDK, traces, EU2

```go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/coralogix/coralogix-opentelemetry-go/sampler"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
    "google.golang.org/grpc/credentials"
)

func main() {
    ctx := context.Background()
    endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT") // ingress.eu2.coralogix.com:443
    token := os.Getenv("CORALOGIX_API_KEY")

    res, _ := resource.Merge(resource.Default(), resource.NewWithAttributes(
        semconv.SchemaURL,
        semconv.ServiceName("order-service"),
        attribute.String("cx.application.name", "ecommerce"),
        attribute.String("cx.subsystem.name", "orders"),
    ))

    exp, _ := otlptracegrpc.New(ctx,
        otlptracegrpc.WithEndpoint(endpoint),
        otlptracegrpc.WithHeaders(map[string]string{"Authorization": "Bearer " + token}),
        otlptracegrpc.WithTLSCredentials(credentials.NewTLS(nil)),
    )

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithSampler(sampler.NewCoralogixSampler(sdktrace.AlwaysSample())),
        sdktrace.WithResource(res),
        sdktrace.WithSpanProcessor(sdktrace.NewBatchSpanProcessor(exp)),
    )
    defer tp.Shutdown(ctx)
    otel.SetTracerProvider(tp)

    tracer := otel.Tracer("order-service")
    _, span := tracer.Start(ctx, "process-order")
    span.SetAttributes(attribute.String("order.id", "42"))
    // ... do work ...
    span.End()
    fmt.Println("done")
}
```

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="ingress.eu2.coralogix.com:443"
export CORALOGIX_API_KEY="your-send-your-data-key"
go run main.go
```

Validation: Coralogix UI → **Explore → Tracing**.

---

## Formatting rules for all templates

- Always use code blocks with the correct language identifier.
- Replace `{{ endpoints.opentelemetry }}` template variables (from the docs source) with
  the actual regional endpoint. Use the base URL for `OTEL_EXPORTER_OTLP_ENDPOINT` — do NOT
  include `/v1/traces` in the base env var (SDK appends signal path automatically for HTTP/proto):
  - gRPC Java/.NET: `https://ingress.<CORALOGIX_REGION>.coralogix.com:443`
  - gRPC Python/Node.js: `ingress.<CORALOGIX_REGION>.coralogix.com:443`
  - gRPC Go `WithEndpoint`: `ingress.<CORALOGIX_REGION>.coralogix.com:443` (bare only)
  - HTTP/proto `OTEL_EXPORTER_OTLP_ENDPOINT`: `https://ingress.<CORALOGIX_REGION>.coralogix.com:443`
  - HTTP/proto programmatic exporter URL: `https://ingress.<CORALOGIX_REGION>.coralogix.com:443/v1/traces`
- For the API key, reference `<CORALOGIX_API_KEY>` (shell) or `os.environ["CORALOGIX_API_KEY"]` (code) — never generate example key values.
- Use inline comments in code blocks only where the line is non-obvious.
- Include validation steps in every new instrumentation answer.
- Keep the "security reminder" section — teams often overlook secret management.
- Do not document SDK installation steps inline; link to the official OpenTelemetry language
  getting-started page.
