# nexpay-config-test-svc — Solution Architect View

## 1. Current Technical State

This repository is in a **pre-implementation state**. The following table captures what exists versus what is expected based on the NexPay platform conventions:

| Component | Expected | Actual Status |
|---|---|---|
| `pom.xml` (Maven build) | Yes — inherits nexpay-parent | **Missing** |
| `Dockerfile` | Yes — bellsoft/liberica JRE | **Missing** |
| Spring Boot application | Yes | **Missing** |
| `application.yaml` | Yes | **Missing** |
| `application-qa.yaml` | Yes — Azure App Config + Managed Identity DB | **Missing** |
| Flyway migrations | Yes — mirroring config-svc V1–V10 | **Missing** |
| GitHub Actions workflows | Yes — deployment, codeql, dependabot | **Missing** |
| Testcontainers tests | Yes | **Missing** |
| Azure Container App | Yes | **Provisioned** (running placeholder) |
| PostgreSQL `configtest` DB | Yes | **Provisioned** (empty) |
| Azure Managed Identity | Yes | **Provisioned** (msi-nexpay-qa) |
| Azure App Configuration keys | Likely | **Unknown** |

## 2. Intended Technical Architecture (Recommended Design)

Based on the NexPay platform conventions and the stated purpose (international payment config testing), the following architecture is recommended when development begins:

### 2.1 Option A: Thin Shadow of config-svc

The simplest approach: `nexpay-config-test-svc` is a **separate deployment of the same codebase** as `nexpay-config-svc`, pointed at the `configtest` database. This is achieved by:

1. Adding `nexpay-config-svc` as a Git submodule or a shared library dependency.
2. Creating a minimal `pom.xml` that depends on the config-svc artifacts.
3. Using the same `application.yaml` / `application-qa.yaml` with `spring.datasource.url` overriding to `configtest`.

**Pros**: Schema always in sync, no duplicate code maintenance.
**Cons**: Couples deployment cadence to config-svc releases; less flexibility for experimental schemas.

### 2.2 Option B: Independent Service with Shared Schema Library

Create a dedicated `nexpay-config-schema` library that contains Flyway migrations and JPA entities, which both `nexpay-config-svc` and `nexpay-config-test-svc` depend on. Each service has its own Boot module, application config, and test suite.

**Pros**: Independent deployment; allows `config-test-svc` to run experimental migrations (test V11 before it lands in config-svc).
**Cons**: Schema library becomes a shared dependency that requires coordination.

### 2.3 Option C: Test Harness Only (No Database)

`nexpay-config-test-svc` is a lightweight test harness that runs `nexpay-config-svc` in-process (using Testcontainers or Spring `@SpringBootTest`) and drives test scenarios through the API. No separate database needed.

**Recommendation**: Option B is the most flexible for the International Payment track's stated purpose of testing new address formats and modalities before they land in config-svc.

## 3. Security Design Considerations

### 3.1 Remove Managed Identity Vault Access Until Code Is Ready

The most urgent action is to remove or narrow the Key Vault access granted to the Container App's managed identity:

```hcl
# In container-apps/main.tf
# Change from:
role_definition_name = "Key Vault Secrets User"
# To: no assignment until the service has code that reads secrets
```

Or alternatively, the managed identity for `config-test-svc` should be a **separate, dedicated identity** with access only to the `configtest`-specific secrets, not the shared `msi-nexpay-qa` identity.

### 3.2 Separation from CDE Services

The `configtest` database should be explicitly excluded from any CDE scope assessment. Its data classification must be documented: synthetic program data only, no PANs, no production program IDs, no real cardholder data. A formal data classification tag in Azure (`DataClassification: NonProduction`) should be applied to both the Container App and the database.

## 4. Template for application-qa.yaml (Recommended)

When code is committed, the `application-qa.yaml` should follow this pattern:

```yaml
spring:
  config:
    import: optional:azureAppConfiguration
  cloud:
    azure:
      appconfiguration:
        enabled: true
        stores:
          - endpoint: "${AZURE_APP_CONFIG_ENDPOINT}"
            selects:
              - key-filter: "nexpay-config-test-svc/"
                label-filter: "qa"
            trim-key-prefix: "nexpay-config-test-svc/"
      credential:
        managed-identity-enabled: true
        client-id: "${AZURE_CLIENT_ID}"
  datasource:
    username: msi-nexpay-${ENVIRONMENT}
    azure:
      passwordless-enabled: true
    hikari:
      maximum-pool-size: 10   # Lower than config-svc since this is test-only
      connection-init-sql: "SET lock_timeout='10s'; SET statement_timeout='30s';"
      data-source-properties:
        authenticationPluginClassName: >
          com.azure.identity.extensions.jdbc.postgresql.AzurePostgresqlAuthenticationPlugin
```

Note: the App Configuration endpoint for `config-test-svc` is the same `appcg-nexpay-qa.azconfig.io` store but under a different key prefix — this is consistent with the platform pattern.

## 5. Decommission Option

If the International Payment project is on hold or if this service's purpose can be served by the existing `nexpay-config-svc` QA instance, the following infrastructure can be safely removed:

1. Remove `config-test-svc` from `container_apps` in `qa.tfvars`
2. Remove `configtest` from `postgresql_servers.postgresql.databases`
3. Remove `config-test-svc` from `container_app_postgresql_mapping`
4. Remove `configtest` from `postgresql_password_users.readonly.databases`

This would eliminate the Container App, database, and associated Azure costs without affecting any other NexPay services.

## 6. Summary Findings

The `nexpay-config-test-svc` repository is a placeholder with full infrastructure provisioning but no application code. The most significant technical risks are:

1. A container running a demo image with full Key Vault secret access (`msi-nexpay-qa` identity)
2. An empty database incurring storage costs without utility
3. No schema management — the `configtest` database has no Flyway migrations applied
4. No security scanning (no CodeQL, no Dependabot) because no code exists

The recommended path is to either: (a) begin development using Option B (shared schema library) with a concrete timeline from the International Payments project, or (b) decommission the infrastructure until development is ready to begin.
