# Data Architecture — nexpay-mock-processor-svc

## Data Stores
| Store | Technology | Purpose |
|-------|-----------|---------|
| SQLite file (`mock-responses.db`) | SQLite 3.47.1 via Xerial JDBC | Persists endpoint response templates |

## Schema / Tables
### `endpoint_response_templates`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | BIGINT (PK, auto-increment) | NOT NULL |
| `endpoint_key` | VARCHAR | NOT NULL, UNIQUE |
| `template` | LOB (TEXT) | NOT NULL |

DDL is managed by Hibernate `ddl-auto: update` — no migration scripts are present.

## Sensitive Data
- No real cardholder data is stored.
- Templates contain structural placeholders (`{cardNum}`, `{maskedPan}`, etc.) that resolve to synthetic values at runtime.
- The `cardNum` generator produces numbers starting with `55555555` — clearly synthetic; these are not real PANs.
- No PII fields stored.

## Encryption
- No data encryption at rest.
- No TLS configuration present in application.yaml; plain HTTP assumed.
- SQLite file is unencrypted on disk — acceptable for a developer-only tool but must not hold real data.

## Data Flow
- On startup `DataSeeder` inserts default rows via JPA `save()` — no migration tool.
- Each HTTP request triggers a SELECT by `endpointKey`, then the template string is returned through `TemplateResolverService`.
- No writes occur during normal request handling (read-only request path).
- Volume mount `./logs:/app/logs` in docker-compose — log files written to host; no structured sensitive data logged.

## Data Quality / Retention
- No retention policy or cleanup mechanism.
- SQLite file grows only with additional template rows; size is negligible.
- No audit trail or change history for template modifications.

## Compliance Gaps
- `ddl-auto: update` is used in all profiles — schema drift risk; Flyway or Liquibase should be used.
- No TLS on the service port (8085) — communications are unencrypted.
- SQLite file is not encrypted; acceptable only in dev environments.
- No data masking or access audit logging.
