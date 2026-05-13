# Universal installer: `otel-installer`

`otel-installer` is the **deployment half** of the per-OS collector setup. It's paired with a per-OS Helm chart that renders the config:

| Chart (renders config) | Installer script (deploys it) |
|---|---|
| `otel-linux-standalone/` | `otel-installer/standalone/coralogix-otel-collector.sh` |
| `otel-macos-standalone/` | `otel-installer/standalone/coralogix-otel-collector.sh` (same script, detects OS) |
| `otel-windows-standalone/` | `otel-installer/windows/coralogix-otel-collector.ps1` |
| (any) | `otel-installer/docker/docker-install.sh` |

The installer accepts `--config <path>` (Linux/macOS) or `-Config <path>` (Windows) pointing at a user-authored config, or nothing — in which case it ships with a minimal built-in config.

Repo: `telemetry-shippers/otel-installer/`. Releases: `telemetry-shippers` GitHub Releases.

## Contents

- One-liners by platform
- Linux, macOS, Docker, and Windows install commands
- Cross-platform flags
- Required environment variables
- Region and domain handling
- When to recommend the installer
- Operational notes and key facts

## One-liners by platform

### Linux (systemd)

```bash
# Download the installer, optionally inspect, then run
curl -sSL https://github.com/coralogix/telemetry-shippers/releases/latest/download/coralogix-otel-collector.sh \
  -o /tmp/coralogix-otel-collector.sh
# less /tmp/coralogix-otel-collector.sh   # review before running if desired
CORALOGIX_PRIVATE_KEY="<key>" \
CORALOGIX_DOMAIN="<cx-region>.coralogix.com" \
  bash /tmp/coralogix-otel-collector.sh
```

Deep coverage of the resulting systemd deployment: `setup-linux-standalone.md`.

### macOS (launchd)

```bash
# Download the installer, optionally inspect, then run
curl -sSL https://github.com/coralogix/telemetry-shippers/releases/latest/download/coralogix-otel-collector.sh \
  -o /tmp/coralogix-otel-collector.sh
# less /tmp/coralogix-otel-collector.sh   # review before running if desired
CORALOGIX_PRIVATE_KEY="<key>" \
CORALOGIX_DOMAIN="<cx-region>.coralogix.com" \
  bash /tmp/coralogix-otel-collector.sh
```

Same script as Linux. Detects macOS and switches to launchd + install prefix `/opt/otelcol`. See the macOS note at the end of `setup-linux-standalone.md`.

### Docker (any OS)

```bash
# Download the installer, optionally inspect, then run
curl -sSL https://github.com/coralogix/telemetry-shippers/releases/latest/download/docker-install.sh \
  -o /tmp/docker-install.sh
# less /tmp/docker-install.sh   # review before running if desired
CORALOGIX_PRIVATE_KEY="<key>" \
CORALOGIX_DOMAIN="<cx-region>.coralogix.com" \
  bash /tmp/docker-install.sh --config /path/to/config.yaml
```

Runs the collector in a container (`otel/opentelemetry-collector-contrib` by default, or `coralogixrepo/otel-supervised-collector` with `--supervisor`) with ports `4317` (gRPC), `4318` (HTTP), `13133` (health) exposed.

### Windows (PowerShell + MSI)

```powershell
$u = 'https://github.com/coralogix/telemetry-shippers/releases/latest/download/coralogix-otel-collector.ps1'
$f = Join-Path $env:TEMP 'coralogix-otel-collector.ps1'
Invoke-WebRequest -Uri $u -OutFile $f -UseBasicParsing
$env:CORALOGIX_PRIVATE_KEY = '<key>'
$env:CORALOGIX_DOMAIN = '<cx-region>.coralogix.com'
& $f -Config 'C:/path/to/config.yaml'
```

Deep coverage: `setup-windows-standalone.md`.

## Flags (consistent across Linux/macOS/Docker)

The PowerShell variant uses `-PascalCase`; the bash variants use `--kebab-case`. Semantics are identical.

| Flag | Purpose | Default |
|---|---|---|
| `--config PATH` / `-Config` | user-supplied config file | built-in minimal |
| `--version X.Y.Z` / `-Version` | pin a collector version | latest |
| `--supervisor` / `-Supervisor` | install with OpAMP supervisor (Fleet Management) | off |
| `--memory-limit MIB` / `-MemoryLimit` | cap for `memory_limiter` processor | 512 |
| `--listen-interface IP` / `-ListenInterface` | receiver bind address | `127.0.0.1` |
| `--foreground` (bash) | run in foreground for debugging (no service) | off |
| `--uninstall` / `-Uninstall` | remove service + binaries | |

## Environment

| Variable | Required? | Purpose |
|---|---|---|
| `CORALOGIX_PRIVATE_KEY` | **yes** | send-your-data API key |
| `CORALOGIX_DOMAIN` | **yes for built-in config and supervisor** | regional Coralogix domain; optional only when a supplied config hardcodes `exporters.coralogix.domain` |
| `OTEL_MEMORY_LIMIT_MIB` | auto | set from `--memory-limit` |
| `OTEL_LISTEN_INTERFACE` | auto | set from `--listen-interface` |

## Region / domain handling

The installer's built-in default config references `${env:CORALOGIX_DOMAIN}`. If a user only passes `CORALOGIX_PRIVATE_KEY`, the collector needs the domain somewhere — either (a) supplied as env, (b) baked into the config via `--config`, or (c) auto-detected from the cloud provider metadata (AWS only; Google/Azure not auto-detected).

Practical advice: always set `CORALOGIX_DOMAIN` explicitly. Auto-detect is best-effort and a user debugging "no data is landing" almost always benefits from being explicit.

## When to recommend the installer vs. a deeper integration

| You have… | Recommend |
|---|---|
| single Linux/macOS/Windows host, want to be shipping in 5 minutes | `otel-installer` |
| trying it out on a test host before rolling wider | `otel-installer` |
| Kubernetes | `setup-kubernetes.md` (Helm, not this installer) |
| ECS | `setup-ecs-ec2.md` / `setup-ecs-fargate.md` (CDOT image + task definition, not this installer) |
| dozens/hundreds of hosts | `otel-installer --supervisor` with Fleet Management |
| custom OS / packaging constraint | fall back to manual install from the OTel Contrib binary |

## Gotchas

- **Inspect before running.** The examples above use the download-first pattern (`curl ... -o /tmp/...`, then `bash /tmp/...`). Always suggest this approach — it lets the user review the script with `less` or an editor before executing it.
- **Version drift on re-run.** Running the installer without `--version` will pull `latest` on every run — a user who re-runs to "fix" something can accidentally upgrade to a breaking minor. Pin versions in repeatable scripts.
- **`--foreground` is for debugging only.** It bypasses service registration, so there's no restart on boot. Don't use it for production.
- **Docker variant exposes ports `4317/4318/13133` on the host.** If the host already uses these, pass `--p <host>:<container>` equivalents via the underlying docker command (the installer surfaces this through env: `OTLP_GRPC_PORT`, `OTLP_HTTP_PORT`, `HEALTH_CHECK_PORT`).
- **The supervisor path pulls a different image** (`coralogixrepo/otel-supervised-collector` vs. the vanilla contrib image). Size on disk is larger; not a concern in most deployments.

## Key Facts

- **The installer is the end-user install path** for every non-k8s, non-ECS case.
- **Same script handles Linux and macOS.** Windows has its own PowerShell variant with equivalent flags.
- **`--version` matters for reproducibility.** Don't pin in exploration; do pin in any documented install.
- **Auto domain detection is AWS-only.** Always set `CORALOGIX_DOMAIN` explicitly.
- **`--supervisor` enables Fleet Management** via the `opampsupervisor` wrapper process. Modern Windows builds (collector ≥ v0.130) also support the in-process `opamp` extension as an alternative; see `setup-windows-standalone.md`.
