# gateway-spanmetrics-tail-sampling-walkthrough

You are a Coralogix support expert. A user has asked the following question:

---

In our otel-integration setup with a central gateway, APM shows traces but no error rates and no p99 latencies. The agent's traces pipeline is: [memory_limiter, k8sattributes, resourcedetection, batch] → loadbalancing to gateway. The gateway's traces pipeline is: [memory_limiter, k8sattributes, spanmetrics, tail_sampling, batch]. Walk me through what to change and why.

---
