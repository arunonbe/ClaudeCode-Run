# Data Architect Report — nexpay-cardprocessor-svc

## 1. Data Architecture Overview

`nexpay-cardprocessor-svc` has a **PostgreSQL-backed persistence layer** managed by Flyway migrations. The data model is documented in `docs/DATABASE_ERD.mmd` and implemented as JPA entities in `nexpay-cardprocessor-data-entity`. The service uses Spring Data JPA with Hibernate and Hibernate Envers for audit logging.

## 2. Core Entity Model

### Card Entity (`Card.java`)

The central data entity representing an issued card:

| Field | Type | PCI Classification | Notes |
|---|---|---|---|
| `id` | UUID (v7) | Non-CHD | Time-ordered UUID for B-tree index efficiency |
| `integrationId` | String | Non-CHD | Caller/application identifier |
| `idempotencyKey` | String | Non-CHD | Unique per create request |
| `scopeType` | String | Non-CHD | PROGRAM or REDEMPTION_PRODUCT |
| `externalScopeId` | String | Non-CHD | Program or redemption product ID |
| `processorConfigId` | String | Non-CHD | FK to ProcessorConfig (sticky at issuance) |
| `processor` | String | Non-CHD | THREDD or FIS (denormalized) |
| `processorCardId` | String | Non-CHD | Processor token (`publicToken` for Thredd, `proxyKey` for FIS) — NOT the PAN |
| `currency` | String | Non-CHD | ISO currency code |
| `maskedPan` | String | **CHD — masked PAN** | Format: first 6 / Xs / last 4 (e.g., `411111XXXXXX0000`) |
| `expiryDate` | LocalDate | **CHD — expiry** | Card expiry date (Thredd only; null for FIS) |
| `status` | String | Non-CHD | Card lifecycle status |
| `processorMetadata` | Map (JSONB) | Potentially CHD | Processor-specific response data |

**PCI DSS Assessment of `maskedPan`**: Storing a masked PAN is permitted under PCI DSS (Requirement 3.4 applies to full PAN storage; truncation/masking is an acceptable protection method). The mask format in `docs/API_REQUEST_FLOW.md` shows `411111XXXXXX1234` — first 6 and last 4 digits visible, which is the maximum permitted by PCI DSS.

**PCI DSS Assessment of `processorMetadata` (JSONB)**: This field stores processor-specific response data. For FIS, `FisCreateCardMetadata` stores `cardNum` (the raw card number from `CO_AssignCard_LoadValue.asp` response, per `docs/API_REQUEST_FLOW.md` line 655). The comment states it is "masked and stored in `card.masked_pan`" — but if the raw `cardNum` also persists in `processorMetadata` before masking, this would constitute a PAN storage violation. This requires audit-level verification.

### CardBalance Entity

| Field | Type | Notes |
|---|---|---|
| `card_id` | PK/FK | 1:1 with Card |
| `available_balance` | bigint (minor units) | Spendable balance |
| `gross_balance` | bigint (minor units) | Thredd only |
| `pending_amount` | bigint (minor units) | Thredd only |
| `balance_as_of` | UTC timestamp | Last balance fetch time |

### Job Entity

Tracks asynchronous card creation workflows with `PENDING`/`RUNNING`/`SUCCEEDED`/`FAILED`/`CANCELLED` states.

### ProcessorConfig / ScopeMap / CardProduct Entities

Configuration data describing processor routing:
- `ProcessorConfig`: Versioned issuance profile linking a card product to a processor account
- `ScopeMap`: Maps a program/redemption product to a processor config with time-bounded effectivity
- `ProcessorAccount`: Processor-level account with `defaults_json` (non-secret configuration)
- `CardProduct`: Card type definition (load type, currency, virtual/physical, limits)

## 3. Secret Resolution Pattern

The `ScopeResolver` documentation reveals a `secret_ref_` prefix convention: configuration keys prefixed with `secret_ref_` are resolved by reading environment variables at runtime. This means processor credentials (Thredd `clientsecret`, FIS `password`) are stored as `secret_ref_thredd_clientsecret` in the `defaults_json` or `overrides_json` columns, and the actual values are injected via environment variables sourced from Azure Key Vault.

`app-config/qa/appsettings.json` confirms Key Vault references:
```json
{
  "key_vault_references": {
    "spring.datasource.url": "card-proc-svc-pg-connection-string",
    "processor.fis.uatusername": "fis-uat-username",
    "processor.fis.uatpassword": "[REDACTED — rotate immediately]",
    "processor.fis.uatcertificate": "fis-cert-base64",
    "processor.thredd.uatclientid": "thredd-uat-clientid",
    "processor.thredd.uatclientsecret": "thredd-uat-clientsecret"
  }
}
```

This is the correct pattern: secrets never in the database, never in the repository, always sourced from Key Vault at runtime.

## 4. Hibernate Envers Audit

The `Card` entity is annotated `@Audited` (`Card.java` line 18), which activates Hibernate Envers audit logging. The application.yaml configures:
```yaml
audit_table_suffix: _aud
revision_field_name: rev
revision_type_field_name: revtype
```

This creates a `card_aud` table with revision history for every card state change. This audit trail supports PCI DSS Requirement 10 (logging and monitoring) and provides the immutable record required for financial dispute resolution.

Note: `processorConfig` is annotated `@NotAudited` on the `Card` entity (`Card.java` line 53-55) — the processor configuration association is excluded from audit history to avoid bloat.

## 5. Database Technology

`application.yaml` configures:
- **PostgreSQL** with `PostgreSQLDialect`
- **JSONB** for `processorMetadata` column
- **Flyway** for schema migrations (`flyway.baseline-on-migrate: true`)
- **Connection pooling**: HikariCP (Spring Boot default) with `batch_size: 20`, `fetch_size: 50`

## 6. Data Risks

1. **`processorMetadata` JSONB contains `cardNum` (raw FIS card number)**: If `FisCreateCardMetadata.cardNum` stores the raw card number before masking, this is a PAN storage violation under PCI DSS Req 3.4. The service notes indicate masking happens, but the flow from raw response to stored `cardNum` must be verified.
2. **FIS credentials in payload**: The FIS adapter embeds `UserId` and `Pwd` in every HTTP request body (form-encoded). These credentials flow through the service's memory and TLS channel — confirmed to not appear in application logs (sensitive fields are masked per `docs/API_REQUEST_FLOW.md` line 645), but the credential values in `attributesMap` must not be logged anywhere.
3. **FIS mTLS certificate as Base64 in config**: `processor.fis.uatcertificate: fis-cert-base64` is stored in Azure Key Vault. The PKCS#12 certificate is loaded per-request into an `SSLContext` — this is functionally correct but loading a PKCS#12 from a base64 string per request may be performance-intensive. Certificate caching should be verified.
