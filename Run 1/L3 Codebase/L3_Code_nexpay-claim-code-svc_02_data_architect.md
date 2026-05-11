# nexpay-claim-code-svc — Data Architect View

## Data Stores

| Store | Type | Access Pattern |
|---|---|---|
| `nexpay_claimable` (Azure SQL / SQL Server) | Relational (SQL Server) | JPA/Hibernate via Spring Data JPA repositories; Flyway for schema migration |

## Schema / Tables

Managed by Flyway migrations in `nexpay-claimcode-data-entity/src/main/resources/db/migration/`:

### `claimable_payment_status` (V1)
| Column | Type | Values |
|---|---|---|
| `claimable_payment_status_id` | INT | PK |
| `code` | NVARCHAR(20) | issued, claimed, blocked, canceled, expired, expired_failed |
| `name` | NVARCHAR(100) | Human-readable status name |

### `claimable_payment_modality` (V2)
| Column | Type | Values |
|---|---|---|
| `claimable_payment_modality_id` | INT | PK |
| `code` | NVARCHAR(20) | virtual, card, p2c, paypal, ach, check |
| `name` | NVARCHAR(100) | Human-readable modality name |

### `claimable_payment` (V3)
| Column | Type | Sensitivity |
|---|---|---|
| `claimable_payment_id` | INT IDENTITY | PK |
| `owner_id` | UNIQUEIDENTIFIER | CDE-adjacent (links to cardholder account) |
| `dda` | NVARCHAR(50) | Sensitive — demand deposit account identifier |
| `amount` | INT | Financial (cents) |
| `claim_code` | NVARCHAR(50) UNIQUE | Sensitive — single-use financial token |
| `claimable_payment_status_id` | INT FK | Status reference |
| `claimable_payment_modality_id` | INT FK | Modality reference (nullable) |
| `issued_date` | DATETIME | |
| `claimed_date` | DATETIME | Nullable |
| `expiration_date` | DATETIME | Nullable |
| `created` | DATETIME DEFAULT GETDATE() | Audit |
| `updated` | DATETIME | Nullable audit |
| `first_name` | NVARCHAR(50) | PII — denormalised from eCountCore |
| `middle_name` | NVARCHAR(50) | PII |
| `last_name` | NVARCHAR(50) | PII |

### `recipient_registration` (V5)
| Column | Type | Sensitivity |
|---|---|---|
| `id` | UNIQUEIDENTIFIER | PK (external UUID) |
| `first_name` | NVARCHAR(50) | PII |
| `last_name` | NVARCHAR(50) | PII |
| `middle_name` | NVARCHAR(50) | PII |
| `suffix_name` | NVARCHAR(50) | PII |
| `home_email` | NVARCHAR(50) | PII |
| `business_email` | NVARCHAR(50) | PII |
| `mobile_email` | NVARCHAR(50) | PII |
| `address1` | NVARCHAR(260) | PII |
| `address2` | NVARCHAR(260) | PII |
| `attention_line` | NVARCHAR(100) | PII |
| `company_name` | NVARCHAR(100) | PII |
| `city` | NVARCHAR(100) | PII |
| `state` | NVARCHAR(100) | PII |
| `postal` | NVARCHAR(50) | PII |
| `country` | NVARCHAR(100) | PII |
| `home_phone` | NVARCHAR(50) | PII |
| `business_phone` | NVARCHAR(50) | PII |
| `mobile_phone` | NVARCHAR(50) | PII |

### `revinfo` (Hibernate Envers — created automatically)
| Column | Type | Notes |
|---|---|---|
| `rev` | INT IDENTITY | Revision number |
| `revtstmp` | BIGINT | Unix timestamp |
| `actor_id` | NVARCHAR(100) | Who made the change (from OTel baggage `actor.id`) |

## Sensitive Data Summary

| Data Category | Fields | PCI/Privacy Scope |
|---|---|---|
| Cardholder-adjacent ID | `owner_id`, `dda` | PCI DSS Req. 3 — `dda` especially if mapped to card DDA |
| Single-use financial token | `claim_code` | Should be treated like a credential; access-controlled |
| Financial amount | `amount` | Not PAN/SAD, but financially sensitive |
| Recipient PII (name) | `first_name`, `middle_name`, `last_name` | GDPR Art. 4, CCPA |
| Recipient contact info | Email, phone, address | GDPR, CCPA, GLBA |

## Encryption

- **At rest**: Not configured at the application layer. Encryption at rest depends on Azure SQL Server TDE (Transparent Data Encryption) being enabled on the `nexpay_claimable` database — this is an infrastructure responsibility, not application code.
- **In transit**: JDBC connection to Azure SQL Server; TLS enforcement depends on the MSSQL JDBC driver connection string (not visible in application source — expected to be in Azure Key Vault via Azure App Configuration).
- **Claim code**: Stored as plain NVARCHAR. No application-layer hashing or encryption. If intercepted from a log or DB read, the code is immediately usable.
- **No field-level encryption**: PII fields in `claimable_payment` and `recipient_registration` are stored in plaintext.

## Data Flow

```
[External caller (NexPay Recipient Web / IVR BFF / Order Orchestrator)]
        |
        v
[nexpay-claim-code-svc REST API (port 8080)]
        |
        v
[ClaimableControllerApiDelegateImpl]
        |
        +--> [ClaimablePaymentRepository (Spring Data JPA)]
        |           |
        |           v
        |    [nexpay_claimable SQL Server — Azure SQL]
        |
        +--> [RecipientRegistrationRepository]
                    |
                    v
             [nexpay_claimable SQL Server — Azure SQL]

[Hibernate Envers AOP]
        |
        v
[revinfo table in nexpay_claimable]
        (actorId from OTel baggage)

[Azure App Configuration + Key Vault (QA profile)]
        |
        v
[application-qa.yaml: datasource connection string injected at startup]
```

## Data Quality and Retention

- Flyway ensures schema versioning and migration integrity; `baseline-on-migrate: true` in default profile.
- `RecipientRegistration` has **no created/updated timestamps** — no audit trail of when records were inserted or modified at the row level.
- `ClaimablePayment.amount` is INT (cents); no currency code stored — assumes single-currency (USD).
- **No TTL or data retention policy** is configured in the application; lifecycle management of claimed/expired records must be handled externally.
- Seed data in `V4__populate_claimcode_data.sql` and `V5__create_recipient_registration.sql` includes test data; `V5` contains a real employee email address.

## Compliance Gaps

1. **Claim codes logged at INFO level**: `ClaimableControllerApiDelegateImpl.java` line 58 — `log.info("getClaimable: called for claimCode={}", claimCode)` — single-use financial tokens should not appear in application logs.
2. **Employee PII in migration seed data**: `V5__create_recipient_registration.sql` line 40 — `andrew.smirnoff@onbe.com` — PII in version-controlled database migration.
3. **No PII encryption at application layer**: All PII in `recipient_registration` is stored plaintext; relies solely on Azure SQL TDE.
4. **No data retention policy**: Claimed/expired payments and registration records accumulate indefinitely.
5. **DDA field scope unclear**: `claimable_payment.dda` — if this is a card DDA (demand deposit account number), it may require PCI DSS Req. 3 protection.
6. **`RecipientRegistration` lacks timestamps**: Violates data management best practices for GDPR right-to-erasure requests (no way to verify when data was collected).
