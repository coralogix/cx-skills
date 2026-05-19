# Kubernetes: OpenTelemetry Operator

The OpenTelemetry Operator manages OpenTelemetry Collector and auto-instrumentation injection in Kubernetes. It uses Custom Resource Definitions (CRDs) to define the collector topology and instrumentation rules.

## Contents

- Comparison to the `otel-integration` Helm chart
- `OpenTelemetryCollector` CRD modes
- Gateway deployment example
- Auto-instrumentation with `Instrumentation` CRD
- Target Allocator configuration

## Comparison to the `otel-integration` Helm Chart

| Feature | OpenTelemetry Operator | `otel-integration` Helm Chart |
|---|---|---|
| **Mechanism** | Kubernetes Operator reconciling CRDs | Helm Chart rendering vanilla K8s manifests |
| **Primary Resource** | `OpenTelemetryCollector` CRD | `DaemonSet` / `Deployment` manifests |
| **Configuration** | Supplied inside the CRD spec | Supplied via Helm `values.yaml` |
| **Auto-instrumentation** | Yes (`Instrumentation` CRD + Mutating Webhook) | No (Chart only deploys the collector) |
| **Coralogix Presets** | No native Coralogix presets | Yes (`kubernetesResources`, `hostEntityEvents`, etc.) |

When deploying with the Operator, all Coralogix-specific logic (e.g., `resource/metadata` processor, `k8sattributes` placement) must be configured manually inside the `OpenTelemetryCollector` CRD.

## OpenTelemetryCollector CRD

The `OpenTelemetryCollector` CRD defines the collector instance. The `mode` field determines the Kubernetes deployment topology.

### Deployment Modes
- `daemonset`: One collector per node. Optimal for host metrics, pod logs (`filelog`), and host-networked `k8sattributes` passthrough.
- `deployment`: A scalable cluster-level collector. Optimal for tail sampling (`gateway` role) and cluster-scoped metrics (`k8s_cluster`, `kubeletstats`).
- `statefulset`: Required when stable network identities or persistent storage across restarts are needed.
- `sidecar`: Injects a collector container into every application pod matching an annotation. Rarely recommended due to high resource overhead and lack of central batching.

### Example: Gateway (Deployment Mode)
```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: coralogix-gateway
  namespace: coralogix
spec:
  mode: deployment
  replicas: 3
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
    processors:
      memory_limiter:
        check_interval: 1s
        limit_percentage: 80
        spike_limit_percentage: 25
      tail_sampling:
        decision_wait: 30s
        num_traces: 50000
        policies:
          - name: errors
            type: status_code
            status_code:
              status_codes: [ERROR]
      batch:
        timeout: 5s
        send_batch_size: 1024
    exporters:
      coralogix:
        domain: "eu2.coralogix.com"
        private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, tail_sampling, batch]
          exporters: [coralogix]
```

## Auto-Instrumentation (Instrumentation CRD)

The Operator uses a mutating webhook to inject auto-instrumentation agents (Java, Python, Node.js, .NET) into application pods.

1. **Define the `Instrumentation` CRD:**
```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: coralogix-instrumentation
  namespace: default
spec:
  exporter:
    endpoint: http://coralogix-gateway-collector.coralogix.svc.cluster.local:4317
  sampler:
    type: parentbased_traceidratio
    argument: "1"
```

2. **Opt-in via Annotations:**
Add annotations to the application's PodTemplateSpec (e.g., inside a Deployment).

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    metadata:
      annotations:
        instrumentation.opentelemetry.io/inject-java: "true"
        # Or point directly to the Instrumentation CR:
        # instrumentation.opentelemetry.io/inject-java: "default/coralogix-instrumentation"
```

### Target Allocator

When running the Operator in `statefulset` mode with Prometheus receivers, the `targetAllocator` can be enabled directly on the `OpenTelemetryCollector` CRD to distribute Prometheus scrape targets across the collector replicas.

```yaml
spec:
  mode: statefulset
  targetAllocator:
    enabled: true
    prometheusCR:
      enabled: true
```
