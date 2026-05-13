# Changelog

## v0.1.2 (2026-05-13)

### Added

- aggregate evals at publish time with skill prefixes for Tessl UI (#11)

### Changed

- add inspect-before-running guidance to agent + unify envs (#10)


## v0.1.1 (2026-05-12)

### Added

- enhance skill quality and add eval + tessl config (#6)

### Fixed

- release PR version (#7)


## v0.1.0 (2026-05-08)

### Added

- add Codex plugin, tighten install docs and CI (#4)
- add opentelemetry-instrumentation skill (#3)
- add OpenTelemetry skills for Coralogix (#1)

### Changed

- replace direct-push release with PR-based verified-commit workflow (#2)
- initial commit


All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-05

### Added

- `opentelemetry-collector` skill — deployment, configuration, and troubleshooting for the OTel Collector shipping to Coralogix (Helm, ECS EC2/Fargate, standalone, universal installer)
- `opentelemetry-instrumentation` skill — SDK instrumentation for Java, Python, Node.js, .NET, and Go with Coralogix OTLP export
- `opentelemetry-ottl` skill — OTTL authoring for transform, filter, and routing processors
- Codex plugin config (`.codex-plugin/`)
- Claude Code plugin config (`.claude-plugin/`)
- Cursor plugin config (`.cursor-plugin/`)
- `llms.txt` for LLM-friendly repo discovery
