# db-namespace-endpoint-fallback

You are a Coralogix support expert. A user has asked the following question:

---

A Helm user put the DB compatibility transform under spanMetrics.dbMetrics.transformStatements. Now db_calls_total has db_namespace populated from db.name, but normal Span Metrics calls_total still has db_system populated and db_namespace blank for database spans. Where should this transform live, and what should the pre-spanmetrics bridge do when db.name and db.namespace are both missing?

---
