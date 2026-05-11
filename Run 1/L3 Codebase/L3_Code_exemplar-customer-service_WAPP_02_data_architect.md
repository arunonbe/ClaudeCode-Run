# Data Architect View — exemplar-customer-service_WAPP

## Data Stores
| Store | Type | Location |
|-------|------|----------|
| SQL Server (Azure SQL) | Relational RDBMS | `exemplar-sqlserver.database.windows.net` (AKS config) / `exemplar-sqlserver` (Docker) |
| H2 in-memory | Embedded (test/local) | In-process JVM |

## Schema / Tables
**CUSTOMER** table (created via Liquibase changeset `db.changelog-1.0.xml`):

| Column | Type | Constraints |
|--------|------|-------------|
| ID | varchar2(36) | PK, NOT NULL |
| VERSION | bigint | Nullable (Hibernate optimistic lock) |
| CUSTOMER_ID | varchar2(36) | NOT NULL, UNIQUE (UDX_CUSTOMER_ID) |
| FIRST_NAME | varchar2(100) | NOT NULL |
| LAST_NAME | varchar2(100) | NOT NULL |
| INSERTED_AT | timestamp(6) | Audit |
| INSERTED_BY | varchar2(255) | Audit |
| UPDATED_AT | timestamp(6) | Audit |
| UPDATED_BY | varchar2(255) | Audit |

## Sensitive Data Classification
| Field | Classification | PCI DSS / Privacy Relevance |
|-------|---------------|----------------------------|
| FIRST_NAME | PII | CCPA, GDPR — personal data |
| LAST_NAME | PII | CCPA, GDPR — personal data |
| CUSTOMER_ID | Pseudonymous ID | Internal reference |

No payment card data (PAN, CVV, expiry) is present in this schema. This is a demo service.

## Encryption
- TLS for DB connection: configurable via `spring.datasource.tlsEnabled` and JKS truststore (`DataSourceConfiguration.java` — lines 30-43). The truststore is expected to be injected as a Base64-encoded string at runtime.
- No column-level encryption for PII fields (FIRST_NAME, LAST_NAME).
- Passwords in `application.yml` are plaintext strings (B00t1ful, [REDACTED — rotate immediately]); these are hardcoded demo values but represent a pattern risk.

## Data Flow
1. REST API receives Customer JSON/XML.
2. Spring controller validates and passes to CustomerServiceImpl.
3. CustomerServiceImpl maps to JPA entity and persists via CustomerRepository (Hibernate/JPA).
4. SQL Server stores the row.
5. Liquibase manages schema at application startup (ddl-auto: none).

## Data Quality / Retention
- No data retention or purge policies implemented in this codebase.
- No soft-delete; records are updated in place.
- Optimistic locking via VERSION column (Hibernate).
- Page size configurable to 100 via `spring.jpa.pageable.page-size`.

## Compliance Gaps
1. PII (first/last name) stored without column-level encryption — mitigate for any production usage.
2. Hardcoded database password in application.yml committed to Git history.
3. No field-level masking or tokenisation implemented.
4. No data retention policy or archival mechanism.
5. `spring.jpa.show-sql: true` — SQL statements including query parameters will appear in logs; if PII were included in queries this would expose personal data in log streams.
