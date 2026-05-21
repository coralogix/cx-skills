# Collector component stability

Collector components do not all have the same production readiness. The upstream
Collector status is mixed, and each receiver, processor, exporter, connector, and
extension documents its own stability per signal in its README. Treat stability as a
deployment requirement, not a doc footnote.

## Stability levels

| Level | How to answer |
|---|---|
| Development | Do not recommend for production. Use only for exploration or repros. |
| Alpha | Limited, non-critical workloads only. Configuration can change with little notice. |
| Beta | Broader usage is reasonable, but breaking changes can still happen. Read release notes before upgrades. |
| Stable | Production default. Backward compatibility is expected except for exceptional cases such as security fixes. |
| Deprecated | Avoid new deployments. Recommend migration and explain removal risk. |
| Unmaintained | Avoid unless there is no alternative and the user accepts ownership/risk. |

For components that handle multiple signals, check the stability for the exact signal
the user is using. A component can be stable for traces and less mature for logs,
metrics, or profiles.

## Answer pattern

When the user asks whether a component is safe to deploy:

1. Ask or infer the collector version, distribution, component name, signal, and workload criticality.
2. Tell them to check the component README stability table for that exact version/signal.
3. If the component is alpha, say it is not the default recommendation for business-critical production traffic.
4. If they still need it, require a pinned collector version, staging test with representative traffic, rollback plan, and release-note review before upgrades.
5. Offer the nearest stable path when one exists, even if it is less feature-rich.

## What validation does not prove

`otelcol validate` and a successful startup prove that YAML parses and components can be
constructed. They do not prove production stability, backward compatibility, safe
upgrade behavior, or acceptable operational risk. Do not call a production plan safe
only because the config validates.

## Common Coralogix-facing examples

- A customer wants a newly released contrib processor for production URL or span-name
  sanitization. Check the processor README stability and qualify alpha/beta risk before
  recommending it broadly.
- A collector image bump pulls in a component with changed config or startup validation.
  Read the component release notes and chart compatibility before telling the user to
  override only `image.tag`.
- A user points at an OpenTelemetry specification page marked stable, but the language
  SDK package or Collector component they need is alpha. The implementation maturity is
  what matters for the recommendation.
