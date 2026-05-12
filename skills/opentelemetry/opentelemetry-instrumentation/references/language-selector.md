# Language Selector — Decision Tree

## Contents
- Step 1: Identify the Target Language / Runtime
- Step 2: Identify Telemetry Signals
- Step 3: Identify Instrumentation Mode
- Step 4: Identify Export Path
- Step 5: Collect Required Variables

Use this file to identify the language, signal, instrumentation mode, and export path
before loading any language-specific reference. Walk each decision in order.

## Step 1: Identify the Target Language / Runtime

| Language / runtime | Reference file to load next |
|---|---|
| Java (any JVM, Spring, Quarkus, etc.) | `java.md` |
| Python (Flask, Django, FastAPI, etc.) | `python.md` |
| Node.js / TypeScript (Express, Fastify, etc.) | `nodejs.md` |
| .NET / C# (ASP.NET Core, console apps) | `dotnet.md` |
| Go / Golang | `go.md` |
| Kubernetes injection (no specific lang yet) | Use `java.md`, `python.md`, `nodejs.md`, or `dotnet.md` — Operator supports all four |
| PHP | Not in scope for this skill — refer to Coralogix PHP docs |
| Lambda / serverless | Not in scope — refer to Coralogix Lambda OTel docs |
| Unknown | Show the matrix in Step 1b and ask |

### Step 1b: Matrix when language is unknown

| Language | Auto-instr | Programmatic | Manual | K8s injection | Coralogix sampler pkg |
|---|---|---|---|---|---|
| Java | Agent JAR (`opentelemetry-javaagent.jar`) | ✗ | `@WithSpan` annotation (extends agent) | Yes (Operator) | None needed |
| Python | `opentelemetry-instrument` CLI | Yes | Yes | Yes (Operator) | `coralogix-opentelemetry` |
| Node.js | Bundled or individual | Via NodeSDK | Yes | Yes (Operator) | `@coralogix/opentelemetry` |
| .NET | Zero-code installer (dotnet-auto) | ✗ | Yes (NuGet SDK) | Yes (Operator) | None needed |
| Go | Out of scope here (OBI/Auto SDK exist) | ✗ | Covered by this skill | ✗ | `coralogix-opentelemetry-go` |

## Step 2: Identify Telemetry Signals

Ask or infer which signals the user needs:

| Signal | Key requirement |
|---|---|
| Traces | Always needed for APM; require `CoralogixTransactionSampler` for Coralogix transactions |
| Metrics | Needed for Coralogix platform metric-dependent features; not required for APM traces-only |
| Logs | Via OTel log bridge (Log4j, SLF4J, slog, zap, NLog, log4net) — SDK logs pipeline, not file-based |
| All signals | Start with traces; metrics and logs can be added incrementally |

## Step 3: Identify Instrumentation Mode

| Mode | When to use it |
|---|---|
| Auto-instrumentation | User wants minimal code changes; frameworks are well-supported |
| Programmatic | User wants some control (e.g. Python + custom samplers) without rewriting app |
| Manual | Full control over span creation; no existing auto-instrumentation library for the framework |
| Code review | Load language reference and `output-templates.md` review section |
| Troubleshooting | Load `troubleshooting.md` |
| Kubernetes injection | User deploys on K8s and wants no-code injection via OpenTelemetry Operator |

### Mode notes by language

**Java:** Coralogix guidance emphasizes the Java agent plus `@WithSpan` annotation-based
span additions. Upstream OpenTelemetry Java also supports pure SDK manual instrumentation,
but that path is not the default Coralogix setup in this skill.

**Python:** Three distinct paths are documented: auto (`opentelemetry-instrument` wrapper),
programmatic (SDK init inside app + `FlaskInstrumentor`), and manual (explicit tracer/span
creation). All three can use `CoralogixTransactionSampler` from `coralogix-opentelemetry`.

**Node.js:** Bundled auto (`@opentelemetry/auto-instrumentations-node` via `NODE_OPTIONS`)
vs individual auto (custom `instrumentation.js` with chosen libraries). Bundled does NOT
support Coralogix transactions — use individual or manual for transaction support.

**Go:** This skill covers manual SDK instrumentation. Go zero-code/eBPF options exist, but
they are out of scope for this SDK instrumentation skill.

## Step 4: Identify Export Path

Do not make a final recommendation until you know the user's scale, runtime, deployment
environment, enrichment needs, retry/buffering requirements, and sampling needs.

| Export path | Good fit when |
|---|---|
| Direct OTLP to Coralogix | Getting started, dev/test, simple deploys |
| Via OTel Collector | Existing collector, production/Kubernetes, enrichment, retry/buffering, or tail sampling needed |
| Unknown | Explain tradeoffs and ask for context |

### Export path tradeoffs

| Aspect | Direct | Via Collector |
|---|---|---|
| Auth | SDK sets `Authorization: Bearer <key>` header | Collector holds the key; SDK exports unauthed to collector |
| Enrichment | Resource attrs in SDK only | Collector can add `k8sattributes`, detect host/cloud |
| Retry / buffer | SDK retry only | Collector `sending_queue` + `file_storage` |
| Sampling | SDK-side head sampling only | Collector can do tail sampling |
| Complexity | Low | Higher (collector deployment) |

## Step 5: Collect Required Variables

Before generating any code or config, confirm these are known (or use placeholders):

| Variable | Placeholder |
|---|---|
| Coralogix region / domain | `<CORALOGIX_REGION>` (e.g. `eu1`, `eu2`, `us1`, `us2`, `ap1`, `ap2`, `ap3`) |
| Send-Your-Data API key | `CORALOGIX_API_KEY` env var |
| Service name | `<SERVICE_NAME>` |
| Application name (Coralogix) | `<CX_APPLICATION_NAME>` |
| Subsystem name (Coralogix) | `<CX_SUBSYSTEM_NAME>` |
| Runtime / framework | (e.g. Flask, Spring Boot, Express, ASP.NET Core) |
| Deployment target | (e.g. bare metal, Docker, Kubernetes, ECS) |

If the region is unknown, instruct the user to find it from their Coralogix platform URL:
`https://dashboard.<region>.coralogix.com` → the region is the subdomain prefix before
`.coralogix.com`. Always load `coralogix-endpoints.md` when generating endpoint config.
