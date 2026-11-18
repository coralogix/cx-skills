# Coralogix Skills

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE) [![tessl](https://img.shields.io/endpoint?url=https%3A%2F%2Fapi.tessl.io%2Fv1%2Fbadges%2Fcoralogix%2Fopentelemetry-skills)](https://tessl.io/registry/coralogix/opentelemetry-skills)

Agent Skills that provide domain-specific context for Coralogix and OpenTelemetry —
APIs, naming conventions, collector behavior, SDK instrumentation, and pipeline patterns.

## Skills

| Skill | Use case | Entry point |
|---|---|---|
| `opentelemetry-collector` | OpenTelemetry Collector deployment, configuration, and troubleshooting for Helm, ECS, standalone, and installer flows. | [`skills/opentelemetry/opentelemetry-collector/SKILL.md`](skills/opentelemetry/opentelemetry-collector/SKILL.md) |
| `opentelemetry-instrumentation` | OpenTelemetry SDK instrumentation for Java, Python, Node.js, .NET, and Go — OTLP exporter setup, Coralogix resource attributes, APM samplers, and debugging missing telemetry. | [`skills/opentelemetry/opentelemetry-instrumentation/SKILL.md`](skills/opentelemetry/opentelemetry-instrumentation/SKILL.md) |
| `opentelemetry-ottl` | OpenTelemetry Transformation Language for transform, filter, and routing questions across logs, metrics, and traces. | [`skills/opentelemetry/opentelemetry-ottl/SKILL.md`](skills/opentelemetry/opentelemetry-ottl/SKILL.md) |
| `opentelemetry-semantic-conventions` | Shape: OpenTelemetry telemetry-shape diagnosis for Coralogix APM, Database Monitoring, Span Metrics, Resource Catalog, AI Center, Custom Metrics, and logs/serverless surfaces. | [`skills/opentelemetry/opentelemetry-semantic-conventions/SKILL.md`](skills/opentelemetry/opentelemetry-semantic-conventions/SKILL.md) |
| `ai-app-instrumentation` | Ingest: instrument a GenAI application with OpenTelemetry `gen_ai.*` spans (model calls with messages, usage and provider, tool calls, agents), run it, and verify it renders in Coralogix AI Center; also verifies existing gen_ai spans. | [`skills/ai-center/ai-app-instrumentation/SKILL.md`](skills/ai-center/ai-app-instrumentation/SKILL.md) |

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

#### Session spans for AI Center

The Claude Code plugin can link each Claude Code session to the git branches it works on, so
that AI Center can join sessions to pull requests and tickets. It is off until you set the
plugin options **Coralogix domain** (such as `eu2.coralogix.com`) and **Coralogix Send-Your-Data
API key**, in the dialog that opens when you enable the plugin or in `/plugin`.

When it is on, the plugin sends one span to `https://ingress.<domain>/v1/traces` on session
start, on each prompt, after each Edit, MultiEdit, Write or NotebookEdit, when the working
directory changes, and at session end. A span holds the session id, the event name, the tool
name of an edit, and the host, `owner/repo` and branch of the repository's `origin`. It never
holds prompts, tool input or output, local paths, or credentials. A background process sends
the span, so the session never waits for the network.

Requirements: Python 3.7 or later and `git`; on macOS, the Xcode Command Line Tools; on
Windows, Git for Windows (Claude Code runs hooks in Git Bash). If no spans arrive, the last
error is in `~/.claude/plugins/data/<plugin id>/session_spans_last_error.txt`.

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
