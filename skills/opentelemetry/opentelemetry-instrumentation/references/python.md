# Python OpenTelemetry Instrumentation

## Contents
- Overview
- Prerequisites
- Required packages
- Auto-Instrumentation
- Programmatic Instrumentation (Traces + FlaskInstrumentor)
- Manual Instrumentation (Traces)
- Metrics (Programmatic)
- Logs (Programmatic)
- Required Environment Variables
- Verification
- Common Mistakes
- Kubernetes Injection

Source: Coralogix Python OpenTelemetry Instrumentation documentation.

## Overview

Python supports three instrumentation modes:

1. **Auto** — `opentelemetry-instrument` CLI wrapper; zero code changes.
2. **Programmatic** — SDK initialized inside the app; auto-instruments compatible libraries.
3. **Manual** — explicit tracer/span/meter creation; full control.

All three modes support direct export to Coralogix and can use `CoralogixTransactionSampler`
for APM transaction support.

## Prerequisites

- Python 3.9+
- Coralogix Send-Your-Data API key and region/domain.

## Required packages

Use the official OpenTelemetry Python getting-started guide for SDK installation:
https://opentelemetry.io/docs/languages/python/getting-started/

For Coralogix APM Transactions, include the Coralogix sampler package documented by
Coralogix (`coralogix-opentelemetry`) in the same dependency management flow.

## Auto-Instrumentation

### Environment setup

```bash
# URL-encoded — %20 is required between "Bearer" and the key
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20<CORALOGIX_API_KEY>"

export OTEL_EXPORTER_OTLP_ENDPOINT="ingress.<CORALOGIX_REGION>.coralogix.com:443"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"
export OTEL_TRACES_EXPORTER="otlp_proto_grpc"
```

**Endpoint scheme note:** `https://ingress.<region>.coralogix.com:443` is also accepted by
the Python gRPC exporter — bare `host:port` is the standard Coralogix form, but both work.
Do NOT flag `https://` as incorrect when it appears in a user's Python gRPC endpoint config.

### Run command

```bash
opentelemetry-instrument \
    --traces_exporter otlp_proto_grpc \
    --metrics_exporter none \
    --service_name <SERVICE_NAME> \
    python app.py
```

To enable metrics, change `--metrics_exporter none` to `--metrics_exporter console,otlp`.

### URL Encoding Requirement (env var form only)

`OTEL_EXPORTER_OTLP_HEADERS` values must be **URL encoded** — this is a Python SDK
requirement for the env var parser and does not apply to Java, Node.js, .NET, or Go.

| Context | Form | Example |
|---|---|---|
| Env var (`OTEL_EXPORTER_OTLP_HEADERS`) | URL-encoded `%20` | `Authorization=Bearer%20myKey` |
| Programmatic gRPC tuple | Literal space | `("authorization", f"Bearer {token}")` |

A literal space in the env var header string causes silent auth failure with no error surfaced.
When diagnosing a Python auth failure or missing traces, **always check URL encoding first**.

**Note:** `%20` in programmatic tuple headers is NOT correct — it will be sent over the wire
literally and Coralogix will return `UNAUTHENTICATED`. Only the env var form needs `%20`.

## Programmatic Instrumentation (Traces + FlaskInstrumentor)

Use this mode when you want auto-instrumentation for your framework but also need to add
custom spans or use `CoralogixTransactionSampler`.

```python
import os
from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import StaticSampler, Decision
from coralogix_opentelemetry.trace.samplers import CoralogixTransactionSampler

# Programmatic gRPC headers: sequence of (key, value) tuples — NOT a dict.
# Key must be lowercase (gRPC/HTTP2 requirement). Value uses a literal space,
# NOT %20 — URL encoding is only needed in the OTEL_EXPORTER_OTLP_HEADERS env var.
# Prefer resource attributes for cx.application.name / cx.subsystem.name —
# they propagate to all signals; header-based values only reach that one exporter.
headers = (
    ("authorization", f'Bearer {os.environ["CORALOGIX_API_KEY"]}'),
)

tracer_provider = TracerProvider(
    resource=Resource.create({
        SERVICE_NAME: '<SERVICE_NAME>',
        'cx.application.name': '<CX_APPLICATION_NAME>',
        'cx.subsystem.name': '<CX_SUBSYSTEM_NAME>',
    }),
    sampler=CoralogixTransactionSampler(StaticSampler(Decision.RECORD_AND_SAMPLE)),
)

exporter = OTLPSpanExporter(
    endpoint=os.environ['CX_ENDPOINT'],  # ingress.<region>.coralogix.com:443
    headers=headers,
)

tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(tracer_provider)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
tracer = trace.get_tracer_provider().get_tracer(__name__)

@app.route("/roll")
def roll():
    span = trace.get_current_span()
    span.set_attribute("custom.key", "custom_value")
    return "ok"
```

**Span processor choice:** Use `SimpleSpanProcessor` for scripts and one-shot jobs — it
exports synchronously on `span.end()`. Use `BatchSpanProcessor` for long-running servers.
A script that exits in under a second with only `BatchSpanProcessor` may drop spans silently.

## Manual Instrumentation (Traces)

Use when you want explicit control over every span:

```python
import os
from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import StaticSampler, Decision
from coralogix_opentelemetry.trace.samplers import CoralogixTransactionSampler

# Literal space in value — NOT %20 (that form is only for the env var parser)
headers = (
    ("authorization", f'Bearer {os.environ["CORALOGIX_API_KEY"]}'),
)

tracer_provider = TracerProvider(
    resource=Resource.create({
        SERVICE_NAME: '<SERVICE_NAME>',
        'cx.application.name': '<CX_APPLICATION_NAME>',
        'cx.subsystem.name': '<CX_SUBSYSTEM_NAME>',
    }),
    sampler=CoralogixTransactionSampler(StaticSampler(Decision.RECORD_AND_SAMPLE)),
)

exporter = OTLPSpanExporter(
    endpoint=os.environ['CX_ENDPOINT'],
    headers=headers,
)
tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer_provider().get_tracer(__name__)

app = Flask(__name__)

@app.route("/roll")
def roll():
    with tracer.start_as_current_span("roll-handler") as span:
        span.set_attribute("http.method", "GET")
        result = dice()
        span.set_attribute("roll.value", result)
        return f"rolled {result}"

@tracer.start_as_current_span("dice")
def dice():
    import random
    return random.randint(1, 6)
```

## Metrics (Programmatic)

```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import os, time

headers = (
    ("authorization", f'Bearer {os.environ["CORALOGIX_API_KEY"]}'),
)

resource = Resource.create({
    SERVICE_NAME: '<SERVICE_NAME>',
    'cx.application.name': '<CX_APPLICATION_NAME>',
    'cx.subsystem.name': '<CX_SUBSYSTEM_NAME>',
})

exporter = OTLPMetricExporter(
    endpoint=os.environ['CX_ENDPOINT'],
    headers=headers,
)

metric_reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(provider)
meter = metrics.get_meter("my.meter.name")

# Example counter
request_counter = meter.create_counter("http.request.count", description="Total HTTP requests")

# ... record metrics ...

# For scripts: wait for at least one export interval before shutdown,
# or call force_flush() — PeriodicExportingMetricReader only exports on its
# interval tick; a process that exits in under a second exports zero metrics.
time.sleep(6)      # > export_interval_millis
provider.shutdown()
```

## Logs (Programmatic)

Sends Python `logging` records to Coralogix as OTel logs via a bridge handler.

**Module path note:** In `opentelemetry-sdk >= 1.28` the logs classes are under
`opentelemetry.sdk._logs` (private). A public `opentelemetry.sdk.logs` alias may not exist
depending on the installed version — use `opentelemetry.sdk._logs` if the public path fails.

```python
import logging
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    SimpleLogRecordProcessor(
        OTLPLogExporter(endpoint=os.environ['CX_ENDPOINT'], headers=headers)
    )
)
set_logger_provider(logger_provider)

# Critical: set root logger level BEFORE adding any handler.
# logging.basicConfig(level=...) is a no-op once any handler exists,
# so the level must be set explicitly — otherwise INFO records are
# filtered at the logger before reaching the OTel handler.
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logging.StreamHandler())           # console
root_logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

log = logging.getLogger("my-service")
log.info("request processed")
log.error("something failed", exc_info=True)

# Flush before exit
logger_provider.shutdown()
```

Validation: Coralogix UI → **Logs**.

## Short-Lived Scripts and One-Shot Jobs

Two silent failure modes affect Python scripts that exit in under a second. Mention **both**
whenever diagnosing missing traces or metrics from a script.

### 1 — BatchSpanProcessor drops spans on fast exit

`BatchSpanProcessor` queues spans and flushes on a background timer. A script that exits
before the timer fires silently drops all spans. **Use `SimpleSpanProcessor` for scripts:**

```python
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# SimpleSpanProcessor exports synchronously on span.end() — safe for scripts
tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
```

`BatchSpanProcessor` is correct for long-running services where the overhead is justified.

### 2 — PeriodicExportingMetricReader exports zero metrics before its interval

`PeriodicExportingMetricReader` only exports on its configured interval (default 60 s). A
script that finishes in half a second and calls `provider.shutdown()` immediately will export
zero metrics because the interval never fired.

**Fix:** either sleep past the interval, or call `force_flush()` explicitly:

```python
import time

# Option A — sleep past the interval
time.sleep(export_interval_ms / 1000 + 1)
provider.shutdown()

# Option B — force flush before shutdown
metric_reader.force_flush()
provider.shutdown()
```

## Required Environment Variables (summary)

| Variable | Value |
|---|---|
| `CORALOGIX_API_KEY` | Your Send-Your-Data API key |
| `CX_ENDPOINT` or `OTEL_EXPORTER_OTLP_ENDPOINT` | `ingress.<region>.coralogix.com:443` |
| `OTEL_EXPORTER_OTLP_HEADERS` | URL-encoded headers (auto-instr only) |
| `OTEL_TRACES_EXPORTER` | `otlp_proto_grpc` (auto-instr) |

## Verification

- Traces: Coralogix UI → **Explore → Tracing**
- Metrics: **Grafana → Explore → Metric Browser** (search by metric name)

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `Bearer%20<key>` in programmatic tuple headers | `UNAUTHENTICATED` error | Use a literal space: `f"Bearer {token}"`. `%20` is only for `OTEL_EXPORTER_OTLP_HEADERS` env var. |
| `Bearer <key>` (literal space) in `OTEL_EXPORTER_OTLP_HEADERS` | Silent auth failure, no traces | URL-encode the space: `Bearer%20<key>`. Literal space breaks the env var parser. |
| Mixed-case gRPC header keys (e.g. `CX-Application-Name`) | `Illegal header key` error | gRPC/HTTP2 requires lowercase keys. Use resource attributes for cx.application.name / cx.subsystem.name instead. |
| `headers` set as a dict in programmatic gRPC code | SDK error or silent failure | Use a sequence of `(key, value)` tuples; env vars remain comma-separated strings |
| `logging.basicConfig(level=INFO)` called after adding a handler | Logs filtered at WARNING; nothing reaches OTel handler | Set `logging.getLogger().setLevel(logging.INFO)` explicitly before `addHandler` — `basicConfig` is a no-op once any handler exists |
| `BatchSpanProcessor` in a short-lived script | Last spans dropped silently | Use `SimpleSpanProcessor` for scripts; `BatchSpanProcessor` for long-running servers |
| `PeriodicExportingMetricReader` in a short-lived script | Zero metrics exported | Wait > export interval before `shutdown()`, or call `force_flush()` on the reader |
| Missing `CoralogixTransactionSampler` | Traces arrive but no Transactions in APM | Wrap sampler with `CoralogixTransactionSampler` |
| Python virtual env not active when setting env vars | Env vars not seen by the app | Set env vars inside the activated venv session |
| `OTEL_TRACES_EXPORTER` set to `otlp` instead of `otlp_proto_grpc` | Export may use HTTP instead of gRPC | Use `otlp_proto_grpc` for gRPC protocol |

## Kubernetes Injection

The OpenTelemetry Operator supports Python auto-instrumentation injection:

```yaml
annotations:
  instrumentation.opentelemetry.io/inject-python: "true"
```

The `Instrumentation` CRD must include a `python:` section pointing to the auto-instrumentation image.
