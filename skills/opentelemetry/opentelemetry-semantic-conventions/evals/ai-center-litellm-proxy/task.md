# ai-center-litellm-proxy

You are a Coralogix support expert. A user has asked the following question:

---

A customer routes LLM traffic through LiteLLM. Coralogix traces are present, but AI Center is blank. The proxy span is name="POST /chat/completions", attributes={http.route="/chat/completions", http.request.method="POST", server.address="litellm-proxy", model="claude-3-5-sonnet"}, and it does not have gen_ai.provider.name, gen_ai.system, or gen_ai.input.messages. Should semconv fix this in the collector, or is the proxy/instrumentation missing something?

---
