# Java OpenTelemetry Instrumentation

## Contents
- Overview
- Auto-Instrumentation
- Additional Instrumentation with `@WithSpan`
- Exception Logging
- Enabling Metrics and Logs
- Verification
- Common Mistakes
- Kubernetes Injection

Source: Coralogix Java OpenTelemetry Instrumentation documentation.

## Overview

Java instrumentation uses the **OpenTelemetry Java Agent** — a JAR that attaches to any
Java 8+ application and injects bytecode to capture telemetry automatically. No manual
SDK init code is required for auto-instrumentation. Manual span additions use the
`@WithSpan` annotation while the agent is attached.

Use the latest stable OpenTelemetry Java agent from the
[releases page](https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases).

## Auto-Instrumentation

### Step 1: Follow the OpenTelemetry Java setup guide

Use the official OpenTelemetry Java getting-started guide for SDK and agent installation:
https://opentelemetry.io/docs/languages/java/getting-started/

Distribute the JAR to each service host or container that needs instrumentation. The JVM
must have access to the JAR at startup.

### Step 2: Set environment variables (recommended)

```bash
export JAVA_TOOL_OPTIONS="-javaagent:/path/to/opentelemetry-javaagent.jar"

export OTEL_TRACES_EXPORTER="otlp"
export OTEL_METRICS_EXPORTER="none"         # set to "otlp" to enable metrics
export OTEL_LOGS_EXPORTER="none"            # set to "otlp" to enable logs
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL="grpc"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.<CORALOGIX_REGION>.coralogix.com:443"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <CORALOGIX_API_KEY>"
export OTEL_SERVICE_NAME="<SERVICE_NAME>"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>"

java -jar myapp.jar
```

### Step 2 (alternative): JVM system properties

```bash
java -javaagent:/path/to/opentelemetry-javaagent.jar \
    -Dotel.traces.exporter=otlp \
    -Dotel.metrics.exporter=none \
    -Dotel.logs.exporter=none \
    -Dotel.exporter.otlp.traces.protocol=grpc \
    -Dotel.exporter.otlp.traces.endpoint="https://ingress.<CORALOGIX_REGION>.coralogix.com:443" \
    -Dotel.exporter.otlp.traces.headers="Authorization=Bearer <CORALOGIX_API_KEY>" \
    -Dotel.service.name="<SERVICE_NAME>" \
    -Dotel.resource.attributes="cx.application.name=<CX_APPLICATION_NAME>,cx.subsystem.name=<CX_SUBSYSTEM_NAME>" \
    -jar myapp.jar
```

### Resource attributes note

Use the current identity attributes consistently:

```
service.name=<SERVICE_NAME>
cx.application.name=<CX_APPLICATION_NAME>
cx.subsystem.name=<CX_SUBSYSTEM_NAME>
```

## Additional Instrumentation with `@WithSpan`

While the agent handles framework-level spans, you can add custom spans to any method
using the `@WithSpan` annotation without touching the tracer API.

### Dependency reference

Use the official OpenTelemetry Java getting-started guide for dependency setup:
https://opentelemetry.io/docs/languages/java/getting-started/

Required package artifact for `@WithSpan`: `opentelemetry-instrumentation-annotations`.
Name this artifact explicitly when explaining custom spans, but do not include install commands
unless the user asks for them.

### Usage

```java
import io.opentelemetry.instrumentation.annotations.WithSpan;

public class CartService {
    @WithSpan  // creates a span named "CartService.addItem" automatically
    public void addItem(String itemId) {
        // method body — span auto-closes when method returns
    }
}
```

The `@WithSpan` annotation only creates spans when the agent is running. Without the agent,
the annotation is a no-op.

## Exception Logging

### Via OpenTelemetry Logs API

```java
import io.opentelemetry.api.logs.Logger;
import io.opentelemetry.api.logs.Severity;

logger.logRecordBuilder()
    .setSeverity(Severity.ERROR)
    .setBody("request failed")
    .setException(new IllegalStateException("database connection failed"))
    .emit();
```

### Via Log4j 2 appender (`opentelemetry-log4j-appender-2.17`)

Use the official OpenTelemetry Java getting-started guide for appender dependency setup:
https://opentelemetry.io/docs/languages/java/getting-started/

`log4j2.xml`:
```xml
<Configuration>
  <Appenders>
    <OpenTelemetry name="OpenTelemetryAppender"/>
  </Appenders>
  <Loggers>
    <Root level="all">
      <AppenderRef ref="OpenTelemetryAppender"/>
    </Root>
  </Loggers>
</Configuration>
```

```java
import io.opentelemetry.instrumentation.log4j.appender.v2_17.OpenTelemetryAppender;
// Call once at startup:
OpenTelemetryAppender.install(openTelemetry);
```

## Enabling Metrics and Logs

By default, only traces are enabled in the examples. To enable metrics and/or logs:

```bash
export OTEL_METRICS_EXPORTER="otlp"   # enables metrics
export OTEL_LOGS_EXPORTER="otlp"      # enables logs (requires log bridge setup)
```

## Verification

1. Start the application with the agent attached.
2. Look for this log line confirming agent attachment:
   ```
   [otel.javaagent ...] INFO io.opentelemetry.javaagent.tooling.VersionLogger - opentelemetry-javaagent - version: <agent-version>
   ```
3. Generate traffic to the application.
4. In Coralogix UI: **Explore → Tracing** — traces should appear within ~30 seconds.
5. If metrics are enabled: **Grafana → Explore → Metric Browser**.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Missing `-javaagent` flag | No agent log line at startup; no traces | Add `-javaagent:` to `JAVA_TOOL_OPTIONS` or command line |
| Wrong endpoint format (bare `host:port` without scheme) | URI parse error or silent export failure | Java SDK requires a URI — use `https://ingress.<region>.coralogix.com:443` (unlike Python/Go/Node.js which accept bare `host:port`) |
| Missing `cx.application.name` / `cx.subsystem.name` | Telemetry lands under defaults; invisible in APM | Add both to `OTEL_RESOURCE_ATTRIBUTES` |
| `@WithSpan` without agent running | No custom spans, no error | Confirm agent is attached; annotation is a no-op without agent |
| Wrong API key type (not Send-Your-Data) | 401 / auth failure | Use Send-Your-Data key from Settings → API Keys |

## Kubernetes Injection

The OpenTelemetry Operator supports injection of the Java agent into pods via the
`Instrumentation` CRD — no JAR download or `JAVA_TOOL_OPTIONS` needed in the pod spec.

```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: coralogix-instrumentation
spec:
  exporter:
    endpoint: http://otel-collector.monitoring.svc.cluster.local:4317
  java:
    image: ghcr.io/open-telemetry/opentelemetry-operator/autoinstrumentation-java:latest
```

Opt in via pod annotation:
```yaml
annotations:
  instrumentation.opentelemetry.io/inject-java: "true"
```

The agent env vars (`OTEL_EXPORTER_OTLP_*`, `OTEL_RESOURCE_ATTRIBUTES`) are injected
automatically from the `Instrumentation` CRD spec.
