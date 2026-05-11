# Business Analysis — nexpay-recipient-profile-svc

## Business Purpose
A Gen-3 NexPay microservice that owns the canonical recipient profile for payment disbursement recipients. It provides a CRUD API for managing recipient identity data (name, contact, address, external-system mappings, arbitrary attributes) and maintains a complete immutable audit history of all changes via Hibernate Envers. This service is the system of record for recipient identity within the NexPay Gen-3 platform.

## Capabilities
- Create, read, update, and delete recipient profiles.
- Manage profile addresses (primary, mailing, business) per profile.
- Manage extensible key/value profile attributes with verification tracking.
- Manage external profile mappings (linking a NexPay profile to an external system identifier, e.g. a legacy ecount member ID).
- Full revision history for recipient profiles, addresses, and attributes via Hibernate Envers.
- Paginated listing of profiles with optional status filter.
- Pagination of revision history per profile, with retrieval of individual revision by number.
- Health and metrics exposure (liveness/readiness probes, Prometheus, OTLP).

## Key Entities
| Entity | Table | Description |
|--------|-------|-------------|
| `RecipientProfile` | `recipient_profile` | Core identity: name, DOB, email, phone, language, status |
| `ProfileAddress` | `profile_address` | Physical or mailing address; types: Primary, Mailing, Business |
| `ProfileAttribute` | `profile_attribute` | Extensible key/value attributes with verification flag |
| `ExternalProfileMapping` | `external_profile_mapping` | Links profile to external system IDs (source_system, external_profile_id) |
| `CustomRevisionEntity` | `revision_info` | Envers revision metadata: actorId, traceId, source, reason |

## Business Rules
- `profile_status` is constrained to: `pending`, `active`, `suspended`, `inactive`, `closed`.
- `address_type` is constrained to: `Primary`, `Mailing`, `Business`.
- Pagination: `limit` capped at 500; `offset` must be a multiple of `limit`.
- Revision pagination: `limit` capped at 100.
- Optimistic locking via `@Version` on all entities — concurrent update conflicts surface as HTTP 409.
- Envers audit tracks: actor (user/service identity), trace ID (correlation), source (application name), reason.
- Profile deletion cascades to all child addresses, attributes, and external mappings.

## Data Flow
1. REST client (other NexPay services or BFFs) calls the API via Spring Boot REST layer.
2. API delegate maps request to JPA entity; service layer applies business rules.
3. JPA/Hibernate writes to PostgreSQL; Envers writes revision rows in the same transaction.
4. Reads use read-only transactions; paginated queries use Spring Data `Page<T>`.
5. Configuration and secrets retrieved from Azure App Configuration / Key Vault at startup.

## Compliance Relevance
- PII stored: first name, last name, date of birth (varchar), email, phone number.
- Date of birth stored as `VARCHAR(10)` — no field-level encryption observed.
- Envers audit log provides an immutable change trail, supporting SOC 2 and PCI DSS audit requirements.
- Azure passwordless authentication (Managed Identity) used for database access in production, reducing credential exposure risk.
- GDPR/CCPA: profile deletion endpoint supports right-to-erasure; cascades to all sub-entities.

## Risks
- `date_of_birth` stored as unencrypted VARCHAR — PII at rest without field encryption.
- `primary_email` and `primary_phone` stored unencrypted — PII at rest.
- No rate limiting or throttling observable in this service.
- `attribute_value` VARCHAR(1000) in `profile_attribute` could store arbitrary sensitive data without type enforcement.
- Swagger UI enabled in production (`qa`, `prod` profiles) — API surface discoverable.
