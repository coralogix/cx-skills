# Coralogix Skills

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-experimental-yellow)

Agent Skills that provide domain-specific context for Coralogix and OpenTelemetry —
APIs, naming conventions, collector behavior, SDK instrumentation, and pipeline patterns.

## Skills

| Skill | Use case | Entry point |
|---|---|---|
| `opentelemetry-collector` | OpenTelemetry Collector deployment, configuration, and troubleshooting for Helm, ECS, standalone, and installer flows. | [`skills/opentelemetry/opentelemetry-collector/SKILL.md`](skills/opentelemetry/opentelemetry-collector/SKILL.md) |
| `opentelemetry-ottl` | OpenTelemetry Transformation Language for transform, filter, and routing questions across logs, metrics, and traces. | [`skills/opentelemetry/opentelemetry-ottl/SKILL.md`](skills/opentelemetry/opentelemetry-ottl/SKILL.md) |

Every skill in this repo is continuously evaluated against all three major LLM providers to ensure consistent cross-model reliability:

- `anthropic/claude-haiku-4-5-20251001`
- `google/gemini-3-flash-preview`
- `openai/gpt-5.4-mini`

## Local development

Spec conformance (no API keys, ~5s):

```bash
pip install skills-ref
agentskills validate skills/<skill_name>
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
