# Solution Architect — oneplatform-azureaffiliate-function

## Technical Architecture
- **Language**: Java 17.
- **Framework**: Azure Functions Java SDK (`azure-functions-java-library:3.1.0`), Azure SQL trigger extension (`azure-functions-java-library-sql:2.1.0`).
- **Serverless runtime**: Azure Functions v4, Windows host.
- **Cache client**: Jedis 2.9.0 (Redis client).
- **Blob client**: `azure-storage-blob:12.24.0`.
- **Secret management**: `azure-security-keyvault-secrets:4.8.0` with `azure-identity:1.12.2` (DefaultAzureCredential / ManagedIdentity).
- **Azure Resource Management**: `azure-resourcemanager:2.43.0` (CDN / Front Door purge).
- **Serialization**: Gson 2.10.1, `org.json:20240303`, Jackson (via azure-storage-blob transitive).
- **Utilities**: Lombok 1.18.32.
- **Logging**: `java.util.logging` (JUL) via ExecutionContext — forwarded to Azure Application Insights by the Functions runtime.

## API Surface

### Inbound (triggers)
| Function | Trigger Type | Source |
|---|---|---|
| `SqlTriggerBindingAffiliateData` | SQL Change Trigger | `[dbo].[affiliate]` table |
| `SqlTriggerBindingLocaleAffiliate` | SQL Change Trigger | `[dbo].[affiliate_locale_affiliate]` table |
| `UpdateBlobData` | Blob Trigger | `data/xContent/{folder}/{name}.{extension}` |

### Outbound (HTTP calls)
| Target | Method | Auth |
|---|---|---|
| `BASE_URL + GET_AFFILIATE_DATA_URI + {affiliate}` | POST | None |
| `BASE_URL + POST_PURGE_CONTENT_URI` | POST | None |

## Security Posture

### Authentication / Authorization
- Inbound function triggers are internal (SQL trigger, blob trigger) — no external HTTP auth needed.
- **Outbound REST calls use no authentication** (`AffiliateCacheService.callRestAPI()` and `callPurgeRestAPI()` do not set any Authorization header). This means any network path to the target BASE_URL can call these endpoints without credentials — a security gap.
- Managed Identity used for Key Vault and Azure Resource Manager access (`DefaultAzureCredentialBuilder`). Correct pattern.

### Cryptography
- TLS for Azure SDK connections (Key Vault, Blob Storage, MSSQL) enforced by Azure SDK.
- Redis TLS controlled by `REDIS_SSL_FLAG`; when enabled, Jedis connects with SSL.
- No application-level encryption of cached values.

### Secrets Management
- Redis password, DB user ID, DB password retrieved from Azure Key Vault — correct pattern.
- `KeyVaultSecretProvider` caches secrets in an in-memory `HashMap` for the lifetime of the function instance.
- **Thread-safety issue**: `KeyVaultSecretProvider.getInstance()` uses double-checked locking but `secretsMap` is a plain `HashMap` accessed from multiple Azure Functions threads without synchronization (`UpdateBlobData.java:184` vs `AffiliateCacheService.java:187-199`).
- **No secret rotation**: cached values in `secretsMap` are never refreshed; secret rotation in Key Vault requires function app restart to take effect.

### CVEs and Vulnerable Dependencies

| Dependency | Version | Notes |
|---|---|---|
| `redis.clients:jedis` | 2.9.0 | **Outdated (2018)**. No TLS 1.3 support; known issues with Redis 6+ ACL authentication. CVE-2023-28856 (Jedis DoS via crafted server response) in older versions. |
| `org.mockito:mockito-core` | 2.23.4 | Test-scope only; outdated but not production risk. |
| `junit-jupiter` | 5.4.2 | Test-scope; outdated but not production risk. |

No critical production CVEs in core dependencies (Azure SDK, MSSQL JDBC 12.4.2, Gson 2.10.1 are current).

## Technical Debt
1. **Cache update commented out**: the primary purpose of the SQL trigger functions (updating Redis cache) is disabled in `SqlTriggerBindingAffiliateData.java:49-51` (comment) and `SqlTriggerBindingAffiliateLocaleAffiliate.java:85` (comment). The function currently only calls a REST API with no write to Redis.
2. **`HttpURLConnection` instead of modern HTTP client**: `AffiliateCacheService` uses `java.net.HttpURLConnection` (2001-era API) instead of Java 11's `java.net.http.HttpClient` or a modern library.
3. **No connection pool for JDBC**: `DriverManager.getConnection()` per event in `SqlTriggerBindingAffiliateLocaleAffiliate.getSkinName()` — creates a new TCP connection on every change event.
4. **Jedis 2.9.0**: must be upgraded to Jedis 4.x+ for Redis 6+ ACL and TLS 1.3.
5. **`Thread.sleep()` in retry loop**: blocking an Azure Functions worker thread during retry wait reduces throughput and can cause function timeout.
6. **`e.getStackTrace().toString()` anti-pattern**: `UpdateBlobData.java:186` and `AffiliateCacheService.java:215` log `e.getStackTrace().toString()` which returns the array object reference, not the stack trace string. Correct call is `Arrays.toString(e.getStackTrace())` or pass the exception directly to the logger.

## Gen-3 Migration Requirements
This IS a Gen-3 component. Required improvements to reach production readiness:
1. Re-enable or document the decision to remove Redis cache update in SQL trigger handlers.
2. Add authentication (OAuth2 / managed identity bearer token) to outbound REST API calls.
3. Upgrade Jedis to 4.x and configure TLS 1.3.
4. Replace `HttpURLConnection` with `java.net.http.HttpClient` (Java 11+).
5. Add JDBC connection pooling (HikariCP or Azure SQL connection pool).
6. Fix `KeyVaultSecretProvider.secretsMap` thread-safety (use `ConcurrentHashMap`).
7. Add secret rotation support (periodic re-fetch from Key Vault).
8. Replace `e.getStackTrace().toString()` with proper exception logging.
9. Add structured correlation IDs to log messages for traceability.
10. Pin shared CI workflow to a tagged release, not a feature branch.

## Code-Level Risks (file:line references)
- `SqlTriggerBindingAffiliateData.java:49-51` — `updateCache()` call commented out; cache is not updated by SQL trigger.
- `SqlTriggerBindingAffiliateLocaleAffiliate.java:85` — `updateCache()` call commented out.
- `AffiliateCacheService.java:137` — `url = new URI(BASE_URL.concat(POST_AFFILIATE_DATA_URI).concat(affiliate)).toURL()`: affiliate value from DB is appended directly to URL without URL encoding — URL injection risk.
- `AffiliateCacheService.java:191-193` — Jedis created with `new Jedis(REDIS_HOST, REDIS_PORT, REDIS_SSL_FLAG)`: Jedis 2.9.0 does not accept a boolean SSL flag in this constructor on all versions; behavior may vary.
- `KeyVaultSecretProvider.java:15-16` — `static Map<String, String> secretsMap = new HashMap<>()`: not thread-safe; concurrent Function invocations may cause data corruption.
- `UpdateBlobData.java:186` — `e.getStackTrace().toString()`: logs array object reference, not stack trace content.
- `AffiliateCacheService.java:215` — same anti-pattern: `e.getStackTrace().toString()`.
- `SqlTriggerBindingAffiliateLocaleAffiliate.java:57` — `DriverManager.getConnection()` without pooling.
