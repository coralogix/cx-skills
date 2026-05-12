# log-attr-to-resource-for-exporter

You are a Coralogix support expert. A user has asked the following question:

---

We route logs to a Coralogix subsystem using the coralogix exporter with subsystem_name_attributes: ["subsystem"]. Our application writes subsystem into the log-record attributes (attributes["log.file.subsystem"]), but the subsystem always comes back blank — the exporter can't see it. We don't want to rename the field in the application. How do I use OTTL so the exporter picks it up?

---
