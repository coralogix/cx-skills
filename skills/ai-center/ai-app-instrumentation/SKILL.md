---
name: ai-app-instrumentation
description: >
  Instrument a GenAI application — any language, provider, framework, and maturity from no OpenTelemetry to a production collector — with OpenTelemetry GenAI spans, get it running, and verify it renders in Coralogix AI Center. Use when asked to send LLM, AI or agent traces to Coralogix, add gen_ai instrumentation, connect an AI app or agent to AI Center, or when an app is missing from AI Center or shows no cost or prompts.
  Not for Claude Code / Cursor CLI telemetry (the Code Agents screen), zero-code eBPF capture, or whole-service APM — use opentelemetry-instrumentation or opentelemetry-collector for those.
license: Apache-2.0
allowed-tools: WebFetch(domain:coralogix.com) WebFetch(domain:github.com) WebFetch(domain:raw.githubusercontent.com) WebSearch Bash(cx docs *) Bash(cx spans *) Bash(cx search-fields *) Bash(cx ai-center *)

metadata:
  version: "0.2.0"
  integration: ai-center
  signals:
    - traces
  triggers:
    description: >
      Load when a user wants to send LLM, AI or agent traces to Coralogix AI Center, add gen_ai
      instrumentation to an application, connect an AI app or agent to AI Center, verify or
      audit existing gen_ai spans, or asks why an app is missing from AI Center or shows no
      cost or prompts.
    always: false
    keywords:
      - AI Center
      - gen_ai
      - GenAI spans
      - LLM tracing
      - agent tracing
      - instrument AI app
      - monitor LLM app
  docs: https://coralogix.com/docs/user-guides/ai/otel-integration/
---
# Coralogix AI Center — instrument, run, verify
Takes a GenAI application at any maturity — from no OpenTelemetry to a production
collector — in any language, provider, or framework. Adds `gen_ai.*` OpenTelemetry
spans, gets the app running, and verifies the spans render correctly in AI Center.

Out of scope: whole-service APM beyond the AI call paths; the Code Agents screen
(Claude Code/Cursor CLI telemetry); zero-code eBPF capture.

## When to Use This Skill
| Use case | What to do |
|---|---|
| Add `gen_ai.*` spans to an app that has none, or has OTel but no GenAI spans | Full flow: Phase 1 Assess → Phase 2 Instrument → Phase 3 Run → Phase 4 Verify |
| An app already emits GenAI spans; "verify", "audit", "pull the spans", app missing from AI Center, no cost or prompts | Verify-only mode (Phase 4 §1b) — no repo changes, no questions beyond scope |
| Choose the library or gateway that produces the spans for a stack | Research ladder in Phase 2, then the Stacks table |
| Spans flow but render wrong (empty conversations, zero cost, one provider for every model) | Pitfalls table, then the gate whose criteria failed in Phase 4 |
| Claude Code / Cursor / Copilot CLI usage telemetry (Code Agents screen) | Not in scope — that is the CLIs' own telemetry, not `gen_ai.*` spans |
| Whole-service APM, collector deployment | Not in scope — use opentelemetry-collector / opentelemetry-instrumentation |

## Terms
- **Span source** — the library, gateway, or hand-written code that produces the `gen_ai.*` spans for a call path.
- **Research ladder / rung** — the priority order for choosing a span source: 1 Coralogix stack row, 2 open-source ecosystem, 3 thin shim, 4 traffic choke point (gateway), 5 manual spans; detail in Phase 2.
- **Inference span vs. wrapper span** — an inference span (`chat`/`text_completion`/`generate_content`) is one model call and carries messages; `embeddings` is also a model call, carrying model + usage, but never rendered messages; a wrapper span (`invoke_agent`, `invoke_workflow`, `create_agent`) is metadata-only — messages placed on any of these (including `embeddings`) never render. `execute_tool` is one tool call, carrying tool name, call id, and the call's content on its own attributes — `gen_ai.tool.call.arguments` / `gen_ai.tool.call.result`, not `gen_ai.input.messages` / `gen_ai.output.messages`.
- **Gate** — one of the 12 pass/fail checks in Phase 4 (G1–G12), tiered MUST / SHOULD / IF-APPLICABLE.
- **Probe / probe marker** — the real interaction run to generate test spans, tagged with a unique id so Verify can prove a trace came from this run.
- **Archive tier vs. frequent tier** — archive (`--tier archive`; the UI's Archive / All Logs screen) is Coralogix's long-term store and the only one AI Center reads; frequent (`--tier frequent`) is fast recent-data storage, useful only to confirm arrival within seconds.
- **Maturity path** — M1–M3, how much OpenTelemetry already exists in the repo (see the Maturity router); a verify/audit request skips the router entirely (Phase 4 §1b).

## Rules
1. **Read this whole file first** — before the first action on the repo, read this file end to end; the Pitfalls section is read up front, not on symptoms. A phase started without its section in context is invalid.
2. **Docs first** — never implement from memory; fetch current Coralogix and OTel GenAI semconv docs before writing code.
3. **Open-source instrumentation only** — no proprietary Coralogix SDK. OpenLLMetry (Traceloop), OTel contrib GenAI instrumentors, or manual `gen_ai.*` spans.
4. **Latest versions, new shape preferred** — newest instrumentation library release and `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`; prefer a span source that produces `gen_ai.provider.name` + `gen_ai.input.messages`. A legacy-only span source (OpenLLMetry's `gen_ai.system` + `gen_ai.prompt.{i}.*`) is acceptable — AI Center parses both shapes.
5. **Docs in this session**: `cx docs fetch "user-guides/ai/otel-integration/span-attributes.md"` once per session, before designing spans (or before Verify in verify-only mode) — recorded in the report.
6. **Attributes from the source of truth only** — the OTel GenAI semconv registry or the Coralogix inventory (`span-attributes.md`). `gen_ai.conversation.id`, `gen_ai.agent.name`, and the `invoke_agent` / `execute_tool` operation names are registry entries; attributes from proposal PRs or vendor extensions do not exist for AI Center.
7. **Archive is the read path** — AI Center reads traces only from the archive tier, never the frequent tier.
8. **App identity** — `cx.application.name` + `cx.subsystem.name` resource attributes, set consistently across every process.
9. **Input and output messages are a MUST, wired per environment** — `gen_ai.input.messages` and `gen_ai.output.messages` are captured on every inference span. Every in-scope environment turns trace export AND content capture ON in a config file that environment actually loads — the environment's own config for a permanent value, the personal gitignored `.env` for a temporary one; a code default or an inline command-line value wires nothing and is FAIL. Quote the proof in the report as `path:line: VAR=value`.
10. **Keys never in chat** — never ask the user to paste an API key or secret into the conversation, and never print one; keys live in env vars, a gitignored `.env`, or the cx profile.
11. **Evidence or label it** — a verification claim needs archive-tier query evidence, or is explicitly labelled user-reported.
12. **Ask only what's the user's to decide** — at most four questions, asked with the agent's structured question tool when it has one (options, the recommended one first, in plain language); otherwise a short numbered list. Everything else is inferred from the repo and the tenant and listed in the report as *Decisions I made*.
13. **Inference span per model call**: every LLM request/response is one inference span (`chat` / `text_completion` / `generate_content`) carrying model, usage and messages. AI Center renders messages ONLY from inference spans; `invoke_agent`, `invoke_workflow`, `create_agent`, `embeddings`, `retrieval` are metadata-only in the UI — content placed there is invisible and FAILS G2. Zero inference spans = FAIL, never a vacuous pass.
14. **One `chat` span = one *completed* model call** with non-zero usage. Streaming SDKs deliver assistant content per block and per delta with empty usage; a span per event over-counts 10–100× with zero tokens and zero price. Before Verify, reconcile per model route that carried traffic (one row per route): chat spans per trace == completed model calls (distinct message ids / the SDK's turn count); any chat span with zero output tokens is a span source defect to fix, never a pricing quirk. When the stream's terminal event carries zero usage for a call, fall back to the SDK's per-turn usage totals and put the turn's totals on that turn's last chat span, stating the fallback in the report; a trace left at zero usage and zero cost is never acceptable as an upstream finding without that fallback and a `cx ai-center model-pricing get` check.
15. **Provider = who served the call.** Behind a gateway or a custom client/in-house wrapper (e.g. an internal `llm_client`), resolve the provider from the routing config of whatever gateway or client wrapper is in the path — e.g. LiteLLM: `model_list` → `litellm_params.model` prefix: `bedrock/`→`aws.bedrock`, `openai/`→`openai`, `vertex_ai/`→`gcp.vertex_ai`, `anthropic/`→`anthropic`. An SDK or CLI "provider" field (`firstParty`, `gateway`) describes the client, not the backend, and the API shape is not the provider. A self-hosted or unknown model gets the semconv value if one fits, else a stable lowercase name, plus a pricing override (see Export path). A static or client-side value FAILS G1.
16. **Cache-token semantics differ by provider** (e.g. Anthropic's `input_tokens` excludes cached tokens, OpenAI's `prompt_tokens` includes them); most instrumentations emit the cache counts separately on `gen_ai.usage.cache_read.input_tokens` / `gen_ai.usage.cache_creation.input_tokens`. How AI Center expects `gen_ai.usage.input_tokens` to relate to them is defined in `span-attributes.md` — follow that doc, don't decide from memory.
17. **Span source by the ladder, with evidence**: every rung above the one chosen is recorded with the lookup that ruled it out (command or URL + what it returned). A rung with no recorded lookup is *not evaluated*, not *ruled out*, and blocks the span source choice — architectural reasoning is not a lookup.
18. **The report is the deliverable**, written for the user, not for the skill: verdict first, findings in product language, gate ids only in parentheses (see the Report section). Evidence completeness is never cut for length; prose is. If the user explicitly narrows the task (e.g. asks only to verify), do what they asked.
19. **One continuous flow**: don't stop between phases. Pause only for the Assess questions, the who-runs question, or when waiting for the user to run the app. Wait for a long probe inside the turn (bounded loop, see Run).
20. **The probe runs the application as configured** — its default model, default entry flow, default flags. Changing the input to make a gate pass (forcing another model, shortening the prompt, disabling a feature) is a FAIL of the probe, not a workaround; a default path that breaks is the finding to report. Every model route that carried traffic in the run is reconciled and gated on its own.
21. **PASS means live evidence** from this run's archive query. A defect fixed in code but not re-run is FAIL (fixed, re-run pending) — never PASS with a qualifier. When the run fails for a reason outside the instrumented path (auth, quota, network), reproduce at most twice, mark the affected gates BLOCKED with the evidence, and ask — do not spend the session debugging the environment.
22. **Counts come from aggregate queries, never from listings.** Every number in the reconciliation and the test-traffic inventory is the result of `groupby … aggregate count()` over the whole application and time window (per `gen_ai.conversation.id` and `gen_ai.operation.name`); a `limit N` listing is not a count. Every conversation id the query returns is in the inventory — unexplained conversations or spans (including test fixtures such as all-zero ids) are a FAIL of hygiene, not noise. Absolute window only: pin an absolute ISO-8601 UTC `--start`/`--end` window (e.g. `date -u +%Y-%m-%dT%H:%M:%SZ` on macOS/Linux; PowerShell `(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')` on Windows) on the first query and reuse it in every later query.

## Workflow
| Phase | Input | Output | Pauses |
|---|---|---|---|
| 1 Assess | repo + optional tenant access | maturity path, the four answers, inferred decisions, ladder rung per call path | the four questions |
| 2 Instrument | Assess output contract | code changes, flags, how to run | — |
| 3 Run | Instrument output contract | probe marker, entry point, time window | who-runs question; user-run: wait for signal |
| 4 Verify | Run output contract | gates table, verdict | — |

If a MUST gate FAILs: gap list → back to Instrument → re-run per who-runs → re-verify — repeat until every MUST gate passes.

Phase transitions are automatic — finishing a phase means starting the next phase's first step in the same turn — except the Assess questions, the who-runs question at the start of Run, and the user-run wait-for-signal.

A phase may be dispatched to a subagent given that phase's section verbatim plus the incoming contract, never a paraphrase.

## Maturity router
| Path | State | What Instrument does |
|---|---|---|
| M1 | no OTel | SDK + instrumentor + export, from scratch |
| M2 | OTel SDK present, no GenAI spans | add instrumentor into the existing provider |
| M3 | `gen_ai` spans already flowing — or the user asks to verify / audit / pull existing spans | Verify-only mode (see the Verify section): no questions, no ladder, no probe, no stability wait; ~12 canonical queries; one-screen report |

Full router, tenant preflight, and the four questions live in the Assess section. The export mechanism — direct OTLP vs an existing collector — is a separate decision from maturity; see the Export path section.

## Working with the user
- Ask only what's genuinely the user's to decide: which environments, which call paths, which real flow to run, what to mask. Never ask what the repo or the tenant already answers (naming, tenant, region, archive, registration, whether the config ships to third parties, which library produces the spans).
- Ask with the agent's structured question tool when it has one — one call, up to four questions, each with 2–4 options in the user's language (no gate ids, no skill jargon), the recommended option first. Otherwise, a short numbered list.
- Who runs the application is asked **after** Instrument, at the start of Run — not in Assess.
- Never end a turn mid-verification. State exactly what remains unverified and the command that completes it.
- Keys are never pasted into chat; point the user at env vars, a `.env` file, or a CLI profile.

## Phase 1 of 4 — Assess
Analyze the repo — and the tenant, when query access is offered — to pick a maturity path and ask the four questions that drive every later phase.

**Input:** repo access. Query access (a configured cx profile) is optional; when absent, see the no-query-access line under Tenant preflight.

### 1. Repo discovery
| Check | How |
|---|---|
| LLM SDKs/frameworks | Read dependency manifests (`pyproject.toml`/`requirements.txt`, `package.json`, `go.mod`, `pom.xml`/`build.gradle`, `*.csproj`) and grep the code for LLM client imports — OpenAI SDK, Anthropic SDK, LangChain, LlamaIndex, Vercel AI SDK, Bedrock, Vertex/Gemini, LiteLLM, etc. List every package that makes GenAI calls; each needs an instrumentation decision in the Instrument section. |
| How the app runs locally | The repo's documented way to run it (README, task runner / build scripts, container compose files, `package.json` scripts, etc.): find the documented local runner and its default input — that command is the default probe (see the third question); an app that also runs in containers or pods still has a local runner more often than not. |
| OTel setup | Is an OTel SDK already installed and configured (tracer provider, exporter)? Does any existing instrumentation emit `gen_ai.*` attributes? |
| Collector hints | Scan for `otel-collector*.yaml`, a collector service in `docker-compose*.yml`, Helm charts/values, k8s manifests, Terraform. The repo is only a hint — collector configs commonly live in a separate infra repo, so the user is the source of truth; ask only when the repo shows a collector whose location is unclear. |
| Naming convention | Check mapping/config files, any collector config found above, and — with query access — `cx spans` on existing spans for `cx.application.name`/`cx.subsystem.name`. **Preserve by default.** Changing the convention is a migration that breaks existing dashboards, alerts, and saved views; it needs the user's explicit approval as a stated decision, never a side effect. |
| Gateway / proxy in the path | LiteLLM/router config, `ANTHROPIC_BASE_URL`/`OPENAI_BASE_URL` overrides, `*_BASE_URL` for sub-processes; a gateway already in the path is a rung-4 span source candidate and the usual answer when the calling process cannot see the HTTP call (CLI/agent SDK sub-process, sandbox). |

### 2. Tenant preflight (query access only)
Run these before asking anything. Their output settles tenant, region, archive and registration — none of those is ever asked when a profile answers:

Step 0 — find the query profile: `cx profiles list`. One profile → use it. Several → ask the user which one. None, or `cx` not installed → run the cx onboarding together with the user (see "Install and first profile" in the cx CLI section), then continue. Confirm access with one `cx spans "limit 1" --tier archive --start now-7d --profile <p>` call: an error (e.g. "required scope", auth) means no query access — fix the profile, not the data; an empty result means access works but there is no data (see below).

```bash
cx ai-center applications list                                                                       # this app already registered?
cx spans "filter tags['gen_ai.provider.name']:string != null | limit 5" --tier archive --start now-7d  # gen_ai.* already flowing?
cx spans "filter tags['gen_ai.prompt_price']:string != null | limit 1" --tier archive --start now-7d   # any tenant span enriched → archive + parsing proven
```
A `cx spans "limit 1" --tier archive` that returns a row proves the archive tier is connected; the profile's region is the region; `applications list` answers registration. An empty result — no spans reached the archive in the last 7 days — means the archive is likely not connected or traces aren't routed to it, and AI Center will show nothing: flag this to the user immediately, do not wait, and point at the archive setup guide: `cx docs fetch "user-guides/data-flow/s3-archive/connect-s3-archive.md"` (https://coralogix.com/docs/user-guides/data-flow/s3-archive/connect-s3-archive/). Fetch `span-attributes.md` and `providers.md` here too — the span-source decision is made from them.

No query access → ask instead: is this app already registered, and is the archive tier connected with traces routed to it?

### 3. The four questions (one call)
| Question (plain language) | Options | Recommended |
|---|---|---|
| Which environments should send traces to AI Center? | local dev / staging / production (multi-select) | the ones the repo has config for |
| Which parts of the app should be traced? | the discovered LLM call paths, named in the app's own terms (e.g. "the chat endpoint", "the nightly summarizer") | all of them |
| Which real flow should I use to check it works end to end? | the documented default flow / a scenario the user names | the default flow, multi-step and tool-using where the app supports it |
| Is there anything in prompts or tool data that must not be exported (PII, secrets)? | nothing — capture everything / mask these fields / exclude these environments | capture everything (messages are required for AI Center); an exclusion is recorded as the user's decision |

Not asked — inferred and listed in the report under *Decisions I made*: application/subsystem naming (the repo's existing convention, or the service name when none — never a new scheme), tenant and region (the working cx profile), archive tier (proven by the `limit 1` archive query), registration (`applications list`), collector (repo config; asked only when the repo shows a collector whose location is unclear), whether the config must stay vendor-neutral (yes when the repo is a published library, SDK or template — detected from package metadata; otherwise Coralogix-specific values are fine), and the span source (the ladder). Ask a fifth question only when a decision is irreversible or touches a shared resource (e.g. changing a shared gateway's config).

### 4. Output contract → Instrument
Hand the Instrument section: maturity path (M1–M3), environments, call paths, the flow to run, masking decision, and the inferred decisions (naming, tenant, archive, registration, collector, vendor-neutral or not, span source), ladder rung per call path + rungs ruled out with the lookup that ruled them out.

## Phase 2 of 4 — Instrument
Choose the instrumentation, write the code that emits OpenTelemetry GenAI spans, and wire the export path. This phase uses no Coralogix credentials.

**Input** — the Assess handoff: maturity path (M1–M3), the flow to run, environments in scope, call paths to instrument, collector answer, naming convention, vendor-neutral decision.

**Output** — files changed; flag names; `cx.application.name` / `cx.subsystem.name` values; how to run the app; per-environment leftovers (deploy-config file + the exact lines that would enable them); and, for user-run, the filled run checklist from the Run section.

Design to the gates in the Verify section — read them before writing code. Its "Required attributes per span type" section is the single source for what each span must carry. AI Center reads trace data only from the archive tier; the prerequisite is checked in the Assess section.

### Principles
- **Laser focus on the AI interaction, in tiers.** MUST: inference spans with the required attributes, including `gen_ai.input.messages` and `gen_ai.output.messages` — an integration without message content does not pass. SHOULD: conversation id, user id, `execute_tool` spans. IF-APPLICABLE / full: request-handler root span, workflow and skill-step spans carrying the step identity, `invoke_agent` spans. Whole-service APM beyond the AI call paths is a separate offer, made after verification passes.
- **Registry attributes only.** Emit only `gen_ai.*` attributes present in the OTel GenAI semconv registry (https://github.com/open-telemetry/semantic-conventions/blob/main/docs/registry/attributes/gen-ai.md) or the Coralogix inventory, because attributes from proposal PRs and vendor extensions do not exist for AI Center.
- **Pass config values explicitly and verify them against the installed library's parser** — the Stacks table carries the variable and accepted values per library. The same value is permissive in one library and strictly rejected in another, and a strict parser can degrade to capturing nothing with only a log warning.
- **Loud failure over silent degradation.** A swallowing guard around telemetry code (bare except, warn-and-continue, an `is not None` skip) costs both the data and the alarm.
- **Attach cross-cutting attributes at a level every span passes through** — a span processor's on-start hook, not app-level decorators, which miss auto-instrumentor spans.
- **In an application you deploy, when an SDK ships its own telemetry backend, turn off the vendor upload and send spans to your OTLP export; in a published library, SDK, or template, leave the backend choice to the consumer (the vendor-neutral rule).** Confirm the switch you used stops the upload, not span generation.
- **Kill switches default OFF in code and are turned on per environment in the deploy config.** Content capture always gets its own switch so prompts can be disabled without losing tracing, but it is ON in every environment in scope — turning it off anywhere is the user's explicit, recorded decision, never a default; add an export switch only when the app has no existing export control. Local dev stays off with a documented one-line opt-in, and every environment in scope must be switched ON — a flag off everywhere delivers nothing. Wire the switch ON in each in-scope environment's config file and cite file:line; inline command-line flags wire nothing. Wire identity and switches for the run you are about to perform into a config file the app loads (temporary values → the personal gitignored `.env`; permanent → the environment's config), then start the app with its documented command and no inline overrides. The report's 'Environments switched on' line points at the line that sets the value — a code default is not such a line.

### Research ladder
Per call path, choose the **span source** — the library, gateway or code that produces the `gen_ai.*` spans — by taking the highest rung that resolves, and verify every rung with a live lookup rather than from memory.

1. **Coralogix.** The stack row in the Stacks table, then the compatibility matrix (`cx docs fetch "user-guides/ai/otel-integration/providers.md"`) and the copy-paste scripts in `user-guides/ai/otel-integration/code-examples.md` (Python, Java, .NET, Go).
2. **The open-source ecosystem.** Check sources in order: OpenLLMetry (https://github.com/traceloop/openllmetry); `open-telemetry/opentelemetry-python-contrib` `instrumentation-genai/`; `open-telemetry/opentelemetry-python-genai` `instrumentation/`; `open-telemetry/opentelemetry-js-contrib`; the semconv-genai conformance matrix (https://github.com/open-telemetry/semantic-conventions-genai → `reference/README.md`), which lists per span type which libraries have verified instrumentation; then a web search and a PyPI/npm search. Guessing package names is not a lookup. Vet each candidate against the code paths the app actually uses — which method it wraps, which conventions it emits, whether its pins are installable. **Prefer a span source that produces the new shape** — `gen_ai.provider.name` with `gen_ai.input.messages` / `gen_ai.output.messages`. A legacy-only span source is acceptable because AI Center parses both shapes: OpenLLMetry today emits `gen_ai.system` with `gen_ai.prompt.{i}.*` / `gen_ai.completion.{i}.*`, and its content switch is `TRACELOOP_TRACE_CONTENT=true`. `OTEL_SEMCONV_STABILITY_OPT_IN` does not flip a legacy span source, so check the shape it actually writes; the Stacks table is the lookup.
3. **Thin shim over a near-miss.** When a package wraps a sibling method, misses one hook, or needs a small adapter or subclass, a shim on top of it beats hand-writing the whole span model.
4. **The traffic choke point.** When the calls already flow through a gateway or proxy (an `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` override, a router), the gateway's own telemetry support can emit GenAI spans for every client passing through it, including CLIs nothing can instrument in-process. Scope the span sources so each call path has exactly one. Before ruling a gateway out: fetch its telemetry doc live (LiteLLM: `cx docs fetch "integrations/ai-observability/ai-apps/litellm.md"`), check its scoping options (per-key/team metadata, per-route callbacks, resource attributes) and whether the app already tags its calls. "Shared with other traffic" is a scoping task, not a disqualifier; record the outcome either way.
5. **Manual spans.** Author the `gen_ai.*` spans yourself per the required-attributes table in the Verify section, and record what was searched and ruled out.

A resolved rung is implemented in the same task. Ask the user only when two rungs are genuinely viable and the trade-off is theirs to make.

Record the ladder as a table in the report: Rung | Lookup performed (command / URL) | What it returned | Verdict. A rung without a lookup is written *not evaluated*; the choice is invalid while any higher rung is not evaluated. Deciding on rung 5 early and then writing justifications for the others is the failure this table exists to catch. "Not evaluated" and "not applicable" are not verdicts you may choose rung 5 on top of: rung 2 is evaluated by opening the named repositories for the SDK in use and recording what was found (package name, version, which method it wraps); rung 3 is evaluated by stating what would be shimmed and why it is or is not thin.

#### Agent SDKs and CLI-driven agents
For any agent SDK or CLI-driven agent, first check live whether its default/built-in telemetry actually produces `gen_ai.*` spans (inference/tool/agent operations). If it does not — vendor-shaped attributes instead — do not use that default mechanism: produce the spans per this section (one `chat` span per completed model call, keyed on the SDK's own call-start/call-end events, usage from the terminal event) or via the gateway (rung 4). Example: Claude Code's built-in telemetry emits vendor `claude_code.*` data (see the Stacks table), not `gen_ai.*`, so it is not a span source for AI Center — don't extrapolate another SDK's internals from the worked example below without checking it live.

- **Worked example — a `chat` span is one completed model call.** Claude Agent SDK / Anthropic streaming: the SDK relays `StreamEvent`s — one model call is `message_start` (carries `message.id`, `model`, input-token usage) → `content_block_*` deltas → `message_delta` (carries `stop_reason` and output-token usage) → `message_stop`. Open the span on `message_start`, close it on `message_stop`, take usage from `message_start` + `message_delta`. `AssistantMessage` arrives per content block and its `usage` is empty or zero in streaming mode — keying spans or usage on it yields zero-usage spans. Zero usage is never an environment or routing issue: the gateway returns usage for every served call, so a zero-usage chat span is your span source reading the wrong event. Usage precedence: `message_delta.usage` + `message_start.message.usage` per call → if both are zero, the SDK's per-turn usage totals on the turn's last chat span (reported as a fallback) → never zero.
- The `invoke_agent` span is the parent and carries agent identity only (`gen_ai.agent.name`, `gen_ai.conversation.id`) — never the messages. Subagent runs (`Agent`/`Task` tool) are nested `invoke_agent` spans with a distinct `gen_ai.agent.name`.
- Tool calls become `execute_tool` children (hooks or tool-use/tool-result events) carrying `gen_ai.tool.name`, `gen_ai.tool.call.id`, arguments and result.
- On tool failure, `gen_ai.tool.call.result` carries the error text as well as `otel.status_code = ERROR` with the description; a tool span with a status and no result is incomplete.
- The provider comes from the response model / gateway route, never from the API shape. Resolve it by looking the response model up in the gateway's route table; the SDK's own `provider`-style field is the client's view and is wrong behind a gateway.
- Reconcile before Verify: chat spans == completed model calls, execute_tool spans == distinct tool call ids, invoke_agent spans == agents that ran; zero-usage chat spans mean the wrong event is being keyed on.
- A run that fails (SDK error result, exception, cancellation) sets `otel.status_code = ERROR` with the description on the `invoke_agent` span too, so failed agent runs are countable; a bare `invoke_agent` root with no status and no children is an unfinished or failed run that hides its failure.
- If the stream cannot yield per-call spans, the gateway (rung 4) is the span source — say so in the report; a single summary span per turn is not an option.

### Implementation
**Install the tracer provider globally** so app spans and every instrumentor join the same traces. A process-local provider produces orphaned GenAI subtrees with no request around them; if you scope it narrower on purpose, state why.

**Author the interaction tree to the tier you committed to.** Where the app has no tracing, create the request-handler root span, the spans inside tools around their backend calls, and the workflow or skill-step spans carrying the step identity. Where it has them, verify the GenAI spans nest under them.

**Set `gen_ai.provider.name` to the semconv well-known value for the provider actually called:**

| Provider | Value |
|---|---|
| OpenAI · Anthropic | `openai` · `anthropic` |
| AWS Bedrock · Azure | `aws.bedrock` · `azure.ai.openai` · `azure.ai.inference` |
| Google | `gcp.vertex_ai` · `gcp.gemini` · `gcp.gen_ai` |
| Mistral · Cohere · DeepSeek | `mistral_ai` · `cohere` · `deepseek` |
| Groq · Perplexity · xAI · IBM watsonx | `groq` · `perplexity` · `x_ai` · `ibm.watsonx.ai` |

**Behind a gateway, override `gen_ai.provider.name` per call** from the model actually routed: one static provider for every call means wrong breakdowns and wrong cost.

**Failed calls set span status `ERROR` and record the exception.** AI Center counts errors only from `otel.status_code == ERROR`, taking the message from `otel.status_description`, so an error caught and logged without touching span status is invisible.

**JSON-valued attributes are string-encoded JSON, never an object.** Every message carries `role`, and parts are typed `text`, `tool_call`, or `tool_call_response`.

**Pin a version ceiling when a shim touches private surfaces** (underscore attributes or methods), make a mismatch fail loudly instead of skipping silently, and let the wiring tests be the upgrade gate.

**Add or upgrade packages with the repo's own package manager and lockfile** (e.g. `uv add`, `poetry add`, `pnpm add`/`npm install --save`, `go get`, Maven/Gradle dependency files) — never a bare `pip install` that leaves the manifest unchanged. Before upgrading an existing package, tell the user "upgrading X a→b because Z" and get approval.

**Wire the tracer provider's shutdown into the app's teardown, ordered LAST.** Batch span processors buffer; without `force_flush()` / `shutdown()` on exit, every deploy, restart, and Ctrl-C drops the final batch — including the spans emitted while other resources close.

### Export path
Choose the export mechanism independently of the maturity path — does the app export through an existing collector, or directly via OTLP?
- **An existing collector is in the path** → the app exports to it, and the Coralogix exporter is added to **its** config, wherever that config lives — that config may sit in another repo; ask the user when this repo shows no collector but production is in scope. One path only, no parallel direct export alongside it. Apply the existing-pipeline checklist below.
- **No collector** → deploy one (recommended) or export directly via OTLP.

A collector handles auth, batching, and retry, keeping credentials out of application code. `private_key` is a Send-Your-Data key, whose env var is checked for presence in the Run section — reference it as an env var here, never as a literal.

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"

exporters:
  coralogix:
    domain: "eu2.coralogix.com"             # your region
    private_key: "${CORALOGIX_PRIVATE_KEY}" # Send-Your-Data API key
    application_name: "my-genai-app"
    subsystem_name: "my-service"
    application_name_attributes:
      - "cx.application.name"
    subsystem_name_attributes:
      - "cx.subsystem.name"
    timeout: 30s

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [coralogix]
```

**Alternative: direct OTLP export (no collector):**

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.eu2.coralogix.com:443"   # your region
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer ${CORALOGIX_SEND_YOUR_DATA_KEY}"   # from the environment, never a literal
# Python OTel SDK: URL-encode the space as %20 — "Authorization=Bearer%20${...}" — a literal space causes silent auth failure
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=my-app,cx.subsystem.name=my-subsystem"
```

**Application environment variables (collector path):**

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_EXPORTER_OTLP_INSECURE="true"
export OTEL_SERVICE_NAME="my-ai-service"
export OTEL_RESOURCE_ATTRIBUTES="cx.application.name=my-app,cx.subsystem.name=my-subsystem"
export OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
# Message-content capture: the variable AND the accepted value depend on the installed
# library version — see the Stacks table. OTel contrib: OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT
# =true, or an enum in newer builds: NO_CONTENT (default) | SPAN_ONLY | EVENT_ONLY | SPAN_AND_EVENT.
# OpenLLMetry: TRACELOOP_TRACE_CONTENT=true.
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
```

#### Existing-pipeline checklist (when exporting through an existing collector)
| Check | Why |
|---|---|
| Head or tail sampling does not drop GenAI spans | Sampled-out spans under-count tokens and cost |
| `filter` / `transform` / `attributes` processors keep the `gen_ai.*` attributes | A drop or redaction rule silently removes message attributes |
| `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` and `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT` left unset | Truncated message JSON no longer parses |
| OTLP gRPC receiver `max_recv_msg_size_mib` and batch `send_batch_max_size` sized for message payloads | The receiver's default 4 MiB message limit rejects large prompt batches |
| `application_name_attributes: [cx.application.name]` and `subsystem_name_attributes: [cx.subsystem.name]` on the Coralogix exporter | Otherwise every app lands under the exporter's static names |

**Cover every environment the user asked for.** Find where env vars and config reach each one (k8s env defaults, Helm values, Terraform, `.env.*` files) and wire both enablement and export there. A collector defined only in a local-dev compose file covers local dev alone; check whether that compose file is also used in production before concluding, then deliver the production half too or use direct export and say why.

**Document every new variable in the repo's env example file** (`.env.example` or equivalent), with a warning on the content-capture flag that enabling it exports user prompts and model responses.

**Code that ships to other people's environments (a library, SDK or template) stays vendor-neutral:** a generic OTLP endpoint and `OTEL_RESOURCE_ATTRIBUTES`, with Coralogix-specific values appearing only as documented examples.

**Unknown or self-hosted models need a pricing override** — register them with `cx ai-center model-pricing set` (JSON file, `--yes`), or their cost stays 0. The four `gen_ai.*_price` attributes are Coralogix enrichment and are never emitted by the app.

### Multi-agent systems
- **Type a subagent's own execution as a nested `invoke_agent` span (MUST when the app spawns agents), not a generic tool span; leaving subagents as a single `execute_tool` is a user decision recorded as the user's answer, never a unilateral scope-out.** The agent graph renders only from `invoke_agent` spans, and a bare tool span hides the subagent's internal structure.
- **Nest recursively.** A subagent dispatched as a tool call is valid: the `execute_tool` span (carrying its tool result) is the parent, and the subagent's `invoke_agent` span nests under it, with the subagent's own inference, tool, and nested agent spans beneath that.
- **Name subagents distinctly** via `gen_ai.agent.name`. Frameworks often default every subagent to the same role name, so derive a specific name from the subagent's actual task.

### Before handing off
A checklist the report echoes line by line:

1. Wiring tests added (file).
2. Tracer shutdown / `force_flush()` wired last in teardown (file:line).
3. Every new variable in the env example file the repo's developers copy from (`.env.example` or its documented equivalent), with the content-capture warning — if that file is a stub, add the variables to it anyway; "unrelated" or "stub" is not a reason to skip.
4. Both switches ON per in-scope environment (file:line).
5. Test suite does not export telemetry — proven by query: run the suite, then query the tenant for spans of this application in that window (`groupby $l.subsystemName, tags['gen_ai.conversation.id']:string aggregate count()`); the result MUST be empty. Settings classes that read a `.env` file make `pytest` inherit a developer's `ENABLE_*=true` — reading a code default proves nothing.
6. Gates walked on paper — every gated attribute has a span source, every model call has an inference span.

Symptom-driven debugging lives in the Pitfalls section.

## Phase 3 of 4 — Run
Get the instrumented application to actually send spans, either the skill runs it or the user does.

**Input:** the instrument handoff — files changed, flags added, app/subsystem names, how to run, per-environment leftovers.

### 0. Who runs it — ask if still unknown
If who runs the app is still unknown, ask: "The code is in place. To check it works, the app has to run once and send a few spans. Do you want me to run it, or will you run it?" Options: *I run it* (state what you need: the run command, an LLM key, the local stack) / *You run it* (the checklist below). This is the first time the user hears about running the app — say why in the question. Skip this question when the user already said who runs the app.

### 1. Shared contract
Both modes must produce the same evidence for the Verify section:

| Element | Requirement |
|---|---|
| Probe marker | A unique conversation id / user id / prompt token the skill defines, included in the interaction, so Verify can prove a trace came from this run ; the probe is the app's real default use case (see the third question in Assess), not a prompt designed for the test |
| Entry point | The one a customer would hit — the product's public API or UI — crossing every process boundary the change touches (queue/worker/background-task hops). Never a dev shortcut (`just`/make target, direct service invocation, an internal test harness) — unless it is the only local runner, in which case use it AND label it as such in the report's Entry-point line; unlabelled shortcuts are omissions |
| Both switches on | Trace export AND message-content capture enabled for the run — a run without content capture proves nothing about messages |
| Time window | Recorded as an absolute ISO-8601 UTC window at probe start and end (e.g. `date -u +%Y-%m-%dT%H:%M:%SZ` on macOS/Linux; PowerShell `(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')` on Windows), for the query in Verify — never estimated from memory |

**Handoff to Verify:** probe marker, entry point used, time window, app/subsystem names, expected span types, who ran it.

### 2. Skill-run
#### Credentials — ask once whether each is configured
- **cx profile** chosen for query access (see Assess § Tenant preflight) — never collect a key value.
- **Export key env var** the app/collector config references is set (existence only — never print or echo its value, e.g. `[ -n "$VAR" ] && echo set || echo missing`).
- **LLM/gateway API keys** the app needs are set.
- **Tenant and region** — confirmed from the working cx profile.

Ask only whether each is configured, never for the value.

#### Live validation (before the real run)
| Step | What | Evidence to record |
|---|---|---|
| 1 | Run one trivial `cx spans "limit 1"` with the configured profile | Query access confirmed |
| 2 | Make one live call with the LLM/gateway key | Call succeeded — present is not valid |
| 3 | First probe arrival | Check `--tier frequent` within a minute of the run for span count and names. If frequent is empty, check the app/collector exporter logs for quota or auth failures — the export key's validity is proven by the probe arriving, not by a separate throwaway call; the archive question was already settled at preflight, so don't wait on `--tier archive` here. Gates still use archive only |

If the user has no Send-Your-Data key, walk them through creating one: `cx docs fetch "user-guides/account-management/api-keys/api-keys.md"`, then guide them click-by-click (Data Flow → API Keys, which key type, what to name it). Keys go into a gitignored `.env` or the collector's environment — never chat.

#### Dependency preflight
Before the end-to-end run, verify everything it will touch: docker daemon and required containers up, DB reachable and migrated, no placeholder values in env files (team id, region), and both enablement flags on. Collect anything missing in one question (the agent's structured question tool, or a short numbered list), re-check, then run.

### Waiting for a long probe
A real use case can run 10–40 minutes. Stay in the turn: wait inside one Bash call with a bounded loop — a blocking status endpoint if the app has one (`GET /run-status?timeout_seconds=`-style), else `until <done-condition>; do sleep 30; done` on the app's log or DB row, cap 45 minutes — then continue to Verify in the same turn. Do not background the probe and end the turn to wait for a notification; a headless session ends with the turn and the run stays unverified. Run the probe as the application runs it by default (its documented command, default model and flags); when a probe attempt fails, record its trace id — every attempt, failed or not, is test traffic to report. After the run, query the tenant with `groupby tags['gen_ai.conversation.id']:string, tags['gen_ai.operation.name']:string aggregate count()` for the application and window; that table is the run inventory. Mechanics: the Bash tool kills or backgrounds a call that exceeds its `timeout` parameter (default 2 min, maximum 10 min). Pass `timeout` = the loop's bound (≤ 600000 ms), keep every wait call under 10 minutes, and chain calls until the condition is met. If a call was backgrounded anyway, re-poll synchronously in a new call — never end the turn to wait for its notification. Never run the wait with `run_in_background`, and never call `ScheduleWakeup` — both hand the run to a notification that a headless session will not live to receive.

#### Run the interaction
A synthetic round-trip (a stubbed model call) is a useful bootstrap to confirm the pipeline works, but the completion bar is a real application run through the entry point from the shared contract — multi-turn and tool-using wherever the app supports it. Prefer one multi-turn probe conversation per verification round over many one-shot runs.

Stop only processes you started, by the PID you recorded; never pattern-kill or kill by port — the machine may be shared.

```bash
your-start-command &
APP_PID=$!   # if the start command is a wrapper, record the server's PID the wrapper reports instead
kill "$APP_PID"
```

### 3. User-run
Hand the user this checklist, as a file in the repo (ask before adding it) or printed inline, then stop and wait:

| Block | Contents |
|---|---|
| **Enable** | Flag names and files per environment, from the instrument handoff (both trace export and content-capture flags); a Send-Your-Data key wired as the export credential — check the env var it lives in is set (never ask for its value), and if missing, tell the user which gitignored `.env` file to put it in; offer the key-creation walkthrough (`cx docs fetch "user-guides/account-management/api-keys/api-keys.md"`) if they need one |
| **Drive** | The interaction to run — through the entry point a customer would hit, multi-turn and tool-using wherever the app supports it, crossing any queue/worker boundary the product has |
| **Mark** | The probe marker to include, agreed now, so Verify can attribute the spans |
| **Signal** | What to send back: the marker, the time window, the entry point used, which environments were run |

Do not proceed to the Verify section until the user signals done. When they do, continue with the probe marker, entry point, and time window they report.

### 4. Re-run on failure
If a MUST gate FAILs in Verify after either mode, the re-run follows the who-runs answer from step 0 — skill-run reruns itself, user-run gets the checklist again.

## Phase 4 of 4 — Verify
Read the spans back from Coralogix and hard-validate them against the gates — the integration's only definition of done.

**Phase input (run handoff):** probe marker, entry point used, time window, `cx.application.name`/`cx.subsystem.name`, expected span types, who ran the app.
**Phase output:** the gates table, PASS/FAIL with evidence per gate; on any MUST FAIL, the gap list that goes back to the Instrument section.

### 1. Verification mode
| Mode | Prerequisite | The skill | The user | Verdict label |
|---|---|---|---|---|
| **skill-run verification** | a configured cx profile, proved with one trivial `cx spans` call | runs every gate query itself, records the output | nothing | stated plainly, evidence attached |
| **user-run verification** | the user can run `cx` or open AI Center; the skill needs no key | hands over each gate query **with its expected values**, then reads the pasted output and rules on it | runs the queries, pastes the output back | **"user-reported"** on every gate |

Missing query access selects user-run verification — it never blocks the phase.

### 1b. Verify-only mode (M3, or "verify / audit / pull the spans")
No repo work, no questionnaire, no span-source ladder, no probe, no stability re-query. Pin the window first, run the canonical set, then write the one-screen report. Budget: the canonical queries below plus at most 5 exploratory queries, each named in the report as an investigation with its finding.

```bash
PROFILE=default   # the cx profile that answered the preflight
S=$(date -u -v-3d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '3 days ago' +%Y-%m-%dT%H:%M:%SZ); E=$(date -u +%Y-%m-%dT%H:%M:%SZ)   # window the user asked for, pinned once
Q=(--tier archive --start "$S" --end "$E" --profile "$PROFILE" -o json)   # array: zsh does not word-split a plain "${Q[@]}"
cx spans "limit 1" "${Q[@]}"                                                                   # access
cx ai-center applications list --profile $PROFILE                                      # catalog + URL
cx ai-center model-pricing get --profile $PROFILE                                      # overrides
cx spans "filter tags['gen_ai.system']:string != null || tags['gen_ai.provider.name']:string != null || tags['gen_ai.input.messages']:string != null || tags['gen_ai.operation.name']:string != null
  | groupby \$l.applicationName as app, \$l.subsystemName as sub, tags['gen_ai.operation.name']:string as op
    aggregate count() as spans, distinct_count(\$d.traceID) as traces,
      count_if(tags['gen_ai.request.model']:string != null) as has_model,
      count_if(tags['gen_ai.usage.output_tokens']:number > 0) as has_usage,
      count_if(tags['gen_ai.input.messages']:string != null || tags['gen_ai.prompt.0.content']:string != null) as has_in,
      count_if(tags['gen_ai.output.messages']:string != null || tags['gen_ai.completion.0.content']:string != null) as has_out,
      count_if(tags['gen_ai.prompt_price']:number > 0) as priced,
      count_if(tags['gen_ai.conversation.id']:string != null) as has_conv,
      count_if(tags['gen_ai.request.user']:string != null || tags['enduser.id']:string != null || tags['user.id']:string != null) as has_user,
      count_if(tags['otel.status_code']:string == 'ERROR') as errors" "${Q[@]}"                # coverage: one query answers detection, messages, usage, cost, identity, errors
cx spans "filter tags['gen_ai.operation.name']:string == 'chat' || tags['gen_ai.operation.name']:string == 'text_completion' || tags['gen_ai.operation.name']:string == 'generate_content'
  | groupby tags['gen_ai.provider.name']:string as provider, tags['gen_ai.request.model']:string as model aggregate count() as c" "${Q[@]}"   # provider per model route
cx spans "filter tags['gen_ai.input.messages']:string != null || tags['gen_ai.prompt.0.content']:string != null
  | select \$l.applicationName as app, \$d.traceID as trace, tags['gen_ai.input.messages']:string as in_msg, tags['gen_ai.output.messages']:string as out_msg,
           tags['gen_ai.prompt.0.role']:string as legacy_role, tags['gen_ai.prompt.0.content']:string as legacy_in, tags['gen_ai.completion.0.content']:string as legacy_out
  | limit 3" "${Q[@]}"   # shape sample, new OR legacy — never dump whole spans
TRACE_ID=0123456789abcdef0123456789abcdef   # one trace id from the shape sample
cx spans "filter \$d.traceID == '$TRACE_ID'
  | select \$d.spanID as span, \$d.parentId as parent, \$l.operationName as name, tags['gen_ai.operation.name']:string as op | limit 200" "${Q[@]}"   # one tree
cx spans "filter tags['otel.status_code']:string == 'ERROR' && tags['gen_ai.provider.name']:string != null
  | groupby \$l.applicationName as app, tags['otel.status_description']:string as why aggregate count() as c | limit 20" "${Q[@]}"   # errors
```
Grade the gates from these outputs locally; do not re-run a query to "confirm" a number you already have.

### 2. Required attributes per span type
The single source for what must be on a span; the Instrument section designs to this table.

| Span type (`gen_ai.operation.name`) | Required (MUST) | Recommended (SHOULD) | Notes |
|---|---|---|---|
| **Every GenAI span** | detection: `gen_ai.provider.name` (legacy fallback `gen_ai.system`) **or** `gen_ai.operation.name`; `gen_ai.operation.name` ∈ `chat`, `text_completion`, `generate_content`, `embeddings`, `invoke_agent`, `create_agent`, `execute_tool`, `invoke_workflow`, `retrieval`; `cx.application.name` + `cx.subsystem.name` | `gen_ai.conversation.id`; `otel.status_description` next to an error status | Span typing reads the attribute only — the span name `{operation} {model}` is a semconv convention, informational. The UI also parses the legacy shape: an instrumentor that emits only `gen_ai.system` (OpenLLMetry/Traceloop) still passes detection. Every model call has an inference span; a trace whose GenAI spans are all wrapper types (`invoke_agent`…) FAILS G1 |
| **Inference** — `chat`, `text_completion`, `generate_content` | On every span: `gen_ai.request.model`, `gen_ai.input.messages` (or, from a legacy-only instrumentor, the indexed `gen_ai.prompt.{i}.role` / `gen_ai.prompt.{i}.content`). On a call that returned a response, add: `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` (> 0), `gen_ai.output.messages` (or legacy `gen_ai.completion.{i}.role` / `gen_ai.completion.{i}.content`), `gen_ai.response.finish_reasons`, plus `gen_ai.usage.cache_read.input_tokens` and `gen_ai.usage.cache_creation.input_tokens` when the provider reports them. On a failed call, add instead: `otel.status_code == ERROR` with `otel.status_description` — no usage or output messages to report | identity — `gen_ai.request.user` \| `enduser.id` \| `user.id`; `gen_ai.conversation.id`; `gen_ai.system_instructions`; tool definitions via `gen_ai.tool.definitions` (legacy `gen_ai.request.tools`) | There is no `cache_write` attribute. `cache_read_input_tokens`, `cached_tokens`, `cache_creation_input_tokens` are normalized on ingest. `gen_ai.usage.total_tokens` is informational. `gen_ai.prompt_price`, `gen_ai.response_price`, `gen_ai.read_cache_price`, `gen_ai.write_cache_price` are Coralogix enrichment, not app-emitted. OpenLLMetry/Traceloop (Python and Node) still emits the legacy shape in practice — prefer a new-shape span source where the stack has one (the Stacks table). AI Center renders messages only from inference spans; wrapper operations are parsed as metadata-only, their `gen_ai.*.messages` are dropped |
| **`embeddings`** | `gen_ai.request.model`, `gen_ai.usage.input_tokens` | — | Metadata-only, like the wrapper operations: no message content required or rendered, but still a valid inference operation for detection and cost |
| **`execute_tool`** | `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` | the backend calls the tool makes, as child spans | `gen_ai.tool.call.id` has to be set explicitly; many instrumentors leave it empty |
| **`invoke_agent`** (and `create_agent`) | `gen_ai.agent.name` | `gen_ai.conversation.id`; inference and tool spans nested underneath | The agent graph renders **only** from `invoke_agent` spans, with `gen_ai.agent.name` as the node label |

**Shape rules**

- `gen_ai.input.messages` / `gen_ai.output.messages` are **string-encoded JSON arrays** of `{role, parts: [{type: text | tool_call | tool_call_response, ...}]}`, with a `role` on every message. A language-native `repr`/`toString` blob stuffed into a `content` field passes a non-empty check and is corrupt for AI Center. Where the chosen instrumentor emits only the legacy indexed prompt/completion attributes, those are the accepted equivalent and are read the same way.
- The input array MUST contain at least one `role: "user"` entry carrying the actual prompt — assistant/system-only input is a FAIL. `gen_ai.response.finish_reasons` is likewise a JSON array encoded as a string.
- `gen_ai.provider.name` MUST be the semconv well-known value of the provider that actually served the call (`openai`, `anthropic`, `aws.bedrock`, `azure.ai.openai`, `gcp.vertex_ai`, `gcp.gemini`, …), resolved per call behind a gateway — never one static value for every call; a legacy-only span source carries that same value on `gen_ai.system`.
- A failed call MUST carry `otel.status_code == ERROR` (with `otel.status_description`): AI Center counts errors from the span status only, never from message content.

### 3. Read the spans back
| Tier | Use | Latency |
|---|---|---|
| frequent | arrival checks only — did anything land, how many, which span names | seconds |
| **archive** | **every gate** — AI Center reads trace data only, and only from the archive tier | minutes up to ~30 min; poll with a retry loop before concluding data is missing |

If a tag filter returns nothing on the frequent tier, filter by application/subsystem (`$l.applicationName` / `$l.subsystemName`) instead; if frequent stays empty for the app entirely, check the app/collector exporter logs rather than waiting on `--tier archive` for arrival — the archive question was already settled at preflight. **All gate evidence comes from `--tier archive`.**

Query patterns, field paths, and tips: the cx CLI section; the canonical query set is in the Verify-only mode above.

**Prove the trace came from this run before auditing it.** Filter on the probe marker from the run handoff. Content inside the payloads proves nothing: shared datasets carry other processes' output, and a stale dev server from another checkout happily produces traces that would otherwise be audited as this run's.

**Prove the run itself is admissible.** The trace must come from the entry point recorded in the handoff — a real application run, crossing the process boundaries the change touches. A dev shortcut, a direct service invocation, or a synthetic call exercises none of the propagation the gates exist to check; if that is all that exists, go back to the Run section for a real run rather than auditing it.

**Fetch the attribute inventory if not already fetched this session — never audit from memory:**

```bash
cx docs fetch "user-guides/ai/otel-integration/span-attributes.md"
```

### 4. Gates
Record PASS/FAIL **with evidence** — the query used and the values observed. **One gates table per instrumented unit** (language, template, service): a unit without its own table is not verified, whatever the others show. N/A is admissible only when the application has no such construct at all (no agents, no tools, no failing call to exercise); a gate that is empty because of the integration's own design — a single summary span, no tool spans, a wrapper carrying the messages — is FAIL, never N/A. PASS is reserved for live evidence from this run; a fix verified only by unit tests is FAIL (fixed, re-run pending). An anomaly on the tenant under your application name — unexpected conversations, bare roots, zero-usage spans — is yours until an aggregate query proves otherwise; never attribute it to another developer, an earlier attempt or the environment without that query. Re-query for stability only when this run generated the traffic and the window includes the last 30 minutes (archive ingestion lags); a closed absolute window over traffic you did not generate cannot drift — never re-query it, never sleep for it. When a wait is warranted, compute it from `date -u +%s`, cap it at 2 minutes, and run it inside one Bash call.

| # | Tier | Gate | PASS criteria | Evidence to record |
|---|---|---|---|---|
| G1 | MUST | Detection + required attributes | every completed inference span is detected as GenAI and carries the Required column of the required-attributes table for its `gen_ai.operation.name`. A legacy-only instrumentor satisfies detection with `gen_ai.system`. And values are correct — `gen_ai.provider.name` is the provider that actually served the call, `gen_ai.request/response.model` the model served; a static provider behind a gateway FAILS ; a chat span with zero usage tokens FAILS unless it correctly carries `ERROR` status (a failed call has no usage to report) |  the read-back query output, one row per span type |
| G2 | MUST | Messages present and well-shaped | `gen_ai.input.messages` non-empty on every completed `chat`/`text_completion`/`generate_content` span and valid per the shape rules, holding a `role: "user"` entry with the probe prompt; `gen_ai.output.messages` non-empty and valid whenever the call returned a response — a failed call carries ERROR status instead (see G8), not empty output messages. Legacy indexed `gen_ai.prompt.{i}` / `gen_ai.completion.{i}` attributes PASS on the same terms — a `gen_ai.prompt.{i}.role` of `user` carrying the prompt. `embeddings` spans are exempt from this gate — model + usage only, never messages. Content present only on a wrapper span = FAIL; zero inference spans = FAIL, not a vacuous PASS | the probe prompt text, quoted from inside the input array |
| G3 | MUST | Cost enrichment | `gen_ai.prompt_price` / `gen_ai.response_price` present and non-zero on inference spans whose model is priced on the tenant (`cx ai-center model-pricing get`); zero price with zero tokens is a span source defect (FAIL G1), zero price with non-zero tokens is an unpriced model (G11) ; zero price on a model the tenant priced before is FAIL G1 (usage), not N/A | the price values on one inference span |
| G4 | MUST | Catalog registration | the application appears in `cx ai-center applications list` | the application ID and the "View in Coralogix" URL the command prints |
| G5 | SHOULD | Request context | `gen_ai.conversation.id` and a user identity on the GenAI spans, for every identity the app actually has | the ids observed, or the statement that the app has no such identity |
| G6 | SHOULD | Within-trace consistency | one conversation id, one user across ALL span types of a trace — workflow, agent, inference, tool (a trace may legitimately call more than one provider) | the per-span values of one full trace |
| G7 | SHOULD | Interaction tree | GenAI spans nest under the request/handler root; tool spans wrap their backend calls; `invoke_agent` spans present when the app has agents ; when the app spawned subagents, each appears as a nested `invoke_agent` with its own `gen_ai.agent.name` — a run with Agent/Task tool calls and no nested `invoke_agent` FAILS unless the user excluded subagents in their answer | the span tree of one `$d.traceID` |
| G8 | SHOULD | Errors visible | a failed call carries `otel.status_code == ERROR` plus `otel.status_description` ; a failed agent run carries ERROR on its `invoke_agent` span, not only on the failing tool span | the failed span with its status |
| G9 | SHOULD — always evaluated | Sensitive data | PII/confidential data masked or excluded from the captured content ; never N/A: content capture exists whenever messages are captured — record what was inspected and the masking decision, even when the decision is 'none, accepted by the user' | what was inspected, what is masked |
| G10 | IF-APPLICABLE | Reference diff | against a known-good trace (production, the app's prior instrumentation, another instrumented service on the tenant): span types, hierarchy, and per-type attributes match; unexplained GenAI losses are gaps, not noise | the two traces side by side |
| G11 | IF-APPLICABLE | Model pricing | run `cx ai-center model-pricing get` and query the tenant for earlier priced spans of the same model (`filter tags['gen_ai.request.model']:string == '<model>' && tags['gen_ai.prompt_price']:number > 0 \| limit 1`, 7 days); run `cx ai-center model-pricing get`; an unknown or self-hosted model has an override applied with `cx ai-center model-pricing set`; without it cost stays 0 ; N/A only when tokens are non-zero, price is non-zero and no unknown model appears — a model the tenant priced earlier is not 'fictional' | `cx ai-center model-pricing get` output |
| G12 | IF-APPLICABLE | No double counting | with more than one span source on a call path, each call yields exactly one inference span and one set of token counts | span count per call on one trace |

### 5. Verdict
**Every MUST passes → done.** SHOULD failures become should-fix findings unless the user scoped them in — then they block. The final message is the report below.

**Report — written for the user (one screen; gate ids only in parentheses; the 12-gate table is your checklist, not the report — attach it as an appendix only if the user asks for the gates):**

1. **Verdict** — one line: what flows, what is broken, in product terms ("prod exports no prompts", "36% of calls have no cost").
2. **Findings** — one table, severity-ordered: Finding · Scope (count / apps / models) · Impact in AI Center · Owner (app team / Coralogix / library upstream) · Query. Use blocking / should fix / nice to have, never MUST/SHOULD. Each finding appears once — not again in a reconciliation or gap list.
3. **What was pulled / what ran** — the inventory table (app × subsystem × operation, counts, distinct traces) for verify-only; for a full run also: entry point + label, probe marker, window, environments with the pasted env-file lines, files changed, tests.
4. **Already fine** — one line listing what passed so the user does not re-check it.
5. **Could not check** — one line (no repo, no browser, no key…), plus anything fixed in code but not re-run live.
6. **Where to look** — the "View in Coralogix" URL and application id(s), with the AI Center views to open.
7. **Next** — one line: the single most valuable next step, and the offer of a re-assert script or runbook (ask before adding files).

Sections that do not apply to the mode (no code, no probe, no environments) are omitted, not filled with N/A. Internal checks the report does not print: the 12 gates with evidence, the span-source ladder table, the docs fetched, the reconciliation per route, the hygiene checklist, the suite-does-not-export query result — keep them in your notes and produce them on request ("show the gates").

**Any MUST fails → loop.** Emit the gap list (gate, evidence, suspected cause) → the Instrument section to fix → re-run per the who-runs decision in the Run section → re-verify, until every MUST passes. A gap caused by an upstream-library defect that cannot be fixed here becomes an issue-ready follow-up, and its gate stays FAIL unless the user accepts it as a known exception. In verify-only mode there is no loop: the findings table with owners is the deliverable.

## Stacks — instrumentor lookup
Rung 1 of the research ladder in the Instrument section; versions verified 2026-09-15 — confirm the current version and its content switch live before use. Semconv column: **New** = `gen_ai.provider.name` + `gen_ai.input.messages`/`gen_ai.output.messages` (string JSON); **Legacy** = `gen_ai.system` + `gen_ai.prompt.{i}.*`/`gen_ai.completion.{i}.*`; **Vendor** = non-`gen_ai.*` attributes, not detected by AI Center.

| Stack | Lang | Instrumentor (version) | Semconv | Content switch | Opt-in | Notes |
|---|---|---|---|---|---|---|
| Anthropic | Py | `opentelemetry-instrumentation-anthropic` (0.62.3, OpenLLMetry) | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Coralogix-verified; new-shape migration incomplete, traceloop/openllmetry#3515 (M) |
| AWS Strands | Py | `strands-agents` native | — | — | — | Coralogix-verified |
| Azure OpenAI | Py | `opentelemetry-instrumentation-openai-v2` (2.4b0, OTel contrib) | Legacy default / New opt-in | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Off by default | Coralogix-verified; New needs `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`; deprecated upstream → `opentelemetry-instrumentation-genai-openai` (H) |
| AWS Bedrock | Py | `opentelemetry-instrumentation-bedrock` (≥0.60.0; 0.62.3 current, OpenLLMetry) | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Coralogix-verified (M) |
| CrewAI | Py | `opentelemetry-instrumentation-crewai` (0.62.3, OpenLLMetry) | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Coralogix-verified (M) |
| Google ADK | Py | `opentelemetry-instrumentation-google-genai` (1.1b1, OTel contrib) | New | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Off by default | Coralogix-verified; covered via google-genai SDK path (M) |
| Google GenAI (Gemini) | Py | `opentelemetry-instrumentation-google-genai` (1.1b1, OTel contrib) | New | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Off by default | Coralogix-verified; values unconfirmed — verify at use; provider `gcp.vertex_ai`/`gcp.gemini` (M) |
| LangChain | Py | `opentelemetry-instrumentation-langchain` (0.62.3, Traceloop pkg) | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Coralogix-verified; OTel-style name but a Traceloop package (M) |
| LiteLLM | Py | `litellm` (≥1.86.0) native, `callbacks: ["otel"]` | New (opt-in var mandatory) | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Off by default | Coralogix-verified; setup guide `integrations/ai-observability/ai-apps/litellm.md`; see Gateways row. Known issue: on streamed calls only, LiteLLM's `otel` callback drops `gen_ai.output.messages` (the response) from the span while the prompt is present — a known upstream gap owned by LiteLLM; check the installed version's changelog for a fix, do not hand-roll spans or add a second span source on the same call path |
| LlamaIndex | Py | `opentelemetry-instrumentation-llamaindex` (0.62.3, OpenLLMetry) | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Coralogix-verified (M) |
| Ollama | Py | OpenLLMetry | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Coralogix-verified; version unconfirmed — verify at use (M) |
| OpenAI (completions) | Py | `opentelemetry-instrumentation-openai-v2` (2.4b0, OTel contrib) | Legacy default / New opt-in | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Off by default | Coralogix-verified; same package as Azure OpenAI row (H) |
| OpenAI Agents | Py | `opentelemetry-instrumentation-openai-agents-v2` (OTel contrib) | New | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Off by default | Coralogix-verified |
| Vertex AI | Py | `opentelemetry-instrumentation-google-genai` (via google-genai SDK) — or Traceloop `-vertexai` pkg (legacy) | New or Legacy | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` / `TRACELOOP_TRACE_CONTENT` | Off / On by default | Coralogix-verified; which package actually runs is unconfirmed — verify at use |
| Mastra | Node | `@mastra/core` (1.67.0) native OTel bridge | New (v1.38) | unverified | — | Coralogix-verified (M) |
| OpenAI | Node | `@opentelemetry/instrumentation-openai` (0.20.0, OTel-JS-contrib) | unconfirmed | unconfirmed | unconfirmed | Not Coralogix-verified — verify at use (M) |
| Anthropic / OpenAI / LangChain | Node | `@traceloop/instrumentation-*` (0.27.0) + `@traceloop/node-server-sdk` | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Not Coralogix-verified (M) |
| Google Generative AI | Node | `@traceloop/instrumentation-google-generativeai` (0.27.0) | Legacy | `TRACELOOP_TRACE_CONTENT` | On by default | Not Coralogix-verified (L) |
| Vercel AI SDK ≤v6 | Node | `ai` `experimental_telemetry` | Vendor (`ai.*`) | `recordInputs`/`recordOutputs` (per call) | Off by default | Not Coralogix-verified; AI Center does not detect these spans (H) |
| Vercel AI SDK v7+ | Node | `@ai-sdk/otel` (1.0.101) `OpenTelemetry` mode | New (`LegacyOpenTelemetry` mode = vendor `ai.*`) | unverified | unverified | Not Coralogix-verified (M) |
| Vertex AI (enterprise SDK) | Node | none found | — | — | — | Gap — use Gateways row or manual spans (M) |
| Spring AI | Java | `spring-ai-model` (1.0.0) native Micrometer→OTel | New (v1.37) | `ObservationRegistry` config | code config | Not Coralogix-verified; no OpenLLMetry for Java exists (M/H) |
| Other Java | Java | manual spans | New | — | — | Per `code-examples.md` Java example |
| Anthropic (anthropic-sdk-go) | Go | `opentelemetry-go-compile-instrumentation` (experimental, compile-time) | New + Legacy dual-emit | — | — | Not Coralogix-verified; no streaming support (M) |
| go-openai | Go | none found | — | — | — | Gap — manual spans per `code-examples.md` Go example (M) |
| Microsoft.Extensions.AI | .NET | `Microsoft.Extensions.AI` (10.10.0) `OpenTelemetryChatClient` native | New (v1.37) | `EnableSensitiveData=true` or `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Off by default | Not Coralogix-verified (H) |
| LiteLLM proxy/SDK | any | native `otel` callback | New (opt-in var mandatory) | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=SPAN_ONLY` | Off by default | Coralogix-verified; `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` mandatory; one span source for any client via `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL`, incl. CLIs nothing else instruments. Known issue: on streamed calls only, LiteLLM's `otel` callback drops `gen_ai.output.messages` (the response) from the span while the prompt is present — a known upstream gap owned by LiteLLM; check the installed version's changelog for a fix, do not hand-roll spans or add a second span source on the same call path |
| Claude Code | any | built-in telemetry | Vendor (`claude_code.*`) | `OTEL_LOG_USER_PROMPTS`/`OTEL_LOG_TOOL_CONTENT`/`OTEL_LOG_RAW_API_BODIES`, gated by `CLAUDE_CODE_ENABLE_TELEMETRY=1` + `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` | Off by default | Not `gen_ai.*` — feeds Code Agents screen, not Application Catalog (H) |
| Claude Agent SDK | Py/TS | `opentelemetry-instrumentation-genai-claude-agent-sdk` (open-telemetry/opentelemetry-python-genai, verify release state) or community `opentelemetry-claude-agent-sdk` / `otel-instrumentation-claude-agent-sdk` (wrap `receive_response()` only — check the call path uses it) — else the Agent-SDK pattern in the Instrument section or the gateway | New | `capture_content=True` | Off by default | Not Coralogix-verified; `invoke_agent`/`execute_tool` spans; some Claude Code versions ignored `ANTHROPIC_BASE_URL` when spawned by Agent SDK — verify on current version (M); SDK process routed to LiteLLM via `ANTHROPIC_BASE_URL` → gateway is a rung-4 candidate |

### Notes
- Vercel AI SDK ≤v6 spans are `ai.*` vendor shape — AI Center does not detect them; propose upgrading to v7 `@ai-sdk/otel` for `gen_ai.*`, with the user's approval.
- Claude Code's built-in telemetry is separate from the Claude Agent SDK `gen_ai.*` path — see the last two table rows.
- Traceloop/OpenLLMetry packages (Python and Node) are legacy-shape only; that shape PASSes AI Center's gates (see the Verify section), but prefer New where a New-shape instrumentor exists for the same call.
- `opentelemetry-instrumentation-openai-v2` is deprecated upstream in favor of `opentelemetry-instrumentation-genai-openai` — re-check on next verify.
- LangChain over Vertex: set `gen_ai.provider.name` to `gcp.vertex_ai`, not `openai`/`anthropic`, even though the instrumentor is the LangChain package.
- A gateway should be the single span source per call path — don't stack a client-side instrumentor and the gateway's own telemetry on the same call (see the Instrument section).
- All `gen_ai.*` attributes are "Development" stability in the OTel GenAI semconv — expect changes between library versions; pin and re-verify on upgrade.
- Provider well-known values: `openai`, `anthropic`, `aws.bedrock`, `azure.ai.openai`, `azure.ai.inference`, `gcp.vertex_ai`, `gcp.gemini`, `gcp.gen_ai`, `mistral_ai`, `cohere`, `deepseek`, `groq`, `perplexity`, `x_ai`, `ibm.watsonx.ai`.

## Pitfalls
Symptom-driven debugging for a GenAI integration that is wired but not rendering correctly.

| Symptom | Cause | Fix |
|---|---|---|
| Spans visible in the Spans Explorer, nothing in AI Center | Traces stay in the frequent tier | Tell the user: traces must reach the archive tier; they change routing in their archive/TCO settings |
| The application never appears in the catalog | Spans lack `gen_ai.provider.name` (legacy `gen_ai.system`) and `gen_ai.operation.name`, so they are not detected as GenAI | Set both; check the provider value is a semconv well-known value, not a vendor string |
| No spans at all | The instrumentor ran before the provider library was imported and had nothing to patch | Call the instrumentor after importing the provider library, or in the library's documented order |
| No spans, or the exporter points at the wrong endpoint | OTel was initialized before the environment file was loaded | Load environment variables before initializing the SDK and the instrumentor |
| The last spans of every run are missing | A batch span processor buffered them and the process exited | Call `force_flush()` / `shutdown()` on exit; in services wire provider shutdown into teardown, ordered last |
| Random spans missing, tokens and cost under-counted | Head or tail sampling drops GenAI spans | Exclude GenAI spans from the sampling policy, or sample whole traces only |
| Prompts and responses empty in the UI | Content capture is off, or the installed parser rejected the value and degraded to no content with only a log warning | Set the library's own switch (`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` or `TRACELOOP_TRACE_CONTENT`) to a value that version's parser accepts, then confirm on a real span |
| Message JSON truncated mid-payload and unparseable | An attribute value length limit is set | Set `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` and `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT` to a higher value, in every environment's config, not just a local shell |
| Large prompts drop while small ones arrive | The OTLP gRPC receiver's default 4 MiB message limit rejects the batch | Raise `max_recv_msg_size_mib` on the receiver and lower the batch processor's `send_batch_max_size` |
| Messages present but unreadable in the conversation view | A language-native `repr` / `toString` blob was stuffed into a content field instead of structured parts | Serialize string-encoded JSON with typed parts (`text`, `tool_call`, `tool_call_response`) |
| A message renders with no author | The message object is missing `role` | Include `role` on every entry of `gen_ai.input.messages` and `gen_ai.output.messages` |
| Message attributes arrive as an object, not text | The attribute was set to a native object rather than string-encoded JSON | Serialize to a JSON string before setting the attribute |
| Every application lands under one name | The collector exporter uses only its static application and subsystem names | Set `application_name_attributes` / `subsystem_name_attributes` on the exporter and emit `cx.application.name` / `cx.subsystem.name` |
| One provider on every call while the model varies | An instrumentor behind a gateway or proxy hard-codes a static provider | Override `gen_ai.provider.name` per call from the model actually routed |
| Tokens and cost roughly doubled | Two instrumentors cover the same call path | Scope span sources so each call path has exactly one, per route, key, or service |
| Cost shows 0 with tokens present | The model is unknown to Coralogix pricing (self-hosted or newly released) | Register it with `cx ai-center model-pricing set` (JSON file, `--yes`) |
| No agent graph despite agent spans | Agent executions are typed as tool or custom spans | Type each agent execution as `invoke_agent` with `gen_ai.agent.name`; the graph renders only from those |
| The agent and tool hierarchy disappears after disabling vendor telemetry | The SDK's "disable tracing" switch also deletes span generation, not just the vendor upload | Clear the vendor's exporter or API key instead, and keep a test fixture that clears the switch |
| Errors show 0 while calls are failing | Failures are caught and logged without touching span status | Set span status `ERROR` and record the exception; the UI counts only `otel.status_code == ERROR` |
| Model or token fields unrecognized | Non-registry attribute names (`gen_ai.model`, invented vendor keys) | Use the exact semconv names from the registry and the Coralogix inventory |
| Flat traces, no step visible | Every span is emitted at the root with no parent context | Nest spans: GenAI spans under the request-handler root, tool backend calls inside tool spans |
| The verified trace does not match the code under test | A stale process, another checkout, or a dev shortcut produced it | Filter on the probe marker and re-run through the real entry point before auditing |
| Prompts contain personal or confidential data | Content capture exports the raw payload | Mask or exclude sensitive fields before the span is created, and keep capture off where it is not allowed |
| Messages captured, conversation view empty | Content on `invoke_agent`/wrapper span; UI parses those as metadata-only | Put messages on the `chat` span of each model call |
| One provider for every call behind a gateway, models vary | Provider set from the API shape or a constant | Derive per call from the routed/response model |
| One span per agent turn, no latency or tool detail | Turn-level summary span | One `chat` span per model response, `execute_tool` children |
| Traces flow locally, nothing after restart/deploy | Switches passed inline on a command line | Wire ON in the environment's config file, cite file:line |
| Hundreds of `chat` spans with zero tokens and zero price | One span per streamed assistant event / content block | Aggregate by message id; end the span on the terminal event; usage from it or the turn result |
| Report cites a code default as the environment switch | `True` default copied from another service; inline value on the command line | Default OFF in code; set ON in the env file the app loads; cite that line |
| Session ended while the probe was running | Probe backgrounded and turn ended "until notified" | Wait in-turn with a bounded loop on the status endpoint or log |
| Gate marked N/A for a construct that exists | N/A used to close an uninvestigated gate | N/A only when the app has no such construct; otherwise PASS/FAIL with evidence |
| Provider says `anthropic` for calls a gateway sent to Bedrock or OpenAI | Provider taken from the SDK/CLI client field or the API shape | Map the response model through the gateway's route table |
| The verified trace used a model the app never uses by default | Input changed to make a gate pass | Run the default configuration; report the default path's failure as the finding |
| Repeated bare `invoke_agent` roots, no status, no children | Failed attempts not marked ERROR and not inventoried | Set ERROR on the agent span on failure; list every attempt in the report |
| Repeated bare `invoke_agent` roots with an all-zero conversation id | The test suite exported: `Settings` read `.env` and inherited `ENABLE_*=true` | Force export off in the test env; prove by tenant query after the run |
| Reconciliation says 9 spans, the tenant holds 17 | Counts read from a `limit N` listing | Count with `groupby … aggregate count()` over the whole window |
| Agent/Task tool calls but no nested `invoke_agent` | Subagents "scoped out" unilaterally | Nested `invoke_agent` per subagent; exclusion is the user's call |
| Chat spans carry zero usage on one model route only | Usage read from `AssistantMessage`, empty in streaming mode | Read usage from `message_start` + `message_delta` of the same message id |
| Assess asks the user for an API key, or silently guesses a profile | Query access is profile-based, not key-based | Run `cx profiles list`; one profile → use it, several → ask which one, none → run the cx onboarding together with the user |
| Wait loop leaves the agent's control, turn ends | Bash call exceeded its `timeout` and was backgrounded | `timeout` = loop bound (≤10 min), chain calls, never end the turn |
| Zero usage blamed on the model or gateway | Terminal stream event carried zeros; no fallback | Fall back to the SDK's per-turn usage totals; check the model's earlier prices on the tenant |
| Own process restarted with `pkill -f` on a shared machine | Pattern kill instead of the recorded PID | Record `APP_PID=$!` at start, `kill "$APP_PID"` at stop |
| Verification of existing spans takes 10–15 minutes | Per-attribute query loops, relative windows re-run, stability re-queries, whole-span dumps | Verify-only mode: pin the window, one coverage groupby, ~12 queries |
| Report unreadable to the user (gate ids, tiers, empty sections) | The internal checklist printed as the report | Verdict + findings table with owners; gates as an appendix on request |
| Responses missing on streamed calls behind LiteLLM, prompts present | Known upstream gap in LiteLLM's `otel` callback, scoped to streamed calls | Check the installed version's changelog for a fix; until then record it as a known upstream gap owned by LiteLLM, do not hand-roll spans or add a second span source on the same call path |
| Five minutes lost waiting for the first span | Arrival checked on the archive tier | Check arrival on `--tier frequent`; archive is for the gates only |
| Users puzzled by the questions | Questionnaire rendered as a table, jargon ("emitter", "upstream-bound"), run question asked first | Ask with the agent's structured question tool (or a short numbered list), four plain questions, who-runs asked at the start of Run |

## Limitations
- No repo access → verify-only mode; nothing can be instrumented or wired.
- No working cx profile → user-run verification: the user runs the gate queries and pastes results; every gate is labelled user-reported.
- No browser: rendering in the AI Center UI is inferred from the parser rules in Phase 4 §2, never observed.
- Shared gateways, containers and databases are the user's to restart or migrate; the skill stops and asks rather than changing them.
- The Code Agents screen and whole-service APM are other skills' territory.

## cx CLI
The `cx` CLI queries Coralogix directly: spans via DataPrime, plus official docs and AI Center config. `cx --help`, `cx spans --help`, `cx docs --help` list the commands and their options.

### Install and first profile
1. Check what's there: `cx --version` and `cx profiles list`. Installed with a profile → done (ask which profile if several).
2. Otherwise ask once (one structured question): the Coralogix URL they open in the browser (e.g. `https://myteam.app.eu2.coralogix.com`), unless already given; and the install method — Homebrew `brew install coralogix/tap/cx` (recommended on macOS) or the install script `curl -fsSL https://get.coralogix.dev/cli | sh` (any platform).
3. Install, then confirm with `cx --version`.
4. `cx init --oauth --url <url> --no-skills` — OAuth opens a browser login, no API key collected; `--no-skills` because this skill is already loaded (other cx skills install later with `cx skills install`); shell completions install later with `cx completions install <shell>`. `cx init --help` lists other options.
5. Verify: `cx profiles list` shows the new default profile; `cx spans "limit 1"` succeeds.
6. Human reference: https://github.com/coralogix/cx-cli/blob/master/docs/agent-setup.md

Profiles live in `~/.cx`/`~/.config/cx`; use one with `cx spans "..." --profile <p>` or by leaving the default profile set.

### Querying GenAI spans
`cx spans` takes a DataPrime query; `source spans` is prepended automatically.

| Need | Path / rule |
|---|---|
| trace, span, parent | `$d.traceID`, `$d.spanID`, `$d.parentId` — derived fields: valid in `filter`/`select`/`groupby`, absent from a raw record dump, so never grep a dump to find them |
| span name, app, subsystem | `$l.operationName`, `$l.applicationName`, `$l.subsystemName` (`name` alone fails) |
| time, duration | `$m.timestamp`, `$m.duration` (µs) |
| attributes | `tags['gen_ai.request.model']:string`, `tags['gen_ai.usage.output_tokens']:number` — always cast |
| aggregates | `count()`, `distinct_count(x)`, `count_if(cond)`, `sum(x:number)`, `min`/`max`; sort with `orderby x desc` (`sort` fails) |
| row cap | `--limit` (default 200) caps the result even when the query says `limit 10000`; pass `--limit` ≥ the in-query limit |
| output envelope | `-o json` rows are `{metadata, labels, userData}` with selected/aggregated fields inside `userData` (aggregates come back flat); the default text mode differs — parse one format only |
| payload size | never select a whole GenAI span — message and tool payloads exceed the tool output cap and truncate silently; `select` the fields you need |
| errors | a 429 or compile error prints on stderr and the stdout is empty; treat empty output as an error, not as zero |
| window | absolute `--start`/`--end` pinned once from `date -u`; `now-Xh` drifts between calls |

```bash
# Recent GenAI spans (archive tier — the one AI Center reads)
cx spans "filter tags['gen_ai.provider.name']:string != null
  | select $d.traceID, $l.operationName, tags['gen_ai.request.model']:string,
           tags['gen_ai.usage.input_tokens']:string, tags['gen_ai.usage.output_tokens']:string
  | limit 10" --tier archive --start <S> --end <E> -o json

# One trace's tree
TRACE_ID=0123456789abcdef0123456789abcdef   # one trace id from the shape sample
cx spans "filter $d.traceID == '$TRACE_ID' | select $d.spanID, $d.parentId, $l.operationName, tags['gen_ai.operation.name']:string | limit 200" --tier archive --start <S> --end <E> -o json
```

### AI Center commands
```bash
# Is the app registered in the AI Center catalog? Prints a "View in Coralogix" URL
# plus a table of ID | Application | Subsystem | Guarded
cx ai-center applications list
APPLICATION_ID=01234567-89ab-cdef-0123-456789abcdef   # the ID column from the list output
cx ai-center applications get $APPLICATION_ID
```

`cx ai-center applications list` prints `View in Coralogix: <url>` — copy it into the report.

```bash
# Cost overrides for models AI Center doesn't price automatically
# (unknown or self-hosted models otherwise show $0 cost)
cx ai-center model-pricing get
cx ai-center model-pricing set --from-file pricing.json --yes
```

## Coralogix documentation
Prefer `cx docs` over a raw web fetch — it's faster and stays in sync with the product.

```bash
cx docs search "AI Center opentelemetry"
cx docs fetch "user-guides/ai/otel-integration.md"
```

Key pages:

- `user-guides/ai/otel-integration.md` — main integration guide
- `user-guides/ai/otel-integration/span-attributes.md` — `gen_ai.*` attribute inventory AI Center consumes
- `user-guides/ai/otel-integration/providers.md` — compatibility matrix per provider/language
- `user-guides/ai/otel-integration/code-examples.md` — copy-paste scripts (Python, Java, .NET, Go)
- `user-guides/ai/getting_started.md` — troubleshooting section
- `user-guides/account-management/api-keys/api-keys.md` — key types and creation
- `user-guides/data-flow/s3-archive/connect-s3-archive.md` — archive connection
- `developer-portal/apis/data-ingestion/opentelemetry-custom-traces.md` — OTLP/HTTP JSON curl example

Fallback: fetch `https://coralogix.com/docs/<path>.md` directly when `cx docs` doesn't have the page.

## References
- **OpenTelemetry GenAI semantic conventions** — https://github.com/open-telemetry/semantic-conventions (registry: `docs/registry/attributes/gen-ai.md`); incubating repo https://github.com/open-telemetry/semantic-conventions-genai
- **Coralogix AI Center OTel integration** — `cx docs fetch "user-guides/ai/otel-integration.md"` and the key pages listed above; human docs: https://coralogix.com/docs/user-guides/ai/otel-integration/
