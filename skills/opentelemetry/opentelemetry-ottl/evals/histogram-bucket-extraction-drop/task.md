# Task

You are a Coralogix support expert. A user has asked the following question:

---

We have a high-volume histogram metric http.server.request.duration with many bucket boundaries. We want to keep the _sum and _count aggregations for average latency calculations but drop the raw histogram buckets entirely to reduce ingestion cost. Can OTTL do this? What's the right sequence to extract the aggregations and then drop the source histogram?

---
