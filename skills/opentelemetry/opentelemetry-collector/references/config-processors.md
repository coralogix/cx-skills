# OpenTelemetry Collector: Processors Configuration

This reference covers the universal processor chain and critical Kubernetes enrichment processors. Order matters fundamentally.

## Universal Processor Chain

Configure pipelines in this order from receiver to exporter:

```
receivers → memory_limiter → resourcedetection/* → resource/metadata → k8sattributes/ecsattributes → transform/k8s_attributes → [transform/filter …] → batch → exporter
```

1. **`memory_limiter` (FIRST)**: Sheds load when approaching memory limits. Must be first to prevent upstream components from doing wasted work on records that will be dropped.
2. **`resourcedetection/*`**: Adds `host.*`, `cloud.*`, `k8s.*`, `aws.*` attributes.
3. **`resource/metadata`**: Injects `k8s.cluster.name`, `cx.otel_integration.name`, and deployment markers like `cx.agent.type` (`agent`, `cluster-collector`, `gateway`). Without this, Coralogix correlation breaks.
4. **`k8sattributes` or `ecsattributes`**: Enriches telemetry with orchestrator metadata (e.g., pod names, replica sets).
5. **`transform/k8s_attributes`**: Derives `k8s.deployment.name` from `k8s.replicaset.name` by stripping the hash suffix. Required for proper workload aggregation in APM.
6. **`transform` / `filter`**: Custom OTTL rules.
7. **`batch` (LAST before exporter)**: Amortizes export cost. Batching prior to enrichment wastes memory and CPU.

## k8sattributes: Passthrough vs. Full Extraction

When running both an agent (daemonset) and a gateway (deployment), **only one role should perform full extraction** to avoid hammering the Kubernetes API server.

- **Agent (passthrough):** Performs a cheap stamp of `k8s.pod.ip` and defers lookup.
- **Gateway (full extraction):** Performs the actual API lookup and enriches the telemetry.

### Agent Configuration (Passthrough)
```yaml
processors:
  k8sattributes:
    passthrough: true
    extract:
      metadata: [k8s.namespace.name, k8s.pod.name, k8s.node.name]
    filter:
      node_from_env_var: K8S_NODE_NAME           # required — or the agent scans all nodes
    pod_association:
      - sources: [{ from: resource_attribute, name: k8s.pod.ip }]
      - sources: [{ from: connection }]
```

### Gateway Configuration (Full Extraction)
```yaml
processors:
  k8sattributes:
    passthrough: false
    extract:
      metadata:
        - k8s.namespace.name
        - k8s.pod.name
        - k8s.pod.uid
        - k8s.deployment.name
        - k8s.statefulset.name
        - k8s.daemonset.name
        - k8s.replicaset.name
        - k8s.job.name
        - k8s.cronjob.name
        - k8s.node.name
        - k8s.cluster.uid
        - k8s.container.name
      labels:
        - tag_name: k8s.app.name
          key: app.kubernetes.io/name
          from: pod
        - tag_name: k8s.app.version
          key: app.kubernetes.io/version
          from: pod
    pod_association:
      - sources: [{ from: resource_attribute, name: k8s.pod.ip }]
      - sources: [{ from: connection }]
```

### The Triple-Duplication Anti-Pattern
Applying full `extract.metadata` on agents, cluster-collectors, and gateways simultaneously leads to:
- High Kubernetes API Server QPS.
- Inflated `otelcol_processor_k8sattributes_pod_tags_add_total` metrics.
- Racing conditions where attributes flap.

**Resolution:** Set `passthrough: true` on agents. Perform full extraction on the gateway (or cluster-collector if no gateway exists).

## Required Resource Attributes for Coralogix

Coralogix Service Catalog and Infrastructure Explorer require the following attributes:

- `k8s.cluster.name` (becomes `cx.cluster.name`)
- `k8s.node.name` + `host.name` or `host.id`
- `k8s.namespace.name`
- `k8s.pod.uid` + `k8s.pod.name`
- `k8s.container.name`
- **Workload identity**: One of `k8s.deployment.name`, `k8s.statefulset.name`, `k8s.daemonset.name`, `k8s.job.name`, `k8s.cronjob.name`
- `service.name`

Missing workload identity tags mean pods cannot aggregate into parent workloads. Verify workload extraction by querying `k8s_pod_phase{k8s_deployment_name=""}`.