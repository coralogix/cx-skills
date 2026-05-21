# Infrastructure Explorer — Required Resource Attributes

Coralogix **Infrastructure Explorer** surfaces hosts (e.g. AWS EC2),
containers (e.g. Kubernetes containers), and OpenTelemetry agents as
first-class resources, with metrics / logs / traces correlated to each
resource. It is enabled via the **Resource Catalog / Infra Explorer**
toggle in the Kubernetes Complete Observability Integration setup, then
accessed at **Infrastructure → Infrastructure Explorer**.

For Infrastructure Explorer to populate, every signal (metrics, traces,
logs) needs to share a consistent set of resource attributes so the
backend can link them to the same resource. These attributes live at
**resource scope only** — record / span / data-point attributes are not
used for correlation.

## Required resource attributes (Kubernetes)

Set all of these on every signal pipeline:

| Attribute | Why |
|---|---|
| `k8s.cluster.name` | identifies the cluster; required for multi-cluster views |
| `k8s.namespace.name` | namespace the pod runs in |
| `k8s.pod.name` | pod identity; without it the pod row never appears |
| Workload identity: one of `k8s.deployment.name`, `k8s.statefulset.name`, `k8s.daemonset.name`, `k8s.job.name`, `k8s.cronjob.name`, or `k8s.replicaset.name` (whichever owns the pod) | links pods to their owning workload. The `k8sattributes` processor sets the right one based on the pod's owner reference — Deployment-owned pods carry `k8s.deployment.name`, StatefulSet-owned pods carry `k8s.statefulset.name`, standalone ReplicaSets carry `k8s.replicaset.name`, etc. **Do not** invent `k8s.deployment.name` for a non-Deployment workload (including standalone ReplicaSets). |
| `k8s.node.name` | links pods to their node |
| `k8s.container.name` | container identity within the pod |
| `service.name` | service identity; same attribute APM uses |

Recommended when available: `service.namespace`, `host.id`,
`k8s.pod.uid` (preferred over `k8s.pod.ip`, which breaks with service
meshes such as Istio and Linkerd).

## Required resource attributes (Hosts, e.g. EC2)

| Attribute | Why |
|---|---|
| `host.name` | host identity; without it the host does not appear |
| `host.id` | stable host identifier across restarts |
| `cloud.provider`, `cloud.region`, `cloud.account.id`, `cloud.availability_zone`, `cloud.platform` | place the host under the right cloud context (otherwise it shows under "unknown cloud") |
| `os.type`, `os.description` | OS metadata for the host detail view |

### Cloud platform value compatibility

`cloud.platform` semconv breaks can be **value** renames, not attribute-name
renames. The Azure platform values have appeared in both underscore and dot
forms:

| Older value | Newer value |
|---|---|
| `azure_vm` | `azure.vm` |
| `azure_aks` | `azure.aks` |

If Infrastructure Explorer / Resource Catalog logic hard-codes the old
values, an OTel Collector or SDK upgrade can move Azure resources into the
wrong bucket even though the `cloud.platform` attribute is still present.
The durable Coralogix-side fix is to accept both values in identity mapping,
filters, and grouping logic.

A collector transform that rewrites the new value back to the old one is a
temporary compatibility bridge only. It preserves current Coralogix behavior
while backend support catches up, but it makes the outgoing telemetry less
compatible with the latest OTel convention:

```yaml
processors:
  transform/cloud_platform_azure_compat:
    error_mode: ignore
    metric_statements:
      - context: resource
        statements:
          - set(attributes["cloud.platform"], "azure_vm") where attributes["cloud.platform"] == "azure.vm"
          - set(attributes["cloud.platform"], "azure_aks") where attributes["cloud.platform"] == "azure.aks"
    trace_statements:
      - context: resource
        statements:
          - set(attributes["cloud.platform"], "azure_vm") where attributes["cloud.platform"] == "azure.vm"
          - set(attributes["cloud.platform"], "azure_aks") where attributes["cloud.platform"] == "azure.aks"
    log_statements:
      - context: resource
        statements:
          - set(attributes["cloud.platform"], "azure_vm") where attributes["cloud.platform"] == "azure.vm"
          - set(attributes["cloud.platform"], "azure_aks") where attributes["cloud.platform"] == "azure.aks"
```

Run this before Coralogix export / Resource Catalog correlation and remove it
once Coralogix accepts both value families.

### Host CPU metrics caveat

Do not assume every `system.cpu.*` metric uses the current upstream system
semantic-convention attribute names. Current OTel system semconv describes
CPU metric attributes as `cpu.mode` and `cpu.logical_number`; the
hostmetricsreceiver CPU scraper documentation still emits `state` and `cpu`
on `system.cpu.time` / `system.cpu.utilization`.

For Infrastructure Explorer host CPU widgets and backend filters, match both
families defensively:

| Meaning | Current system semconv | hostmetricsreceiver shape |
|---|---|---|
| CPU mode / state | `cpu.mode` | `state` |
| Logical CPU number | `cpu.logical_number` | `cpu` |
| IO wait mode | `iowait` | `wait` |

Symptoms of getting this wrong include host CPU utilization looking much
higher than expected, filters accidentally using requested CPU instead of
actual usage, or a calculation that fails to divide / aggregate across all
logical CPUs. Treat this as a metrics-pipeline or query compatibility issue,
not a missing resource-attribute issue.

## Recommended telemetry correlation processor chain

Use the same processor chain across all three pipelines so attributes are
populated identically. This chain correlates metrics / traces / logs to
resources that already exist in the Resource Catalog; it does **not** create
the inventory entries by itself.

```yaml
processors:
  k8sattributes:
    extract:
      metadata:
        - k8s.namespace.name
        - k8s.pod.name
        - k8s.node.name
        - k8s.deployment.name
        - k8s.statefulset.name
        - k8s.daemonset.name
        - k8s.job.name
        - k8s.cronjob.name
        - k8s.container.name
        - k8s.replicaset.name   # optional; useful to derive deployment
    pod_association:
      - sources:
          - from: resource_attribute
            name: k8s.pod.uid
      - sources:
          - from: resource_attribute
            name: k8s.pod.ip
      - sources:
          - from: connection

  resource/metadata:
    attributes:
      - action: upsert
        key: k8s.cluster.name
        value: "my-cluster"

  # Optional temporary ReplicaSet-to-Deployment fallback. Semconv owns the
  # diagnosis: this must run at resource scope for metrics, traces, and
  # logs so all signals share the same workload identity; strip the
  # ReplicaSet hash before copying into k8s.deployment.name; do not apply
  # it to standalone ReplicaSets because that invents a fictional
  # deployment. Exact replace_pattern / set / delete_key syntax belongs to
  # the opentelemetry-ottl skill.
  transform/k8s_attributes:
    # OTTL implementation is intentionally omitted here.

  resourcedetection:
    detectors: [env, system, ec2]   # choose the cloud detector for your environment: ec2, gcp, azure, ecs, etc.
    timeout: 2s
    override: false

service:
  pipelines:
    metrics:
      receivers: [hostmetrics, kubeletstats, prometheus]
      processors: [k8sattributes, resource/metadata, transform/k8s_attributes, resourcedetection]
      exporters: [coralogix]

    traces:
      receivers: [otlp]
      processors: [k8sattributes, resource/metadata, transform/k8s_attributes, resourcedetection]
      exporters: [coralogix]

    logs:
      receivers: [otlp, filelog]
      processors: [k8sattributes, resource/metadata, transform/k8s_attributes, resourcedetection]
      exporters: [coralogix]
```

Notes on each processor:

- **`k8sattributes`** injects Kubernetes context into every signal.
- **`resource/metadata`** sets `k8s.cluster.name` centrally — there is no
  k8s API field for cluster name, so it has to be configured.
- **`transform/k8s_attributes`** derives a clean `k8s.deployment.name`
  when only `k8s.replicaset.name` is present. The target is
  `k8s.deployment.name` after stripping the ReplicaSet hash; do not apply
  that replacement to standalone ReplicaSets.
- **`resourcedetection`** populates `host.id`, `host.name`, and `cloud.*`
  in cloud-managed environments when its `detectors` list matches the
  deployment. Use `ec2` for EC2/EKS node metadata, `gcp` for GCP/GKE,
  `azure` for Azure, `ecs` only when the collector shares the app task,
  and `env` / `system` as the common baseline.

For Helm-based Coralogix integrations, the
`coralogix/otel-integration/k8s-helm` chart preconfigures these processors
and toggles. Set `global.clusterName` to populate `k8s.cluster.name` and
toggle on **Host metrics**, **Kubelet metrics**, **Cluster metrics**, and
**Resource Catalog / Infra Explorer** under Observability Features.

For self-managed collectors, there is one additional inventory path:
configure the Resource Catalog equivalent on the **cluster-collector**. In
support answers for empty self-managed inventory, name the missing
cluster-collector inventory path explicitly:

- `k8sobjects` receiver on the **cluster-collector**;
- `resourcedetection/resource_catalog`;
- dedicated `coralogix/resource_catalog` exporter;
- logs header `x-coralogix-ingress: metadata-as-otlp-logs/v1`.

Sending normal MELT pipelines to the default `coralogix` exporter is not
enough to populate the Infrastructure Explorer inventory. Full collector
wiring belongs in the `opentelemetry-collector` skill.

## Resource Catalog lifecycle metadata

Resource Catalog inventory has lifecycle semantics beyond normal MELT
resource attributes.

| Field / attribute | Meaning |
|---|---|
| `resource_ttl` | Compatibility field for how long a resource may live without refresh before removal. |
| `interval` | Raw collection interval that lets downstream owners decide TTL buffering/margins. |
| `otel.entity.interval` | Entity-event interval carried by some chart/entity pipelines. Interpret based on source mode, such as watch versus periodic collection. |
| `schema_url` | OpenTelemetry schema identifier for resource attributes; useful when semconv versions differ across collectors. |
| `entityType` / `pillar` | Product/gateway classification for shared metadata streams; taxonomy ownership is product/catalog-specific. |

If resources disappear too early, never disappear, or inventory traffic is
misclassified, check whether the inventory path carries the lifecycle and
classification fields the Resource Catalog/Lumos path expects. This skill
can name the fields and product dependency; proto evolution, Kafka topics,
and gateway routing belong to the owning metadata/collector workflow.

## Resource reduction and enrichment order

If `k8s.*`, `host.*`, or `cloud.*` attributes appear on some spans but not
others, check processor order and signal coverage before assuming the
instrumentation is wrong.

Common failure modes:

- `reduceResourceAttributes` removes Kubernetes metadata before export.
- The k8s enrichment chain is present on traces but not metrics or logs.
- Datadog or eBPF receiver metadata remains in receiver-specific fields such
  as `processTags` instead of OTel resource attributes.
- Cloud tag detection is enabled for one pipeline but not the Resource
  Catalog path.

Required metadata should be enriched before reduction/export, and the same
resource identity should exist on every signal that the product correlates.
Short-answer anchor: promote receiver-specific metadata such as
`processTags` into OTel resource attributes before `reduceResourceAttributes`
or export, then preserve the same `k8s.*`, `host.*`, and `cloud.*` resource
identity across metrics, traces, and logs.

## EC2 tag and host identity

For EC2-hosted collectors, `host.name` may default to private DNS. If the
product expects the EC2 `Name` tag:

1. Enable the EC2 tag/resource detector in the relevant logs/metrics/traces
   and resource catalog paths.
2. Ensure IAM permits tag lookup, especially `ec2:DescribeTags`.
3. Confirm overwrite behavior is intentional because `host.name` is a
   standard resource identity field.
4. Verify the final value is at resource scope before Coralogix export.

## Ownership filters (Environment, Service, Team)

Infrastructure Explorer normalises ownership from a specific set of
Kubernetes labels and cloud tags (not from arbitrary OTel resource
attributes). Add any of these on the underlying Kubernetes resource
or cloud resource — Infra Explorer merges them into the three
ownership attributes shown in the sidebar.

| Filter | Supported tag keys |
|---|---|
| **Environment** | `environment`, `env`, `cx_environment`, `cx_env`, `app.kubernetes.io/environment`, `app.kubernetes.io/env`, `CX_ENV_ID`, `Env` (AWS), and the OpenTelemetry resource attribute `deployment.environment.name` |
| **Service** | `service`, `cx_service`, `app.kubernetes.io/service`, `CX_SERVICE_NAME` (AWS). If a Kubernetes workload defines none of these, Infra Explorer **falls back to the workload name** (Deployment / StatefulSet / DaemonSet / Job / CronJob / standalone ReplicaSet name) as the service identifier — so every workload has at least one Service value even before tagging is standardised. |
| **Team** | `team`, `cx_team` |

Two things to know:

- The OTel resource attribute `service.name` (which APM Service Catalog
  uses) is **not** among the Service ownership keys. Set
  `app.kubernetes.io/service` or `cx_service` as a Kubernetes label on
  the workload if you want Infra Explorer's Service filter to pick a
  specific value rather than fall back to the workload name.
- For Team, there is no OpenTelemetry standard attribute. Set the
  `team` or `cx_team` label on the Kubernetes / cloud resource.

Infra Explorer resolves ownership in this order: declarative tags →
inheritance from parent Kubernetes workloads → discovered runtime
metadata → manual UI entries. All sources merge into the displayed
value; multiple values per attribute are kept when sources disagree.

Source: [Understand and use ownership](https://coralogix.com/docs/user-guides/infrastructure/infrastructure-explorer/ownership/) (Notion: *Understand and use ownership*).

## What Infrastructure Explorer is *not*

- It does not require any `cgx.*` or `cx.*` attribute. Those are routing
  primitives owned by the `core` skill and APM transactions, not Infra
  Explorer.
- The `k8sattributes` / `resource` / `transform` chain alone does not
  create Resource Catalog inventory. It only attaches resource attributes
  so logs, metrics, and traces can correlate with inventory emitted through
  the `coralogix/resource_catalog` path.
- The Coralogix exporter's `application_name_attributes` does not affect
  whether resources show up in Infra Explorer — it controls Coralogix
  application/subsystem routing for the underlying telemetry, separate
  from resource correlation.
- Dashboard panels are not a separate semantic-convention surface. If the
  issue is a built-in dashboard panel, receiver preset, metric name, or
  PromQL label, use the `opentelemetry-collector` or `create-dashboard`
  skill. Stay here only when the root cause is missing `k8s.*` / `host.*`
  resource attributes needed for Resource Catalog / Infrastructure
  Explorer correlation.

## References

- [Coralogix: Infrastructure Explorer overview](https://coralogix.com/docs/user-guides/infrastructure/infrastructure-explorer/overview/)
- [Coralogix: Infrastructure Explorer ownership](https://coralogix.com/docs/user-guides/infrastructure/infrastructure-explorer/ownership/)
- [Coralogix: Infrastructure Explorer Kubernetes enrichment options](https://coralogix.com/docs/user-guides/infrastructure/infrastructure-explorer/kubernetes-enrichment-options/)
- [Coralogix: Getting started with Kubernetes monitoring](https://coralogix.com/docs/user-guides/infrastructure/infrastructure-explorer/getting-started-kubernetes/)
- [Coralogix: Kubernetes Complete Observability configuration guide](https://coralogix.com/docs/opentelemetry/kubernetes-observability/kubernetes-complete-observability-basic-configuration/)
- [OpenTelemetry: system metrics semantic conventions](https://opentelemetry.io/docs/specs/semconv/system/system-metrics/)
- [OpenTelemetry Collector: hostmetricsreceiver CPU scraper](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/hostmetricsreceiver/internal/scraper/cpuscraper/documentation.md)
- `opentelemetry-collector` skill — `k8sattributes`, `resourcedetection`
  processor configuration
- `opentelemetry-ottl` skill — OTTL transforms (e.g. the
  ReplicaSet-to-Deployment derivation above)
