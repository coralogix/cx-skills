# Associated Information and Ownership Boundaries

Semantic-convention diagnosis is often incomplete if it stops at the
attribute name. Coralogix products also depend on collection topology,
generated metrics, product-specific routing, or signal maturity. This page
keeps those boundaries explicit without making this skill own every
implementation detail.

## Rule of thumb

This skill should answer:

1. Which Coralogix surface is affected.
2. Which signal shape the surface consumes.
3. Which attributes, labels, proto fields, or scopes are relevant.
4. Where a compatibility bridge must happen conceptually.
5. Which adjacent skill owns the exact implementation.

It should not write full collector pipelines, SDK setup, OTTL transforms,
Coralogix routing configuration, or profiling setup unless the answer needs
a tiny illustrative snippet to explain the scope.

## Common boundary cases

| Case | Semconv diagnosis | Owner for implementation |
|---|---|---|
| Continuous Profiling proto changes | OTel profiles proto versions and resource enrichment can affect product identity, including `ProfilesDictionary` and profile attribute indices, but profiles are still a separate signal with unstable proto details. | Profiling workflow / `opentelemetry-collector`. |
| Profiles app/subsystem identity | The same resource-scope principles apply, but profile attributes may be dictionary/indexed through `ProfilesDictionary` rather than normal resource attributes. | Profiling workflow / core routing owner. |
| Javaagent HTTP metrics vs Tomcat/JMX metrics | Javaagent HTTP server metrics use HTTP semconv attributes; Tomcat runtime metrics require JMX scraping. | `opentelemetry-instrumentation` or `opentelemetry-collector`. |
| TraceID load balancing | Tail sampling and often `spanmetrics` need consistent traceID routing in multi-gateway topologies; spans from one trace must reach the same gateway before stateful trace-aware processing. | `opentelemetry-collector`. |
| APM overview empty despite traces | APM overview may require spanmetrics, transaction enrichment, and server/consumer span kinds. | Semconv for span kind/labels; collector/instrumentation for processors and sampler wiring. |
| `cx.application.name` / `cx.subsystem.name` | These are Coralogix routing attributes, not upstream OTel semconv. Final answers should say `core` owns routing configuration, while semconv only diagnoses resource-scope visibility. | `core`, with semconv only noting resource-scope visibility. |
| OTTL bridge syntax | This skill picks bridge location and source/target scope. If the user asks for exact `set(...)`, context, or where-clause syntax, name source and destination scopes and hand off instead of inventing full OTTL. | `opentelemetry-ottl`. |

## Handoff wording

Use direct handoff language:

- "Semconv diagnosis: the value is at log-record scope, but the exporter
  reads resource scope. Use `opentelemetry-ottl` to write the copy-up
  statement."
- "Semconv diagnosis: the generated RED metric label changed after
  spanmetrics. Use `opentelemetry-collector` for the metrics-pipeline
  processor placement."
- "AI Center / GenAI spans are not a semconv diagnosis here. Use
  `ai-app-instrumentation` for GenAI span shape, library setup, and AI
  Center verification."
- "Semconv diagnosis: multiple gateways are splitting one trace before
  tail sampling and `spanmetrics`; use traceID routing / load-balancing
  exporter configuration from `opentelemetry-collector`."

## What not to do

- Do not classify every collector wiring issue as semantic conventions.
- Do not tell customers to downgrade instrumentation when a compatibility
  bridge or product support for both names is the right path.
- Do not hide product-specific constraints behind generic upstream OTel
  language. If Coralogix currently reads a mirror name or generated label,
  say so and name the boundary.
