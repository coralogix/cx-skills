# Coralogix Endpoints for SDK Instrumentation

## Contents
- OTLP Endpoint for Direct SDK Export
- Regional Domains
- Authentication Header
- Coralogix-Specific OTLP Headers
- Endpoint vs Domain — SDK vs Collector
- PrivateLink

## OTLP Endpoint for Direct SDK Export

When exporting directly from the SDK (not via a collector), the required endpoint format
depends on the language:

**Java and .NET** — the SDK's URI parser requires a full URI with `https://` scheme:
```
https://ingress.<region>.coralogix.com:443
```

**Python and Node.js** — the standard Coralogix gRPC form is bare `host:port`:
```
ingress.<region>.coralogix.com:443
```
The OpenTelemetry gRPC exporter spec also requires SDKs to accept `https://host:port`.
So `https://ingress.<region>.coralogix.com:443` is valid for Python and Node.js gRPC,
but prefer the bare form in generated Coralogix examples.

**Go** — `WithEndpoint` uses bare `host:port` with no scheme or path:
```
ingress.<region>.coralogix.com:443
```
Use `credentials.NewTLS(nil)` with Go gRPC exporters. Do not pass `https://` to
`WithEndpoint`; use `WithEndpointURL` only when intentionally using a full URL option.

TLS is always enabled on port 443. Do not use `http://` for direct Coralogix export — all
Coralogix OTLP endpoints require TLS.

For HTTP/protobuf exporters (e.g. Node.js `@opentelemetry/exporter-trace-otlp-proto`),
append the signal path:

```
https://ingress.<region>.coralogix.com:443/v1/traces
https://ingress.<region>.coralogix.com:443/v1/metrics
https://ingress.<region>.coralogix.com:443/v1/logs
```

Every generated direct-export setup must show these required environment variables:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.<CORALOGIX_REGION>.coralogix.com:443/v1/traces"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer $CORALOGIX_API_KEY"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"
```

For gRPC exporters, use `https://ingress.<CORALOGIX_REGION>.coralogix.com:443` (Java/.NET) or
the standard bare form `ingress.<CORALOGIX_REGION>.coralogix.com:443` (Python/Node.js/Go),
and keep TLS enabled. Python and Node.js also accept the `https://host:port` URL form.

## Regional Domains

| Region name | Domain | OTLP gRPC endpoint |
|---|---|---|
| US1 | `us1.coralogix.com` | `ingress.us1.coralogix.com:443` |
| US2 | `us2.coralogix.com` | `ingress.us2.coralogix.com:443` |
| EU1 | `eu1.coralogix.com` | `ingress.eu1.coralogix.com:443` |
| EU2 | `eu2.coralogix.com` | `ingress.eu2.coralogix.com:443` |
| AP1 | `ap1.coralogix.com` | `ingress.ap1.coralogix.com:443` |
| AP2 | `ap2.coralogix.com` | `ingress.ap2.coralogix.com:443` |
| AP3 | `ap3.coralogix.com` | `ingress.ap3.coralogix.com:443` |

**How to find your region:** Your Coralogix platform URL shows the region — e.g.
`https://dashboard.eu2.coralogix.com` → region is `eu2`, domain is `eu2.coralogix.com`,
OTLP endpoint is `ingress.eu2.coralogix.com:443`.

## Authentication Header

All direct OTLP export to Coralogix requires a **Send-Your-Data API key** passed as an
OTLP header:

```
Authorization=Bearer $CORALOGIX_API_KEY
```

The key is found in the Coralogix platform under **Settings → Users and Teams → API Keys**.
Only **Send-Your-Data** keys work for telemetry ingestion. Team keys and personal keys do not.

### Setting the header per language

**Environment variable (Java, Node.js, Go, most gRPC SDK env config):**
```bash
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer $CORALOGIX_API_KEY"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"
```

**Python — URL encoding required in env vars:**
```bash
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20$CORALOGIX_API_KEY"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"
```
Note: `%20` = space between `Bearer` and the key value.

**Java — env var or JVM system property:**
```bash
# env var
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer $CORALOGIX_API_KEY"
# or JVM property
-Dotel.exporter.otlp.headers="Authorization=Bearer $CORALOGIX_API_KEY"
```

**Go — programmatic (headers map):**
```go
headers: map[string]string{"Authorization": "Bearer " + token}
```

**.NET — programmatic (OTLP options):**
```csharp
options.Endpoint = new Uri("https://ingress.<CORALOGIX_REGION>.coralogix.com:443");
options.Protocol = OtlpExportProtocol.Grpc;
options.Headers = $"Authorization=Bearer {config.ApiKey}";
```

## Coralogix-Specific OTLP Headers

When calling the Coralogix OTLP endpoint directly, you may pass application and subsystem
names as OTLP headers in addition to resource attributes. Both mechanisms work; resource
attributes are the standard approach:

| Header | Purpose |
|---|---|
| `CX-Application-Name` | Alternative to `cx.application.name` resource attribute |
| `CX-Subsystem-Name` | Alternative to `cx.subsystem.name` resource attribute |

Prefer setting these as **resource attributes** (`cx.application.name`, `cx.subsystem.name`)
in the SDK — they propagate to all signals. Header-based values only reach the signals on
that specific exporter.

## Endpoint vs Domain — SDK vs Collector

The OTel Collector's `coralogix` exporter uses `domain: eu2.coralogix.com` (bare hostname,
no `ingress.` prefix, no port). SDK endpoints use `ingress.` prefix and port 443. The
required format varies by language and protocol.

| Shipper | Format | Example |
|---|---|---|
| OTel SDK direct gRPC (Python, Node.js) | Prefer `ingress.<region>.coralogix.com:443`; `https://host:port` also accepted | `ingress.eu2.coralogix.com:443` |
| OTel SDK direct gRPC (Go `WithEndpoint`) | `ingress.<region>.coralogix.com:443` | `ingress.eu2.coralogix.com:443` |
| OTel SDK direct gRPC (Java, .NET) | `https://ingress.<region>.coralogix.com:443` | `https://ingress.eu2.coralogix.com:443` |
| OTel SDK direct HTTP/protobuf | `https://ingress.<region>.coralogix.com:443/v1/<signal>` | `https://ingress.eu2.coralogix.com:443/v1/traces` |
| OTel Collector `coralogix` exporter | `domain: <region>.coralogix.com` | `domain: eu2.coralogix.com` |

## PrivateLink

When using AWS PrivateLink, replace `ingress.<region>` with `ingress.private.<region>`:
```
ingress.private.eu2.coralogix.com:443
```
