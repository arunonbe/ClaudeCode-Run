# Enterprise Architect Report — functionapptest

## 1. Platform Generation Assessment

`functionapptest` is a **modern cloud-native Azure Functions application** representing the newest generation of Onbe's technology stack. Key indicators:

| Indicator | Evidence |
|---|---|
| Java 17 | `pom.xml` line 14: `<java.version>17</java.version>` |
| Azure Functions v4 runtime | `pom.xml` line 165, `host.json` |
| Azure SDK for Java (BOM 1.2.21) | `pom.xml` lines 82–87 |
| Azure Key Vault integration | `azure-security-keyvault-secrets` 4.8.0 |
| DefaultAzureCredential / ManagedIdentity | `KeyVaultSecretProvider.java` lines 36–43 |
| Lombok annotation processing | `pom.xml` lombok 1.18.32 |
| GitHub Actions CI/CD | `.github/workflows/azure-functions-app-java.yml` |
| JUnit 5 / Mockito testing | `pom.xml` test dependencies |
| `com.onbe` package namespace | Post-Onbe rebranding |

This is a **Generation 3 / cloud-native service**, in stark contrast to the Generation 1 `file-transfer-service_LIB` and Generation 2 `finance-webservice_API` in this same repository set. The codebase was written under the Onbe brand and is designed for Azure deployment.

---

## 2. Role in Enterprise Architecture

### 2.1 Integration Position

This function app is the **caching and event synchronization layer** between the operational database and the cardholder-facing recipient web portal:

```
[SQL Server: dbo.affiliate]
    |
    | SQL Change Feed (Azure Functions SQL Trigger)
    v
[functionapptest: RecipientWebAzureFunctions]  ← This service
    |
    |--→ [Internal REST API (xplatform/affiliate service)]
    |--→ [Redis Cache (Azure Cache for Redis)]
    |--→ [Azure Blob Storage]
    
[Recipient Web Portal]
    |
    | Redis lookup (cache hit)
    v
[Redis Cache]
```

### 2.2 Relationship to Other Repos

Based on the package namespace (`com.onbe.recipientweb.functions`) and the CI/CD target (`func-az1-rcpweb-qa-ss`), this function app is a component of the **Onbe Recipient Web** platform, alongside:
- `nexpay-recipientweb-bff` — Recipient web backend-for-frontend
- `nexpay-recipient-profile-svc` — Recipient profile service
- `xContent-recipient` — Recipient content management

The `functionapptest` name appears to be a working/development name for what is functionally the `RecipientWebAzureFunctions` service.

---

## 3. Architecture Patterns

### 3.1 Event-Driven Cache Synchronization

The SQL trigger pattern implements **Change Data Capture (CDC) at the application layer** — a modern event-driven approach where database changes automatically propagate to cache without polling. This aligns with Onbe's apparent architectural direction toward event-driven microservices.

### 3.2 CQRS-Adjacent Pattern

The separation of the SQL write path (affiliate management) from the Redis read path (portal lookup) is consistent with a **Command Query Responsibility Segregation (CQRS)** pattern, where writes go to SQL and reads come from Redis.

### 3.3 Singleton Secret Provider Pattern

`KeyVaultSecretProvider` uses a double-checked locking singleton (`KeyVaultSecretProvider.java` lines 25–31) with in-memory caching of secrets. This is functionally correct for Azure Functions with warm instances but has a potential race condition on cold start if multiple function invocations start simultaneously (the `synchronized` block at line 28 mitigates this).

---

## 4. Fit / Gap Analysis Against Onbe Target Architecture

| Dimension | Current State | Gap / Assessment |
|---|---|---|
| Runtime | Azure Functions v4, Java 17 | ALIGNED — current generation |
| Authentication | Managed Identity + Key Vault | ALIGNED — no secrets in code |
| CI/CD | GitHub Actions | ALIGNED — but prod credentials missing |
| Observability | Application Insights (built-in) | PARTIAL — no custom metrics |
| Redis | Jedis 2.9.0, no auth, no TTL | GAP — outdated client, security gap |
| Error handling | RuntimeException propagation | GAP — no dead-letter / retry strategy |
| Testing | JUnit 5 / Mockito available | GAP — no tests visible in main code |
| Security scanning | No CodeQL | GAP — no static analysis |
| SQL trigger | Only Update events processed | GAP — Insert/Delete not handled |

---

## 5. Dependencies

| Dependency | Type | Risk Level |
|---|---|---|
| Azure Functions SQL binding (`azure-functions-java-library-sql`) | Azure SDK | LOW — actively maintained |
| Azure Cache for Redis (Jedis 2.9.0) | Infrastructure + client | HIGH — outdated client |
| Azure Key Vault + Managed Identity | Azure infrastructure | LOW — correct pattern |
| Internal REST API (`BASE_URL`) | Internal microservice | MEDIUM — single point of failure if API is unavailable |
| Azure SQL Server (`[dbo].[affiliate]`) | Database | MEDIUM — shared with other services |
| Azure Blob Storage | Storage | LOW |

---

## 6. Migration Complexity Assessment

Migration complexity is rated **LOW** for the following reasons:

1. **Cloud-native**: No on-premise dependencies. All infrastructure is Azure.
2. **Modern Java 17**: No legacy API or framework constraints.
3. **Modular**: The function app is small (6 main classes) with clear separation of concerns.
4. **Key Vault ready**: The secret management pattern is already correct.

Primary improvement actions are not migrations but **upgrades and security fixes**:
- Upgrade Jedis to 5.x and enable Redis authentication
- Add CodeQL scanning
- Configure prod/stage CI/CD credentials
- Remove `HttpExample` placeholder
- Handle SQL trigger Insert and Delete operations

---

## 7. Lifecycle Recommendation

This service is **in active use** (CI/CD deploys to `func-az1-rcpweb-qa-ss`) and represents the correct architectural direction for Onbe. It should be:

1. **Renamed**: Remove the `test` suffix from the repository name to reflect its operational status
2. **Hardened**: Address the Redis authentication gap and Jedis upgrade
3. **Completed**: Implement Insert and Delete trigger handling
4. **Monitored**: Add custom Application Insights metrics for cache hit/miss rates
5. **Tested**: Write unit tests for `AffiliateCacheService`, `KeyVaultSecretProvider`, and the trigger handlers
