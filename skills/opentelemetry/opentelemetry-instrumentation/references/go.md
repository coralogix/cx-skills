# Go OpenTelemetry Instrumentation

## Contents
- Overview
- Prerequisites
- Required environment variables
- Step 1: Initialize Go module and shared setup
- Traces
- Metrics
- Logs (beta)
- Exception Logging
- Common Mistakes

Source: Coralogix Golang OpenTelemetry Instrumentation documentation.

## Legacy SDK Deprecation

The Coralogix Go SDK (`go-coralogix-sdk`, `github.com/coralogix/go-coralogix-sdk`) is
**deprecated** and reaches end-of-life on **June 30, 2026**. No bug fixes, security patches,
or new features will be provided after that date. If a user asks about `go-coralogix-sdk`,
`coralogix.NewCoralogixLogger`, or the `CORALOGIX_LOG_URL` pattern, redirect them to this
OpenTelemetry Go instrumentation guide immediately. Do not explain how to configure or use
the deprecated SDK.

See: https://coralogix.com/docs/user-guides/latest-updates/deprecations/

## Overview

This skill covers **manual Go SDK instrumentation**. OpenTelemetry also has Go zero-code/eBPF
options such as OBI and the Auto SDK, but those are out of scope here.

**FIPS / boringcrypto note:** Go auto-instrumentation (eBPF/OBI) is incompatible with
`boringcrypto`-compiled (`GOEXPERIMENT=boringcrypto`) binaries and panics with
"invalid semantic version" since v0.21.0. If a user asks why Go auto-instrumentation fails
on a FIPS-compliant build, redirect them to this manual SDK guide — it works correctly on
FIPS builds. All three signals
(traces, metrics, logs) use a shared setup pattern with reusable provider constructors.

Go OTel signal stability:
- Traces: **stable**
- Metrics: **stable**
- Logs: **beta** (API and behavior may change)

## Prerequisites

- Go 1.25+
- Coralogix Send-Your-Data API key and OTLP endpoint.

## Required environment variables

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="ingress.<CORALOGIX_REGION>.coralogix.com:443"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"
```

## Step 1: Initialize Go module and shared setup

Use the official OpenTelemetry Go getting-started guide for SDK installation:
https://opentelemetry.io/docs/languages/go/getting-started/

**Semconv version must match the installed OTel SDK.** The `semconv/vX.Y.Z` packages are
part of the `go.opentelemetry.io/otel` module — do **not** add them as separate `go.mod`
require entries. Import the package version that matches `SchemaURL` used by `resource.Default()`
(same as the otel SDK version). A mismatch panics at runtime with "conflicting Schema URL".
To find the right version: check which `semconv/v*` directories exist under your installed
`go.opentelemetry.io/otel` module in `$(go env GOPATH)/pkg/mod`.

```go
package main

import (
    "errors"
    "os"

    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/sdk/resource"
    semconv "go.opentelemetry.io/otel/semconv/v1.40.0"  // match your SDK version
)

type OtelSetup struct {
    Resource *resource.Resource
    endpoint string
    headers  map[string]string
}

func Configure() (*OtelSetup, error) {
    endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT") // e.g. ingress.eu2.coralogix.com:443
    token := os.Getenv("CORALOGIX_API_KEY")

    if endpoint == "" || token == "" {
        return nil, errors.New("OTEL_EXPORTER_OTLP_ENDPOINT and CORALOGIX_API_KEY must be set")
    }

    res, err := resource.Merge(
        resource.Default(),
        resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceName("<SERVICE_NAME>"),
            semconv.ServiceVersion("0.1.0"),
            attribute.String("cx.application.name", "<CX_APPLICATION_NAME>"),
            attribute.String("cx.subsystem.name", "<CX_SUBSYSTEM_NAME>"),
        ),
    )
    if err != nil {
        return nil, err
    }

    return &OtelSetup{
        Resource: res,
        endpoint: endpoint,
        headers:  map[string]string{"Authorization": "Bearer " + token},
    }, nil
}
```

## Traces

Use the official OpenTelemetry Go getting-started guide for trace SDK setup:
https://opentelemetry.io/docs/languages/go/getting-started/

Package artifacts used by this trace setup:
`go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc`,
`go.opentelemetry.io/otel/sdk/trace`, `google.golang.org/grpc/credentials`, and
`github.com/coralogix/coralogix-opentelemetry-go/sampler`. The Coralogix sampler package
enables APM Transactions; do not omit it when transactions matter.

```go
import (
    "context"
    "time"

    "github.com/coralogix/coralogix-opentelemetry-go/sampler"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    "google.golang.org/grpc/credentials"
)

func (s *OtelSetup) NewTracerProvider(ctx context.Context) (*sdktrace.TracerProvider, error) {
    exp, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithEndpoint(s.endpoint),
        otlptracegrpc.WithHeaders(s.headers),
        otlptracegrpc.WithTLSCredentials(credentials.NewTLS(nil)),
        otlptracegrpc.WithTimeout(5*time.Second),
    )
    if err != nil {
        return nil, err
    }

    return sdktrace.NewTracerProvider(
        // CoralogixSampler enables Coralogix APM transactions
        sdktrace.WithSampler(sampler.NewCoralogixSampler(sdktrace.AlwaysSample())),
        sdktrace.WithResource(s.Resource),
        sdktrace.WithSpanProcessor(sdktrace.NewBatchSpanProcessor(exp)),
    ), nil
}
```

### Creating spans

```go
import (
    "go.opentelemetry.io/otel"
    otel_trace "go.opentelemetry.io/otel/trace"
    "go.opentelemetry.io/otel/attribute"
)

const tracerName = "my-service"

func handleRequest(ctx context.Context) {
    tracer := otel.Tracer(tracerName)
    ctx, span := tracer.Start(ctx, "handle-request",
        otel_trace.WithSpanKind(otel_trace.SpanKindServer),
    )
    defer span.End()

    span.SetAttributes(
        attribute.String("http.method", "GET"),
        attribute.String("http.route", "/roll"),
    )
    // ... do work ...
}
```

### Wire up and shutdown

```go
func main() {
    ctx := context.Background()

    setup, err := Configure()
    if err != nil { panic(err) }

    tp, err := setup.NewTracerProvider(ctx)
    if err != nil { panic(err) }
    defer func() {
        if err := tp.Shutdown(ctx); err != nil { fmt.Println(err) }
    }()

    otel.SetTracerProvider(tp)
    // ... register handlers, start server ...
}
```

Validation: Coralogix UI → **Explore → Tracing**.

## Metrics

Use the official OpenTelemetry Go getting-started guide for metric SDK setup:
https://opentelemetry.io/docs/languages/go/getting-started/

Package artifacts used by this metric setup:
`go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc`,
`go.opentelemetry.io/otel/sdk/metric`, and `google.golang.org/grpc/credentials`.
Use `credentials.NewTLS(nil)` on this exporter too.

```go
import (
    "go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
    sdkmetric "go.opentelemetry.io/otel/sdk/metric"
)

func (s *OtelSetup) NewMeterProvider(ctx context.Context) (*sdkmetric.MeterProvider, error) {
    exp, err := otlpmetricgrpc.New(ctx,
        otlpmetricgrpc.WithEndpoint(s.endpoint),
        otlpmetricgrpc.WithHeaders(s.headers),
        otlpmetricgrpc.WithTLSCredentials(credentials.NewTLS(nil)),
        otlpmetricgrpc.WithTimeout(5*time.Second),
    )
    if err != nil {
        return nil, err
    }

    return sdkmetric.NewMeterProvider(
        sdkmetric.WithResource(s.Resource),
        sdkmetric.WithReader(sdkmetric.NewPeriodicReader(exp)),
    ), nil
}
```

```go
// In main:
otel.SetMeterProvider(mp)
meter := otel.Meter("my-service")
reqCounter, _ := meter.Int64Counter("http.server.requests",
    metric.WithDescription("Total HTTP requests"),
)
reqCounter.Add(ctx, 1, metric.WithAttributes(attribute.String("method", "GET")))
```

Validation: Coralogix Grafana → **Explore → Metric Browser**.

## Logs (beta)

Use the official OpenTelemetry Go getting-started guide for log SDK setup:
https://opentelemetry.io/docs/languages/go/getting-started/

Package artifacts used by this log setup:
`go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc`,
`go.opentelemetry.io/otel/sdk/log`, `go.opentelemetry.io/otel/log/global`,
`go.opentelemetry.io/contrib/bridges/otelslog`, and `google.golang.org/grpc/credentials`.
Use `credentials.NewTLS(nil)` on this exporter too.

```go
import (
    "go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc"
    logsdk "go.opentelemetry.io/otel/sdk/log"
    "go.opentelemetry.io/otel/log/global"
    "go.opentelemetry.io/contrib/bridges/otelslog"
    "log/slog"
)

func (s *OtelSetup) NewLoggerProvider(ctx context.Context) (*logsdk.LoggerProvider, error) {
    exp, err := otlploggrpc.New(ctx,
        otlploggrpc.WithEndpoint(s.endpoint),
        otlploggrpc.WithHeaders(s.headers),
        otlploggrpc.WithTLSCredentials(credentials.NewTLS(nil)),
        otlploggrpc.WithTimeout(5*time.Second),
    )
    if err != nil {
        return nil, err
    }
    return logsdk.NewLoggerProvider(
        logsdk.WithResource(s.Resource),
        logsdk.WithProcessor(logsdk.NewBatchProcessor(exp)),
    ), nil
}

// Wire slog bridge in main:
global.SetLoggerProvider(lp)
h := otelslog.NewHandler("my-app", otelslog.WithLoggerProvider(lp))
slog.SetDefault(slog.New(h))

slog.Info("Hello from Coralogix Go OTel")
```

Validation: Coralogix UI → **Logs**.

## Exception Logging

```go
import "go.opentelemetry.io/otel/log"

func emitException(ctx context.Context, logger log.Logger) {
    err := errors.New("database connection failed")
    record := log.Record{}
    record.SetSeverity(log.SeverityError)
    record.SetBody(log.StringValue("request failed"))
    record.SetErr(err)   // available in go.opentelemetry.io/otel/log >= v0.18.0
    logger.Emit(ctx, record)
}
```

### Using otelzap bridge

Use the official OpenTelemetry Go documentation for bridge installation details:
https://opentelemetry.io/docs/languages/go/getting-started/

```go
core := otelzap.NewCore("my-app", otelzap.WithLoggerProvider(lp))
logger := zap.New(core)
logger.Error("request failed", zap.Error(errors.New("db failed")))
```

Use `zap.Error(err)` — named errors like `zap.NamedError("db", err)` emit as regular
attributes, not exception semantic convention fields.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Missing TLS credentials | TLS handshake failure | Use `credentials.NewTLS(nil)` on all exporters |
| `OTEL_EXPORTER_OTLP_ENDPOINT` includes `https://` | Dial error | Use bare host:port `ingress.<region>.coralogix.com:443`; keep the required `:443` port |
| Semconv version mismatches installed SDK | `panic: conflicting Schema URL` at startup | Import `semconv/vX.Y.Z` that matches your `go.opentelemetry.io/otel` version; do not add semconv as a separate `go.mod` require entry |
| Missing `CoralogixSampler` (Go sampler) | No Transactions in APM | Wrap sampler: `sampler.NewCoralogixSampler(sdktrace.AlwaysSample())` |
| No `tp.Shutdown()` deferred | Last spans dropped | Always defer `Shutdown` with a timeout context |
| Logs API used below `v0.18.0` | `SetErr` not available | Upgrade `go.opentelemetry.io/otel/log` to `>= v0.18.0` |
