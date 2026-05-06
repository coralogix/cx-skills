# Deployment index: every mode in telemetry-shippers

Quick reference for which deployment strategy applies to which infrastructure. The other rule files in this skill cover the six primary modes in depth; everything else is indexed here with a one-paragraph callout.

## Contents

- Master deployment table
- Secondary deployment callouts
- Deprecated Kubernetes charts
- Fleet Management-related paths
- macOS standalone
- Choosing the right mode
- Key facts

## Master table

| Path in `telemetry-shippers` | Mode | Infrastructure | Status | Covered by |
|---|---|---|---|---|
| `otel-integration/k8s-helm` | Daemonset + Deployment (+ Gateway) | EKS, GKE, AKS, OpenShift, EKS Fargate, GKE Autopilot, vanilla k8s | **primary** | `setup-kubernetes.md` |
| `otel-agent/k8s-helm` | Daemonset | Kubernetes (Linux) | **deprecated** — migrate to `otel-integration` | callout below |
| `otel-agent/k8s-helm-windows` | Daemonset | Kubernetes (Windows nodes) | **deprecated** — use `otel-integration` with `opentelemetry-agent-windows.enabled: true` | callout below |
| `otel-ecs-ec2` | Daemon service | ECS on EC2, Linux | **primary** | `setup-ecs-ec2.md` |
| `otel-ecs-ec2-windows` | Daemon service | ECS on EC2, Windows Server 2022 | secondary | callout below |
| `otel-batch-ecs-ec2` | Sidecar per AWS Batch job | AWS Batch on EC2 | secondary | callout below |
| `otel-ecs-fargate` | Sidecar | ECS Fargate | **primary** | `setup-ecs-fargate.md` |
| `otel-ecs-supervisor` | Fargate or EC2 task with OpAMP supervisor | ECS (Fargate or EC2) | secondary (Fleet Management) | callout below |
| `otel-eks-fargate` | Statefulset + self-monitoring Deployment | EKS Fargate | secondary | callout below |
| `otel-linux-standalone` | Helm chart rendering a Linux-tuned config (consumed by `otel-installer/standalone` → systemd) | Any Linux host (EC2, VM, bare metal) | **primary** | `setup-linux-standalone.md` |
| `otel-macos-standalone` | Helm chart rendering a macOS-tuned config (consumed by `otel-installer/standalone` → launchd) | macOS | secondary | note in `setup-linux-standalone.md` |
| `otel-windows-standalone` | Helm chart rendering a Windows-tuned config (consumed by `otel-installer/windows` → PowerShell MSI) | Any Windows host | **primary** | `setup-windows-standalone.md` |
| `otel-installer` | Bootstrap scripts (Bash/PowerShell/Docker) that download the collector MSI/package, register the service, and apply a config — chart-rendered or user-supplied | Linux, macOS, Windows, Docker | **primary** (install path) | `setup-installer.md` |
| `otel-supervised-collector` | Docker + OpAMP supervisor | any Docker host | secondary (Fleet Management) | callout below |
| `otel-supervised-cdot` | Docker + OpAMP supervisor (Coralogix distribution) | any Docker host | secondary (Fleet Management) | callout below |
| `otel-supervised-ebpf-profiler` | Docker + OpAMP supervisor + eBPF profiling | Linux (no Windows) | secondary (profiling + FM) | callout below |
| `otel-infrastructure-collector` | Deployment | Kubernetes | **deprecated** — replaced by `otel-integration` cluster-collector | callout below |
| `otel-collector-windows-image` / `telemetrygen-windows-image` | Container images | Windows | supporting artifact, not a deployment | — |

## Callouts — secondary deployments

Short one-paragraph entries for the modes not covered in a dedicated rule file. Enough to route a user to the right directory and flag the unique gotcha; read the source README for the full recipe.

### `otel-ecs-ec2-windows`

Windows Server 2022 ECS on EC2 with OTel deployed as a Daemon service. **Network mode is `awsvpc`, not host** — unlike Linux ECS EC2. No `filelog` receiver (Windows containers don't expose log files on the host the same way), no Docker socket access, so logs come through OTLP from applications only. **`opamp` extension depends on the pinned image version** — the Windows CloudFormation template historically ships an older Windows collector image (`coralogixrepo/coralogix-otel-collector:<version>-windowsserver-2022`) that predates OpAMP on Windows; for Fleet Management there, use the `-Supervisor` wrapper or bump to a collector build ≥ v0.130. (The `otel-windows-standalone` chart on a modern build DOES render `extensions: [opamp]` by default.) Minimum instance type `t3.xlarge` because of Windows memory footprint; infrastructure uses a NAT Gateway in a private subnet. `resourcedetection.detectors` uses `[env]` only — the `system` detector fails on Windows. See `telemetry-shippers/otel-ecs-ec2-windows/` for the values.yaml.

### `otel-batch-ecs-ec2`

AWS Batch job definitions with a sidecar OTel container. Batch jobs are one-shot: start → run → exit. Config is pulled from **SSM Parameter Store** (`otel_config_parameter_store_cfn.yaml` creates the parameter + execution role), loaded via `--config env:OTEL_CONFIG`. The app container must `dependsOn: [{containerName: otel-collector, condition: START}]` — same anti-race pattern as ECS Fargate but scoped to one-shot jobs. FireLens routes logs through the sidecar. Image: `coralogixrepo/coralogix-otel-collector:<version>`. Troubleshooting: "job stuck in RUNNABLE" is usually compute-environment vCPU limits, not an OTel problem; "permission denied" is the Batch execution role missing `ssm:GetParameter` on the config parameter.

### `otel-eks-fargate`

EKS Fargate uses a **statefulset** for the primary collector (Fargate doesn't support daemonsets because there's no shared host) and a **secondary deployment** that acts as a self-monitoring pod (Fargate workloads can't reach the host kubelet). Two manifests: `cx-eks-fargate-otel.yaml` (primary) and `cx-eks-fargate-otel-self-monitoring.yaml` (secondary). Requires **IRSA (IAM roles for service accounts)** with `CloudWatchAgentServerPolicy`:

```bash
eksctl utils associate-iam-oidc-provider --cluster=NAME --approve
eksctl create iamserviceaccount --cluster=NAME --region=REGION \
  --name=cx-otel-collector --namespace=cx-eks-fargate-otel \
  --role-name=EKS-Fargate-cx-OTEL-ServiceAccount-Role \
  --attach-policy-arn=arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy --approve
kubectl apply -f cx-eks-fargate-otel.yaml
```

**Current `cx-eks-fargate-otel.yaml` includes `k8sattributes` in the `traces` and `metrics/otlp` pipelines** (verified against the telemetry-shippers HEAD manifest). A historical version was missing it — users on an older copy of the manifest who report empty pod metrics / related-data visualizations should re-pull the manifest rather than hand-patching. The `metrics/kubeletstats` and `metrics/self` pipelines intentionally do **not** run `k8sattributes`; users needing pod-level enrichment on those pipelines still need to add it. Each Fargate pod has a **unique IP** (contrary to an earlier misconception that Fargate pods shared IPs), so `pod_association: [{sources: [{from: resource_attribute, name: k8s.pod.ip}]}]` works correctly. Alternative for users wanting cluster-wide tail sampling: the `otel-integration` chart with `values-eks-fargate.yaml` deploying into the same cluster. See `telemetry-shippers/otel-eks-fargate/`.

### `otel-agent/k8s-helm` and `otel-agent/k8s-helm-windows` (deprecated)

The old agent-only chart (`coralogix/opentelemetry-coralogix`). Deprecated in favor of `otel-integration` which bundles agent + cluster-collector + optional gateway in one chart. Users still on this chart see missing features (no Infra Explorer entity events, missing span metrics defaults, no Fleet Management support). Migration:

```bash
helm uninstall otel-coralogix-agent -n coralogix
helm upgrade --install otel-coralogix-integration coralogix/otel-integration -n coralogix -f values.yaml
```

Similarly, `otel-agent/k8s-helm-windows` is deprecated — use `otel-integration` with `opentelemetry-agent-windows.enabled: true`.

### `otel-infrastructure-collector` (deprecated)

Single-replica cluster-level collector. Superseded by the `opentelemetry-cluster-collector` subchart of `otel-integration`. No new deployments — migrate users to the current chart.

## Fleet Management–related paths

`otel-ecs-supervisor`, `otel-supervised-collector`, `otel-supervised-cdot`, `otel-supervised-ebpf-profiler` — all use the OpAMP supervisor pattern for remote config management. See `preset-fleet-management.md` for the surface area that intersects with this skill. Deep OpAMP protocol / supervisor-binary / remote-config-precedence coverage is out of scope here.

## macOS standalone

`otel-macos-standalone` uses launchd (`com.coralogix.otelcol` plist label, `/opt/otelcol` install prefix). Same env conventions as Linux standalone (`CORALOGIX_PRIVATE_KEY`, `CORALOGIX_DOMAIN`). Logs via `filelog` against `/var/log/system.log` (no `journald` on macOS). See the macOS note at the end of `setup-linux-standalone.md`.

## Choosing the right mode

| User asks… | Start from |
|---|---|
| "How do I install on my EC2 instance?" | `setup-installer.md` → `setup-linux-standalone.md` |
| "How do I run on Windows Server?" | `setup-installer.md` → `setup-windows-standalone.md` |
| "We're on EKS" | `setup-kubernetes.md` |
| "We're on EKS Fargate" | `setup-kubernetes.md` + EKS Fargate callout above |
| "We're on ECS" | Is it EC2 or Fargate? → `setup-ecs-ec2.md` or `setup-ecs-fargate.md` |
| "We have Windows ECS tasks" | `otel-ecs-ec2-windows` callout above |
| "We run one-shot Batch jobs" | `otel-batch-ecs-ec2` callout above |
| "We want Fleet Management / remote config" | `preset-fleet-management.md` |
| "We use macOS on dev machines" | macOS section above |
| "We're on bare-metal Linux" | `setup-installer.md` → `setup-linux-standalone.md` |
| "We use GKE Autopilot" | `setup-kubernetes.md` + GKE Autopilot Warden section |

## Key Facts

- **`otel-integration` is the primary Kubernetes deployment.** `otel-agent/k8s-helm` and `otel-infrastructure-collector` are deprecated.
- **ECS EC2 Windows uses `awsvpc` + no filelog.** Linux ECS EC2 uses host network + filelog. Don't reuse Linux patterns on Windows.
- **EKS Fargate uses a statefulset and needs a separate self-monitoring pod.** Current manifest HAS `k8sattributes` in `traces` and `metrics/otlp` (earlier versions did not — users on old copies should re-pull).
- **AWS Batch sidecars load config from SSM** and need the `dependsOn START` anti-race pattern.
- **macOS = launchd**, Linux = systemd, Windows = Service. Otherwise the same env/config contract.
- **Fleet Management / OpAMP-supervisor paths (`otel-ecs-supervisor` etc.) are out of scope beyond the minimum overlap** — see `preset-fleet-management.md` for that overlap (endpoint shape, values-vs-UI precedence). Deep OpAMP internals are not covered here.
