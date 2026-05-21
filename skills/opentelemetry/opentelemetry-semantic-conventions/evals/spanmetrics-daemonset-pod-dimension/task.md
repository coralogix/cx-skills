# spanmetrics-daemonset-pod-dimension

You are a Coralogix support expert. A user has asked the following question:

---

We run the OTel Collector as a Kubernetes DaemonSet with one agent per node. A service has pods on several nodes, and its Span Metrics counters look like multiple writers are colliding for the same service_name. Should k8s.pod.name be a spanmetrics dimension only if there are multiple collectors on one node, or can the normal one-agent-per-node topology need it too?

---
