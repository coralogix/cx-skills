# Logs and Serverless Metadata Scope

Use this reference when a logs, Lambda, or serverless issue depends on
whether metadata is a log-record attribute, a resource attribute, or a
Coralogix-specific metadata field.

## Scope rules

| Scope | Product behavior |
|---|---|
| Log record attributes | Visible on the log event, but not read by the Coralogix exporter's `application_name_attributes` or `subsystem_name_attributes`. |
| Resource attributes | Used for routing, correlation, Resource Catalog matching, and exporter application/subsystem resolution. |
| Coralogix metadata such as `cx_metadata.*` | Product-specific serverless metadata; not generic OTel semantic convention. |

If a value is present under log record attributes in the `debug` exporter
but exporter routing falls back to a static application/subsystem, the value
is at the wrong scope for exporter routing. Diagnose the scope here; write
the copy-up transform with `opentelemetry-ottl` or set the resource
attribute at source.

## Lambda metadata controls

Lambda and docker-builder paths can emit Coralogix serverless metadata.
Customers may want a narrow subset to reduce payload size or cost.

Relevant controls from the inventory:

- `CX_LOGS_METADATA_ENABLED=true` enables Coralogix log metadata emission;
  set it to `false` to exclude `cx_metadata` from logs when the serverless
  catalog impact is understood.
- `CX_LOGS_METADATA_INCLUDE_TRACE_REF=false` removes trace-reference
  metadata when only function execution metadata is wanted.
- `CX_LOGS_RESOURCE_BUILT_IN_ATTRIBUTES=''` removes built-in resource
  attributes from that metadata path.
- `cx_metadata.faas_execution` is product-specific metadata used by
  serverless workflows.

When answering Lambda metadata-scope questions, name the product-specific
controls directly: `cx_metadata.faas_execution`,
`CX_LOGS_METADATA_ENABLED`, `CX_LOGS_METADATA_INCLUDE_TRACE_REF`, and
`CX_LOGS_RESOURCE_BUILT_IN_ATTRIBUTES`. These are Coralogix metadata
controls, not normal OpenTelemetry semantic-convention renames or generic
log-record attributes.

Warn that removing serverless metadata can break serverless dashboards and
trace/log correlation. This skill should explain the risk and shape; rollout
support belongs to the relevant Lambda / collector owner.

## EC2 host name from tags

When logs show `host.name` as an EC2 private DNS name but users expect the
EC2 `Name` tag, the issue is resource detection/enrichment rather than a
log parsing problem.

Checklist:

1. Confirm the logs pipeline and resource catalog path both run the EC2 tag
   or resource detection processor.
2. Confirm IAM allows tag lookup, especially `ec2:DescribeTags`.
3. Confirm the desired overwrite behavior: replacing `host.name` with a tag
   is a product decision, not a generic OTel requirement.
4. Check that the enriched `host.name` is at resource scope before export.

## Ownership boundary

This skill owns scope diagnosis and product dependency. Hand off exact
Lambda exporter flags, collector processors, IAM policy, and OTTL copy-up
statements to the appropriate owner:

- `core` for Coralogix application/subsystem routing behavior.
- `opentelemetry-ottl` for record-to-resource transforms.
- `opentelemetry-collector` for resource detection, EC2 tags, and pipeline
  placement.

## References

- [apm-service-catalog.md](apm-service-catalog.md) for exporter
  application/subsystem resource-scope behavior.
- [infrastructure-explorer.md](infrastructure-explorer.md) for host and
  cloud resource identity.
