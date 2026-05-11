# az-appconfig-demo — Data Architect View

## Data Stores

| Store | Type | Purpose | Evidence |
|---|---|---|---|
| Azure App Configuration | Managed Azure PaaS (key-value store) | Runtime configuration properties and feature flags | `bootstrap.yaml` lines 21–46; endpoint `https://as-app-configuration.azconfig.io` in `compose.yaml` line 19 |
| Azure Key Vault | Managed Azure PaaS (secrets store) | Database password resolution via Key Vault reference | `bootstrap.yaml` lines 62–64; `appsettings.json` lines 7–10 |
| MSSQL Server (`petstore` DB) | Relational (SQL Server) | Target application database (demo/reference) | `appsettings.json` line 3: `r2dbc:mssql://sqlserver:1433/petstore` |
| Log file volume | Docker volume (`log-data`) | Structured application log persistence | `compose.yaml` lines 8–10, 38–40 |

No embedded database (H2, etc.) or in-process data store is present. The application is read-only with respect to configuration data — it consumes configuration, never writes it.

## Schema & Tables

No SQL DDL, JPA entities, Flyway, or Liquibase migrations are present in this repository. The application does not directly own or manage any database schema.

The `DatabaseConfigProperties` record (`DatabaseConfigProperties.java`) carries three fields bound from Azure App Configuration under the prefix `database.cbaseapp`:

| Field | Type | Sensitivity |
|---|---|---|
| `url` | String | Low — connection string (no credential) |
| `username` | String | Medium — database user identity |
| `password` | String | HIGH — database credential |

In the QA `appsettings.json` (`app-config/qa/appsettings.json`):
- `petstore.r2dbc.url` = `r2dbc:mssql://sqlserver:1433/petstore`
- `petstore.r2dbc.username` = `sa` — the SQL Server `sa` (system administrator) account, which is a critical finding (see Compliance Gaps below)
- `db.password` resolved as Key Vault reference name `"mysecret"`
- `r2dbc.pool.validation-query` = `SELECT 2`
- Feature flags: `FeatureA=true`, `FeatureB=false`

## Sensitive Data Handling

- **Database password**: Sourced from Azure Key Vault via a Key Vault reference (`appsettings.json` line 8: `"db.password": "mysecret"`). At runtime, the Azure Spring Cloud SDK resolves the Key Vault secret name and injects the value — it is never written to disk or committed to source control.
- **`toString()` protection**: `DatabaseConfigProperties.java` lines 12–15 override `toString()` to emit only `url` and `username`, explicitly dropping `password`. This prevents Lombok's `@ToString` (not used here) or Spring's default bean inspection from logging the credential.
- **SPN credentials for local dev**: `compose.yaml` line 12 (`env_file: .env`) passes `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET` into the container at runtime. These are not stored in the repository (assumed `.gitignore`'d) but represent a local secret management gap — developers must manually manage `.env` files.
- **No PAN, CHD, or cardholder data**: No evidence of payment card data, account numbers, or other CHD fields in any source file. This repository does not appear to be in-scope for the Cardholder Data Environment (CDE).

## Encryption & Protection

- **In-transit**: All communication with Azure App Configuration and Azure Key Vault is over HTTPS (TLS). Endpoints use `https://` (`compose.yaml` line 19, `bootstrap.yaml` line 22).
- **At-rest (App Config)**: Azure App Configuration provides server-side encryption by default. No customer-managed key configuration is visible in this repository.
- **At-rest (Key Vault)**: Azure Key Vault encrypts secrets at rest using HSM-backed keys. No application-layer encryption is applied.
- **At-rest (logs)**: Log files written to the Docker volume (`/log/appconfigdemo.log`) are unencrypted at the container layer. Volume-level encryption depends on the host/AKS node configuration, which is outside this repository's scope.
- **Token-based push refresh**: `bootstrap.yaml` lines 37–39 configure a push-notification token (`AZURE_APP_CONFIG_PUSH_TOKEN_NAME`, `AZURE_APP_CONFIG_PUSH_TOKEN_SECRET`). The secret is injected via environment variable — not in source — and is used to authenticate inbound webhook calls from Azure Event Grid.

## Data Flow

```
[Azure App Configuration]
       |
       | HTTPS (Managed Identity / SPN)
       | key-filter: "om-audit-logging-api/" or "om-user-api/"
       | label-filter: "<spring.profiles.active>"
       v
[Spring Cloud Azure AppConfig Client]
       |
       | Key Vault Reference resolution
       v
[Azure Key Vault] --> secret value for "db.password"
       |
       v
[DatabaseConfigProperties bean]  <-- url, username (plain), password (resolved from KV)
       |
       v
[AppConfigController] -- logs url + username only (password excluded by toString())
       |
       v
[Log file / stdout]  --> structured JSON (logstash format)
```

Feature flag data follows the same path but terminates at `FeatureManager` (Azure Spring Cloud Feature Management).

Config refresh path:
- **Push**: Azure Event Grid webhook → `/actuator/refresh` endpoint → App Config client re-fetches → beans refreshed.
- **Poll**: Every 15 minutes (configurable via `AZURE_APP_CONFIG_REFRESH_INTERVAL`), client checks sentinel key for version change.

## Data Quality & Retention

- **Log retention**: No log rotation or retention policy is defined within this repository. The Docker volume `log-data` is declared as `external: true` (`compose.yaml` line 39), meaning its lifecycle is managed externally.
- **Structured logging**: `compose.yaml` lines 34–35 configure Logstash JSON format for both console and file output, enabling downstream ingestion by log aggregation platforms (e.g., Splunk, ELK).
- **Config versioning**: Azure App Configuration natively versions key-value pairs. No explicit history or audit trail configuration is set within this repository.
- **No data validation**: No JSR-380 (`@NotNull`, `@Size`, etc.) annotations are applied to `DatabaseConfigProperties` fields. Malformed or missing values will cause runtime failures, not startup-time validation failures.

## Compliance Gaps

1. **`sa` account usage** (`appsettings.json` line 5: `"petstore.r2dbc.username": "sa"`): Using the SQL Server system administrator account for an application connection violates the principle of least privilege. This must not be replicated in production services.
2. **`"mysecret"` Key Vault reference name** (`appsettings.json` line 9): This is a placeholder value. If the QA Key Vault contains an actual secret named `"mysecret"` with a real password, the naming convention is non-descriptive and non-auditable. PCI DSS Req. 8 requires strong credential management practices including meaningful, traceable secret identifiers.
3. **HTTP logging at BODY_AND_HEADERS level** (`bootstrap.yaml` line 14): Azure SDK HTTP responses may include bearer tokens or other credentials in response headers. Logging at this level in production would constitute a secret exposure risk. This must be reduced to `NONE` or `HEADERS` (with token scrubbing) before production deployment.
4. **No field-level validation on `DatabaseConfigProperties`**: Missing `@NotBlank` or `@NotNull` constraints mean a misconfigured or missing App Config key produces a `null` password injected into the application, which may cause obscure runtime failures rather than an explicit startup error.
5. **Log volume encryption not enforced at application layer**: Structured logs may contain usernames and connection strings. Volume-level encryption at the AKS/host layer must be confirmed by the infrastructure team.
