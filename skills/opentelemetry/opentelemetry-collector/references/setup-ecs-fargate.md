# ECS Fargate: OTel sidecar

Fargate doesn't expose a host to run a daemonset, so the Coralogix pattern is a **sidecar** collector in every task definition. The app container and the collector share the task's network namespace (`awsvpc`), so apps send OTLP to `localhost:4317`.

- **Image**: `coralogixrepo/coralogix-otel-collector:<version>` (CDOT) or `otel/opentelemetry-collector-contrib:<version>`. Prefer CDOT because it includes the healthcheck binary referenced below.

## Contents

- Minimum task definition
- Essential-container race and healthcheck fix
- Configuration loading from SSM or S3
- IAM requirements
- FireLens log routing
- Typical sidecar pipelines
- Cross-cluster tail sampling
- Operational notes and key facts

## Minimum task definition (abbreviated)

```json
{
  "family": "my-fargate-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "my-app:1.2.3",
      "essential": true,
      "dependsOn": [
        { "containerName": "otel-collector", "condition": "HEALTHY" }
      ],
      "environment": [
        { "name": "OTEL_EXPORTER_OTLP_ENDPOINT", "value": "http://localhost:4317" }
      ]
    },
    {
      "name": "otel-collector",
      "image": "coralogixrepo/coralogix-otel-collector:v0.5.0",
      "essential": false,
      "command": ["--config", "env:OTEL_CONFIG"],
      "environment": [
        { "name": "CORALOGIX_DOMAIN", "value": "eu2.coralogix.com" }
      ],
      "secrets": [
        { "name": "CORALOGIX_PRIVATE_KEY", "valueFrom": "arn:aws:secretsmanager:...:coralogix-private-key" },
        { "name": "OTEL_CONFIG",           "valueFrom": "arn:aws:ssm:...:parameter/otel-config" }
      ],
      "healthCheck": {
        "command": ["CMD", "/healthcheck"],
        "interval": 5,
        "timeout": 3,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

## The essential-container race (and the healthcheck fix)

The bug: if the app container is `essential: true` and the OTel sidecar is `essential: false`, and the app crashes within the first couple seconds, ECS terminates the entire task — including the sidecar — before the collector has finished its `~2–5s` startup. Logs buffered by FireLens never drain; traces/metrics emitted right before the crash are lost.

The fix: make the app container **depend on the sidecar being healthy** before the app starts. That requires (a) the collector to expose a healthcheck and (b) the app's task-definition `dependsOn` to gate on `condition: HEALTHY`.

CDOT (`coralogixrepo/coralogix-otel-collector`) ships with a `/healthcheck` binary exactly for this — see the task definition above. If a user is on `otel/opentelemetry-collector-contrib` and doesn't want to switch, they can enable the `health_check` extension and probe `curl -sf localhost:13133` instead:

```yaml
extensions:
  health_check:
    endpoint: "0.0.0.0:13133"

service:
  extensions: [health_check]
```

```json
"healthCheck": {
  "command": ["CMD-SHELL", "curl -sf http://localhost:13133/ || exit 1"],
  "interval": 5, "timeout": 3, "retries": 3, "startPeriod": 10
}
```

## Configuration loading from S3 or Parameter Store

CDOT and upstream OTel Contrib both honor the `env:` and `envprovider` providers in `--config`. Common Fargate patterns:

- **SSM Parameter Store** — store YAML in a parameter, inject the value into `OTEL_CONFIG` via task `secrets`. `command: ["--config", "env:OTEL_CONFIG"]`.
- **S3 bucket** — set `command: ["--config", "s3://my-bucket.s3.us-east-1.amazonaws.com/config.yaml"]` and give the task role `s3:GetObject` on the key.
- **Inline YAML in env var** — works for short configs; awkward for multi-kilobyte pipelines.

## IAM

Execution role:
- `secretsmanager:GetSecretValue` on the `CORALOGIX_PRIVATE_KEY` secret.
- `ssm:GetParameter(s)` on the config parameter when injecting `OTEL_CONFIG` from Parameter Store via task `secrets`.

Task role:
- Nothing is required for direct-to-Coralogix when the config is inline or injected into `OTEL_CONFIG`.
- If the collector loads config via `s3://...`, grant `s3:GetObject` on the config object (and `s3:GetBucketLocation` if the provider needs to resolve the bucket region).
- Exception: if the user enables AWS-native receivers (e.g. `awsxray`), they need the relevant permissions.

## Log routing: FireLens sidecar pattern

For applications that stream stdout/stderr as logs, FireLens routes those logs into the OTel sidecar via `awsfirelens`:

```json
"logConfiguration": {
  "logDriver": "awsfirelens",
  "options": {
    "Name": "forward",
    "Host": "localhost",
    "Port": "24224"
  }
}
```

The sidecar runs a `fluentforward` receiver on port 24224, routing the stream through the OTel pipeline. Log drivers alternative: `awslogs` → CloudWatch → Coralogix via the Firehose integration (out of scope here).

## Default pipelines (typical)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
      http:
        endpoint: "0.0.0.0:4318"
  fluentforward:
    endpoint: "0.0.0.0:24224"
  awsecscontainermetrics:
    collection_interval: 60s

processors:
  memory_limiter:
    check_interval: 2s
    limit_mib: 384
  resourcedetection:
    detectors: [env, ecs, system]                  # on Fargate, `ecs` IS correct — collector shares task with app
  batch:

exporters:
  coralogix:
    domain: "${env:CORALOGIX_DOMAIN}"
    private_key: "${env:CORALOGIX_PRIVATE_KEY}"
    application_name_attributes: ["aws.ecs.task.family"]
    subsystem_name_attributes: ["aws.ecs.container.name"]

service:
  pipelines:
    logs:
      receivers: [fluentforward, otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
    metrics:
      receivers: [awsecscontainermetrics, otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
```

Note: unlike ECS EC2 daemonset, **`ecs` detector IS correct here** — the collector shares the task with the app, so task metadata maps to the app's container.

## Cross-region / cross-cluster tail sampling

Tail sampling needs a full trace view. On Fargate-only users with traces spanning multiple ECS clusters, the sidecar model alone can't deliver complete traces to a single sampler. The documented pattern is a **centralized collector on ECS EC2** (or EKS) that all Fargate sidecars forward to via `loadbalancing` exporter keyed on `trace_id`:

```
Fargate sidecar ─► loadbalancing (by trace_id) ─► Central EC2 collector ─► Coralogix
                                                 (tail_sampling + spanmetrics here)
```

The same pattern works for pure ECS Fargate by replacing the EKS half with another ECS cluster: sidecar loadbalances by `trace_id` to a central EC2 collector that owns `tail_sampling` + `spanmetrics`.

## Gotchas

- **Essential-container race without the healthcheck.** Without the `dependsOn: HEALTHY` pattern, app crashes within the first ~5s lose buffered logs/traces.
- **OTLP endpoint is `localhost:4317`.** Because of `awsvpc`, the sidecar shares the task ENI. Apps must not try to use the task's ENI IP — `localhost` is correct (and faster).
- **`ecs` detector IS enabled in Fargate.** Don't carry over the "disable ecs detector" rule from `setup-ecs-ec2.md` — that only applies to daemonset mode.
- **Spanmetrics in a sidecar means per-task span metrics.** Fine for per-service metrics; misleading if you expected cluster-wide aggregates. Tail sampling and aggregated spanmetrics belong on a centralized collector.
- **FireLens log driver means logs flow through the sidecar, not straight to CloudWatch.** If the sidecar dies before FireLens flushes, those logs are lost — another reason to use the healthcheck pattern.
- **Fargate has no host-level metrics.** `hostmetrics` receiver is useless here; rely on `awsecscontainermetrics` (available on Platform 1.4.0+ via Task Metadata V4) and `ecs.task.*` metadata via `resourcedetection`.

## Key Facts

- **Sidecar-only on Fargate.** No daemonset possible.
- **App `essential: true`, collector `essential: false`, app `dependsOn: HEALTHY` on the collector.** Prevents the startup race.
- **Apps send OTLP to `localhost:4317`** — shared awsvpc ENI.
- **Config from SSM or S3** via `--config env:OTEL_CONFIG` or `--config s3://...`.
- **`ecs` detector IS correct in sidecar mode** (unlike daemonset).
- **Tail sampling + spanmetrics need a centralized EC2/EKS collector** that all Fargate sidecars forward to via `loadbalancing` on `trace_id`.
- **No task-role AWS perms needed for direct-to-Coralogix with inline or SSM-injected config.** S3 config loading and AWS-native receivers are runtime AWS calls and need task-role permissions.
