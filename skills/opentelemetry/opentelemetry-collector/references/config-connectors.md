# OpenTelemetry Collector: Connectors Configuration

This reference covers the `spanmetrics` and `tail_sampling` components. Proper placement in the collector topology is required for APM to calculate correct error rates and latencies.

## Topology Rules

- **`spanmetrics` connector belongs on the agent.** Span metrics must be generated from **100% of spans** before any sampling decision. If sampling precedes spanmetrics, APM dashboards undercount error rates and percentiles.
- **`tail_sampling` processor belongs on the gateway.** Tail sampling requires the full trace in memory to evaluate a policy. Daemonset agents only see their node's spans, so a tail sampler on the agent drops traces partially.
- **`transactions` processor must run before `spanmetrics`.** `transactions` enriches spans with `cgx.transaction.*` tags. `spanmetrics` must consume those tags to emit per-transaction metric dimensions.

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