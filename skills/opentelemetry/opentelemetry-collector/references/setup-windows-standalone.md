# Windows standalone: MSI installer + Windows Service

A PowerShell one-liner downloads the MSI, registers the `OpenTelemetry Collector` Windows Service, and wires an optional user-authored config.

```
coralogix-otel-collector.ps1   ─►   Windows Service: OpenTelemetry Collector
  Invoke-WebRequest + & installer     downloads MSI + registers service
  optional: -Config <user-supplied YAML>
```

The PowerShell installer (`coralogix-otel-collector.ps1`) downloads the `otelcol-contrib` MSI, registers `OpenTelemetry Collector` as a Windows Service, and (with `-Config`) copies the supplied config into place. With `-Supervisor`, it additionally installs the `opampsupervisor` MSI and registers a second service that wraps the collector for Fleet Management.

Supported: Windows 10/11, Windows Server 2016+, x64/ARM64. Service name: `OpenTelemetry Collector` (quote it: `Get-Service "OpenTelemetry Collector"`).

## Contents

- Regular and supervisor install modes
- Install-script flags
- On-disk layout and service management
- Minimum Windows collector config
- IIS high-CPU / Defender diagnosis
- OpAMP support on Windows
- Dynamic IIS log parsing
- Operational notes and key facts

## Install — regular mode (local config)

```powershell
$u = 'https://github.com/coralogix/telemetry-shippers/releases/latest/download/coralogix-otel-collector.ps1'
$f = Join-Path $env:TEMP 'coralogix-otel-collector.ps1'
Invoke-WebRequest -Uri $u -OutFile $f -UseBasicParsing
# Review before running: https://github.com/coralogix/telemetry-shippers/blob/master/otel-installer/windows/coralogix-otel-collector.ps1
$env:CORALOGIX_PRIVATE_KEY = '<send-your-data-api-key>'
$env:CORALOGIX_DOMAIN = '<cx-region>.coralogix.com'
& $f -Config 'C:/path/to/config.yaml'
```

The `-Config` path is a YAML the user has authored or adapted — any valid config with a correctly-configured coralogix exporter block.

## Install — supervisor mode (Fleet Management)

Needs `CORALOGIX_DOMAIN` in addition to the API key. The chart has `opentelemetry-agent.presets.fleetManagement.supervisor.enabled: true` as the counterpart setting — keep them aligned.

```powershell
$u = 'https://github.com/coralogix/telemetry-shippers/releases/latest/download/coralogix-otel-collector.ps1'
$f = Join-Path $env:TEMP 'coralogix-otel-collector.ps1'
Invoke-WebRequest -Uri $u -OutFile $f -UseBasicParsing
# Review before running: https://github.com/coralogix/telemetry-shippers/blob/master/otel-installer/windows/coralogix-otel-collector.ps1
$env:CORALOGIX_DOMAIN = '<cx-region>.coralogix.com'
$env:CORALOGIX_PRIVATE_KEY = '<send-your-data-api-key>'
& $f -Supervisor
```

In supervisor mode the installer registers a second Windows Service, `opampsupervisor`, which manages the collector process out-of-process. The supervisor handles the OpAMP connection to Fleet Manager — the collector's **base config** (passed via `-Config`) must **not** contain an `extensions: [opamp]` block, because the supervisor is the one running the OpAMP connection. (The in-process `opamp` extension IS supported on modern Windows collector builds, but you pick one or the other, not both — see the OpAMP-on-Windows section below.)

This mode is the recommended path for running older collector versions (e.g., v0.92.0) that do not support the in-process OpAMP extension.

See `preset-fleet-management.md` for the full precedence model (values.yaml vs Fleet Manager UI).

## Install-script flags

| Flag | Purpose | Default |
|---|---|---|
| `-Config <path>` | Path to a config.yaml. In regular mode this is required — without it the service runs a nop config. In supervisor mode it becomes the **base config** merged with remote config from Fleet Manager (cannot contain `opamp` extension). | nop |
| `-Version <X.Y.Z>` | Pin the collector MSI version. | latest |
| `-MemoryLimit <MiB>` | Sets `OTEL_MEMORY_LIMIT_MIB` env var (reference as `${env:OTEL_MEMORY_LIMIT_MIB}` in config). | 512 |
| `-ListenInterface <IP>` | Sets `OTEL_LISTEN_INTERFACE` — use `0.0.0.0` for gateway mode. | 127.0.0.1 |
| `-Supervisor` | Switches to supervisor mode. Registers the `opampsupervisor` wrapper service. | off |
| `-SupervisorVersion <X.Y.Z>` | Pin the supervisor binary version independently of the collector. | latest |
| `-CollectorVersion <X.Y.Z>` | Pin the collector version under the supervisor. | same as `-Version` |
| `-SupervisorMsi <path>` | Use a locally-downloaded supervisor MSI instead of fetching from GitHub. Useful for air-gapped hosts. | off |
| `-SupervisorConfig <path>` | Override the auto-generated supervisor config entirely. Advanced. | auto |
| `-EnableDynamicIISParsing` | Creates `C:/ProgramData/OpenTelemetry/Collector/storage` and passes `--feature-gates=filelog.allowHeaderMetadataParsing` so IIS log parsers read the `#Fields:` header dynamically. **Regular mode only** — cannot combine with `-Supervisor`. Also required when the config uses the `file_storage` extension (e.g. checkpointing). | off |
| `-Uninstall` | Remove the service + binaries. | — |

## On-disk layout

```
C:/Program Files/OpenTelemetry Collector/
  otelcol-contrib.exe                 # binary
  config.yaml                         # copied from -Config

C:/ProgramData/OpenTelemetry/Collector/
  logs/
    otelcol.log                       # collector logs (when configured)
  cache/                              # filestorage extension target, if enabled
```

Service management:

```powershell
Get-Service "OpenTelemetry Collector"
Stop-Service "OpenTelemetry Collector"
Start-Service "OpenTelemetry Collector"
```

## Minimum Windows config

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "127.0.0.1:4317"
      http:
        endpoint: "127.0.0.1:4318"
  hostmetrics:
    collection_interval: 60s
    scrapers: { cpu: {}, memory: {}, filesystem: {}, network: {}, processes: {} }

  # Default chart enables all three: System, Application, Security
  windowseventlog/system:
    channel: System
  windowseventlog/application:
    channel: Application
  windowseventlog/security:
    channel: Security

  iis:                                             # enable only if IIS is present
    collection_interval: 60s

  filelog/iis:
    include: ['C:/inetpub/logs/LogFiles/*/*.log']
    start_at: end
    operators:
      - type: regex_parser
        regex: '^#'                                # (headers — filtered; simplified)

processors:
  memory_limiter:
    check_interval: 2s
    limit_mib: 512
  resourcedetection:
    detectors: [env, system]                       # `gcp`/`azure` if running there
    timeout: 2s
    override: false
  batch:

exporters:
  coralogix:
    domain: "${env:CORALOGIX_DOMAIN}"
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    application_name: "windows-host"
    subsystem_name_attributes: ["host.name"]

service:
  pipelines:
    logs:
      receivers: [windowseventlog/system, windowseventlog/application, windowseventlog/security, filelog/iis, otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
    metrics:
      receivers: [hostmetrics, iis, otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
  telemetry:
    logs:
      level: info                                  # NOT "detailed" in prod (see perf gotcha below)
```

## IIS: high CPU during peak traffic (the filesystem pressure story)

A frequent user symptom — "the OTel collector is at 90% CPU when IIS is under load."

Usually the collector isn't the culprit. Windows Defender (`msmpeng.exe`) scanning new IIS log files as they rotate can saturate disk I/O on the log path, which causes the collector and everything else that touches those files to look CPU-bound in the resource monitor.

Diagnostic order:
1. **Open Windows Resource Monitor → Disk**, look at queue length and latency on the `C:/inetpub/logs/LogFiles/*` path. If Defender is the top disk consumer, the collector is a victim, not the cause.
2. **Confirm collector's verbosity.** A config with `service.telemetry.logs.level: debug` or a `debug` exporter with `verbosity: detailed` dumps every signal to stdout/file — expensive on Windows. Drop to `info` / `basic` in prod.
3. **Only then look at pipeline tuning.** Batch sizing, `memory_limiter`, receiver intervals.

Fix for Defender: exclude the IIS log directory from real-time scanning, or (better) route the collector to read from `log` channels via `windowseventlog` instead of the file path.

## OpAMP on Windows: both shapes work on modern builds

Fleet Management on Windows can use **either** the in-process `opamp` extension **or** the out-of-process `opampsupervisor` wrapper. Both ship with the modern Windows MSI (verified on collector v0.130.7 as rendered by the `otel-windows-standalone` chart).

- **In-process extension (`extensions: [opamp]`)** — the collector itself maintains the OpAMP connection to Fleet Manager. The `otel-windows-standalone` chart renders this by default when `fleetManagement.enabled: true` is set. Config embeds the `opamp` extension pointing at `https://ingress.<domain>/opamp/v1`.
- **Supervisor wrapper (`-Supervisor` on the installer)** — installs a separate `opampsupervisor` Windows Service that runs the collector as a child process. The supervisor owns the OpAMP connection and writes runtime configs to disk that the collector reloads. Required flags: `CORALOGIX_DOMAIN` env in addition to `CORALOGIX_PRIVATE_KEY`. See `preset-fleet-management.md` for the precedence model.

Known caveat — **older image pins**. The `otel-integration` Helm chart's `opentelemetry-agent-windows` sub-preset has historically defaulted to `coralogixrepo/opentelemetry-collector-contrib-windows:0.92.0`, which pre-dates OpAMP support on Windows. If a user on the K8s-on-Windows path (not the standalone MSI) enables `extensions: [opamp]` and sees the collector refuse to start, check the image tag. The fix is to bump to a collector image ≥ 0.130, or switch to the supervisor wrapper.

Practical implication for this skill's scope: a Windows collector that won't start with `extensions: [opamp]` loaded is almost always running an **older image** (e.g. the `otel-integration` Windows sub-preset pinned to `contrib-windows:0.92.0`). Bump the image to ≥ v0.130, or switch to the supervisor wrapper. The `otel-windows-standalone` chart has opamp on by default on current builds.

## Dynamic IIS log parsing

IIS log fields are configurable per-site — you can add custom fields in IIS Manager, and the header comment at the top of each log file declares which columns are present. Static parsers break when a user changes their IIS config.

`-EnableDynamicIISParsing` swaps the baked `filelog` operators for a parser that reads the `#Fields:` header at the start of each file and maps columns dynamically. Turn it on for any user running IIS — off by default for compatibility, but the dynamic parser is what you actually want.

## Gotchas

- **Default install has a nop config.** Without `-Config`, the service runs but routes nothing. Every real deployment passes `-Config`.
- **`CORALOGIX_PRIVATE_KEY` env at install time is written into the service environment**, not the config file. Re-running the installer with a new key overwrites it; hand-edits to the service env via `sc.exe config` get reset on upgrade.
- **`windowseventlog` receiver channels are case-sensitive.** `Application`, `System`, `Security`. Typos result in silently empty logs.
- **Path separators matter.** Use forward slashes in YAML paths (`C:/Program Files/...`). They work everywhere the collector library accepts paths.
- **IIS receiver vs IIS `filelog`.** The `iis` receiver scrapes perf counters (metrics); `filelog` reads IIS access logs (logs). They're complementary, not alternatives. Users asking for "IIS integration" usually want both.
- **OS-level high CPU ≠ collector high CPU.** Use Resource Monitor's per-process view, not Task Manager's defaults.

## Key Facts

- **Install via `coralogix-otel-collector.ps1`**, not from source. For a custom config, pass `-Config <path>` with a YAML that has a correctly-configured coralogix exporter block.
- **Install via the PowerShell bootstrap script with `-Config`** — never skip that flag for real deployments.
- **Service name is the quoted string `"OpenTelemetry Collector"`.** Config lives at `C:/Program Files/OpenTelemetry Collector/config.yaml`.
- **Fleet Management works on Windows two ways** — in-process `extensions: [opamp]` (rendered by default in the modern standalone chart) **or** the `opampsupervisor` wrapper service (`-Supervisor`). Older Windows images (e.g. the `contrib-windows:0.92.0` pinned in the K8s `opentelemetry-agent-windows` sub-preset) predate OpAMP and need the wrapper path or an image bump.
- **Set both `CORALOGIX_PRIVATE_KEY` and `CORALOGIX_DOMAIN` unless the config hardcodes `exporters.coralogix.domain`.** Supervisor mode also needs both.
- **High CPU with IIS is usually Defender, not the collector.** Check disk latency before tuning the pipeline.
- **Prod log level is `info`, not `debug`.** `debug` + `verbosity: detailed` is a known perf regression on Windows hosts.
- **`-EnableDynamicIISParsing` is regular-mode only.** Can't combine with `-Supervisor`. Also required whenever the config uses `file_storage` extension.
