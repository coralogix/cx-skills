# .NET OpenTelemetry Instrumentation

## Contents
- Overview
- Auto-Instrumentation (Zero-Code)
- Manual Instrumentation
- Traces
- Metrics
- Logs
- Exception Logging
- Log Framework Bridges (NLog, log4net)
- Kubernetes Injection
- Common Mistakes

Source: Coralogix .NET OpenTelemetry Instrumentation documentation.

## Legacy SDK Deprecation

The Coralogix .NET SDKs — `Coralogix.SDK` (for .NET Framework) and `CoralogixCoreSDK`
(for .NET Core) — are **deprecated** and reach end-of-life on **June 30, 2026**. This
also covers the Coralogix NLog SDK, log4net SDK, and Serilog SDK. If a user asks about
`CoralogixLogger`, `CORALOGIX_LOG_URL`, or any Coralogix-branded .NET NuGet package,
redirect them to OTel .NET instrumentation immediately. Do not explain how to configure
the deprecated SDKs.

See: https://coralogix.com/docs/user-guides/latest-updates/deprecations/dotnet-sdk-deprecation/

## Overview

.NET supports:
1. **Auto-instrumentation (zero-code)** — OpenTelemetry .NET Auto-Instrumentation profiler.
2. **Manual instrumentation** — explicit `TracerProvider`, `MeterProvider`, `LoggerProvider`
   via NuGet SDK packages.

Both paths export traces, metrics, and logs to Coralogix via OTLP/gRPC.

**Requirements:** .NET SDK 8.0 or later (for .NET Framework: 4.6.2 or later).

## Auto-Instrumentation (Zero-Code)

The [OpenTelemetry .NET Auto-Instrumentation](https://opentelemetry.io/docs/zero-code/dotnet/)
instruments .NET applications without modifying source code.

### Required environment variables

```bash
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.<CORALOGIX_REGION>.coralogix.com:443"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"
```

**Note:** For .NET auto-instrumentation, `OTEL_EXPORTER_OTLP_ENDPOINT` uses `https://` scheme
(unlike gRPC where the scheme is normally implicit). Follow the
[OpenTelemetry .NET Auto-Instrumentation docs](https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation)
for profiler setup and OS-specific installation.

### Region values

Replace `<CORALOGIX_REGION>` with: `eu1`, `eu2`, `us1`, `us2`, `ap1`, `ap2`, or `ap3`.

## Manual Instrumentation

Follow the official OpenTelemetry .NET getting-started guide for SDK installation:
https://opentelemetry.io/docs/languages/dotnet/getting-started/

Relevant NuGet package artifacts to name in manual setup answers:
`OpenTelemetry`, `OpenTelemetry.Exporter.OpenTelemetryProtocol`,
`OpenTelemetry.Extensions.Hosting`, and any signal-specific instrumentation package such as
`OpenTelemetry.Instrumentation.Runtime`. Name the NuGet artifacts, but do not include
`dotnet add package` install commands unless the user explicitly asks for commands.

**Important:** .NET OTLP exporters
require the full `https://` URI scheme — use `https://ingress.<region>.coralogix.com:443`,
not the bare `host:port` form used by Go `WithEndpoint` and commonly shown in Python/Node.js
Coralogix gRPC examples. Java also requires the `https://` URI form.

### Step 1: Create and configure the app

```bash
dotnet new console -n CoralogixOtelExample
cd CoralogixOtelExample
```

### Step 2: Set environment variables

```bash
export CORALOGIX_SERVICE_NAME="<SERVICE_NAME>"
export CORALOGIX_APP_NAME="<CX_APPLICATION_NAME>"
export CORALOGIX_SUBSYSTEM_NAME="<CX_SUBSYSTEM_NAME>"
export CORALOGIX_DOMAIN="<REGION>"   # e.g. eu2 — do not include .coralogix.com
```

### Step 3: Shared configuration setup

```csharp
using OpenTelemetry;
using OpenTelemetry.Resources;

private static CoralogixConfig LoadConfiguration()
{
    var domain = Environment.GetEnvironmentVariable("CORALOGIX_DOMAIN") ?? "EU1";
    var apiKey = Environment.GetEnvironmentVariable("CORALOGIX_API_KEY")
        ?? throw new InvalidOperationException("CORALOGIX_API_KEY is required");
    var serviceName = Environment.GetEnvironmentVariable("CORALOGIX_SERVICE_NAME") ?? "dotnet-service";
    var applicationName = Environment.GetEnvironmentVariable("CORALOGIX_APP_NAME") ?? "dotnet-app";
    var subsystemName = Environment.GetEnvironmentVariable("CORALOGIX_SUBSYSTEM_NAME") ?? "default";

    return new CoralogixConfig { Domain = domain, ApiKey = apiKey,
        ServiceName = serviceName, ApplicationName = applicationName, SubsystemName = subsystemName };
}

private static ResourceBuilder BuildResourceAttributes(CoralogixConfig config)
{
    return ResourceBuilder.CreateDefault()
        .AddService(serviceName: config.ServiceName, serviceNamespace: config.ApplicationName)
        .AddAttributes(new Dictionary<string, object>
        {
            ["cx.application.name"] = config.ApplicationName,
            ["cx.subsystem.name"] = config.SubsystemName,
        });
}

// Shared OTLP exporter config
private static void ConfigureOtlpExporter(
    OpenTelemetry.Exporter.OtlpExporterOptions options, CoralogixConfig config)
{
    options.Endpoint = new Uri($"https://ingress.{config.Domain.ToLower()}.coralogix.com:443");
    options.Protocol = OpenTelemetry.Exporter.OtlpExportProtocol.Grpc;
    options.Headers = $"Authorization=Bearer {config.ApiKey}";
}
```

### Traces

No extra package artifact is needed beyond the base NuGet artifacts above for this minimal
manual trace example.

```csharp
using OpenTelemetry.Trace;
using System.Diagnostics;

private static readonly ActivitySource ActivitySource = new("CoralogixOtelExample", "1.0.0");

private static TracerProvider ConfigureTracing(ResourceBuilder resourceBuilder, CoralogixConfig config)
{
    return Sdk.CreateTracerProviderBuilder()
        .SetResourceBuilder(resourceBuilder)
        .AddSource(ActivitySource.Name)
        .AddOtlpExporter(options => ConfigureOtlpExporter(options, config))
        .Build();
}

// Usage in main:
using (var activity = ActivitySource.StartActivity("SampleOperation"))
{
    activity?.SetTag("user.id", "user-123");
    activity?.SetStatus(ActivityStatusCode.Ok);
}
Thread.Sleep(1000); // allow export before process exit
```

Validation: Coralogix UI → **Explore → Tracing**.

### Metrics

```csharp
using OpenTelemetry.Metrics;
using System.Diagnostics.Metrics;

private static readonly Meter Meter = new("CoralogixOtelExample", "1.0.0");

private static MeterProvider ConfigureMetrics(ResourceBuilder resourceBuilder, CoralogixConfig config)
{
    return Sdk.CreateMeterProviderBuilder()
        .SetResourceBuilder(resourceBuilder)
        .AddMeter("CoralogixOtelExample")
        .AddRuntimeInstrumentation()
        .AddOtlpExporter(options => ConfigureOtlpExporter(options, config))
        .Build();
}

// Create and record a counter
var requestCounter = Meter.CreateCounter<long>("sample.counter", "requests", "Sample counter");
requestCounter.Add(1, new KeyValuePair<string, object?>("status", "success"));
Thread.Sleep(1000);
```

Validation: Coralogix Grafana → **Explore → Metric Browser**.

### Logs

```csharp
using Microsoft.Extensions.Logging;
using OpenTelemetry.Logs;

private static ILoggerFactory ConfigureLogging(ResourceBuilder resourceBuilder, CoralogixConfig config)
{
    return LoggerFactory.Create(builder =>
    {
        builder.SetMinimumLevel(LogLevel.Information);
        builder.AddOpenTelemetry(options =>
        {
            options.SetResourceBuilder(resourceBuilder);
            options.AddOtlpExporter(otlpOptions => ConfigureOtlpExporter(otlpOptions, config));
            options.IncludeFormattedMessage = true;
            options.IncludeScopes = true;
        });
    });
}

// Usage
var logger = loggerFactory.CreateLogger<Program>();
logger.LogInformation("Hello from Coralogix .NET OpenTelemetry!");
logger.LogError(new InvalidOperationException("db failed"), "request failed");
Thread.Sleep(5000); // allow export
```

Validation: Coralogix UI → **Logs**.

## Exception Logging

Pass the exception object to the logger — do not format it into the message string:

```csharp
try { /* ... */ }
catch (Exception ex)
{
    logger.LogError(ex, "Could not process item {ItemId}", 42);
}
```

Requires `OpenTelemetry.Exporter.OpenTelemetryProtocol >= 1.8.0` for exception semantic
convention support.

## Log Framework Bridges (for auto-instrumentation)

### NLog bridge

```bash
export OTEL_DOTNET_AUTO_LOGS_ENABLED=true
export OTEL_DOTNET_AUTO_LOGS_ENABLE_NLOG_BRIDGE=true
```

Supported NLog: `>= 5.0.0` and `< 7.0.0`. Available in auto-instrumentation `>= 1.14.0`.

### log4net bridge

```bash
export OTEL_DOTNET_AUTO_LOGS_ENABLED=true
export OTEL_DOTNET_AUTO_LOGS_ENABLE_LOG4NET_BRIDGE=true
```

Supported log4net: `>= 2.0.13` and `< 4.0.0`. Available in auto-instrumentation `>= 1.10.0`.

If NLog or log4net is already configured as a `Microsoft.Extensions.Logging` provider, use
the `Microsoft.Extensions.Logging` path instead of enabling the bridge — enabling both
causes duplicate logs.

## Kubernetes Injection

The OpenTelemetry Operator supports .NET auto-instrumentation injection:

```yaml
annotations:
  instrumentation.opentelemetry.io/inject-dotnet: "true"
```

## Span Status

.NET does **not** automatically set span status to `Error` when an exception is thrown.
Without explicit status setting, spanmetrics will report `STATUS_CODE_UNSET` for all spans
including those that caught exceptions — making error-rate metrics unreliable.

Always set span status explicitly in catch blocks:

```csharp
using (var activity = ActivitySource.StartActivity("ProcessOrder"))
{
    try
    {
        // ... do work ...
        activity?.SetStatus(ActivityStatusCode.Ok);
    }
    catch (Exception ex)
    {
        activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
        activity?.RecordException(ex);
        throw;
    }
}
```

`RecordException` attaches the exception as a span event following OTel semantic conventions.
Requires `OpenTelemetry.Exporter.OpenTelemetryProtocol >= 1.8.0`.

## Context Propagation (.NET Framework)

.NET 5+ (ASP.NET Core) propagates W3C `traceparent` on incoming requests automatically via
`OpenTelemetry.Instrumentation.AspNetCore`. Classic .NET Framework (ASP.NET) requires
explicit server-side setup. If traces from upstream Node.js or Java services are not
continuing into a .NET Framework backend (independent spans created instead of child spans),
confirm:

1. `OpenTelemetry.Instrumentation.AspNet` NuGet package is installed (not the Http package —
   that instruments outgoing client calls, not incoming requests)
2. `.AddAspNetInstrumentation()` is called on the `TracerProvider` so the server reads and
   continues the incoming `traceparent` header
3. The upstream service sends W3C format headers (not B3/Zipkin)

**Note:** `AddHttpClientInstrumentation()` / `OpenTelemetry.Instrumentation.Http` instruments
outgoing `HttpClient` calls and does NOT fix broken incoming trace propagation.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Wrong domain casing (e.g. `EU2` instead of `eu2` in URI) | Connection failure | Lowercase the domain in the `Uri` constructor |
| `Thread.Sleep` too short | No data exported | Allow at least 1–5 seconds before process exit for async export |
| Missing `cx.application.name` / `cx.subsystem.name` | APM features degraded | Add to `AddAttributes` in `ResourceBuilder` |
| NLog bridge + `Microsoft.Extensions.Logging` NLog provider both active | Duplicate logs | Use only one path |
| `OpenTelemetry.Exporter.OpenTelemetryProtocol < 1.8.0` | Exceptions not emitted as semantic convention fields | Upgrade to `>= 1.8.0` |
| Exceptions thrown but spanmetrics show `STATUS_CODE_UNSET` | Span status not set explicitly | Call `activity.SetStatus(ActivityStatusCode.Error, message)` in every catch block |
| Auto-instrumentation on musl-based systems (Alpine) | glibc build fails on musl libc | Use the musl-specific build of the auto-instrumentation profiler |
