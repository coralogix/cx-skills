# keep-keys-ismap-guard

You are a Coralogix support expert. A user has asked the following question:

---

I added a transform processor with keep_keys(body, ["message", "level"]) in context: log, but the collector is now logging INVALID_ARGUMENT errors and some logs are being dropped. The bodies look like plain strings in some of our log sources. How do I fix this so the statement only runs when the body is actually a map?

---
