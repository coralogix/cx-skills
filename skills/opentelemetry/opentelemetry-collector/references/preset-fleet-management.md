# Fleet Management: overlap notes

Fleet Management (OpAMP supervisor + remote config via the Coralogix UI) intersects with the OTel Collector configuration in a few places. Only those overlap points are covered here — deep OpAMP protocol internals, supervisor-binary flags, remote-config-rendering precedence, the Coralogix Distribution of OpenTelemetry (CDOT), and the Fleet Manager UI itself are out of scope for this skill.

## The three things that matter here

### 1. Supervisor OpAMP endpoint **does** use the `ingress.` prefix — unlike the coralogix exporter

The single most common confusion: the coralogix exporter's `domain:` field is a bare hostname (`eu2.coralogix.com`), but the supervisor's OpAMP endpoint is a **full URL with the ingress prefix**:

```yaml
# coralogix EXPORTER — bare hostname
exporters:
  coralogix:
    domain: "eu2.coralogix.com"

# SUPERVISOR OpAMP endpoint — full URL WITH ingress prefix
presets:
  fleetManagement:
    enabled: true
    supervisor:
      enabled: true
      server:
        endpoint: "https://ingress.eu2.coralogix.com/opamp/v1"
```

Both are right in their own place. They look inconsistent because they route through different Coralogix ingest paths. If a user hardcodes `https://ingress.<domain>` as their coralogix exporter `domain:` in order to make the supervisor work, they have mixed the two up — separate them.

The chart handles this automatically when `.Values.global.domain` is set. Direct-to-helm users editing a raw config by hand are the ones who get caught.

### 2. `presets.fleetManagement.supervisor.enabled: true` overrides values.yaml at runtime

When the supervisor is enabled, the collector's runtime config comes from the **Fleet Manager UI**, not from the Helm values.yaml applied at deploy time. A user pushing changes via `helm upgrade` (especially from ArgoCD) and seeing "why isn't my change taking effect" has hit this.

The precedence is:

```
Fleet Manager UI config  >  values.yaml at helm upgrade time
```

Values.yaml still matters for: chart version, pod resource requests, service account, ingress endpoints, *presets* themselves. It does **not** matter for: receiver/processor/exporter configuration, pipeline wiring, filter/transform OTTL.

Diagnostic: if a user says "I redeployed with new values but the config didn't change," check whether `supervisor.enabled: true`. If so, refer to the Fleet Manager UI.

Opt-out: set `supervisor.enabled: false` (chart values) and manage config via helm as usual. Users using pure GitOps (ArgoCD with declarative intent) typically prefer this.

### 3. Windows: image version determines whether in-process `opamp` works

Both Fleet Management shapes are available on Windows with **modern** collector builds — verified against the rendered `otel-windows-standalone` chart (collector v0.130.7), which ships `extensions: [opamp]` by default.

- **In-process extension** works when the collector image is ≥ v0.130. Standalone chart defaults here.
- **Supervisor wrapper** (`-Supervisor` on the installer) works regardless of collector version — it runs a separate `opampsupervisor` service.

The trap — **older image pins**:
- `otel-integration`'s `opentelemetry-agent-windows` sub-preset historically defaults to `coralogixrepo/opentelemetry-collector-contrib-windows:0.92.0`, which predates OpAMP on Windows. A user enabling `extensions: [opamp]` there will see the collector refuse to start.
- `otel-ecs-ec2-windows` similarly pins an older image in its CloudFormation template.

Practical implication: a Windows user whose `extensions: [opamp]` fails is either on an old image (fix: bump, or use the supervisor wrapper) or on the K8s Windows sub-preset (same fix). On modern standalone, it just works.

## Signals that fleet-management scope is intruding

When any of these appear in a user's issue, refer to the supervisor skill (or this file's section 2):

- "Config keeps reverting to something I didn't set."
- "`helm upgrade` says applied, but the pipeline behavior is unchanged."
- "We have `opamp` extension enabled but the collector won't start." (Likely Windows, see section 3.)
- "Supervisor endpoint is returning 404."
- "Fleet Manager shows my cluster but no agents."
- "eBPF profiler doesn't connect to Fleet Manager."
- "Changing `X-Coralogix-Distribution` header in the exporter config had no effect." (It's set by the supervisor; edit in Fleet Manager.)

## When this skill is the wrong place to look

Questions that need the OpAMP supervisor / Fleet Manager internals rather than the collector-config overlap covered here:

- Deploying with Fleet Management end-to-end from scratch.
- Remote-config precedence details beyond "UI beats values.yaml at runtime" (section 2 above).
- `otel-supervised-cdot` or `otel-supervised-ebpf-profiler` image specifics.
- Debugging the OpAMP supervisor binary itself (crash loops, auth handshake failures).

Those sit with the Fleet Manager / CDOT documentation, not with this OTel Collector skill.

## Key Facts

- **Supervisor OpAMP endpoint is `https://ingress.{domain}/opamp/v1`.** The coralogix exporter `domain:` is a bare hostname. Two different fields, two different shapes — don't mix them.
- **With `supervisor.enabled: true`, Fleet Manager UI beats values.yaml at runtime.** ArgoCD users usually want `supervisor.enabled: false`.
- **Windows supports both in-process `opamp` and the supervisor wrapper — on modern builds.** The `otel-windows-standalone` chart (collector ≥ v0.130) renders `extensions: [opamp]` by default. Older pinned images (notably `contrib-windows:0.92.0` used in the K8s Windows sub-preset and `otel-ecs-ec2-windows`) predate it — there, use the `-Supervisor` wrapper or bump the image.
- **Signals of Fleet Management scope** = config reverts, `helm upgrade` has no effect, `X-Coralogix-Distribution` changes ignored.
- **Deep OpAMP / supervisor / CDOT coverage is out of scope.** Only the overlap with collector configuration (endpoint shape, values-vs-UI precedence, Windows image pitfall) lives here.
