# Contributing to Coralogix Skills

This guide is for anyone adding a new skill, editing an existing one, or
touching the CI configuration. For a high-level overview of the repo
layout, read [`README.md`](README.md) first.

Skill structure and frontmatter are defined by the upstream
[Agent Skills specification](https://agentskills.io/specification) and
enforced by [`skills-ref`](https://pypi.org/project/skills-ref/) in CI. For
authoring guidance, see
[agentskills.io/skill-creation](https://agentskills.io/skill-creation/best-practices).
This file covers the repo-specific mechanics (directory layout, CI, local
commands) on top of that.

## Skill structure

Every skill lives under `skills/` and must contain exactly these files:

```
skills/<skill-name>/                    # e.g. skills/opentelemetry/opentelemetry-ottl/
├── SKILL.md                            # frontmatter + operating rules (required)
└── references/                         # topical reference files (required — or a non-empty SKILL.md body)
    └── *.md
```

Spec conformance is enforced by [`skills-ref`](https://pypi.org/project/skills-ref/),
the reference validator from the Agent Skills maintainers.

## SKILL.md frontmatter

Required fields — `skills-ref` validates the Agent Skills spec fields
(`name`, `description`); the others are repo conventions:

The Agent Skills spec allows only these top-level keys: `name`, `description`,
`license`, `allowed-tools`, `compatibility`, `metadata`. All repo-specific
fields live under `metadata:`. `skills-ref` uses `strictyaml`, so lists must
use block style (`- item` on its own line), not flow style (`[a, b]`).

```yaml
---
name: <skill-name>              # kebab-case; must match the directory name exactly
description: >                  # one-line summary
  What this skill covers and when to load it.
license: Apache-2.0
metadata:
  version: "x.y.z"              # semver (quoted)
  integration: <name>           # primary integration (e.g. ottl, coralogix)
  signals:
    - logs
    - metrics
    - traces
  deployment:
    - kubernetes
    - helm
    - docker
    - ecs
    - aws
  triggers:
    description: >
      When the agent should load this skill.
    always: false
    file_patterns:
      - "**/*.yaml"
    config_keys:
      - "some_key:"
    keywords:
      - relevant term
  docs: https://coralogix.com/docs/...    # canonical upstream reference
---
```

## Adding a new skill

1. **Create the skill directory**: `mkdir -p skills/<skill-name>` and add a
   `SKILL.md` with the frontmatter schema above. `name` must match the
   directory name exactly and be kebab-case.
2. **Add reference files under `references/`** — one `.md` per topic area.
   Weave silent-failure modes and common misuses into the relevant topic
   file rather than isolating them in their own document — readers learn
   the trap at the moment they encounter the feature. The folder name
   follows the [Agent Skills spec](https://agentskills.io/specification#optional-directories).
   If the skill is small, you can skip `references/` and use the `SKILL.md`
   body as the prompt; the validator requires at least one of the two paths
   to produce content.
3. **Validate locally**: `pip install skills-ref && agentskills validate skills/<skill-name>` must pass.
4. **Open a PR**. The CI validation workflow will run automatically.

No workflow changes are ever required — `validate.yml` discovers skills dynamically.

## Running validation locally

### Spec validation (fast, no API keys)

```bash
pip install skills-ref
agentskills validate skills/<skill-name>
```

`skills-ref` checks the Agent Skills spec: `SKILL.md` present, frontmatter
parses, required `name` and `description` fields, `name` matches the directory
name.

## CI

One workflow runs on every PR to `master`:

| Workflow | Trigger | What it checks | Runtime |
|---|---|---|---|
| [`validate.yml`](.github/workflows/validate.yml) | Changes to `skills/` | Agent Skills spec conformance via `agentskills validate` | ~5s |

The spec workflow is fast and deterministic — it must pass before a PR can be merged.
