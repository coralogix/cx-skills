# Task

You are a Coralogix support expert. A user has asked the following question:

---

Our Java services on Kubernetes produce stack traces that arrive in Coralogix as dozens of separate log records — one per line — instead of a single merged entry. I added multiline configuration to the filelog receiver with a line_start_pattern matching the timestamp format, but it only captures the first line of the exception and drops all the "at ..." lines. Looking at the raw /var/log/pods files, every single log line has logtag F. Why isn't the multiline config helping, and what's the right approach?

---
