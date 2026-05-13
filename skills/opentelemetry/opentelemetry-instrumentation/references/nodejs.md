# Node.js OpenTelemetry Instrumentation

## Contents
- Overview
- Required packages
- Bundled Auto-Instrumentation
- Individual Auto-Instrumentation (supports Coralogix transactions)
- Manual Instrumentation
- Exception Logging
- Kubernetes Injection
- Common Mistakes

Source: Coralogix Node.js OpenTelemetry Instrumentation documentation.

## Legacy SDK Deprecation

The Coralogix Node.js SDK (`coralogix-logger`, `@coralogix/coralogix-sdk`) and the
Coralogix Winston and Bunyan integrations are **deprecated** and reach end-of-life on
**June 30, 2026**. The official Coralogix Node.js SDK docs page has already been rewritten
to show OpenTelemetry as the replacement. If a user asks about `coralogix-logger`, the
Coralogix Winston integration, or the Coralogix Bunyan integration, redirect them to OTel
Node.js instrumentation immediately. Do not explain how to configure the deprecated packages.

See: https://coralogix.com/docs/user-guides/latest-updates/deprecations/

## Prerequisites

- Node.js `^18.19.0 || >=20.6.0` (required by OTel JS SDK 2.x — Node 14/16 are not supported)
- Coralogix Send-Your-Data API key and region/domain.

## Overview

Node.js supports three approaches:

1. **Bundled auto-instrumentation** — loads all available auto-instrumentation libraries via `NODE_OPTIONS`.
2. **Individual auto-instrumentation** — custom `instrumentation.js` with chosen libraries.
3. **Manual instrumentation** — explicit `BasicTracerProvider` + span creation.

**Coralogix transactions caveat:** Bundled auto-instrumentation is NOT supported for
Coralogix transactions (APM → Transactions view). Use individual auto-instrumentation or
manual instrumentation to enable `CoralogixTransactionSampler`.

## Required packages

Use the official OpenTelemetry Node.js getting-started guide for SDK installation:
https://opentelemetry.io/docs/languages/js/getting-started/nodejs/

For Coralogix APM Transactions, include `@coralogix/opentelemetry` in the same dependency
management flow.

## Bundled Auto-Instrumentation

Set environment variables and use `NODE_OPTIONS` to load the registration library:

```bash
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
export OTEL_EXPORTER_OTLP_COMPRESSION="gzip"
# gRPC endpoint: bare host:port is the standard Coralogix form; https://host:port is also accepted
export OTEL_EXPORTER_OTLP_ENDPOINT="ingress.<CORALOGIX_REGION>.coralogix.com:443"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
export OTEL_NODE_RESOURCE_DETECTORS="all"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"

node --require @opentelemetry/auto-instrumentations-node/register YourApp.js
```

Or using `NODE_OPTIONS`:
```bash
export NODE_OPTIONS="--require @opentelemetry/auto-instrumentations-node/register"
node YourApp.js
```

**Reminder:** Env vars cannot be set inside the application code — they must be available
before the auto-instrumentation library starts at process startup.

**Limitation:** Bundled auto-instrumentation does NOT support Coralogix transactions.
Switch to individual method below if transactions are needed.

**ESM apps (using `import` syntax):** `--require` does not fire for ES modules — auto-instrumentation silently does nothing. Use `--import` plus the loader hook instead:
```bash
node --experimental-loader=@opentelemetry/instrumentation/hook.mjs \
     --import @opentelemetry/auto-instrumentations-node/register YourApp.mjs
```

## Individual Auto-Instrumentation (supports Coralogix transactions)

Create an `instrumentation.js` file:

```js
// instrumentation.js
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const opentelemetry = require("@opentelemetry/sdk-node");
const { CoralogixTransactionSampler } = require("@coralogix/opentelemetry");
const { AlwaysOnSampler } = require("@opentelemetry/sdk-trace-base");

// Exporter is configured via env vars (OTEL_TRACES_EXPORTER, OTEL_EXPORTER_OTLP_PROTOCOL,
// OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_HEADERS) — same as the bundled approach.
const sdk = new opentelemetry.NodeSDK({
  sampler: new CoralogixTransactionSampler(new AlwaysOnSampler()),
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
    // add more individual instrumentation libraries as needed
  ],
});

sdk.start();
```

Use the same environment variables as bundled (above), then run:

```bash
node --require ./instrumentation.js YourApp.js
```

This approach allows `CoralogixTransactionSampler` to be wired into the sampler chain,
enabling Coralogix Transactions support.

## Manual Instrumentation

Full manual control over span creation using `NodeTracerProvider`:

```js
const opentelemetry = require('@opentelemetry/api');
const { resourceFromAttributes } = require('@opentelemetry/resources');
const { ATTR_SERVICE_NAME } = require('@opentelemetry/semantic-conventions');
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { SimpleSpanProcessor, AlwaysOnSampler } = require('@opentelemetry/sdk-trace-base');
const { OTLPTraceExporter } = require("@opentelemetry/exporter-trace-otlp-proto");
const { CoralogixTransactionSampler } = require('@coralogix/opentelemetry');

const exporter = new OTLPTraceExporter({
  timeoutMillis: 15000,
  // HTTP/proto exporter requires /v1/traces path
  url: 'https://ingress.<CORALOGIX_REGION>.coralogix.com:443/v1/traces',
  headers: {
    Authorization: `Bearer ${process.env.CORALOGIX_API_KEY}`,
  },
});

const provider = new NodeTracerProvider({
  resource: resourceFromAttributes({
    [ATTR_SERVICE_NAME]: '<SERVICE_NAME>',
    'cx.application.name': '<CX_APPLICATION_NAME>',
    'cx.subsystem.name': '<CX_SUBSYSTEM_NAME>',
  }),
  sampler: new CoralogixTransactionSampler(new AlwaysOnSampler()),
  spanProcessors: [new SimpleSpanProcessor(exporter)],
});

provider.register();

// Graceful shutdown
['SIGINT', 'SIGTERM'].forEach(signal => {
  process.on(signal, () => provider.shutdown().catch(console.error));
});

const tracer = opentelemetry.trace.getTracer('<SERVICE_NAME>');
const span = tracer.startSpan('main');
// ... do work ...
span.end();
```

### Required package artifacts for manual

Name these package artifacts when explaining the manual setup, but use the official
OpenTelemetry Node.js getting-started guide for installation details and current versions:

- `@opentelemetry/api`
- `@opentelemetry/exporter-trace-otlp-proto`
- `@opentelemetry/resources`
- `@opentelemetry/sdk-trace-base`
- `@opentelemetry/sdk-trace-node`
- `@coralogix/opentelemetry`

## Exception Logging

```js
const { logs, SeverityNumber } = require('@opentelemetry/api-logs');
const { LoggerProvider, SimpleLogRecordProcessor } = require('@opentelemetry/sdk-logs');

const loggerProvider = new LoggerProvider({
  processors: [new SimpleLogRecordProcessor(/* add OTLP exporter here */)],
});
logs.setGlobalLoggerProvider(loggerProvider);

const logger = logs.getLogger('my-logger', '1.0.0');
const error = new Error('database connection failed');
logger.emit({
  severityNumber: SeverityNumber.ERROR,
  severityText: 'ERROR',
  body: 'request failed',
  exception: error,
});
```

Exception support requires `@opentelemetry/api-logs` and `@opentelemetry/sdk-logs` >= `0.212.0`.

## Kubernetes Injection

The OpenTelemetry Operator supports Node.js auto-instrumentation injection:

```yaml
annotations:
  instrumentation.opentelemetry.io/inject-nodejs: "true"
```

## Context Propagation

OTel Node.js propagates W3C `traceparent` headers automatically on outgoing HTTP requests
via `@opentelemetry/instrumentation-http`. To verify propagation is working:

1. Enable SDK debug logging — look for `traceparent` in outgoing request headers in the output
2. Confirm the downstream service uses W3C TraceContext propagator (not B3/Zipkin only)
3. Verify intermediaries (load balancers, API gateways) are not stripping `traceparent`

If the downstream service creates independent spans despite receiving `traceparent`:
- .NET Framework backends need `OpenTelemetry.Instrumentation.AspNet` + `AddAspNetInstrumentation()` on the server-side `TracerProvider` to read incoming `traceparent` headers (`AddHttpClientInstrumentation` instruments outgoing calls, not incoming)
- Java Spring backends need `opentelemetry-spring-webmvc-instrumentation` on the receiver
- Some frameworks require `TextMapPropagator` to be configured explicitly to read the header

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Using `--require` in an ESM app | Auto-instrumentation silently does nothing | Use `--import` + `--experimental-loader=@opentelemetry/instrumentation/hook.mjs` for ESM |
| Setting env vars inside the app | Auto-instrumentation ignores them | Set env vars before process start |
| Bundled auto-instr + expects Transactions | Transactions view empty in Coralogix | Switch to individual method with `CoralogixTransactionSampler` |
| HTTP exporter URL missing `/v1/traces` path | 404 from Coralogix | Append `/v1/traces` to the HTTP/proto endpoint URL |
| gRPC exporter URL includes `/v1/traces` path | Connection or export failure | gRPC endpoints have no signal path. Prefer `ingress.<region>.coralogix.com:443`; `https://host:port` is also accepted. HTTP/proto uses `https://...:443/v1/<signal>` |
| `OTEL_NODE_RESOURCE_DETECTORS=all` on local machine | Resource detector errors | Use `env,host,os,process` locally to suppress errors |
| Missing `cx.application.name` / `cx.subsystem.name` | APM features degraded | Set as resource attributes in SDK or as OTLP headers |
