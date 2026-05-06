# ECS EC2 (Linux): CDOT daemonset

Coralogix's ECS-on-EC2 integration runs the **Coralogix Distribution of OpenTelemetry (CDOT)** as an ECS service deployed as a Daemon (one task per EC2 node). Apps in other tasks send OTLP to the host IP of their EC2 node.

- **Image**: `coralogixrepo/coralogix-otel-collector:<version>` — the Coralogix Distribution of OpenTelemetry (CDOT), a fork of `otel/opentelemetry-collector-contrib` with extra `ecsattributes` + log-routing components.
- **Deployment shape**: ECS Service with `schedulingStrategy: DAEMON`, host network mode, `awsvpc` is **not** used.
- **Not Fargate.** Fargate can't run daemonsets — see `setup-ecs-fargate.md`.

## Contents

- App-to-collector routing through the EC2 host IP
- Environment variables and task definition shape
- Why to omit the `ecs` detector in daemonset mode
- Typical receivers, processors, and pipelines
- IAM requirements
- When to choose ECS EC2 over Fargate
- Operational notes and key facts

## App → Collector routing

Because the collector uses host network, it binds to `:4317` and `:4318` on the node's private IP. Applications need to send OTLP to **the node IP, not localhost**, unless the app runs in the same network namespace as the collector (rare — bridge-mode tasks still need the host IP).

The common pattern is pulling the instance IP from the AWS metadata service at task startup and passing it as `OTEL_EXPORTER_OTLP_ENDPOINT`:

```bash
INSTANCE_IP=$(curl -sf http://169.254.169.254/latest/meta-data/local-ipv4)
export OTEL_EXPORTER_OTLP_ENDPOINT="http://${INSTANCE_IP}:4317"
```

Bake that into the app container's entrypoint or task-definition `command`. Don't hardcode `localhost` — it only works for sidecar-mode (which ECS-EC2 is not).

## Environment variables

The CDOT image reads these. They are passed as container `environment` entries in the task definition, or pulled from AWS Secrets Manager:

| Variable | Purpose | Example |
|---|---|---|
| `CX_DOMAIN` | Coralogix region domain (no URL, no prefix) | `eu2.coralogix.com` |
| `CX_PRIVATE_KEY` | Send-Your-Data API key | `<secret>` — pull from Secrets Manager |
| `CX_APPLICATION_NAME` | default `application_name` for the exporter | `my-ecs-app` |
| `OTEL_CONFIG` | config YAML path/URL resolved at startup | `ssm://arn:aws:ssm:eu-west-1:...:parameter/otel-config`, `s3://bucket/path/config.yaml`, or an inline param-store value |

`OTEL_CONFIG` accepts the standard OTel collector env-provider syntax. Most users store the config in SSM Parameter Store and reference the parameter ARN.

## Minimum task definition (abbreviated)

```json
{
  "family": "coralogix-otel-collector",
  "networkMode": "host",
  "requiresCompatibilities": ["EC2"],
  "containerDefinitions": [
    {
      "name": "otel-collector",
      "image": "coralogixrepo/coralogix-otel-collector:v0.5.0",
      "essential": true,
      "command": ["--config", "env:OTEL_CONFIG"],
      "environment": [
        { "name": "CX_DOMAIN", "value": "eu2.coralogix.com" },
        { "name": "CX_APPLICATION_NAME", "value": "my-ecs-app" }
      ],
      "secrets": [
        { "name": "CX_PRIVATE_KEY", "valueFrom": "arn:aws:secretsmanager:...:coralogix-private-key" },
        { "name": "OTEL_CONFIG",    "valueFrom": "arn:aws:ssm:...:parameter/otel-config" }
      ]
    }
  ]
}
```

The ECS Service runs this task definition with `schedulingStrategy: DAEMON`. The Auto Scaling Group maintains EC2 capacity. CloudWatch Logs captures the collector's own stdout/stderr.

## Disable the `ecs` detector in `resourcedetection`

The single most common misconfig on this integration.

If you enable the `ecs` detector in a daemonset-mode collector, `resourcedetection` pulls the ECS Task Metadata endpoint — but from the **collector's own task**, not the application task. The collector then stamps its own `aws.ecs.container.id` onto every log/metric/span, overwriting the real container ID from `filelog` or the app's OTLP.

```yaml
processors:
  resourcedetection:
    detectors: [env, ec2, system]                  # NOT "ecs" — omit it for daemonset mode
    timeout: 2s
    override: false
```

The `ecsattributes/container-logs` processor handles per-container attribution correctly from the Docker socket — that's what you want for logs. The `ecs` detector is appropriate only for sidecar mode, where the collector shares its task with the app.

## Receivers and pipelines (typical)

```yaml
receivers:
  filelog/docker:
    include: ["/var/lib/docker/containers/*/*.log"]
    start_at: end
    operators:
      - type: json_parser
        parse_from: body
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
      http:
        endpoint: "0.0.0.0:4318"
  awsecscontainermetrics:                          # task-metadata endpoint, container-level metrics
  hostmetrics:
    collection_interval: 60s
    scrapers:
      cpu: {}
      memory: {}
      filesystem: {}
      network: {}

processors:
  memory_limiter:
    check_interval: 2s
    limit_mib: 512
  ecsattributes/container-logs:                    # in-house CDOT component — attribute logs to correct container
  resourcedetection:
    detectors: [env, ec2, system]                  # no "ecs"
  batch:

exporters:
  coralogix:
    domain: "${env:CX_DOMAIN}"
    private_key: "${env:CX_PRIVATE_KEY}"
    application_name: "${env:CX_APPLICATION_NAME}"
    subsystem_name_attributes: ["docker.container.name"]

service:
  pipelines:
    logs:
      receivers: [filelog/docker]
      processors: [memory_limiter, ecsattributes/container-logs, resourcedetection, batch]
      exporters: [coralogix]
    metrics:
      receivers: [awsecscontainermetrics, hostmetrics, otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [coralogix]
```

## IAM

The task execution role needs:
- `secretsmanager:GetSecretValue` on the CX_PRIVATE_KEY secret
- `ssm:GetParameter` / `ssm:GetParameters` on the OTEL_CONFIG parameter
- `logs:CreateLogStream` / `logs:PutLogEvents` if using CloudWatch Logs for the collector's own logs

No AWS service permissions are needed by the collector **at runtime** for direct-to-Coralogix — the collector doesn't talk to AWS APIs (it only talks to Coralogix). The task role is therefore minimal; users who insist on a broad task role should be pushed back against.

## When to choose EC2 over Fargate

| You have… | Recommend |
|---|---|
| existing EC2 ECS cluster, want one collector per node | **ECS EC2 daemonset** (this file) |
| new workload, want managed capacity, lower ops | **ECS Fargate sidecar** (`setup-ecs-fargate.md`) |
| need host-level metrics, hostmetrics receiver, Docker socket access | **ECS EC2** — Fargate can't |
| Windows workloads | **ECS EC2 Windows** (deployment-index callout) |

## Gotchas

- **Bridge-mode task networking still needs host IP.** Even if the app task uses bridge networking, OTLP still has to reach `http://<INSTANCE_IP>:4317`. `localhost` does not work across container network namespaces on the same host.
- **Service/Daemon scheduling strategy matters.** Use `schedulingStrategy: DAEMON`. Without it, ECS runs one task total, not one per node.
- **FireLens+fluentbit+Firehose is a different flow** — not OTel at all. If a user has that shape, ask why they aren't using this integration; the answer is usually legacy or a feature gap, not a preference.
- **Old CloudFormation template marketing language calls CDOT a "Coralogix Daemon."** CDOT is a distribution of the OTel Collector — still OpenTelemetry-based. The in-house components are narrow (ecsattributes/container-logs and a log-routing shim). Users asking "is this proprietary?" deserve a precise answer: OTel Contrib + two components, no fork of the core.

## Key Facts

- **Apps send OTLP to node IP `:4317`, not localhost.** Pull the IP from `http://169.254.169.254/latest/meta-data/local-ipv4` at startup.
- **Omit `ecs` from `resourcedetection.detectors` on a daemonset.** It stamps the collector's own container ID onto everything.
- **Config lives in SSM or S3.** Set `OTEL_CONFIG` to the `ssm://` or `s3://` URI, `command: ["--config", "env:OTEL_CONFIG"]`.
- **CDOT image is OTel-Contrib + two in-house components** (ecsattributes/container-logs and log routing). Not a fork of the core — just a repackage with extras.
- **Task role is minimal for direct-to-Coralogix.** Execution role needs Secrets/SSM; runtime role needs nothing.
- **`ecsattributes/container-logs` (CDOT component) does per-container log attribution.** That's what you want for container logs — not the `ecs` detector.
