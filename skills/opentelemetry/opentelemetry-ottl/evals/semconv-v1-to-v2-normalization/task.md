# Task

You are a Coralogix support expert. A user has asked the following question:

---

Our fleet has a mix of old and new OpenTelemetry instrumentation libraries. Some spans come in with http.method and http.status_code (v1 semconv), others with http.request.method and http.response.status_code (v2). Our dashboards expect v2 attribute names. How do I write OTTL that normalizes the old v1 names to v2 without overwriting spans that already have v2?

---
