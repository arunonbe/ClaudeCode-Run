# nexpay-config-test-svc — Business Analyst View

## 1. Service Purpose

`nexpay-config-test-svc` is described in its `README.md` as:

> "A playground/test service used in the International Payment project for testing purposes only."

This is a dedicated test service for the NexPay International Payment (global payout) track. Its primary business function is to provide a controlled environment for validating configuration behaviour without affecting production or QA program configurations managed by `nexpay-config-svc`.

Despite the minimalist repository content (only `README.md` and `.gitignore` are present), the service is fully provisioned in the QA Azure environment, as confirmed by multiple infrastructure references:

- `qa.tfvars` line 128–139: Container App `config-test-svc` is provisioned with identical resource sizing to `config-svc` (0.25 vCPU, 0.5Gi memory, `internal` only).
- `qa.tfvars` line 335: A dedicated `configtest` PostgreSQL database is created and mapped to this service.
- `container_app_postgresql_mapping` line 332–336: The service uses Managed Identity (`use_managed_identity: true`) for database access.
- The `postgresql_password_users.readonly` configuration (line 339–345) includes `configtest` in the list of databases the readonly user can access.

## 2. Business Context — International Payments

The "International Payment project" likely refers to Onbe's global payout capability, which enables disbursements to recipients in non-US markets. This involves:

- Multi-currency support (ISO 4217 currency data is already in `nexpay-config-svc`)
- International address format validation (the `country_address_config` and `address_detail` tables in `nexpay-config-svc` were added specifically for international address handling — V7, V8, V9 migrations)
- OFAC/sanctions screening for international recipients
- Cross-border transfer compliance (PIPEDA, GDPR, Quebec Law 25 for Canadian recipients; local payment regulations for other regions)

The config-test-svc likely mirrors or shadows the config-svc schema and API to allow testing of international-specific configuration scenarios (e.g., adding a new country, configuring country-specific address formats) without polluting the main QA configuration database that other QA tests depend on.

## 3. Relationship to nexpay-config-svc

The service's database is `configtest` on the same PostgreSQL server as `config` (`postgresql` server in `qa.tfvars`). This suggests:
- Same schema (likely) — Flyway migrations would be sourced from `nexpay-config-svc` or a shared module.
- Separate data — test programs and test configurations that do not conflict with QA integration test data.
- Independent lifecycle — can be reset or reloaded without affecting QA runs that depend on `nexpay-config-svc`.

## 4. Likely Use Cases

Based on the naming convention and context:

1. **International address format testing**: Validate that new country address configurations (V8, V9 migrations) correctly enforce address validation rules for a new target country before releasing to the main config service.
2. **Program modality testing**: Test enabling a new payment modality for international programs (e.g., SEPA, SWIFT, local wallet) against a disposable configuration without risk to existing QA data.
3. **Regression testing harness**: The `nexpay-config-test-svc` may be the service-under-test for `qa-api-test-automation` regression suites targeting the international payment flow.
4. **Data migration validation**: Test Flyway migration scripts against a production-like PostgreSQL configuration before applying to `nexpay-config-svc`.

## 5. Business Risks and Observations

### 5.1 Near-Empty Repository

The repository contains only two files (`README.md`, `.gitignore`). This means:
- No application code has been committed. The Container App is running the placeholder image `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest` (from `qa.tfvars` line 130) — a Microsoft demo image, not a NexPay application.
- The `configtest` PostgreSQL database exists but has no application-managed schema (no Flyway migrations would have run).

This is a **dormant but provisioned service** — infrastructure resources are being consumed (Container App, database storage, private DNS) without an active workload.

**Business risk**: If this service is listed in APIM catalogues or referenced in integration tests, the placeholder image will return unexpected responses, causing test failures or misleading data.

### 5.2 Infrastructure Cost

The Container App (min 1 replica, Consumption) and the `configtest` PostgreSQL database (32GB storage) represent real Azure costs in QA even with no application code. If the service is not actively used, consider scaling to 0 replicas and suspending database billing until development begins.

### 5.3 Data Classification

The `configtest` database should be explicitly classified as "non-production test data" with no real PAN, cardholder data, or live program IDs. If test programs are created by seeding data from production snapshots, PCI DSS Requirement 3.3.2 (masking of PAN in non-production environments) applies.

## 6. Recommended Actions

1. **Confirm project status**: Determine whether the International Payment project is active and when this service will receive application code. If shelved, remove infrastructure provisioning to reduce cost and attack surface.
2. **Document intended schema**: Add the `nexpay-config-svc` as a dependency and document the intended Flyway migration path for `configtest`.
3. **Add data classification tag**: Tag the `configtest` database in Azure with `DataClassification: TestData` to distinguish it from the production `config` database.
