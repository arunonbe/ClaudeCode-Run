# jobservice-integration_LIB — Enterprise Architect View

## Platform Generation

**Gen-1** — Same provenance as `jobserviceintegration_LIB`. See that repo's enterprise architect analysis for full evidence.

## Business Domain

**Inbound Client File Integration** — Identical domain to `jobserviceintegration_LIB`. Converts automotive and telecom client data files to eCount batch format for prepaid card enrolment and funding.

## Relationship to jobserviceintegration_LIB

This repository is a **fork/duplicate** of `jobserviceintegration_LIB`. Both carry the same Maven artifact coordinates. From an enterprise architecture perspective this creates:

1. **Ambiguity of canonical source**: It is unclear which repository should be treated as the authoritative version.
2. **Divergence risk**: Changes made to one may not be reflected in the other, causing the two to drift over time.
3. **Maven conflict**: Identical artifact coordinates mean one repo's published JAR will silently overwrite the other.

## Role in the Platform

Same as `jobserviceintegration_LIB` — data translation layer between client file delivery and eCount job service.

## Strategic Status

| Dimension | Assessment |
|---|---|
| Lifecycle | **Retire / Consolidate** — This repo should either be merged with `jobserviceintegration_LIB` or archived |
| Canonical repo | To be determined by platform team |
| Migration target | Gen-3 NexPay disbursement API |
| Urgency | High — duplicate artifact is an active build system risk |

## Migration Blockers

Same as `jobserviceintegration_LIB`, plus:
- **Repo consolidation**: Must determine canonical source before migration work begins
- **Artifact conflict**: Must resolve the duplicate Maven artifact before either can be published reliably

## Dependencies

Same upstream and downstream dependencies as `jobserviceintegration_LIB`.
