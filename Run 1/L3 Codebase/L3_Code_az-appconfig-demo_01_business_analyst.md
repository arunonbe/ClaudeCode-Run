# az-appconfig-demo — Business Analyst View

## Business Purpose

`az-appconfig-demo` is an Onbe internal reference/demonstration application. Its stated purpose (README.md line 5–8) is to demonstrate the correct pattern for connecting a Spring Boot microservice to **Azure App Configuration** for configuration properties and feature flags, and to **Azure Key Vault** for secrets management. It is not a production business service but a canonical template that Onbe development teams are expected to copy configuration patterns from when building production services.

The application is deployed into the Onbe platform (QA environment confirmed via `app-config/qa/appsettings.json` and redeploy workflow) and appears to reference the `PetStoreAPI` app-config prefix (`app-config.yml` line 12) and the `om-audit-logging-api` key filter (`compose.yaml` line 22), indicating it doubles as a live integration testbed against real Azure infrastructure.

## Business Capabilities

- **Configuration Distribution**: Demonstrates how microservices consume centralised configuration from Azure App Configuration rather than embedding config in code or environment-variable sprawl.
- **Feature Flag Management**: Demonstrates real-time feature flag evaluation via Azure App Configuration Feature Management (`FeatureA`, `FeatureB` flags evaluated at startup and on a 5-minute scheduled basis — `AppConfig.java` lines 33–38, `AppConfigController.java` lines 29–30).
- **Secret Reference Resolution**: Demonstrates how Key Vault references (`key_vault_references.db.password` in `appsettings.json`) are resolved transparently at runtime without the application holding secret values.
- **Dynamic Refresh**: Demonstrates push-notification and polling-based config refresh (bootstrap.yaml lines 29–44), enabling zero-restart config updates across Onbe services.
- **Reference Architecture Guidance**: README.md explicitly instructs engineers to copy `pom.xml` dependency declarations to ensure correct Spring Cloud Azure library version compatibility with Spring Boot 3.x.

## Business Entities

| Entity | Source | Notes |
|---|---|---|
| `DatabaseConfigProperties` | `DatabaseConfigProperties.java` | Bound to `database.cbaseapp.*`; fields: `url`, `username`, `password` |
| Feature Flags | `appsettings.json`, `AppConfig.java`, `AppConfigController.java` | `FeatureA` (enabled=true in QA), `FeatureB` (enabled=false in QA) |
| App Configuration Store | `bootstrap.yaml` | Azure App Config endpoint supplied via `AZURE_APP_CONFIG_ENDPOINT` |
| Sentinel Key | `bootstrap.yaml` line 32, `compose.yaml` line 27 | `/{app.name}/sentinel` or `database.cbaseapp.username`; triggers config refresh |

The `DatabaseConfigProperties` record (`DatabaseConfigProperties.java`) represents a downstream database connection for `cbaseapp`. In the QA `appsettings.json` the equivalent properties target an MSSQL `petstore` database (`r2dbc:mssql://sqlserver:1433/petstore`), indicating the entity is a stand-in for real Onbe application database config.

## Business Rules & Validations

- **Password excluded from `toString()`**: `DatabaseConfigProperties.java` lines 13–15 — the `toString()` override deliberately omits the `password` field to prevent accidental credential logging. This is a hard-coded defensive rule.
- **Feature flag state is logged at startup and every 5 minutes** — provides auditable evidence of flag state over time (`AppConfig.java` line 33: `@Scheduled(fixedDelay = 5, timeUnit = TimeUnit.MINUTES)`).
- **Non-null API package**: `pig.template` enforces `@NonNullApi` / `@NonNullFields` on generated package-info files, mandating explicit nullability declaration across the codebase.
- **Fail-fast disabled**: `bootstrap.yaml` line 25 sets `fail-fast: false`, meaning the application will start even if Azure App Config is unreachable — a deliberate resilience trade-off.
- **Retry policy fixed**: 5 retries with 10-second delay (`bootstrap.yaml` lines 7–9) before treating Azure connectivity as failed.

## Business Flows

1. **Startup Flow**
   - Spring Boot starts → `bootstrap.yaml` loaded → Azure App Config endpoint resolved from `AZURE_APP_CONFIG_ENDPOINT` env var.
   - Credentials resolved: Managed Identity (qa/stage/prod profiles) or SPN client credentials (local profile).
   - Properties fetched for key-filter/label-filter matching the active Spring profile.
   - Key Vault references resolved transparently by the Azure SDK.
   - `DatabaseConfigProperties` bean populated.
   - `AppConfigController.handleAppStartedEvent()` logs resolved config and feature flag states.

2. **Feature Flag Evaluation Flow**
   - At startup and every 5 minutes, `FeatureManager.isEnabled("FeatureA")` and `isEnabled("FeatureB")` are called.
   - Values come from Azure App Configuration's feature flag store, refreshed per `feature-flag-refresh-interval` (default 15 minutes, 5 minutes in local compose).

3. **Dynamic Config Refresh Flow**
   - A sentinel key change in Azure App Config (push notification via webhook token or 15-minute polling) triggers client-side refresh.
   - Updated `DatabaseConfigProperties` is re-injected without application restart.

4. **HTTP Request Flow**
   - `GET /` → `AppConfigController.index()` → returns static greeting string. No business logic; purely a health/smoke-test endpoint.

## Compliance & Regulatory Concerns

- **PCI DSS Scope**: `DatabaseConfigProperties` holds `password` for a database connection. The password is sourced from Azure Key Vault via a Key Vault reference (`appsettings.json` line 8: `"db.password": "mysecret"`). This is architecturally sound for PCI DSS (secrets not in source control), but the placeholder value `"mysecret"` in the QA config file must not propagate to production Key Vault entries.
- **Credential Logging Prevention**: The `toString()` override in `DatabaseConfigProperties.java` is a direct PCI DSS / data minimisation control. However, `AppConfigController.java` line 28 logs the full `config` object (`log.info("DatabaseConfigProperties: {}", config)`). If `toString()` is correctly overridden, `password` is excluded — but this dependency on correct `toString()` behaviour is fragile.
- **HTTP Logging at BODY_AND_HEADERS level** (`bootstrap.yaml` line 14): Azure SDK HTTP traffic including headers is logged. If any credential or token flows through HTTP headers to Azure endpoints, those may appear in logs. This logging level is appropriate for demo/dev but must be reviewed before any production hardening.
- **Secrets in `.env` file**: `compose.yaml` line 12 references a `.env` file for `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`. The `.gitignore` must exclude `.env`; this should be verified. SPN credentials (`AZURE_CLIENT_SECRET`) represent a high-value secret.

## Business Risks

- **Snapshot dependency in production path**: `pom.xml` line 9 declares parent version `0.0.22-SNAPSHOT`. SNAPSHOT builds are non-deterministic; using SNAPSHOT in a deployed QA environment introduces reproducibility risk.
- **Placeholder QA config (`"mysecret"`)**: `appsettings.json` line 9 contains `"mysecret"` as the Key Vault secret name reference. If this is the literal secret value rather than a Key Vault reference name, it represents a hardcoded credential.
- **Container scan disabled**: `deployment.yml` line 24 sets `CONTAINER_SCAN: false` with comment "container scan frequently fails, so disabling it temporarily" — this suppresses vulnerability detection on the deployed container image.
- **`user: "0:0"` in compose**: `compose.yaml` line 9 runs the container as root, which is a security risk if the container is compromised.
- **No formal test coverage**: `pom.xml` line 47 includes `spring-boot-starter-test` but no test source files were found in the repository. Maven test execution is enabled (`-Dmaven.test.skip=false`), so the build will pass with zero tests.
