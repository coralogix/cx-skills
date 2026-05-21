# AI Center / GenAI Semantic Conventions

Coralogix AI Center is a trace product surface. It does not populate from
logs or metrics alone, and customer-visible rows depend on GenAI span
attributes being present in the trace data path that AI Center reads.

Use this reference when a customer has LLM traces in Coralogix but AI Center
rows, model/provider columns, prompts, or token usage are missing.

## Detection attributes

AI Center supports both legacy and newer OpenTelemetry GenAI semantic
convention shapes.

| Format | Detection attributes | Notes |
|---|---|---|
| Legacy GenAI semconv | `gen_ai.system` | Common in older instrumentation and some OpenLLMetry-style libraries. |
| Newer GenAI semconv | `gen_ai.provider.name` or `gen_ai.input.messages` | Many libraries require `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` before emitting this shape. |

If none of those attributes are present on the GenAI span, AI Center should
be treated as having no GenAI row to render even if the trace itself exists.

## Product path requirements

- AI Center consumes **trace data**. Logs and metrics do not create AI Center
  LLM rows.
- AI Center depends on the trace/archive path it is designed to read. A
  trace that exists only in a frequent-search or non-archive path can be
  visible elsewhere while absent from AI Center.
- Gateway-side AI enrichment can route only the GenAI spans from a mixed
  trace for enrichment, then return the enriched OTLP trace data to the
  normal trace pipeline. The detection key still comes from GenAI span
  attributes.
- Preserve trace identity and Coralogix ingestion headers through any
  enrichment side path. Header/topic wiring belongs to the ingestion or
  collector owner, not this skill.

## Required troubleshooting checks

1. Confirm the spans are traces, not logs or metrics.
2. Inspect a raw span and look for `gen_ai.system`,
   `gen_ai.provider.name`, or `gen_ai.input.messages`.
3. Check whether message content is disabled by instrumentation defaults.
   Common toggles include:
   - `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`
   - `TRACELOOP_TRACE_CONTENT=true`
4. For newer GenAI semconv, check whether the process opted in with
   `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`.
5. If the customer uses a proxy such as LiteLLM, confirm the proxy or custom
   instrumentation emits GenAI span attributes. A proxy can forward LLM
   traffic without automatically producing AI Center-compatible spans.

## Common attribute-shape mistakes

| Symptom | Likely issue | Fix direction |
|---|---|---|
| No LLM rows | No `gen_ai.system`, `gen_ai.provider.name`, or `gen_ai.input.messages` | Add supported library instrumentation or manual GenAI span attributes. |
| Provider/model empty | Only generic span names are emitted | Add `gen_ai.provider.name`, `gen_ai.request.model`, and `gen_ai.response.model` where available. |
| Messages missing | Content capture is disabled | Enable the library-specific message-content capture setting if customer policy allows. |
| New-format parser misses messages | `gen_ai.input.messages` is an object, not a string | Emit the attribute in the shape expected by the instrumentation/product path. |
| Manual instrumentation works in traces but not AI Center | Trace data is not archived in the AI Center-supported path | Fix routing/archive setup in the collector or ingestion owner. |

## Ownership boundary

This skill owns the telemetry-shape diagnosis: which `gen_ai.*` attributes
are required, which signal is consumed, and why a proxy/custom library might
miss them.

Hand off:

- SDK/library setup and manual span code to `opentelemetry-instrumentation`.
- Collector routing, archive/exporter placement, and gateway side topics to
  `opentelemetry-collector` or the owning ingestion workflow.
- OTTL transforms to `opentelemetry-ottl`.

## References

- OpenTelemetry GenAI semantic conventions:
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
- [apm-service-catalog.md](apm-service-catalog.md) for general span/resource
  identity.
- [associated-boundaries.md](associated-boundaries.md) for topology handoffs.
