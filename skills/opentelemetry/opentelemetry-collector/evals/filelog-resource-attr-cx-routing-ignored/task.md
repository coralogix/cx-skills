# filelog-resource-attr-cx-routing-ignored

You are a Coralogix support expert. A user has asked the following question:

---

We set up the Coralogix Linux host integration with a filelog receiver. To route logs from different files to different Coralogix subsystems, we added an operator that sets cx.application.name and cx.subsystem.name as resource attributes on each log record. The operators are definitely running — we can see the attributes in the debug exporter output. But all logs arrive in Coralogix under the global application_name and subsystem_name values hardcoded in the exporter block. The per-file attributes are completely ignored. What's wrong?

---
