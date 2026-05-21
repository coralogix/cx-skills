# redactionprocessor-url-sanitizer

You are a Coralogix support expert. A user has asked the following question:

---

We do not have `http.route` on spans, so APM operations are based on raw URL-like
span names and `url.full`. They include account IDs, merchant IDs, query params,
and sometimes tokens. We need to reduce spanmetrics cardinality and avoid sending
PII/secrets to Coralogix. Should we use the redaction processor, OTTL, or both,
and where should this run?

---
