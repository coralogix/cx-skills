# http-protocol-profiles-signal-upgrade

You are a Coralogix support expert. A user has asked the following question:

---

After upgrading opentelemetry-collector-contrib from 0.140 to 0.144, our collector fails to start with: "Error: exporters::coralogix: profiles signal is not supported with HTTP protocol, use gRPC protocol (default) instead". We have protocol: http set in our coralogix exporter config, but we are not sending profiles — only logs, metrics, and traces. The same config worked fine on 0.140. What changed and how do we fix it?

---
