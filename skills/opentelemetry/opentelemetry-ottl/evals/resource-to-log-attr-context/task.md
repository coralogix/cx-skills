# Task

You are a Coralogix support expert. A user has asked the following question:

---

I'm trying to copy the k8s namespace name from the resource down into each log record as an attribute so I can filter on it later. I wrote this in my transform processor under context: log — set(attributes["namespace"], attributes["k8s.namespace.name"]) — but the attribute always comes out nil. What am I doing wrong?

---
