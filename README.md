# Coralogix Skills

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE) ![Status](https://img.shields.io/badge/status-experimental-yellow)

Agent Skills that provide domain-specific context for Coralogix and OpenTelemetry —
APIs, naming conventions, collector behavior, SDK instrumentation, and pipeline patterns.

## Skills

| Skill | Use case | Entry point |
|---|---|---|
| `opentelemetry-collector` | OpenTelemetry Collector deployment, configuration, and troubleshooting for Helm, ECS, standalone, and installer flows. | [`skills/opentelemetry/opentelemetry-collector/SKILL.md`](skills/opentelemetry/opentelemetry-collector/SKILL.md) |
| `opentelemetry-instrumentation` | Instrument Java, Python, Node.js, .NET, and Go applications with OpenTelemetry SDKs — OTLP exporter setup, Coralogix auth headers, APM transactions, Kubernetes Operator injection, and missing-telemetry debugging. | [`skills/opentelemetry/opentelemetry-instrumentation/SKILL.md`](skills/opentelemetry/opentelemetry-instrumentation/SKILL.md) |
| `opentelemetry-ottl` | OpenTelemetry Transformation Language for transform, filter, and routing questions across logs, metrics, and traces. | [`skills/opentelemetry/opentelemetry-ottl/SKILL.md`](skills/opentelemetry/opentelemetry-ottl/SKILL.md) |

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

## Skill review

Validate a skill against the Tessl spec (no API keys required)

```bash
npx tessl skill review skills/<skill_name>
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
