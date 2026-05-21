# spanmetrics-url-full-cardinality

You are a Coralogix support expert. A user has asked the following question:

---

Our APM dashboards stop loading beyond a few days. The worst offender is
`duration_ms_bucket`, and the spanmetrics connector has these dimensions:
`http.method`, `cgx.transaction`, `cgx.transaction.root`, `status_code`,
`url.full`, `http.response.status_code`, plus Kubernetes pod labels. `url.full`
alone has hundreds of thousands of values because it includes IDs and query
strings. Should we just raise the cardinality limit, or is there a better fix?

---
