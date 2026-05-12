# Linux standalone: installer + systemd

A one-line installer that installs the `otelcol-contrib` package, registers a systemd service, and wires an env file — optionally with a user-authored config. Same pattern on macOS (launchd) via the same installer script; Windows has its own PowerShell installer (see `setup-windows-standalone.md`).

```
coralogix-otel-collector.sh   ─►   otelcol-contrib.service
  curl-piped bash                   systemd-active
  .deb/.rpm install
  optional: --config <user-supplied YAML>
```

The Bash installer (`coralogix-otel-collector.sh`) works on both Linux (systemd) and macOS (launchd). It downloads the `.deb`/`.rpm` on Linux or the tarball on macOS, registers the service, and wires the env file. For custom pipelines, author a YAML and pass `--config <path>`. With `--supervisor`, it additionally installs the OpAMP supervisor binary for Fleet Management.

Service name: `otelcol-contrib.service`. Config: `/etc/otelcol-contrib/config.yaml`. Env file: `/etc/otelcol-contrib/otelcol-contrib.conf`.

## Contents

- Install one-liner and installer options
- Systemd layout and environment file
- Default receivers: journald, hostmetrics, otlp, prometheus, filelog
- Host metrics and process scrapers
- Database service discovery
- UI wizard `telemetry.sdk.*` workaround
- Minimum standalone config
- macOS launchd notes
- Operational notes and key facts

## Install (end-user one-liner)

```bash
curl -sSL https://github.com/coralogix/telemetry-shippers/releases/latest/download/coralogix-otel-collector.sh \
  -o "${TMPDIR:-/tmp}/coralogix-otel-collector.sh"
less "${TMPDIR:-/tmp}/coralogix-otel-collector.sh"   # inspect before running
CORALOGIX_PRIVATE_KEY="<key>" \
CORALOGIX_DOMAIN="<cx-region>.coralogix.com" \
  bash "${TMPDIR:-/tmp}/coralogix-otel-collector.sh"
```

Options the installer accepts:

| Flag | Purpose | Default |
|---|---|---|
| `--config PATH` | user-supplied config file (overrides default) | built-in |
| `--version X.Y.Z` | pin a collector version | latest |
| `--memory-limit MIB` | `OTEL_MEMORY_LIMIT_MIB` for the `memory_limiter` processor | 512 |
| `--listen-interface IP` | receiver bind IP (`0.0.0.0` to expose externally) | 127.0.0.1 |
| `--supervisor` | install with OpAMP supervisor for Fleet Management (see `preset-fleet-management.md`) | off |

## Systemd layout (after install)

```
/etc/otelcol-contrib/
  config.yaml                        # collector config
  otelcol-contrib.conf               # EnvironmentFile read by the unit
  discovery.env                      # service-discovery credentials (see below)

/etc/systemd/system/otelcol-contrib.service
/usr/bin/otelcol-contrib             # binary
/var/log/otelcol-contrib/            # logs (via systemd journal, or file if configured)
```

`otelcol-contrib.conf` holds `CORALOGIX_PRIVATE_KEY`, `CORALOGIX_DOMAIN`, and any other env the config references. This file should be `root:root` / `0600` because it contains the API key.

```bash
# /etc/otelcol-contrib/otelcol-contrib.conf
CORALOGIX_PRIVATE_KEY=...
CORALOGIX_DOMAIN=<cx-region>.coralogix.com
OTEL_MEMORY_LIMIT_MIB=512
OTEL_LISTEN_INTERFACE=127.0.0.1
```

```bash
sudo systemctl restart otelcol-contrib
sudo systemctl status otelcol-contrib
journalctl -u otelcol-contrib -f
```

## Default receivers (from the chart render)

The `otel-linux-standalone` chart renders with these receivers by default: `hostmetrics`, `journald`, `systemd`, `otlp`, `prometheus` (self-scrape). The `filelog` receiver is **not** on by default — add it only for apps that write to plain files instead of journald.

| Receiver | Default? | When to use | Trade-off |
|---|---|---|---|
| `journald` | yes | systemd-managed logs, distro default (RHEL/Ubuntu/Debian modern) | structured, metadata-rich; misses apps that log to plain files |
| `systemd` | yes | unit-level metrics (service up/active state) | useful for entity-events + alerting on unit failures |
| `hostmetrics` | yes | CPU/memory/disk/network/processes | standard host-level metrics |
| `otlp` | yes | apps sending OTLP to `localhost:4317` | always on |
| `prometheus` | yes (self-scrape) | collector's own metrics | part of self-telemetry |
| `filelog` | **no** | app writes to `/var/log/*.log` or custom paths | fine-grained glob control; lose journal metadata |

```yaml
receivers:
  journald:
    units: ["ssh.service", "nginx.service"]       # leave empty to read all
    priority: info

  filelog/nginx:
    include: ["/var/log/nginx/*.log"]
    start_at: end
    operators:
      - type: regex_parser
        regex: '^(?P<client>\S+) (?P<ident>\S+) (?P<user>\S+) \[(?P<ts>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<proto>\S+)" (?P<status>\d+) (?P<size>\S+)'
```

## Host metrics and process-level scrapers

`hostmetrics` is standard; the distinguishing feature on Linux is the `process` scraper.

```yaml
receivers:
  hostmetrics:
    collection_interval: 60s
    scrapers:
      cpu: {}
      load: {}
      memory: {}
      filesystem: {}
      network: {}
      paging: {}
      processes: {}
      process:
        include:
          names: ["nginx", "postgres", "java"]
          match_type: strict
        metrics:
          process.cpu.utilization:
            enabled: true
          process.memory.utilization:
            enabled: true
```

`process` scraper needs read access to `/proc`. Under systemd, that works out of the box; some hardened distros (`ProtectProc=`) may require `ProtectProc=default` on the unit. The `processes` (plural) scraper is the whole-system rollup.

## Database service discovery

The installer provisions Linux capabilities so the collector can probe common databases without running as root. Credentials live in `/etc/otelcol-contrib/discovery.env`:

```
POSTGRESQL_USERNAME=otel
POSTGRESQL_PASSWORD=...
MYSQL_USERNAME=otel
MYSQL_PASSWORD=...
REDIS_PASSWORD=...
MONGODB_USERNAME=otel
MONGODB_PASSWORD=...
```

Supported out-of-the-box: PostgreSQL, MySQL, Redis, MongoDB, NGINX, Apache httpd, RabbitMQ, Memcached, Elasticsearch, Kafka, Cassandra. The installer wires the matching receivers into the default config when it detects the service is running.

For a non-default setup, enable the receiver manually:

```yaml
receivers:
  postgresql:
    endpoint: localhost:5432
    username: "${env:POSTGRESQL_USERNAME}"
    password: "${env:POSTGRESQL_PASSWORD}"
    collection_interval: 60s
    tls:
      insecure: true

service:
  pipelines:
    metrics/db:
      receivers: [postgresql]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
```

## Known bug: UI wizard strips `telemetry.sdk.*` for Linux host

When users generate their config through the Coralogix UI's Host integration wizard (OS: Linux), the output config drops the `telemetry.sdk.language`, `telemetry.sdk.name`, and `telemetry.sdk.version` resource attributes from the traces pipeline. APM then renders those services without language icons.

Workaround until the UI fix lands: restore those attributes in a `transform` processor on the traces pipeline, or ask the user to hand-edit the generated config. The same bug was resolved for the Kubernetes wizard earlier — the Host wizard has not yet caught up.

## Minimum standalone config

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "${env:OTEL_LISTEN_INTERFACE}:4317"
      http:
        endpoint: "${env:OTEL_LISTEN_INTERFACE}:4318"
  journald:
  hostmetrics:
    collection_interval: 60s
    scrapers: { cpu: {}, memory: {}, filesystem: {}, network: {}, processes: {} }

processors:
  memory_limiter:
    check_interval: 2s
    limit_mib: "${env:OTEL_MEMORY_LIMIT_MIB}"
  resourcedetection/env:
    detectors: [env, system, ec2]
    timeout: 2s
    override: false
  batch:

exporters:
  coralogix:
    domain: "${env:CORALOGIX_DOMAIN}"
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    application_name_attributes: ["service.name"]
    subsystem_name_attributes: ["host.name"]
    application_name: "linux-host"
    subsystem_name: "default"

service:
  pipelines:
    logs:
      receivers: [journald, otlp]
      processors: [memory_limiter, resourcedetection/env, batch]
      exporters: [coralogix]
    metrics:
      receivers: [hostmetrics, otlp]
      processors: [memory_limiter, resourcedetection/env, batch]
      exporters: [coralogix]
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection/env, batch]
      exporters: [coralogix]
  telemetry:
    logs:
      level: info
```

## macOS note

macOS uses launchd instead of systemd. Service name `com.coralogix.otelcol` (configurable via `PLIST_LABEL`). Install prefix `/opt/otelcol`. Config lives at `<prefix>/config.yaml`. The `journald` receiver is Linux-only — on macOS use `filelog` against `/var/log/system.log` or `log stream`. Otherwise the same rules apply; the same installer script handles both.

## Gotchas

- **Env-file permissions matter.** `/etc/otelcol-contrib/otelcol-contrib.conf` must be `0600` — it contains the private key. The installer sets this; users who hand-edit sometimes widen it.
- **`OTEL_LISTEN_INTERFACE` defaults to `127.0.0.1`.** If apps on the same host can't send OTLP, check they're not trying to reach the external interface. For cross-host receive, set `OTEL_LISTEN_INTERFACE=0.0.0.0` and firewall accordingly.
- **Systemd journal is gated by permissions.** The `journald` receiver needs the collector's user in the `systemd-journal` group (the installer does this). If a user moved the unit to run as a different user, fix group membership.
- **`process` scraper on hardened systems.** `ProtectProc=invisible` (default on some distros) hides other users' processes. Override to `ProtectProc=default` in the unit file if the user needs cross-user process metrics.
- **Installer pins collector version.** Passing `--version` makes reproducibility explicit; running without it may pick up breaking changes at reinstall time.

## Key Facts

- **Install via `coralogix-otel-collector.sh`**, not from source. For a custom config, pass `--config <path>`. Same installer works on macOS (launchd); Windows has a parallel PowerShell installer (see `setup-windows-standalone.md`).
- **Env file at `/etc/otelcol-contrib/otelcol-contrib.conf`**, `0600`, holds `CORALOGIX_PRIVATE_KEY` and `CORALOGIX_DOMAIN`.
- **Prefer `journald` over `filelog` on systemd distros** — richer metadata and less config.
- **DB service discovery credentials go in `/etc/otelcol-contrib/discovery.env`**; installer wires the receivers.
- **UI Host wizard strips `telemetry.sdk.*` from traces** — add them back via `transform` until the UI fix lands.
- **macOS path is launchd** (`com.coralogix.otelcol`, `/opt/otelcol`). Same installer script handles both.
