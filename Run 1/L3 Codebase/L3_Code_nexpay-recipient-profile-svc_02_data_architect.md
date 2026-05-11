# Data Architecture — nexpay-recipient-profile-svc

## Data Stores
| Store | Technology | Purpose |
|-------|-----------|---------|
| PostgreSQL (Azure) | PostgreSQL via JDBC, HikariCP | Primary operational store for all profile data |
| Azure App Configuration | Azure SDK | Externalised config and feature flags |
| Azure Key Vault | Via App Configuration KV provider | Secrets (DB credentials, connection strings) |

## Schema / Tables (from V1__initial_schema.sql)
### `recipient_profile`
| Column | Type | Notes |
|--------|------|-------|
| `profile_id` | UUID PK | gen_random_uuid() |
| `auth_id` | VARCHAR(255) | External auth system identifier |
| `first_name` | VARCHAR(100) | PII |
| `last_name` | VARCHAR(100) | PII |
| `date_of_birth` | VARCHAR(10) | PII — stored as string, not DATE |
| `primary_email` | VARCHAR(255) | PII — indexed |
| `primary_phone` | VARCHAR(50) | PII — indexed |
| `preferred_language` | VARCHAR(10) | |
| `profile_status` | VARCHAR(50) | CHECK: pending/active/suspended/inactive/closed |
| `status_reason` | VARCHAR(100) | |
| `status_comment` | VARCHAR(500) | |
| `version` | INT | Optimistic lock counter |

### `external_profile_mapping`
| Column | Type | Notes |
|--------|------|-------|
| `mapping_id` | UUID PK | |
| `profile_id` | UUID FK → recipient_profile | ON DELETE CASCADE |
| `source_system` | VARCHAR(100) | e.g. "ecount", "fis" |
| `external_profile_id` | VARCHAR(255) | External system's identifier |
| `mapping_status` | VARCHAR(50) | |
| `linked_at` | TIMESTAMPTZ | |
| `version` | INT | |

### `profile_address`
| Column | Type | Notes |
|--------|------|-------|
| `address_id` | UUID PK | |
| `profile_id` | UUID FK → recipient_profile | ON DELETE CASCADE |
| `address_type` | VARCHAR(50) | CHECK: Primary/Mailing/Business |
| `line1`–`line2` | VARCHAR(255) | Street address lines |
| `city` | VARCHAR(100) | |
| `state_province` | VARCHAR(100) | |
| `postal_code` | VARCHAR(20) | |
| `country_code` | VARCHAR(10) | |
| `version` | INT | |

### `profile_attribute`
| Column | Type | Notes |
|--------|------|-------|
| `attribute_id` | UUID PK | |
| `profile_id` | UUID FK → recipient_profile | ON DELETE CASCADE |
| `attribute_category` | VARCHAR(100) | |
| `attribute_key` | VARCHAR(100) | |
| `attribute_value` | VARCHAR(1000) | Arbitrary — could hold sensitive data |
| `is_verified` | BOOLEAN | |
| `verified_at` | TIMESTAMPTZ | |
| `version` | INT | |

### Envers Audit Tables
`revision_info`, `recipient_profile_aud`, `profile_address_aud`, `profile_attribute_aud`, `external_profile_mapping_aud` — store full history of each entity state at each revision, with actor_id, trace_id, source, reason.

## Sensitive Data
- `first_name`, `last_name`, `date_of_birth`, `primary_email`, `primary_phone` — PII fields.
- `attribute_value` — untyped; may hold SSN, bank account numbers, or other sensitive data depending on caller usage.
- Audit tables replicate all PII fields into `_aud` tables — PII lifecycle must cover audit tables.

## Encryption
- No application-level field encryption observed.
- Database-at-rest encryption assumed to be Azure-managed (Azure Database for PostgreSQL transparent encryption).
- Passwordless authentication in production via Azure Managed Identity + `AZURE_POSTGRESQL_AD_NON_ADMIN_USERNAME` — no static DB password.
- Local/docker profiles: password via environment variable `SPRING_DATASOURCE_PASSWORD` — must not be empty in real use.

## Data Flow
- Flyway manages schema migrations (`classpath:db/migration`); `clean-disabled: true` in all non-local profiles.
- `validate` DDL mode in production — schema must match entity definitions exactly.
- HikariCP pool: max 20 connections in production, leak detection threshold 60 s.
- OTLP metrics exported to Dynatrace endpoint in qa/prod profiles.

## Data Quality / Retention
- No data retention policy implemented in code.
- `clean-disabled: false` only in local profile — safe.
- No archival or soft-delete pattern (hard delete cascades all children).
- Envers audit tables grow indefinitely — no pruning mechanism observed.

## Compliance Gaps
- `date_of_birth`, `primary_email`, `primary_phone` stored without column-level encryption — gap against PCI DSS cardholder data field encryption best practice and GDPR data minimisation.
- Envers audit tables replicate unencrypted PII — GDPR erasure requests must also purge audit rows or legal hold must be documented.
- `attribute_value` is untyped — no guardrails prevent storage of sensitive authentication data (SAD) here.
- Swagger UI enabled in qa/prod profiles (`api-docs.enabled: true`) — API surface discoverable by unauthenticated callers if not protected by gateway.
