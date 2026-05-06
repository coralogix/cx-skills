# Coralogix Helm Presets for Kubernetes

This reference covers the Coralogix abstractions built into the `otel-integration` Helm chart via `presets`. Do not use full `service.pipelines` overrides; use presets to enable features safely.

## Core Presets

| Preset | Runs on | Purpose | When to enable |
|---|---|---|---|
| `logsCollection` | agent | `filelog` on pod logs + checkpointing | almost always |
| `kubeletMetrics` | agent | `kubeletstats` receiver | almost always |
| `hostEntityEvents` | agent | host-level entity events for Infra Explorer | when utilizing Infra Explorer for host context |
| `kubernetesEvents` | cluster-collector | `k8sevents` receiver | almost always |
| `kubernetesResources` | cluster-collector | `k8sobjects` scrape + `resourcedetection/resource_catalog` + dedicated `coralogix/resource_catalog` pipeline | **required** for Infrastructure Explorer |
| `kubernetesApiServerMetrics` | cluster-collector | scrape `kube-apiserver` | for control-plane dashboards |
| `clusterMetrics` | cluster-collector | `k8s_cluster` receiver (namespace/deploy/replicaset rollups) | almost always |
| `kubernetesExtraMetrics` | agent/cluster-collector | cadvisor + apiserver metrics pre-packaged | instead of rolling your own Prometheus scrape |

## Infrastructure Explorer / Resource Catalog

For Infrastructure Explorer to populate, the following prerequisite chain must be complete:

1. **`kubernetesResources` preset on the cluster-collector** (enabled by default — do not disable it):
```yaml
opentelemetry-cluster-collector:
  presets:
    kubernetesResources:
      enabled: true   # default; shown explicitly to prevent accidental disablement
```

2. **Dedicated Exporter with Headers**: The preset automatically wires the `coralogix/resource_catalog` exporter with the `x-coralogix-ingress: metadata-as-otlp-logs/v1` header.

3. **`hostEntityEvents` Preset** on the agent for node-level Infra Explorer entries (enabled by default — do not disable it, except on GKE Autopilot where hostMetrics is unavailable):
```yaml
opentelemetry-agent:
  presets:
    hostEntityEvents:
      enabled: true   # default; must be false on GKE Autopilot (requires hostMetrics)
```

**Failure Mode**: The `resourcedetection/resource_catalog` processor crashes on a daemonset with `can't get K8s Instance Metadata; node name is empty`. Do not enable `kubernetesResources` on the agent; it must run on the cluster-collector.

## Anti-Pattern: Wholesale Pipeline Overrides

Manual overrides of `service.pipelines` inside the `otel-integration` values file strip the default receivers and processors that populate Coralogix dashboards and Infra Explorer.

**Symptom**: Dashboards populate on one cluster but remain empty on another, despite identical chart versions.
**Resolution**: Remove the custom `service.pipelines` block. Use `presets.<feature>.enabled` and `extraProcessors` / `extraReceivers` hooks. Wholesale overrides break the `resource/metadata` processor that sets `cx.agent.type`, silently breaking chart upgrades and correlation rules.
