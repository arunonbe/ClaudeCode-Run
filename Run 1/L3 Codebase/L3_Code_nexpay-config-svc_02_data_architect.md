# nexpay-config-svc — Data Architect View

## 1. Data Store Inventory

| Store | Type | Purpose | Location (QA) |
|---|---|---|---|
| PostgreSQL (`config` database) | Relational | Canonical program/country/currency config | Azure PostgreSQL Flexible Server, VNet-integrated |
| Redis (Azure Cache for Redis) | In-memory | Idempotency distributed lock + response cache | Azure Cache for Redis (TLS port 6380) |
| Azure App Configuration | Key-value | Runtime config injection (non-secret values + Key Vault refs) | `appcg-nexpay-qa.azconfig.io` |
| Azure Key Vault | Secret store | Database credentials, Redis key, JWT secret | `kv-nexpay-qa` |

## 2. PostgreSQL Database Schema

The schema evolves through 10 Flyway migrations. The logical entity-relationship model is:

```
currencies (1) ──< programs (1) ──< promotions
                       │
                       ├──< program_modality
                       ├──< program_registration
                       └──< program_country_config >── countries (1) ──< country_address_config
                                                                               │
                                                                               └── address_detail
```

### 2.1 Core Tables (V1)

**`countries`**: ISO 3166-1 reference table. Primary key `country_code` (alpha-3). `is_active` flag for lifecycle management. Indexed on `is_active` and `region`.

**`currencies`**: ISO 4217 reference table. `minor_unit` integer (0–4) represents decimal places. `is_fund` distinguishes fund-type currencies from transactional currencies.

**`programs`**: Central entity. `program_id` is an alphanumeric business key (max 20 chars), not a surrogate UUID. Foreign key to `currencies.currency_code`. The non-UUID key design suggests program IDs may be imported from a legacy system (eCount/Atlys).

**`promotions`**: Child of `programs`. Partial unique index prevents more than one `is_default = TRUE` per program (V1, line 106–108).

### 2.2 Audit Tables (V2 — Hibernate Envers)

Envers creates `*_aud` shadow tables for each `@Audited` entity:
- `programs_aud`, `promotions_aud`, `currencies_aud`, etc.
- `revinfo` table: stores revision number, timestamp, `application` (V6), `trace_id` (V6), `source`, `reason` (V10)

The V10 migration renames `application` to `source` and adds `reason` — aligning the audit trail with the `AuditFilter` baggage fields in the BFF layer. This is a deliberate design to create an end-to-end audit chain from HTTP request to database mutation.

### 2.3 Program Extensions (V4)

`program_modality`: Payment modality types per program (prepaid card, ACH, push-to-card, virtual card, global payout). Exact columns in V4 migration (not shown fully but implied by `ProgramModality` entity and `ProgramModalityRepository`).

`program_registration`: Registration flow settings (self-registration enabled, OTP required, verification method). Referenced by `ProgramRegistrationSettingsApi`.

### 2.4 Address Configuration (V7–V9)

`address_detail`: Defines address format rules (field names, validation patterns, required/optional flags) for different address format variants.

`country_address_config`: Maps a country to its address format requirements. Referenced by `CountryAddressConfigApi`.

`program_country_config`: Activates a specific country for a specific program, with optional override of the default country address config. Referenced by `ProgramCountryConfigApi`.

## 3. Database Authentication

The QA environment uses **passwordless authentication** via Azure Managed Identity:

```yaml
# application-qa.yaml lines 61–77
datasource:
  username: msi-nexpay-${ENVIRONMENT}
  azure:
    passwordless-enabled: true
  hikari:
    data-source-properties:
      authenticationPluginClassName: "com.azure.identity.extensions.jdbc.postgresql.AzurePostgresqlAuthenticationPlugin"
```

The managed identity name follows the pattern `msi-nexpay-qa`. The PostgreSQL user is created via the `pgaadauth_create_principal()` function, executed by the `ca-nexpay-pg-setup-qa` Container App Job during infrastructure deployment (`terraform-qa-deploy.yml` lines 177–193). This eliminates static database passwords for the application account.

A `readonly` password-based user is also provisioned (`qa.tfvars` lines 339–345) for read-only tooling access. Its password is stored in Azure Key Vault (`nexpay-sql-password-qa` secret, `kv-secrets.json` line 37).

## 4. Redis Data Model

Redis is used for two purposes:

### 4.1 Idempotency (Platform Library)

Key pattern (from `application.yaml` commented block): `idem:<idempotency-key-hash>`
- TTL: 24 hours (configurable)
- Lock TTL: 30 seconds (distributed lock for in-flight request deduplication)
- `fail-open-on-redis-error: true` — if Redis is down, requests proceed without idempotency. This is the correct default for availability but means duplicate requests may succeed during a Redis outage.

### 4.2 Response Caching

The `application-qa.yaml` references:
- `config-svc:affiliate` — not observed directly but inferred from the pattern in `application-qa.yaml` of `nexpay-config-svc/` key-filter settings in App Configuration. Specific cache key prefixes for config-svc are not defined in the YAML files reviewed, suggesting they are in the App Configuration store.

## 5. Secret and Sensitive Data Inventory

| Secret | Storage | Access Method |
|---|---|---|
| Redis primary access key | Azure Key Vault (`redis-primary-access-key`) | App Configuration Key Vault reference |
| JWT secret (QA) | Azure Key Vault (`jwt-secret-qa`) | App Configuration Key Vault reference |
| PostgreSQL readonly password | Azure Key Vault (`nexpay-sql-password-qa`) | Direct Key Vault reference |
| FIS UAT username/password | Azure Key Vault (`fis-uat-username`, `fis-uat-password`) | App Configuration Key Vault reference |
| FIS certificate (Base64) | Azure Key Vault (`fis-cert-base64`) | App Configuration Key Vault reference |
| Thredd client ID/secret | Azure Key Vault (`thredd-uat-clientid`, `thredd-uat-clientsecret`) | App Configuration Key Vault reference |
| Dynatrace API token | GitHub Secrets → Terraform deploy (not in KV) | TF_VAR_dynatrace_api_token at deploy time |

**Observation**: The config service likely does not directly use FIS or Thredd credentials — those are card processor credentials. They are listed in the shared `kv-secrets.json` because all NexPay platform secrets are loaded into the single `kv-nexpay-qa` vault via the `sync-secrets-to-kv.yml` workflow. This is not a violation but it means the config-svc managed identity could access processor credentials if RBAC is not scoped correctly. The `Key Vault Secrets User` role on the ACA managed identity grants access to **all** secrets in the vault — a violation of least-privilege. Separate Key Vaults per service, or named-secret access policies, should be evaluated.

## 6. Data Migration Strategy

Flyway manages schema evolution (`flyway.baseline-on-migrate: true` in `application.yaml` line 26). The `baseline-on-migrate` flag handles the case where the database already has tables (legacy import scenario). Migrations run at service startup, making the service responsible for its own schema deployment — aligned with the "you build it, you own it" microservices principle.

**Risk**: `V5__Seed_test_data.sql` exists in the production migration path. If this migration has not yet run in production, it will insert synthetic test records on first deployment. This must be removed or conditionally applied (e.g., only if `ENVIRONMENT != prod`).

## 7. Connection Pool Configuration

```yaml
hikari:
  maximum-pool-size: 20
  minimum-idle: 5
  connection-timeout: 20000
  connection-init-sql: "SET lock_timeout='10s'; SET statement_timeout='30s';"
  keepalive-time: 60000
```

The `statement_timeout='30s'` and `lock_timeout='10s'` session-level settings (`application-qa.yaml` lines 71–73) are defensive configurations that prevent long-running queries from monopolising pool connections. These are best-practice settings for a shared PostgreSQL Flexible Server.
