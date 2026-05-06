---
name: opentelemetry-collector
description: >
  OpenTelemetry Collector deployment, configuration, and troubleshooting for Coralogix
  users. Use when writing or debugging collector configs — the `coralogix` exporter
  (`domain:` vs `endpoint:`, `${env:CORALOGIX_PRIVATE_KEY}` bracket syntax,
  `coralogix/resource_catalog` variant), the universal processor chain, agent →
  cluster-collector → gateway topology, spanmetrics/tail_sampling/k8sattributes placement,
  and Coralogix-specific presets. Covers the `otel-integration` Helm chart (EKS/GKE/AKS/
  OpenShift, GKE Autopilot Warden, EKS Fargate), ECS EC2 daemonset, ECS Fargate sidecar,
  Linux/Windows/macOS standalone, Docker, and the universal installer. Not for OTTL
  authoring (use the `opentelemetry-ottl` skill) or OpAMP supervisor/Fleet Manager internals beyond the
  config-precedence callout.
license: Apache-2.0
metadata:
  version: "0.1.0"
  integration: otel-collector
  signals:
    - logs
    - metrics
    - traces
  deployment:
    - kubernetes
    - helm
    - docker
    - ecs
    - aws
  triggers:
    description: >
      Load when the user is deploying, configuring, or troubleshooting an OpenTelemetry
      Collector that ships telemetry to Coralogix — across any infrastructure (Kubernetes
      via the otel-integration Helm chart, ECS EC2/Fargate, EC2/VM standalone, Windows,
      macOS, Docker).
    always: false
    file_patterns:
      - "**/otel-collector*.yaml"
      - "**/otelcol*.yaml"
      - "**/collector-config*.yaml"
      - "**/*collector*.yaml"
      - "**/values*.yaml"
      - "**/otel-integration*.yaml"
      - "**/otel-agent*.yaml"
      - "**/task-definition*.json"
      - "**/task-definition*.yaml"
    config_keys:
      - "receivers:"
      - "exporters:"
      - "processors:"
      - "service:"
      - "pipelines:"
      - "coralogix:"
      - "opentelemetry-agent:"
      - "opentelemetry-cluster-collector:"
      - "opentelemetry-gateway:"
    keywords:
      - otel collector
      - opentelemetry collector
      - otelcol
      - otelcol-contrib
      - otel-integration
      - coralogix exporter
      - CDOT
      - CORALOGIX_PRIVATE_KEY
      - CORALOGIX_DOMAIN
      - k8sattributes
      - resource_catalog
      - tail_sampling
      - spanmetrics
      - memory_limiter
      - daemonset
      - sidecar
      - cluster-collector
      - gateway
  docs: https://coralogix.com/docs/opentelemetry/
  repo: https://github.com/coralogix/telemetry-shippers
---

# OpenTelemetry Collector

The Coralogix-flavored OpenTelemetry Collector — the `coralogix` exporter, the
`otel-integration` Helm chart for Kubernetes, CDOT for ECS, and the universal installer
for standalone hosts. Load this skill when a user is deploying, configuring, or
debugging a collector that ships to Coralogix. Most failures come down to a handful of
Coralogix-specific defaults that vanilla OpenTelemetry docs don't cover.

## When to Use This Skill

| Use case | What to do |
|---|---|
| Configure the `coralogix` exporter (domain, private key, app/subsystem names) | `domain:` (bare hostname, not URL), `${env:CORALOGIX_PRIVATE_KEY}` bracketed → [references/config-exporters.md](references/config-exporters.md) and [references/config-processors.md](references/config-processors.md) |
| Enable Infrastructure Explorer / Resource Catalog | Dedicated `coralogix/resource_catalog` exporter + `x-coralogix-ingress` header + `kubernetesResources` preset → [references/preset-kubernetes.md](references/preset-kubernetes.md) |
| Pick a deployment mode | Master table of all `telemetry-shippers` modes → [references/setup-index.md](references/setup-index.md) |
| Deploy on Kubernetes (EKS/GKE/AKS/OpenShift, Autopilot, EKS Fargate) | `otel-integration` Helm chart + presets + Warden/securityContext notes → [references/setup-kubernetes.md](references/setup-kubernetes.md) |
| Deploy via OpenTelemetry Operator | Operator CRDs and auto-instrumentation → [references/setup-opentelemetry-operator.md](references/setup-opentelemetry-operator.md). For `otel-integration` chart Target Allocator, use [references/setup-kubernetes.md](references/setup-kubernetes.md). |
| Deploy on ECS EC2 (Linux) | CDOT daemonset, host network, AWS metadata IP, `ecs` detector pitfall → [references/setup-ecs-ec2.md](references/setup-ecs-ec2.md) |
| Deploy on ECS Fargate | Sidecar + essential-container race + `dependsOn: HEALTHY` → [references/setup-ecs-fargate.md](references/setup-ecs-fargate.md) |
| Deploy on Linux/macOS standalone | systemd/launchd, env-file perms, journald vs filelog, UI-wizard `telemetry.sdk.*` bug → [references/setup-linux-standalone.md](references/setup-linux-standalone.md) |
| Deploy on Windows standalone | PowerShell MSI, `windowseventlog`/`iis`, Defender-vs-IIS high CPU → [references/setup-windows-standalone.md](references/setup-windows-standalone.md) |
| Bootstrap any host with the universal installer | One-liners per OS + flags table → [references/setup-installer.md](references/setup-installer.md) |
| Place `spanmetrics`, `tail_sampling`, `k8sattributes` correctly in K8s | Agent vs gateway placement rules → [references/config-connectors.md](references/config-connectors.md) |
| Diagnose memory issues — `memory_limiter` firing, RSS vs Go heap | `memory_limiter` semantics + kernel page cache + `sending_queue`/`file_storage` → [references/ops-memory-performance.md](references/ops-memory-performance.md) |
| Troubleshoot a symptom ("no data", "no traces", "Resource Catalog empty") | Symptom → root-cause table + debug workflow → [references/ops-troubleshooting.md](references/ops-troubleshooting.md) |
| OpAMP supervisor / Fleet Manager config precedence | Minimum overlap with collector config → [references/preset-fleet-management.md](references/preset-fleet-management.md). Deep OpAMP / supervisor-binary / CDOT coverage is out of scope. |
| Write OTTL statements (`transform` / `filter` / `routing`) | Not in scope — use the `opentelemetry-ottl` skill |
| Instrumentation-library problems inside the app SDK | Not in scope — SDK issue, not a collector issue |

Reference material for each topic lives under [`references/`](references/) and is listed
in the [References](#references) footer at the bottom of this file.

## Key Concepts

- **Exporter routing is Coralogix-specific.** Use `domain:` with a bare regional
  hostname and bracketed env vars like `${env:CORALOGIX_PRIVATE_KEY}`; never use
  `endpoint:` or a UI hostname. Details and snippets:
  [references/config-exporters.md](references/config-exporters.md).
- **Kubernetes role placement matters.** `spanmetrics`, `tail_sampling`, and full
  `k8sattributes` extraction belong in different collector roles. Placement rules:
  [references/config-connectors.md](references/config-connectors.md) and
  [references/config-processors.md](references/config-processors.md).
- **Processor order is part of correctness.** Keep `memory_limiter` first and
  `batch` last before export; chart metadata processors should not be removed by
  wholesale pipeline overrides. See [references/config-processors.md](references/config-processors.md)
  and [references/setup-kubernetes.md](references/setup-kubernetes.md).
- **Troubleshoot from the boundary first.** "No data" is usually exporter
  config, key scope, DNS/TLS/proxy, or egress before it is a pipeline problem.
  Symptom table and debug workflow: [references/ops-troubleshooting.md](references/ops-troubleshooting.md).
- **Memory symptoms need self-telemetry.** Distinguish Go heap, container RSS,
  page cache, throttling, and OOM before changing limits. See
  [references/ops-memory-performance.md](references/ops-memory-performance.md).

## High-Signal Answer Rules

For these recurring cases, include the exact corrective detail in the final answer:

- **GKE Autopilot Warden:** say Warden blocks writable `hostPath` mounts; in the values
  override set `logsCollection.storeCheckpoints: false`, disable `coralogix-ebpf-profiler`,
  `hostMetrics`, and `resourceDetection` on the agent (Autopilot blocks `/proc`/`/sys`
  mounts and `/etc/machine-id` — so `hostEntityEvents` must also be disabled since it
  requires hostMetrics); also disable `resourceDetection` on the cluster-collector (it
  reads `/etc/machine-id` too). Use `gke-autopilot-values.yaml` as the canonical reference.
- **ECS EC2 daemonset localhost:** say ECS tasks have separate network namespaces;
  apps must not use `localhost`, must target the EC2 host IP from metadata, and the
  daemonset must run with `networkMode: host`.
- **ECS Fargate startup loss:** say add a collector sidecar `healthCheck` and make
  the app depend on `dependsOn: [{containerName: otel-collector, condition: HEALTHY}]`.
- **Standalone installer:** recommend `otel-installer`/one-liner with both
  `CORALOGIX_PRIVATE_KEY` and `CORALOGIX_DOMAIN`.
- **No data + transform/OTTL:** clearly say to stop trying OTTL; check receiver/exporter
  connectivity, DNS/TLS/proxy/egress, private key, and region/domain.
- **Infrastructure Explorer (Kubernetes):** `kubernetesResources` and `hostEntityEvents`
  are **enabled by default** in the chart — do not disable them. `kubernetesResources`
  must stay on the `opentelemetry-cluster-collector` only (enabling it on the agent
  crashes with `can't get K8s Instance Metadata; node name is empty`). Use a dedicated
  `coralogix/resource_catalog` exporter with `x-coralogix-ingress: metadata-as-otlp-logs/v1`.
- **Resource Catalog daemonset crash:** `resourcedetection/resource_catalog` belongs on
  the `opentelemetry-cluster-collector` Deployment only; remove it from daemonset agents.
- **Spanmetrics with tail sampling:** gateway `spanmetrics` sees only sampled traces,
  so errors/p99 undercount. Move `spanmetrics` to the agent, upstream of sampling; run
  `transactions`/`groupbytrace/transactions` before `spanmetrics`; do not run it on
  both agent and gateway.
- **Full `k8sattributes`:** exactly one role should do full extraction; set
  `passthrough: true` on the others.
- **OpAMP supervisor endpoint:** it is different from exporter `domain:` and needs the
  full URL, e.g. `https://ingress.eu2.coralogix.com/opamp/v1`.
- **Java multiline stack traces not merging (Kubernetes):** CRI tags every log line as
  `F` (full/final) — the standard `P→F` recombine never triggers. Use `firstEntryRegex`
  on the filelog `recombine` operator to detect new entries by timestamp pattern.
- **`spanNameReplacePattern` escaping:** there are two layers: single-quote or block
  scalar for YAML/OTTL backslashes, and write backreferences as `$$1`/`$$2` because the
  collector envprovider expands `$...`; verify with `helm template`.
- **Target Allocator debugging:** port-forward
  `svc/coralogix-opentelemetry-targetallocator` on `8080`; inspect `/jobs` and
  `/scrape_configs`; then check RBAC, selectors, and watched namespaces.

## Common Workflows

### 1. Triage a "no data reaching Coralogix" report

Use the symptom table and self-telemetry workflow in
[references/ops-troubleshooting.md](references/ops-troubleshooting.md). Start with exporter
domain/key/egress, then inspect pipeline wiring only after export is healthy.

### 2. Bring up a new Kubernetes cluster with `otel-integration`

Use [references/setup-kubernetes.md](references/setup-kubernetes.md) for install flow,
per-platform variants, Target Allocator, and chart-specific failure modes. Use
[references/preset-kubernetes.md](references/preset-kubernetes.md) when the question is
about Helm presets or Infrastructure Explorer.

### 3. Bring up ECS Fargate (sidecar mode)

Use [references/setup-ecs-fargate.md](references/setup-ecs-fargate.md). The fragile pieces are
sidecar health checks, `dependsOn: HEALTHY`, `essential` flags, and keeping the `ecs`
detector enabled only for sidecar mode.

### 4. Diagnose `memory_limiter` firing constantly

Use [references/ops-memory-performance.md](references/ops-memory-performance.md). Compare
Go heap metrics to RSS before changing pod limits or `memory_limiter` settings.

## Best Practices

### Exporter and routing

1. **`domain:` is a bare hostname, not a URL.** `eu2.coralogix.com` — not
   `https://ingress.eu2.coralogix.com`, and never a Coralogix UI hostname. The UI and
   the data-ingestion endpoint are different hosts; see `core` for regions
   and the UI-vs-ingestion rule.
2. **Bracket env vars.** `${env:CORALOGIX_PRIVATE_KEY}`, not `$CORALOGIX_PRIVATE_KEY`.
   The old unbracketed form silently stopped expanding in OTel Collector v0.76+ (a
   confmap/envprovider change upstream, not specific to the coralogix exporter).
3. **Use a dedicated `coralogix/resource_catalog` exporter for Infrastructure Explorer**
   with the `x-coralogix-ingress: metadata-as-otlp-logs/v1` header. The default
   `coralogix` exporter won't light up the entity views.

### Pipeline placement (Kubernetes)

1. **`memory_limiter` first, `batch` last.** Every other order sheds load after work
   has been done, or fails to batch enriched records.
2. **One role owns full `k8sattributes` extraction.** Typically gateway. Daemonset
   agents stay on `passthrough: true`. Triple-duplication of full extraction hammers the
   Kubernetes API server.
3. **`spanmetrics` on agent, `tail_sampling` on gateway.** Span metrics must see all
   spans before sampling; tail sampling must see all spans of a trace, which only works
   at a central role.
4. **Don't replace `service.pipelines` wholesale** in Helm values — prefer the chart's
   `extraProcessors` / `extraReceivers` hooks. Wholesale overrides break the
   `resource/metadata` processor that sets `cx.agent.type` and silently break chart
   upgrades.

### ECS

1. **ECS EC2 daemonset: remove `ecs` from `resourcedetection.detectors`.** It stamps
   the collector's own container ID onto every record.
2. **ECS EC2 apps must target the host IP, not `localhost`.** ECS tasks each get their
   own network namespace; `localhost` on the app task is not `localhost` on the
   daemonset. Use the EC2 metadata IP (`169.254.169.254` → `local-ipv4`).
3. **ECS Fargate: use the CDOT image and wire `dependsOn: HEALTHY`.** Without it,
   sidecar teardown throws away buffered telemetry when the app container exits.

### Troubleshooting discipline

1. **Prove the collector is the problem first.** "No data" is usually DNS / TLS / proxy
   / API key, not a pipeline mistake. If a `transform` processor was added to "force
   data through" and it made no difference, the root cause is upstream.
2. **Enable self-telemetry before editing pipelines.** The collector's own metrics
   (`otelcol_*`, `process.runtime.go.mem.*`) are the ground truth for memory, queue
   depth, and export failures.

## Limitations

This skill does not cover:

- **OTTL authoring** (`transform`, `filter`, `routing` statements, contexts, path
  expressions, `error_mode`). Use the `opentelemetry-ottl` skill.
- **OpAMP protocol internals, supervisor-binary flags, Fleet Manager UI, remote-config
  rendering, CDOT distribution details.** The `preset-fleet-management.md` reference only
  covers the overlap with Helm/standalone configs (endpoint shape, values-vs-UI
  precedence, the Windows image pitfall). Deep OpAMP and supervisor work lives in the
  Fleet Manager / CDOT documentation, not here.
- **Application SDK instrumentation problems.** The collector can only work with what
  the SDK sends; missing trace IDs, wrong span kinds, or unconfigured propagators are
  SDK issues.
- **Infrastructure problems upstream of the collector.** DNS, TLS termination, proxies,
  IAM / IRSA, NAT gateways, VPC endpoints, Kubernetes admission webhooks (beyond the
  known GKE Autopilot Warden case). Diagnose to the boundary, then escalate.

## References

- **[references/config-exporters.md](references/config-exporters.md) and [references/config-processors.md](references/config-processors.md)** — the `coralogix`
  exporter config (`domain:` shape, bracketed env vars, `*_name_attributes`),
  Infrastructure Explorer exporter, universal processor chain,
  agent/cluster-collector/gateway topology.
- **[references/ops-troubleshooting.md](references/ops-troubleshooting.md)** — symptom →
  root-cause table, the self-telemetry-first debugging workflow, "is this even a
  collector problem?" framing.
- **[references/setup-index.md](references/setup-index.md)** — master table
  of every `telemetry-shippers` mode (primary + secondary) and which reference file
  covers it.
- **[references/setup-opentelemetry-operator.md](references/setup-opentelemetry-operator.md)** — OpenTelemetry Operator CRDs and auto-instrumentation.
- **[references/setup-kubernetes.md](references/setup-kubernetes.md)** — the
  `otel-integration` Helm chart: presets, per-variant `values-<>.yaml` files
  (EKS/GKE/AKS/OpenShift/EKS-Fargate/GKE-Autopilot), Warden, ArgoCD meta-chart trap.
- **[references/setup-ecs-ec2.md](references/setup-ecs-ec2.md)** — CDOT daemonset, host
  network, AWS metadata IP discovery, the `ecs` detector pitfall.
- **[references/setup-ecs-fargate.md](references/setup-ecs-fargate.md)** — sidecar
  mode, essential-container race, CDOT `healthCheck`, `dependsOn: HEALTHY`.
- **[references/setup-linux-standalone.md](references/setup-linux-standalone.md)** —
  systemd, env-file permissions, journald vs filelog, DB service discovery, the
  UI-wizard `telemetry.sdk.*` bug (macOS launchd note at the end).
- **[references/setup-windows-standalone.md](references/setup-windows-standalone.md)** —
  PowerShell MSI, `windowseventlog` / `iis` receivers, IIS high-CPU-is-usually-Defender.
- **[references/setup-installer.md](references/setup-installer.md)** — the universal
  installer (Bash/PowerShell/Docker) one-liners per OS, flags table.
- **[references/preset-kubernetes.md](references/preset-kubernetes.md)** — Coralogix Helm presets, Infrastructure Explorer prerequisites.
  prerequisite chain.
- **[references/ops-memory-performance.md](references/ops-memory-performance.md)** —
  `memory_limiter` semantics, Go heap vs RSS / kernel page cache, `sending_queue` +
  `file_storage` back-pressure.
- **[references/preset-fleet-management.md](references/preset-fleet-management.md)** — the OpAMP /
  supervisor overlap with collector config: endpoint shape, values-vs-UI precedence,
  Windows image pitfall. Deep OpAMP / CDOT internals are out of scope.

Upstream:
- [Coralogix OpenTelemetry docs](https://coralogix.com/docs/opentelemetry/)
- [`telemetry-shippers` (Helm charts, ECS task defs, installer)](https://github.com/coralogix/telemetry-shippers)
- [`integration-definitions` (UI wizards)](https://github.com/coralogix/integration-definitions)
- [OpenTelemetry Collector (upstream)](https://github.com/open-telemetry/opentelemetry-collector)
- [OTel Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib)
