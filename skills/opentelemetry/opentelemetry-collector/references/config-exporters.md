# OpenTelemetry Collector: Exporters Configuration

This reference covers the `coralogix`, `coralogix/resource_catalog`, and `loadbalancing` exporters.

## Coralogix Exporter

The `coralogix` exporter ships telemetry to Coralogix over OTLP. Regional routing is handled by a `domain` field.

```yaml
exporters:
  coralogix:
    domain: "eu2.coralogix.com"          # bare hostname for your region; NOT a URL
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    application_name: "my-app"
    subsystem_name: "my-service"
    timeout: 30s
```

### Critical Rules

- **Domain is a bare hostname:** Set `domain:` to the regional data-ingestion hostname (e.g., `eu2.coralogix.com`). Never use `endpoint:`, `https://`, or a trailing slash. Never use a UI hostname.
- **Bracketed syntax for env vars:** Use `${env:CORALOGIX_PRIVATE_KEY}`. The unbracketed `$CORALOGIX_PRIVATE_KEY` form silently fails to expand in newer versions (≥ v0.76).
- **Dynamic Routing:** Use `application_name_attributes` and `subsystem_name_attributes` to dynamically route telemetry based on resource attributes, falling back to static strings:

```yaml
exporters:
  coralogix:
    domain: "eu2.coralogix.com"
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    application_name_attributes: ["service.namespace", "application"]
    subsystem_name_attributes: ["service.name", "k8s.deployment.name"]
    application_name: "default-app"      # fallback when no derived value
    subsystem_name: "default-subsystem"
```

### Transport protocol

The coralogix exporter uses gRPC by default. Do not set `protocol: http` — since v0.144 of
`opentelemetry-collector-contrib`, the exporter validates HTTP compatibility for **all** signals
at startup, including profiles. Profiles do not support HTTP transport, so the exporter rejects
`protocol: http` even when no profiles pipeline is configured:

```
Error: exporters::coralogix: profiles signal is not supported with HTTP protocol,
use gRPC protocol (default) instead
```

The fix is to remove the `protocol:` field entirely (gRPC is the default and works for all signals).
This validation runs at startup before pipeline wiring, so the error appears even if profiles are
never exported.

### Transport protocol

Do not set `protocol: http`. Since collector-contrib v0.144, the coralogix exporter validates
HTTP compatibility for all signals at startup — including profiles, which require gRPC. The
validation runs before pipeline wiring, so `protocol: http` fails even with no profiles pipeline:

```
Error: exporters::coralogix: profiles signal is not supported with HTTP protocol
```

Remove the `protocol:` field. gRPC is the default and works for all signals.

### Back-pressure
The exporter's `sending_queue` and `retry_on_failure` blocks provide resilience and back-pressure.

```yaml
exporters:
  coralogix:
    domain: "eu2.coralogix.com"
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 5000
      storage: file_storage                # optional: persist to disk for crash-safe buffering
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
    timeout: 30s
```

## Infrastructure Explorer / Resource Catalog Exporter

Entity metadata requires a dedicated exporter and specific HTTP headers.

```yaml
exporters:
  coralogix/resource_catalog:
    domain: "eu2.coralogix.com"
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    application_name: "resource"
    subsystem_name: "catalog"
    logs:
      headers:
        x-coralogix-ingress: "metadata-as-otlp-logs/v1"
    timeout: 120s
```

- **Required Header:** Without `x-coralogix-ingress: metadata-as-otlp-logs/v1`, entity events reach the logs pipeline but never populate Infrastructure Explorer.

## Loadbalancing Exporter

Used on the agent daemonset to route spans to a central gateway deployment based on `trace_id`. This is required for `tail_sampling` on the gateway to evaluate complete traces.

```yaml
exporters:
  loadbalancing:
    protocol:
      otlp:
        tls:
          insecure: true
    resolver:
      dns:
        hostname: otel-gateway.coralogix.svc.cluster.local
        port: 4317
    routing_key: traceID
```

- **Routing Key:** `routing_key: traceID` enforces consistent hashing on the trace ID. Without it, spans distribute round-robin, and the gateway's tail sampler sees incomplete traces, producing `sampling_trace_dropped_too_early` metrics.
