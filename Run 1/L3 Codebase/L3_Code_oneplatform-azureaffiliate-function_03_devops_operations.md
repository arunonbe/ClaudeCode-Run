# DevOps / Operations — oneplatform-azureaffiliate-function

## Build System
- Maven, Java 17 (`java.version=17`).
- `azure-functions-maven-plugin:1.32.0` packages the function app JAR.
- Artifact: `RecipientWebAzureFunctions-1.0.3.jar`.
- Target runtime: Azure Functions v4 (`~4`), Windows OS, Java 17.
- Function app name: `RecipientWebAzureFunctions`.
- Resource group: `java-functions-group` (hardcoded in pom.xml — likely placeholder).
- Region: `westus` (hardcoded in pom.xml).
- Build wrapper: `mvnw` / `mvnw.cmd`.
- `maven-clean-plugin` removes `.NET` `obj/` folder (artifact of Azure Functions tooling residue).
- `host.json`: Azure Functions v2 extension bundle `[4.*, 5.0.0)`, function timeout 5 minutes.

## CI/CD Pipeline
- `.github/workflows/main.yml`: delegates to shared workflow `Onbe/om-ci-setup/.github/workflows/functionapp-workflow.yaml@feature/javafunctionappwf`.
- Triggers: push to `main` and PRs (opened, synchronized, labeled).
- Parameters: `APP_NAME: OmrecipientFunc`, `JAVA_STACK: true`, all other stacks false, `ACCEPTANCE_TESTS: false`, `EXCLUDE_STAGE: false`.
- Shared workflow on **feature branch** (`@feature/javafunctionappwf`) — not a stable release tag.

## Config Management
- All runtime configuration via Azure Function Application Settings (environment variables):
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_SSL_FLAG`
  - `BASE_URL`, `GET_AFFILIATE_DATA_URI`, `POST_PURGE_CONTENT_URI`
  - `AffiliateDBConnectionString`
  - `AzureWebJobsStorage`
  - `KEY_VAULT_NAME`
  - `FRONT_DOOR_NAME`, `FD_ENDPOINT_NAME`
  - `JDBCSqlserverConnectionString`
- Secrets (Redis password, DB credentials) in Azure Key Vault, referenced by name in code.
- `.vscode/settings.json` and `launch.json` present for local development configuration.

## Observability
- **Logging**: `java.util.logging` via `ExecutionContext.getLogger()` — Azure Functions built-in logging, forwarded to Application Insights.
- Log levels used: INFO, SEVERE (on errors), WARNING.
- No distributed tracing integration (no Application Insights SDK calls, no correlation IDs).
- No structured logging format (log messages are plain strings concatenated with data).

## Infrastructure Dependencies
- **Azure Functions v4** runtime (Windows).
- **Azure SQL / SQL Server**: source database with change tracking enabled for SQL trigger bindings.
- **Azure Redis Cache**: Jedis client connection.
- **Azure Blob Storage**: trigger and read/write operations.
- **Azure Key Vault**: secrets retrieval.
- **Azure Front Door**: CDN purge API endpoint.
- **Recipient Web REST API**: `BASE_URL` + `GET_AFFILIATE_DATA_URI` endpoint (unauthenticated HTTP POST).

## Operational Risks
1. **Shared CI on feature branch**: `@feature/javafunctionappwf` is not a stable ref; pipeline behavior can change without notice.
2. **Hardcoded pom.xml deploy config**: `resourceGroup=java-functions-group`, `region=westus` are placeholder values; if the pipeline deploys using these, it will fail or deploy to wrong resource group.
3. **Function timeout 5 minutes**: if a single SQL change batch is large or the downstream REST API is slow, the function may time out and retry, potentially causing duplicate cache updates.
4. **No dead-letter / retry queue for failed SQL trigger events**: if the function throws an exception during SQL trigger processing, Azure Functions may retry the same batch; idempotency of `callRestAPI()` is not guaranteed.
5. **No Application Insights correlation**: without correlation IDs in logs, tracing a specific affiliate change through the system is difficult.
6. **`ACCEPTANCE_TESTS: false`** in CI: no integration or acceptance tests run in the pipeline.
7. **`KeyVaultSecretProvider` singleton not thread-safe**: the `synchronized` block only covers the `null` check; `secretsMap` (a `HashMap`) is accessed from multiple threads without synchronization, creating a race condition.
