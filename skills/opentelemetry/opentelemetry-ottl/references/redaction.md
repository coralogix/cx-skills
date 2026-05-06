# OTTL Data Redaction and PII Masking

Patterns for redacting, masking, and pseudonymizing sensitive data before telemetry leaves
the collector. All patterns use the `transform` processor.

---

## Pseudonymize with SHA256

Replace a sensitive value with its hash rather than dropping it. Preserves correlation
(same input always hashes to the same output) without exposing raw identifiers.

```yaml
log_statements:
  - context: log
    statements:
      - set(attributes["user.id"], SHA256(attributes["user.id"])) where attributes["user.id"] != nil

trace_statements:
  - context: span
    statements:
      - set(attributes["user.id"], SHA256(attributes["user.id"])) where attributes["user.id"] != nil
```

---

## Mask credit card numbers

```yaml
log_statements:
  - context: log
    statements:
      # Mask PAN in a structured body field
      - replace_pattern(body["message"], "[0-9]{4}[-\\s]?[0-9]{4}[-\\s]?[0-9]{4}[-\\s]?[0-9]{4}", "[CARD_REDACTED]") where IsMap(body) and body["message"] != nil

      # Mask PAN in plain-string body
      - replace_pattern(body, "[0-9]{4}[-\\s]?[0-9]{4}[-\\s]?[0-9]{4}[-\\s]?[0-9]{4}", "[CARD_REDACTED]") where IsString(body)
```

---

## Redact Authorization headers in spans

`replace_all_patterns` iterates over all values in a map and applies the replacement where
the pattern matches — avoids listing every possible header key.

```yaml
trace_statements:
  - context: span
    statements:
      - replace_all_patterns(attributes, "value", "(?i)^(bearer|basic)\\s+.+$", "$1 [REDACTED]")
```

---

## Drop an attribute matching a PII pattern

Use when the attribute itself is the PII and should not appear at all:

```yaml
log_statements:
  - context: log
    statements:
      - delete_key(attributes, "user.email") where IsMatch(attributes["user.email"], ".+@.+\\..+")
```

---

## Redact tokens from URL query strings

```yaml
log_statements:
  - context: log
    statements:
      - replace_pattern(attributes["http.url"], "([?&])(token|api_key|secret|password)=[^&]+", "$1$2=[REDACTED]") where attributes["http.url"] != nil

trace_statements:
  - context: span
    statements:
      - replace_pattern(attributes["url.full"], "([?&])(token|api_key|secret|password)=[^&]+", "$1$2=[REDACTED]") where attributes["url.full"] != nil
```

---

## Redact from plain-string body

```yaml
log_statements:
  - context: log
    statements:
      - replace_pattern(body, "([?&])(token|api_key|secret|password)=[^&]+", "$1$2=[REDACTED]") where IsString(body)
      - replace_pattern(body, "[0-9]{4}[-\\s]?[0-9]{4}[-\\s]?[0-9]{4}[-\\s]?[0-9]{4}", "[CARD_REDACTED]") where IsString(body)
```

---

## Truncate long attribute values

Prevents large blobs (stack traces, request bodies) from inflating storage:

```yaml
log_statements:
  - context: log
    statements:
      - truncate_all(attributes, 512)   # cap all attribute values at 512 chars
```
