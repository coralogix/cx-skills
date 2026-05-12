# Kubernetes: the otel-integration Helm chart

Primary Coralogix Kubernetes deployment. Ships three collector roles (agent, cluster-collector, optional gateway) from a single chart.

- **Chart**: `coralogix/otel-integration` (JFrog Artifactory: `cgx.jfrog.io/artifactory/coralogix-charts-virtual`)
- **Repo**: `telemetry-shippers/otel-integration/k8s-helm/`
- **Supported platforms**: EKS, GKE, AKS, OpenShift, EKS Fargate, GKE Autopilot, vanilla Kubernetes 1.24+
- **Deprecated predecessor**: `coralogix/opentelemetry-coralogix` (the `otel-agent/k8s-helm` directory). Do **not** recommend it. Users still running it should migrate to `otel-integration`.

## Contents

- Install and minimal EKS values
- Per-platform overrides: EKS, GKE, AKS, OpenShift, Fargate, Autopilot, Windows
- Collector roles: agent, cluster-collector, gateway
- Helm presets and Infrastructure Explorer prerequisites
- Target Allocator and Prometheus Operator integration
- ArgoCD, pipeline overrides, and config escaping failure modes
- Deprecated chart migration
- Key facts

## Install

```bash
kubectl create namespace coralogix
kubectl -n coralogix create secret generic coralogix-keys \
  --from-literal=PRIVATE_KEY="<send-your-data-api-key>"

helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual
helm repo update

helm upgrade --install otel-coralogix-integration \
  coralogix/otel-integration \
  -n coralogix \
  -f values.yaml
```

The chart expects a Kubernetes `Secret` named `coralogix-keys` with field `PRIVATE_KEY` in the target namespace. Do not inline the API key into values.yaml.

## Minimal values.yaml (EKS)

```yaml
global:
  domain: "eu2.coralogix.com"                      # NO https://, NO /ingress, NO trailing slash
  clusterName: "prod-use1"                         # becomes k8s.cluster.name / cx.cluster.name
  logLevel: warn
  collectionInterval: 60s

opentelemetry-agent:
  enabled: true
  presets:
    logsCollection:
      enabled: true
      storeCheckpoints: false                      # see gotcha below re: securityContext conflict
    kubeletMetrics:
      enabled: true

opentelemetry-cluster-collector:
  enabled: true
  presets:
    kubernetesEvents:
      enabled: true
    kubernetesResources:                           # required for Infrastructure Explorer / Resource Catalog
      enabled: true
    clusterMetrics:
      enabled: true
    kubernetesApiServerMetrics:
      enabled: true
```

## Per-platform overrides

| Platform | Override file to base from | Key differences |
|---|---|---|
| **EKS (EC2 nodes)** | `values.yaml` (default) | nothing special |
| **GKE** | `values.yaml` | typically works; watch for Autopilot restrictions (below) |
| **AKS** | `values.yaml` | tolerate Azure node taints if present |
| **OpenShift** | `values.yaml` | grant SCC (`hostaccess` / `privileged`) to the service account — the chart needs hostPath mounts and host network |
| **vanilla K8s 1.24+** | `values.yaml` | nothing special |
| **EKS Fargate** | `values-eks-fargate.yaml` | agent runs as a statefulset, not a daemonset; needs a self-monitoring pod; requires IRSA with CloudWatchAgentServerPolicy. See the EKS-Fargate callout in `setup-index.md`. |
| **GKE Autopilot** | `values.yaml` + Autopilot constraints (below) | Warden blocks hostPath write mode — disable `storeCheckpoints`, eBPF profiler, and other writes to host paths |
| **Windows nodes** | enable `opentelemetry-agent-windows` under the same release | sub-preset historically pins `contrib-windows:0.92.0` which predates OpAMP on Windows — bump to collector ≥ v0.130 for in-process `extensions: [opamp]`, or use the `-Supervisor` wrapper. Different hostPath mount semantics than Linux. |

### GKE Autopilot: Warden denies hostPath writes

```
admission webhook "warden-validating.common-webhooks.networking.gke.io" denied the request:
GKE Warden rejected the request because it violates one or more constraints.
Violations details: {"[denied by autogke-no-write-mode-hostpath]": ["hostP..."]}
```

Fix: disable anything that mounts a hostPath in write mode. Autopilot also blocks `/proc`/`/sys` mounts and `/etc/machine-id`, so `hostMetrics` and `resourceDetection` must be disabled too. Use `gke-autopilot-values.yaml` from the `telemetry-shippers` repo as the canonical starting point.

```yaml
opentelemetry-agent:
  presets:
    logsCollection:
      enabled: true
      storeCheckpoints: false    # must be false — Autopilot blocks write-mode hostPath
    hostMetrics:
      enabled: false             # cannot mount /proc and /sys on Autopilot
    hostEntityEvents:
      enabled: false             # requires hostMetrics; must be disabled on Autopilot
    resourceDetection:
      enabled: false             # no /etc/machine-id on Autopilot nodes
opentelemetry-cluster-collector:
  presets:
    resourceDetection:
      enabled: false             # cluster-collector also reads /etc/machine-id; must be disabled
coralogix-ebpf-profiler:
  enabled: false                 # eBPF profiler not supported on Autopilot
```

### EKS Fargate

Agent runs as a stateful set because Fargate pods cannot daemonset across a shared host. See `setup-index.md` for the Fargate-specific values file (`values-eks-fargate.yaml`) and the secondary self-monitoring pod. Current manifests include `k8sattributes` in the traces and `metrics/otlp` pipelines; users running an older saved copy with empty pod metrics or related-data visualizations should re-pull the manifest before hand-patching collector config.

## Three roles, one chart

| Role | Subchart key | Default | Typical processors |
|---|---|---|---|
| Agent | `opentelemetry-agent` | daemonset, per node, `hostNetwork: true` | `memory_limiter`, `k8sattributes` (passthrough), `resourcedetection`, `batch`, `spanmetrics` connector |
| Cluster-collector | `opentelemetry-cluster-collector` | deployment, singleton | `memory_limiter`, `k8sattributes`, `resourcedetection/resource_catalog`, `batch` |
| Gateway | `opentelemetry-gateway` | deployment, disabled by default | `memory_limiter`, `tail_sampling`, `k8sattributes`, `batch` |

Enable the gateway when users need tail sampling, loadbalancing, or centralized buffering:

```yaml
opentelemetry-gateway:
  enabled: true
  replicaCount: 3
  config:
    processors:
      tail_sampling:
        decision_wait: 30s
        num_traces: 50000
        policies:
          - name: errors-policy
            type: status_code
            status_code:
              status_codes: [ERROR]
          - name: default-sample
            type: probabilistic
            probabilistic:
              sampling_percentage: 10
```

Agents feed the gateway via a `loadbalancing` exporter with `consistent_hashing` by `trace_id` — otherwise spans for one trace split across gateway replicas and tail sampling makes partial decisions.

## Presets (what you actually turn on)

| Preset | Runs on | Purpose | When to enable |
|---|---|---|---|
| `logsCollection` | agent | `filelog` on pod logs + checkpointing | almost always |
| `kubeletMetrics` | agent | `kubeletstats` receiver | almost always |
| `hostEntityEvents` | agent | host-level entity events for Infra Explorer | when user uses Infra Explorer for host context |
| `kubernetesEvents` | cluster-collector | `k8sevents` receiver | almost always |
| `kubernetesResources` | cluster-collector | `k8sobjects` scrape + `resourcedetection/resource_catalog` + dedicated `coralogix/resource_catalog` pipeline | **required** for Infrastructure Explorer |
| `kubernetesApiServerMetrics` | cluster-collector | scrape `kube-apiserver` | for control-plane dashboards |
| `clusterMetrics` | cluster-collector | `k8s_cluster` receiver (namespace/deploy/replicaset rollups) | almost always |
| `kubernetesExtraMetrics` | agent/cluster-collector | cadvisor + apiserver metrics pre-packaged | instead of rolling your own Prometheus scrape |
| `profilesCollection` / `coralogix-ebpf-profiler.enabled` | dedicated daemonset | eBPF continuous profiling | when user has the profiling add-on (not on Autopilot / Windows) |

## Known gotchas

### securityContext override conflicts with `collectorCRD.generate` + `storeCheckpoints`

When both `opentelemetry-agent.collectorCRD.generate: true` and `opentelemetry-agent.presets.logsCollection.storeCheckpoints: true` are set, the chart hardcodes a `privileged: true` security context. Any custom `securityContext` in values.yaml then conflicts with it and the chart fails with a YAML parse / admission error.

Fix (pick one):
- Disable one of the two flags (usually `storeCheckpoints: false` is enough).
- Don't override `securityContext` for the agent.

### `hostNetwork: true` daemonset + cross-node ServiceMonitor strategy

The agent runs with `hostNetwork: true` so it listens on the node IP at `:4317`. A `ServiceMonitor` with the default `consistent-hashing` strategy picks a single agent pod and tries to scrape targets that may live on other nodes — the host-networked agent can't reach cross-node pods directly.

Fix: use `per-node` strategy for the ServiceMonitor. That scopes each node's agent to its own pods, which is what the daemonset + hostNetwork topology is designed for.

### Target Allocator (Prometheus CR integration)

**When it comes up.** A user already using Prometheus Operator — i.e. they have `ServiceMonitor` / `PodMonitor` resources in their cluster — needs to keep those scrape configs flowing through Coralogix once the OTel agent is the collection path. That's Target Allocator's job: it watches the Prometheus CRs and distributes the discovered targets to the per-node agent collectors' `prometheus` receivers.

**Enable flag.** `opentelemetry-agent.targetAllocator.enabled: true` in the values file. Disabled by default. When enabled the chart adds a separate deployment in the collector namespace that reconciles `ServiceMonitor` / `PodMonitor` and exposes a `/jobs` + `/scrape_configs` HTTP API that each agent polls.

**Why it fits the daemonset topology.** The chart ships with allocation strategy **pre-configured to `per-node`** — each target is assigned to the agent running on the same node as the target endpoint. This is the same design as the existing `hostNetwork: true` / per-node ServiceMonitor strategy note above: host-networked agents can't scrape cross-node pods, so allocation has to be node-local.

**HA and scrape tuning.** `opentelemetry-agent.targetAllocator.replicas: <n>` for HA (`>1` if you can't tolerate a rediscovery pause during TA rollout). `opentelemetry-agent.targetAllocator.prometheusCR.scrapeInterval` customizes how often TA reconciles the CRs (default `30s`); this is TA → CR polling, distinct from the agent collectors' actual scrape interval.

**Debugging what TA sees.** Port-forward the allocator service and hit the two debug endpoints:

```bash
kubectl port-forward -n <namespace> svc/coralogix-opentelemetry-targetallocator 8080:8080
# then in another shell:
curl -s localhost:8080/jobs | jq          # all discovered jobs (one per ServiceMonitor/PodMonitor)
curl -s localhost:8080/scrape_configs | jq # full rendered scrape config with relabel rules
```

If a ServiceMonitor isn't showing up in `/jobs`: check RBAC (TA needs cluster-wide get/list on the CR's API group), selector labels, and that the CR lives in a namespace TA is watching (`targetAllocator.prometheusCR.serviceMonitorSelector` / `podMonitorSelector`, which default to empty — meaning match-all — but can be tightened).

**Version pinning rule (pre-existing gotcha).** The bundled `targetallocator` image version is pinned per chart version. Mixing chart `v0.0.132` with `targetallocator` `v0.0.137` breaks because the CRD schemas drift between minors. Bump the whole chart to the latest release; don't override `targetallocator.image.tag` unless you have a tested reason.

**Canonical reference.** The upstream Coralogix documentation for this feature lives at [`coralogix/telemetry-shippers/otel-integration/k8s-helm/README.md`](https://github.com/coralogix/telemetry-shippers/tree/master/otel-integration/k8s-helm) (section "Target Allocator and Prometheus Operator with OpenTelemetry"). When a user needs the full walkthrough with screenshots, point them there.

### ArgoCD: the meta-chart trap

`otel-integration` is a meta-chart that depends on `opentelemetry-collector` (the upstream community subchart). Some users rewrite values to point directly at the community subchart via ArgoCD — which skips the Coralogix defaults in `otel-integration/k8s-helm/values.yaml`, including sensible exporters and the required `k8sattributes` wiring.

Signal to look for: "I deployed via ArgoCD and the kubeletstats metrics aren't coming in." If the user is pulling from `open-telemetry/opentelemetry-helm-charts`, they're not using `otel-integration` at all — refer to `coralogix/otel-integration` and stop tuning the subchart.

### Don't override `opentelemetry-*` pipelines wholesale

User configs that manually override `service.pipelines` inside an `otel-integration` values file strip the default receivers and processors that populate Coralogix dashboards and Infra Explorer. Changes should use presets (`presets.X.enabled`) and `extraProcessors` / `extraReceivers` hooks — not a full pipeline replacement.

Symptom: dashboards populated on one cluster but empty on another, with identical chart versions. Root cause: the broken cluster has a custom `service.pipelines` block.

### Escape layers in collector config YAML (and Helm presets)

Two **independent** escape rules apply when a regex or any OTTL fragment ends up in an OpenTelemetry Collector config — whether that config is written by hand, rendered by Helm, or emitted by a chart preset like `opentelemetry-agent.presets.spanMetrics.spanNameReplacePattern`.

**Rule 1 — YAML ↔ OTTL string literal.** The regex has to survive *two* parsers: the YAML scalar parser, then OTTL's own string-literal parser. Double-quoted YAML consumes backslashes (`\\.` → `\.`), and OTTL rejects `\.` as an invalid string escape. Use single-quoted YAML (no escape processing) or a block scalar (`|-` / `>-`).

**Rule 2 — Collector envprovider `$` expansion.** At startup the collector's default `envprovider` scans the merged config for `$VAR` / `${VAR}` / `${env:VAR}` references and substitutes them. To emit a **literal** `$` anywhere in the final config, write `$$`. This is a general collector rule — it applies to regex backreferences (`$$1`, `$$2`), literal dollar signs in attribute values, Prometheus label values, and anything else containing `$` — not just to this preset and not just to Helm-rendered configs.

Both rules apply to chart-rendered span-name replacement patterns. The chart template at `charts/opentelemetry-collector/templates/_config.tpl` renders

```
- replace_pattern(span.name, "{{ $pattern.regex }}", "{{ $pattern.replacement }}")
```

so a double-quoted YAML `regex:` plus a `$1` replacement violates both rules simultaneously. Helm's templating engine itself passes `$` through unchanged — `{{ ... }}` is the only character sequence Helm rewrites. Verify end-to-end with `helm template` and `otelcol-contrib validate`.

Symptom when you get Rule 1 wrong:

```
processors::transform/span_name: statement has invalid syntax:
1:28: invalid quoted string "\"cycle-(manager|rpa-manager)\\.[0-9a-f]...\"": invalid syntax
```

Symptom when you get Rule 2 wrong: no startup error, but regex replacements produce empty or unreplaced output in exported spans/metrics — `$1` gets resolved as env var `1` (typically empty) rather than as the first capture group.

Correct shape for the preset:

```yaml
opentelemetry-agent:
  presets:
    spanMetrics:
      spanNameReplacePattern:
        - regex: '\.\d+\.'                                       # single quotes → no YAML escapes
          replacement: '.{num}.'
        - regex: 'cycle-(manager|rpa-manager)\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_(.+)'
          replacement: 'cycle-$$1.$$2'                           # $$ → $ after envprovider
        - regex: '(SELECT|INSERT|UPDATE|DELETE|CALL) ([\w-]+)\.[\w-]+(.*)'
          replacement: '$$1 $$2.*$$3'
```

Verify the rendered OTTL before `helm upgrade`:

```bash
helm template otel-coralogix-integration coralogix/otel-integration \
  -f values.yaml \
  | grep -A 20 'transform/span_name'
```

The same two rules apply to any other preset or `extraProcessors` block that takes OTTL fragments (filter expressions, transform set/replace statements). When in doubt, `helm template` first, then `otelcol-contrib validate --config=<rendered>` — both are offline and don't need a cluster.

### Default `otel-agent` chart is deprecated

If values.yaml references `opentelemetry-coralogix` (old chart name) or the repo is still set to `coralogix` pointing at that chart, the user is on the deprecated agent. Migrate to `otel-integration`:

```bash
helm uninstall otel-coralogix-agent -n coralogix
helm upgrade --install otel-coralogix-integration coralogix/otel-integration -n coralogix -f values.yaml
```

`opentelemetry-agent-windows` and `otel-infrastructure-collector` are similarly deprecated in favor of the unified `otel-integration` chart.

## Key Facts

- **`otel-integration` is the current chart. `otel-agent` is deprecated.** Don't hand a new user the old chart.
- **Secret is `coralogix-keys`, field is `PRIVATE_KEY`.** Same namespace as the collector release.
- **Daemonset is `hostNetwork: true`, so apps send OTLP to the node IP `:4317`** — not `localhost` from pod-level, not a k8s Service IP.
- **`kubernetesResources` preset is required for Infrastructure Explorer.** Runs on cluster-collector only — crashes on daemonset with `can't get K8s Instance Metadata; node name is empty`.
- **Don't enable `storeCheckpoints: true` + `collectorCRD.generate: true` with a custom `securityContext`.** Pick two.
- **GKE Autopilot blocks hostPath writes.** Disable checkpoints + eBPF profiler.
- **EKS Fargate uses a statefulset + self-monitoring pod**, not a daemonset. Current manifests include `k8sattributes`; users on old saved copies should re-pull before hand-patching.
- **Target allocator version is pinned per chart — don't mix.**
- **Never override `service.pipelines` wholesale.** Use presets and the extra hooks.
- **Preset OTTL fragments (e.g. `spanNameReplacePattern`) need `$$` for regex backreferences.** The collector envprovider turns `$$` into a literal `$`; Helm passes `$` through unchanged. Verify with `helm template` before `helm upgrade`.
- **Gateway enabled = tail sampling + loadbalancing**; agents fan traces in with `consistent_hashing` by `trace_id`.
