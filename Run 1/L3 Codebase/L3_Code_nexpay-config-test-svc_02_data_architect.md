# nexpay-config-test-svc — Data Architect View

## 1. Data Store Inventory

Despite the minimal repository content, the IaC provisions the following data infrastructure for this service:

| Store | Type | Details | Status |
|---|---|---|---|
| `configtest` PostgreSQL database | Relational | On shared `postgresql` Flexible Server | Provisioned, no schema applied |
| Azure App Configuration | Key-value | Keys under `nexpay-config-test-svc/` label `qa` | Provisioned via `appcg-nexpay-qa.azconfig.io` |
| Azure Key Vault | Secret store | Shared `kv-nexpay-qa` | Access granted via managed identity |

## 2. PostgreSQL Database Configuration

### 2.1 Database Provisioning (from `qa.tfvars`)

```hcl
databases = {
  configtest = {
    collation = "en_US.utf8"
    charset   = "UTF8"
  }
}
```

The `configtest` database is created as a peer of `config`, `cardprocessor`, `recipientprofile`, and `recipientauth` on the same PostgreSQL Flexible Server (`postgresql` in QA). It shares the server's resource limits (burstable `B_Standard_B1ms` SKU, 32GB storage) with all other NexPay databases.

### 2.2 Authentication and Access

From `container_app_postgresql_mapping` (`qa.tfvars` lines 332–336):
```hcl
"config-test-svc" = {
  postgresql_server_key = "postgresql"
  database_key          = "configtest"
  use_managed_identity  = true
}
```

The Container App managed identity (`msi-nexpay-qa`) is granted access to the `configtest` database via the Entra ID `pgaadauth_create_principal()` role provisioning job. This is consistent with the passwordless authentication pattern used across all NexPay services.

Additionally, the `readonly` password-based user has SELECT access to `configtest` (`postgresql_password_users` in `qa.tfvars` line 343), enabling read-only tooling or monitoring queries.

### 2.3 Current Schema State

No application code means no Flyway migrations have run. The `configtest` database exists but is empty — only the PostgreSQL system catalog tables are present. The placeholder Container App image (`mcr.microsoft.com/azuredocs/containerapps-helloworld:latest`) does not connect to the database.

## 3. Intended Data Model (Inferred)

Given the service's stated purpose as a test companion to `nexpay-config-svc`, the intended schema is likely identical to or a subset of the `config` database schema (V1–V10 migrations). The data model would therefore include:

- `countries`, `currencies` (reference data)
- `programs`, `promotions` (test programs with synthetic IDs)
- `program_modality`, `program_registration`
- `address_detail`, `country_address_config`, `program_country_config`
- Hibernate Envers audit tables (`*_aud`, `revinfo`)

The key difference from the production `config` database would be the data content: `configtest` would contain synthetic test programs rather than real client programs.

## 4. Data Isolation and Test Data Strategy

### 4.1 Why a Separate Database (Not Separate Schema)?

Using a separate database (rather than a separate PostgreSQL schema within the same database) provides stronger isolation:
- Separate connection pools — a runaway test cannot exhaust the `config` database's connections
- Independent Flyway versioning — `configtest` can run experimental migrations without affecting `config`
- Separate backup/restore — test data can be reset without touching production config data

### 4.2 Data Seeding Strategy (Recommended)

For the service to fulfil its testing purpose, a repeatable data seeding strategy is needed:
1. A `V5__Seed_test_data.sql` (analogous to the one in `nexpay-config-svc`) should seed test programs with clearly synthetic IDs (e.g., `TEST-PROG-001`).
2. An optional reset mechanism (Flyway clean + re-migrate) should be available for CI/CD test runs that need a clean slate.
3. No real client program IDs, real PANs, or real cardholder data should ever be inserted.

### 4.3 PCI DSS Non-Production Data Requirements

PCI DSS Requirement 6.3.4 prohibits using live PANs for testing. If `configtest` ever receives data derived from production:
- All PANs must be masked (first 6/last 4 only)
- Cardholder names must be replaced with synthetic values
- Account numbers must be tokenised or masked

Given the current empty state, this is not an immediate risk. However, when the International Payment project begins seeding test data, a data masking policy must be in place before any production-derived data is used.

## 5. Azure App Configuration Integration (Expected)

When application code is committed, the service will likely follow the same App Configuration pattern as `nexpay-config-svc`:

```yaml
spring:
  cloud:
    azure:
      appconfiguration:
        stores:
          - endpoint: "${AZURE_APP_CONFIG_ENDPOINT}"
            selects:
              - key-filter: "nexpay-config-test-svc/"
                label-filter: "qa"
```

The `nexpay-config-test-svc/` key namespace in App Configuration is likely either empty or will mirror `nexpay-config-svc/` keys with test-environment overrides (e.g., different downstream service endpoints pointing to mock services).

## 6. Data Architecture Risks

| Risk | Description | Severity |
|---|---|---|
| Empty database with provisioned infrastructure | No schema applied; database is a cost centre without utility | Medium |
| Shared server with production-adjacent databases | A schema migration error in `configtest` Flyway run could exhaust server connections or corrupt shared WAL logs | Medium |
| Managed identity overpermission | `msi-nexpay-qa` has `configtest` access plus all other databases | Medium — see config-svc analysis |
| No data retention policy defined | Without a retention policy, the `configtest` database could accumulate unbounded test data | Low |

## 7. Recommendations

1. **Define schema ownership**: Confirm whether `configtest` will use the `nexpay-config-svc` Flyway migrations or a separate migration set. Document this decision in the README.
2. **Add database tags**: Tag the `configtest` database in Azure with `Purpose: IntegrationTesting` and `DataClassification: Synthetic` to distinguish it from business-data databases.
3. **Implement a reset job**: Create a Container App Job that can drop and recreate the `configtest` schema on demand for CI/CD pipeline use.
4. **Establish data masking policy**: Before any real program IDs or client data are used in tests, establish a documented data masking/anonymisation procedure.
