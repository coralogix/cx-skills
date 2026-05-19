# OpenTelemetry Collector: Connectors Configuration

This reference covers the `spanmetrics` and `tail_sampling` components. Proper placement in the collector topology is required for APM to calculate correct error rates and latencies.

## Topology Rules

- **`spanmetrics` connector belongs on the agent.** Span metrics must be generated from **100% of spans** before any sampling decision. If sampling precedes spanmetrics, APM dashboards undercount error rates and percentiles.
- **`tail_sampling` processor belongs on the gateway.** Tail sampling requires the full trace in memory to evaluate a policy. Daemonset agents only see their node's spans, so a tail sampler on the agent drops traces partially.
- **`transactions` processor must run before `spanmetrics`.** `transactions` enriches spans with `cgx.transaction.*` tags. `spanmetrics` must consume those tags to emit per-transaction metric dimensions.
- **All instrumented services must route spans through the agent daemonset.** If an application sends OTLP directly to the gateway or cluster-collector (bypassing the agent), the agent's `spanmetrics` connector never sees those spans. No span metrics are generated, APM Service Catalog stays empty, and `calls_total`/`duration_ms_bucket` metrics are absent — even though traces appear in Explore. Verify the OTLP exporter endpoint in each service points to the agent (typically `http://<node-ip>:4317`) and not directly to the gateway.

## Helm Span Metrics DB Label Transforms

If `db_calls_total` has `db_namespace` but normal Span Metrics `calls_total`
has a blank `db_namespace`, check where the Helm DB compatibility transform is
configured.

In `otel-integration` values, DB label compatibility statements that need to
affect normal Span Metrics must live under top-level
`spanMetrics.transformStatements`. Those statements run on spans before the
`spanmetrics` connector consumes them, so both `calls_total` and
`db_calls_total` see the same normalized span attributes.

Do not put this bridge only under
`spanMetrics.dbMetrics.transformStatements`. That DB-metrics-only placement can
make `db_calls_total` look correct while `calls_total` still has blank
`db_namespace` for the same database spans. Treat that as a values
misconfiguration, not as a chart-default bug.

The pre-spanmetrics bridge should populate `db.namespace` from the first
available source: `db.name`, then endpoint attributes such as `server.address`,
`network.peer.name`, or `net.peer.name`, and finally `db.system`. Use the OTTL
skill when the user needs the exact transform statement syntax.

## Agent Configuration (spanmetrics)

```yaml
# AGENT (daemonset)
connectors:
  spanmetrics:
    dimensions:
      - name: http.method
      - name: http.status_code
      - name: cgx.transaction
      - name: cgx.transaction.root
      - name: db.system

processors:
  transactions:                                    # runs BEFORE spanmetrics
    # ... populate cgx.transaction.* tags on spans

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, k8sattributes, resourcedetection, transactions, batch]
      exporters: [spanmetrics, loadbalancing]     # spanmetrics connector fans out to metrics pipeline
    metrics/spanmetrics:
      receivers: [spanmetrics]                    # connector-consumed pipeline
      processors: [memory_limiter, batch]
      exporters: [coralogix]                      # spanMetrics go direct to Coralogix
```

## Gateway Configuration (tail_sampling)

To ensure the gateway evaluates complete traces, the agent MUST route spans via the `loadbalancing` exporter configured with `routing_key: traceID`.

```yaml
# GATEWAY (deployment)
processors:
  tail_sampling:
    decision_wait: 30s
    num_traces: 50000
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: default
        type: probabilistic
        probabilistic:
          sampling_percentage: 10

service:
  pipelines:
    traces:
      receivers: [otlp]                           # fed by loadbalancing on agents
      processors: [memory_limiter, k8sattributes, tail_sampling, batch]
      exporters: [coralogix]
```
