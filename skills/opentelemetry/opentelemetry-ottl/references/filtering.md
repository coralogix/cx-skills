# Filtering with OTTL

The `filter` processor drops records that match the given condition. A match = drop.

Place `filter` **before `transform`** in the pipeline. If you need enrichment attributes to
make the filter decision (e.g., k8s labels), place the enrichment processor before `filter`.

---

## Log filtering

```yaml
processors:
  filter:
    error_mode: ignore
    logs:
      log_record:
        # Drop DEBUG and TRACE — reduces volume by 20-40% in many environments
        - severity_number < SEVERITY_NUMBER_INFO

        # Drop health check hits by URL pattern in body
        - IsMatch(body, "GET /(healthz?|readyz?|ping|livez?) HTTP/[0-9\\.]+ 200")

        # Drop by service name
        - resource.attributes["service.name"] == "noisy-sidecar"

        # Drop by service name pattern
        - IsMatch(resource.attributes["service.name"], "^(fluent-bit|prometheus-agent)$")

        # Drop by severity + service combo (drop high-volume low-severity from specific services)
        - 'IsMatch(resource.attributes["service.name"], "(metrics-proxy|telemetry-agent)") and severity_number <= 9'
```

### Drop by namespace (denylist)

```yaml
filter:
  error_mode: ignore
  logs:
    log_record:
      - resource.attributes["k8s.namespace.name"] == "kube-system"
      - resource.attributes["k8s.namespace.name"] == "cert-manager"
      - resource.attributes["k8s.namespace.name"] == "monitoring"
```

### Keep only specific namespaces (allowlist)

The filter processor drops records that match — to keep only specific namespaces, drop everything else:

```yaml
filter:
  error_mode: ignore
  logs:
    log_record:
      - not (resource.attributes["k8s.namespace.name"] == "prod" or resource.attributes["k8s.namespace.name"] == "payments")
```

---

## Metric filtering

```yaml
processors:
  filter:
    error_mode: ignore
    metrics:
      metric:
        # Drop by exact name
        - name == "go.goroutines"
        # Drop all Go runtime metrics
        - IsMatch(name, "^go\\..*")
        # Drop by prefix
        - IsMatch(name, "^runtime\\..*")
```

### Drop metrics that lack a required attribute

```yaml
filter:
  error_mode: ignore
  metrics:
    datapoint:
      # Drop datapoints with no service.name (unidentifiable, noisy)
      - resource.attributes["service.name"] == nil

      # Drop only datapoints missing a per-series label; keep the metric and
      # any sibling datapoints that still match the backend contract.
      - attributes["tenant"] == nil
```

Use `metrics.datapoint` for per-series/per-point filtering. A `metrics.metric`
condition evaluates the whole metric and can remove every datapoint under that
metric, which is not what you want when only some datapoints are invalid.

---

## Trace filtering

```yaml
processors:
  filter:
    error_mode: ignore
    traces:
      span:
        # Drop health check endpoints
        - attributes["http.target"] == "/healthz"
        - attributes["http.target"] == "/readyz"
        - IsMatch(attributes["http.url"], ".*/(healthz?|readyz?|ping)$")

        # Drop very short spans (sub-millisecond — typically noise)
        - duration < 1000000                                 # nanoseconds

        # Drop spans from a specific service
        - resource.attributes["service.name"] == "k6-load-test"

        # Drop non-DB spans in a DB-specific pipeline
        - attributes["db.system"] == nil

        # Drop spans where service is not the one you care about
        - resource.attributes["service.name"] != "api-gateway"
```

---

## Tail sampling with OTTL conditions

Tail sampling policies support OTTL via `ottl_condition`. This runs at the span level, not
the trace level — combine with other policy types (status_code, probabilistic, rate_limiting)
using `and` policies.

```yaml
processors:
  tail_sampling:
    policies:
      # Force sample traces that have a custom "force_sample" attribute set
      - name: force-sample
        type: ottl_condition
        ottl_condition:
          error_mode: ignore
          span:
            - 'attributes["force_sample"] == "true" or attributes["http.request.header.x-debug"] == "true"'

      # Sample error spans from specific operations at 5%
      - name: sample-noisy-errors
        type: and
        and:
          and_sub_policy:
            - name: is-error
              type: status_code
              status_code:
                status_codes: [ERROR]
            - name: is-noisy-span
              type: ottl_condition
              ottl_condition:
                error_mode: ignore
                span:
                  - 'IsMatch(name, "^(exec_binder|getContentDetail|getContentRating)$")'
            - name: probabilistic
              type: probabilistic
              probabilistic:
                sampling_percentage: 5

      # Sample all other errors at 25%
      - name: sample-other-errors
        type: and
        and:
          and_sub_policy:
            - name: is-error
              type: status_code
              status_code:
                status_codes: [ERROR]
            - name: exclude-noisy
              type: ottl_condition
              ottl_condition:
                error_mode: ignore
                span:
                  - 'not IsMatch(name, "^(exec_binder|getContentDetail|getContentRating)$")'
            - name: probabilistic
              type: probabilistic
              probabilistic:
                sampling_percentage: 25

      # Sample 5xx HTTP errors with a rate limit
      - name: http-5xx-errors
        type: and
        and:
          and_sub_policy:
            - name: is-5xx
              type: ottl_condition
              ottl_condition:
                error_mode: ignore
                span:
                  - 'IsMatch(attributes["http.status_code"], "5..")'
            - name: probabilistic
              type: probabilistic
              probabilistic:
                sampling_percentage: 10.0
            - name: rate-limit
              type: rate_limiting
              rate_limiting:
                spans_per_second: 400

      # Decentralized sampling control: services set sampling.rule resource attribute
      - name: service-defined-full-sample
        type: ottl_condition
        ottl_condition:
          error_mode: ignore
          span:
            - 'IsMatch(resource.attributes["sampling.rule"], ".*-100-sampling$")'
```

**Important limitation**: OTTL conditions in tail sampling evaluate at span level, but sampling
decisions are made at trace level. A condition that matches only some spans in a trace does
not selectively drop those spans — it influences whether the whole trace is sampled.
