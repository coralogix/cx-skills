# Troubleshooting — SDK Instrumentation to Coralogix

## Contents
- Symptom → Root Cause Table
- Enable SDK Debug Logging
- Connectivity Check
- Decision Flow
- Out-of-Scope Issues

Use this reference for "no data", "missing traces", "missing metrics", or "missing logs"
reports from the application SDK side (not collector-side issues).

## Symptom → Root Cause Table

| Symptom | Most likely cause | First action |
|---|---|---|
| No traces in Coralogix, no error in app | Endpoint wrong or auth header missing | Enable SDK debug logging; check `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` |
| 401 / Unauthorized from Coralogix | Wrong API key type or malformed auth header | Confirm key is Send-Your-Data; check `Authorization=Bearer <key>` format |
| `connection refused` or timeout | Wrong region / DNS failure / port blocked | Verify endpoint `ingress.<region>.coralogix.com:443`; test connectivity with `curl` or `nc` |
| TLS handshake failure or silent export failure | Go: missing `credentials.NewTLS`; Java/.NET: endpoint missing `https://` scheme | Add TLS credentials (Go); for Java and .NET ensure endpoint is `https://ingress.<region>.coralogix.com:443` — bare `host:port` fails because the Java/dotnet OTLP exporter performs URI parsing |
| Traces arrive but no APM Transactions | Missing `CoralogixTransactionSampler` | Add `CoralogixTransactionSampler` to sampler chain (Python, Node.js, Go) |
| Python: traces arrive but auth fails intermittently | OTLP header not URL encoded | Replace `Bearer <key>` with `Bearer%20<key>` in `OTEL_EXPORTER_OTLP_HEADERS` |
| Node.js: no transactions despite setting up CoralogixTransactionSampler | Using bundled auto-instrumentation | Switch to individual `instrumentation.js` method |
| Java: no traces at startup | Agent JAR not attached | Check for `[otel.javaagent ...]` log line; verify `-javaagent:` path in JAVA_TOOL_OPTIONS |
| Traces visible but no `cx.application.name` / `cx.subsystem.name` in Coralogix | Missing resource attributes | Add `cx.application.name` and `cx.subsystem.name` to `OTEL_RESOURCE_ATTRIBUTES` |
| Metrics not appearing in Grafana | Metrics exporter set to `"none"` | Set `OTEL_METRICS_EXPORTER=otlp` (or `otlp_proto_grpc` for Python) |
| Go: last spans missing at process exit | No deferred `tp.Shutdown()` | Always `defer tp.Shutdown(ctx)` with a timeout context |
| .NET: no data exported before process exit | `Thread.Sleep` too short | Add 1–5 second sleep after span/metric creation before exit |
| .NET: no traces exported despite endpoint/auth set | `OTEL_TRACES_EXPORTER` is empty or `"none"` | Set `OTEL_TRACES_EXPORTER=otlp` |
| Logs cannot be correlated with traces | Missing trace/span context in structured logs | Include `trace_id` and `span_id` in log records emitted inside active spans |
| Metrics are too expensive or unusable | High-cardinality metric attributes | Keep metric attributes bounded; avoid user IDs, request IDs, raw paths, and timestamps |
| Data in wrong Coralogix account / team | Wrong region for the account | Confirm region from Coralogix UI URL (`dashboard.<region>.coralogix.com`) |
| APM Service Catalog empty; all spans show as `internal` or `client`, no `server` spans | Auto-instrumentation missing server-side framework library, or framework not instrumented | Verify the HTTP server framework instrumentation library is loaded (e.g. `@opentelemetry/instrumentation-express`, Spring MVC, ASP.NET Core); check SDK debug logs for active instrumentations list |
| Spanmetrics show `STATUS_CODE_UNSET` for error spans | SDK not explicitly setting span status on exceptions | Java and Node.js auto-set span status via exception handlers; .NET requires explicit `activity.SetStatus(ActivityStatusCode.Error, message)` in catch blocks |
| Distributed trace broken: downstream service creates independent spans instead of continuing the trace | W3C TraceContext propagation not configured on the receiving service | Verify all services in the chain use W3C `traceparent` (not B3/Zipkin); .NET Framework specifically needs `OpenTelemetry.Instrumentation.AspNet` + `AddAspNetInstrumentation()` on the receiving `TracerProvider` to extract incoming trace context |

## Enable SDK Debug Logging

Debug logging from the OTel SDK is the fastest way to see what is happening at export time.

### Java

```bash
export OTEL_LOG_LEVEL=debug
# or JVM property:
-Dotel.log.level=debug
```

Look for `io.opentelemetry.exporter.otlp` log messages showing export attempts.

### Python

```bash
export OTEL_PYTHON_LOG_LEVEL=debug
```

Or in code before setting up providers:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Node.js

```js
const { diag, DiagConsoleLogger, DiagLogLevel } = require('@opentelemetry/api');
diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
```

Add this before any SDK initialization.

### .NET

```bash
export OTEL_LOG_LEVEL=debug
```

For SDK self-diagnostics, create `OTEL_DIAGNOSTICS.json` in the process working directory:
```json
{
  "LogDirectory": ".",
  "FileSize": 32768,
  "LogLevel": "Warning",
  "FormatMessage": "true"
}
```

Or configure application logging via `appsettings.json` for ASP.NET Core:
```json
{
  "Logging": {
    "LogLevel": {
      "OpenTelemetry": "Debug"
    }
  }
}
```

### Go

The Go SDK does not have a built-in env var for debug logging. Use the OTel error handler:

```go
otel.SetErrorHandler(otel.ErrorHandlerFunc(func(err error) {
    fmt.Fprintf(os.Stderr, "OTEL error: %v\n", err)
}))
```

## Connectivity Check

Test OTLP endpoint reachability from the application host:

```bash
# Check TCP connectivity to the OTLP gRPC endpoint
nc -zv ingress.<CORALOGIX_REGION>.coralogix.com 443

# Or with curl (HTTP/proto)
curl -v https://ingress.<CORALOGIX_REGION>.coralogix.com:443/v1/traces \
  -H "Authorization: Bearer <CORALOGIX_API_KEY>" \
  -H "Content-Type: application/x-protobuf" \
  -d "" 2>&1 | head -20
```

A 400 response from Coralogix (empty body) confirms connectivity and auth work. A timeout or
`connection refused` points to a network or firewall issue.

## Decision Flow

```
No data in Coralogix?
│
├─ Does SDK debug log show export attempts?
│   ├─ No → SDK not initialized or signal exporter = "none" → fix init / exporter config
│   └─ Yes → export errors shown?
│       ├─ 401/403 → wrong key or malformed auth header
│       ├─ timeout/refused → network, firewall, wrong endpoint
│       └─ No errors, 0 spans exported → nothing instrumented; no traffic; sampler dropping all
│
├─ Is OTEL_EXPORTER_OTLP_ENDPOINT correct?
│   Format: https://ingress.<region>.coralogix.com:443 (Java/.NET gRPC),
│   ingress.<region>.coralogix.com:443 (standard Python/Node.js/Go gRPC),
│   or https://....:443/v1/traces (HTTP/protobuf)
│
├─ Is OTEL_EXPORTER_OTLP_HEADERS correct?
│   Format: Authorization=Bearer <key>
│   Python: Authorization=Bearer%20<key> (URL-encoded space)
│
├─ Are service identity attributes present?
│   Check OTEL_SERVICE_NAME plus cx.application.name and cx.subsystem.name in OTEL_RESOURCE_ATTRIBUTES
│
├─ Is telemetry safe and queryable?
│   Avoid sensitive data, keep span names low-cardinality, and keep metric labels bounded
│
└─ Is the region correct?
    Check: Coralogix platform URL → dashboard.<region>.coralogix.com
```

## Out-of-Scope Issues

If the SDK is exporting successfully (no export errors, data visible in Coralogix) but:

- **Data is missing enrichment** (no pod name, no namespace) — this is a collector-side or
  `k8sattributes` issue; use the `opentelemetry-collector` skill.
- **Broken distributed trace propagation** (downstream creates independent spans despite receiving `traceparent`) — check that all services use W3C TraceContext propagator; .NET Framework needs `OpenTelemetry.Instrumentation.AspNet` + `AddAspNetInstrumentation()` on the receiving service (not `AddHttpClientInstrumentation`, which only covers outgoing calls); verify intermediaries (load balancers, API gateways) are not stripping the `traceparent` header.
- **Span data is malformed** (wrong span kind, missing parent) — instrumentation library or propagator configuration issue in the app, not a Coralogix issue.
- **Platform features not working** (APM service map incomplete, Infrastructure Explorer
  empty) — verify resource attributes first; then check collector config.
