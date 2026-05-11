# Task

You are a Coralogix support expert. A user has asked the following question:

---

I want to set attributes["db.namespace"] to whichever of db.name, server.address, or net.peer.name is populated on the span — whichever one appears first wins. I tried jamming it all into one set() with a big conditional and the statement is unreadable. How does OTTL express a first-non-nil-wins fallback chain cleanly?

---
