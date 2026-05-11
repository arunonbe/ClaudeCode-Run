# DevOps & Operations Report — functionapptest

## 1. Build System

### 1.1 Build Tool

The project uses **Apache Maven** with the Azure Functions Maven plugin for packaging. The POM (`pom.xml`) defines all build configuration.

| Property | Value |
|---|---|
| GroupId | `com.onbe.recipientweb.functions` |
| ArtifactId | `RecipientWebAzureFunctions` |
| Version | `1.0.1` |
| Packaging | `jar` |
| Java Version | 17 |
| Azure Functions Runtime | v4 (`FUNCTIONS_EXTENSION_VERSION=~4`) |

### 1.2 Key Build Plugins

| Plugin | Version | Purpose |
|---|---|---|
| `maven-compiler-plugin` | 3.8.1 | Compile Java 17 source |
| `azure-functions-maven-plugin` | 1.32.0 | Package and deploy Azure Functions |
| `maven-clean-plugin` | 3.1.0 | Clean including `obj/` directory |

### 1.3 Key Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `azure-functions-java-library` | 3.1.0 | Azure Functions Java SDK |
| `azure-functions-java-library-sql` | 2.1.0 | SQL trigger binding |
| `azure-security-keyvault-secrets` | 4.8.0 | Key Vault secret retrieval |
| `azure-identity` | 1.11.4 | DefaultAzureCredential / ManagedIdentity |
| `azure-storage-blob` | 12.24.0 | Blob Storage operations |
| `redis.clients:jedis` | 2.9.0 | Redis client |
| `com.google.code.gson` | 2.10.1 | JSON serialization |
| `org.json` | 20240303 | JSON parsing |
| `lombok` | 1.18.32 | Code generation |
| `mssql-jdbc` | 12.4.2.jre11 | SQL Server JDBC driver |
| `slf4j-api` + `slf4j-simple` | 2.0.12 | Logging |
| `junit-jupiter` | 5.4.2 | Unit testing |
| `mockito-core` | 2.23.4 | Mocking |

### 1.4 Build Command

```bash
mvn clean package
```

The Maven build produces a JAR in the `target/azure-functions/RecipientWebAzureFunctions/` directory, which is then deployed by the Azure Functions Maven plugin.

---

## 2. CI/CD Pipeline

### 2.1 GitHub Actions Workflow (`.github/workflows/azure-functions-app-java.yml`)

The CI/CD pipeline deploys to Azure on every push to the `main` branch:

```yaml
on:
  push:
    branches: ["main"]
```

**Target App Name**: `func-az1-rcpweb-qa-ss` (QA environment only for the `qa` matrix entry; `stage` has no login credentials configured — it will be skipped per line 67: `if: matrix.ENVIRONMENT != 'stage'`)

**Environments**: The matrix defines `[qa, stage, prod]` but only `qa` has `AZURE_CREDENTIALS` configured. Stage and prod deployments appear to be placeholders without active credentials.

**Build Steps**:
1. Checkout code (`actions/checkout@v4`)
2. Set up Java 17 (`actions/setup-java@v1`)
3. `mvn clean package` (PowerShell: `pushd/popd` pattern, line 59–62)
4. Azure CLI login via Service Principal (`azure/login@v1`)
5. Azure Functions Action deploy (`Azure/functions-action@v1`) using Publish Profile secret

**Authentication**: Uses `SERVICE_PRINCIPAL` auth type with `api://AzureADTokenExchange` audience (lines 69–74). The publish profile secret `PUBLISH_PROFILE` is used as the deployment credential.

**Parallel Matrix**: The `max-parallel: 1` setting (line 35) ensures sequential environment deployments.

### 2.2 CodeQL Security Scanning

No CodeQL workflow is visible for this repo, unlike `file-transfer-service_LIB` and `global-deposit-batch_LIB` which have `codeql.yml`. This gap means no static security analysis is running against this function app.

---

## 3. Deployment

### 3.1 Azure Function App Configuration

| Configuration | Value |
|---|---|
| App Name | `func-az1-rcpweb-qa-ss` |
| Resource Group | `java-functions-group` (from `pom.xml` line 143) |
| App Service Plan | `java-functions-app-service-plan` |
| Region | `westus` (`pom.xml` line 148) |
| OS | Windows (`pom.xml` line 158) |
| Java Version | 17 |
| Runtime | Azure Functions v4 |

### 3.2 Runtime Configuration

The function app requires the following Application Settings (environment variables) at runtime:

| Setting | Source | Purpose |
|---|---|---|
| `REDIS_HOST` | App Settings | Redis connection host |
| `REDIS_PORT` | App Settings | Redis port |
| `REDIS_SSL_FLAG` | App Settings | SSL flag for Redis |
| `BASE_URL` | App Settings | Internal REST API base URL |
| `KEY_VAULT_NAME` | App Settings | Azure Key Vault name for secrets |
| `AffiliateDBConnectionString` | App Settings (Key Vault ref) | SQL Server connection string for SQL trigger |
| `FUNCTIONS_EXTENSION_VERSION` | App Settings | `~4` |

These are NOT committed to source control and must be configured in the Azure Portal or via Terraform/Bicep IaC.

### 3.3 Managed Identity

The function app uses `DefaultAzureCredentialBuilder` for Key Vault access, which automatically uses the Function App's system-assigned or user-assigned managed identity when deployed to Azure. This is the correct zero-credential approach for Azure-native services.

---

## 4. Monitoring and Observability

### 4.1 Logging

Logging is done via `ExecutionContext.getLogger()` (Azure Functions built-in logger) which routes to Application Insights. Log statements use `context.getLogger().info()` and `context.getLogger().severe()` for error conditions.

No structured logging format (JSON) is implemented — messages are plaintext concatenations.

### 4.2 No Custom Metrics

There are no custom Application Insights telemetry calls (`TelemetryClient`). The built-in function invocation metrics (execution count, duration, success rate) from Azure Functions will be available via Application Insights, but no business-level metrics (cache hit rates, API call latencies) are captured.

### 4.3 Error Handling

Error handling in `AffiliateCacheService.updateCache()` (lines 77–80) throws a `RuntimeException` on Redis failure, which will cause the function invocation to fail and show up as a failed execution in Application Insights. The SQL trigger will retry on failure according to the SQL trigger binding retry configuration.

In `HttpTriggeredAffiliateData.run()` (lines 58–63), exceptions return HTTP 500 with the exception message. Exception messages may disclose internal API error details.

---

## 5. Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| Redis auth commented out | CRITICAL | See `02_data_architect.md` section 5.1 |
| No production CI/CD credentials | HIGH | Stage and prod deployments not configured |
| No CodeQL scanning | HIGH | No static security analysis |
| Jedis 2.9.0 (outdated) | HIGH | No modern TLS/cluster support |
| No TTL on Redis cache entries | MEDIUM | Stale entries accumulate |
| New Jedis connection per invocation | MEDIUM | TCP overhead at scale |
| HTTP 500 exposes exception messages | MEDIUM | Internal error disclosure |
| `HttpExample` placeholder in production | LOW | Unnecessary attack surface |
| `westus` region in POM | LOW | POM region may not match actual deployment |
