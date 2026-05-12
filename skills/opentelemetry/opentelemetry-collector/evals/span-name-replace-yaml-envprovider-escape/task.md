# span-name-replace-yaml-envprovider-escape

You are a Coralogix support expert. A user has asked the following question:

---

Our otel-integration values.yaml has spanNameReplacePattern under opentelemetry-agent.presets.spanMetrics to reduce span_name cardinality:

  spanNameReplacePattern:
    - regex: "cycle-(manager|rpa-manager)\\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_(.+)"
      replacement: "cycle-$1.$2"

helm upgrade fails with: "processors::transform/span_name: statement has invalid syntax: 1:28: invalid quoted string ... invalid syntax". The regex itself works in a standalone regex tester. What's wrong with the values file?

---
