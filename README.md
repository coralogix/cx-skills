# Coralogix Skills

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE) [![tessl](https://img.shields.io/endpoint?url=https%3A%2F%2Fapi.tessl.io%2Fv1%2Fbadges%2Fcoralogix%2Fopentelemetry-skills)](https://tessl.io/registry/coralogix/opentelemetry-skills)

Agent Skills that provide domain-specific context for Coralogix and OpenTelemetry —
APIs, naming conventions, collector behavior, SDK instrumentation, and pipeline patterns.

## Skills

| Skill | Use case | Entry point |
|---|---|---|
| `coralogix-ai-center` | Instrument a GenAI application with OpenTelemetry `gen_ai.*` spans, run it, and verify it renders in Coralogix AI Center — any language, provider, framework, or OTel maturity; also verifies existing gen_ai spans. | [`skills/ai-center/coralogix-ai-center/SKILL.md`](skills/ai-center/coralogix-ai-center/SKILL.md) |
| `opentelemetry-collector` | OpenTelemetry Collector deployment, configuration, and troubleshooting for Helm, ECS, standalone, and installer flows. | [`skills/opentelemetry/opentelemetry-collector/SKILL.md`](skills/opentelemetry/opentelemetry-collector/SKILL.md) |
| `opentelemetry-instrumentation` | OpenTelemetry SDK instrumentation for Java, Python, Node.js, .NET, and Go — OTLP exporter setup, Coralogix resource attributes, APM samplers, and debugging missing telemetry. | [`skills/opentelemetry/opentelemetry-instrumentation/SKILL.md`](skills/opentelemetry/opentelemetry-instrumentation/SKILL.md) |
| `opentelemetry-ottl` | OpenTelemetry Transformation Language for transform, filter, and routing questions across logs, metrics, and traces. | [`skills/opentelemetry/opentelemetry-ottl/SKILL.md`](skills/opentelemetry/opentelemetry-ottl/SKILL.md) |
| `opentelemetry-semantic-conventions` | OpenTelemetry telemetry-shape diagnosis for Coralogix APM, Database Monitoring, Span Metrics, Resource Catalog, AI Center, Custom Metrics, and logs/serverless surfaces. | [`skills/opentelemetry/opentelemetry-semantic-conventions/SKILL.md`](skills/opentelemetry/opentelemetry-semantic-conventions/SKILL.md) |

Every skill in this repo is continuously evaluated against all three major LLM providers Anthropic, OpenAI & Google to ensure consistent cross-model reliability

## Installation

### Agent Skills CLI, Codex, and other agents

Use this for any tool that supports the [Agent Skills](https://agentskills.io)
standard:

```bash
npx skills add coralogix/cx-skills
```

OpenAI Codex can also package these skills as a plugin via
`.codex-plugin/plugin.json`.

### Claude Code

```bash
# Add this marketplace
claude plugin marketplace add coralogix/cx-skills

# Install the plugin
claude plugin install coralogix@cx-skills
```

### Cursor

Via the UI:

1. Open **Cursor Settings** — **Cmd+Shift+J** (macOS) or **Ctrl+Shift+J** (Windows/Linux)
2. Navigate to **Rules**
3. Under **Project Rules**, click **Add Rule** → **Remote Rule (GitHub)**
4. Enter: `https://github.com/coralogix/cx-skills`

Or clone directly into Cursor's global skills directory:

```bash
git clone https://github.com/coralogix/cx-skills ~/.cursor/skills/cx-skills
```

### Tessl CLI

Install from the [Tessl Registry](https://tessl.io/registry/coralogix/opentelemetry-skills) (workspace: `coralogix`):

```bash
npx tessl i coralogix/opentelemetry-skills
```

### Skill review

Validate a skill against the Tessl spec (no API keys required)

```bash
npx tessl skill review skills/<skill_name>
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
