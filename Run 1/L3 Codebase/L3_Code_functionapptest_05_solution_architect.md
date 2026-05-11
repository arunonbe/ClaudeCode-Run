# Solution Architect Report — functionapptest

## 1. Complete Class and Method Inventory

### Package: `com.onbe.recipientweb.functions`

| Class | Methods | File |
|---|---|---|
| `Function` | `run(HttpRequestMessage<Optional<String>>, ExecutionContext) → HttpResponseMessage` | `Function.java` |
| `HttpTriggeredAffiliateData` | `run(HttpRequestMessage<Optional<String>>, ExecutionContext) → HttpResponseMessage` | `HttpTriggeredAffiliateData.java` |
| `SqlTriggerBindingAffiliateData` | `run(SqlChangeAffliateItem[], ExecutionContext)`, `processChange(SqlChangeAffliateItem, ExecutionContext)` | `SqlTriggerBindingAffiliateData.java` |
| `SqlTriggerBindingAffiliateData.SqlChangeAffliateItem` (inner) | Lombok `@Getter`/`@Setter`/`@AllArgsConstructor`; `SqlChangeAffliateItem()` | `SqlTriggerBindingAffiliateData.java` |
| `SqlTriggerBindingAffiliateData.SqlChangeOperation` (enum) | `Insert(0)`, `Update(1)`, `Delete(2)` | `SqlTriggerBindingAffiliateData.java` |
| `SqlTriggerBindingAffiliateData.AffiliateItem` (inner) | `iaffiliate_id`, `szaffiliate_short_name`, `iaffiliate_munged_id`, `szaffiliate_virtual_directory` fields | `SqlTriggerBindingAffiliateData.java` |
| `SqlTriggerBindingAffiliateLocaleAffiliate` | (inferred similar pattern to `SqlTriggerBindingAffiliateData`) | `SqlTriggerBindingAffiliateLocaleAffiliate.java` |
| `UpdateBlobData` | (trigger type and method inferred) | `UpdateBlobData.java` |

### Package: `com.onbe.recipientweb.functions.service`

| Class | Methods | File |
|---|---|---|
| `AffiliateCacheService` | `AffiliateCacheService()`, `createRestRequestBody(JSONObject)`, `createRestRequestBody(String)`, `callRestAPI(JSONObject)`, `updateCache(String, JSONObject, ExecutionContext)` | `service/AffiliateCacheService.java` |

### Package: `com.onbe.recipientweb.functions.util`

| Class | Methods | File |
|---|---|---|
| `KeyVaultSecretProvider` | `KeyVaultSecretProvider()` (private), `getInstance()`, `buildSecretClient()`, `getSecret(String)` | `util/KeyVaultSecretProvider.java` |
| `ConstantsAzFunctions` | (constants class — all fields) | `util/ConstantsAzFunctions.java` |

---

## 2. Security Vulnerability Assessment

### VULN-001 — CRITICAL: Redis Authentication Disabled (Commented Out)

**Location**: `AffiliateCacheService.java` lines 71–72

```java
// jedis.auth(keyVaultSecretProvider.getSecret(ConstantsAzFunctions.REDIS_SECRET_NAME));
jedis.connect();
```

**Risk**: Redis connections are established without authentication. Azure Cache for Redis instances should always require authentication (access key or Entra ID). Without authentication:
- Any system that can reach the Redis port can read or write cache entries
- An attacker could poison the affiliate cache to redirect portal users to malicious content
- This violates PCI DSS Requirement 8 (authentication for all system access)

**Remediation**: Uncomment and implement the `jedis.auth()` call. Retrieve the Redis password from Azure Key Vault via the existing `KeyVaultSecretProvider`. Better yet, upgrade to `Jedis 5.x` and use Azure Cache for Redis with Entra ID (token-based) authentication instead of password-based auth. Priority: **CRITICAL — do not deploy to production with auth commented out**.

---

### VULN-002 — HIGH: Anonymous HTTP Trigger Authorization Level

**Location**: `Function.java` line 28; `HttpTriggeredAffiliateData.java` line 33

```java
authLevel = AuthorizationLevel.ANONYMOUS
```

**Risk**: Both HTTP-triggered functions allow anonymous access — no Azure Functions host key, no API key, no identity authentication is required. Any Internet-accessible host (if the function app has a public endpoint) can call these functions and trigger cache operations. The `HttpAffiliateData` function allows cache manipulation by any caller.

**Remediation**: Change `AuthorizationLevel.ANONYMOUS` to `AuthorizationLevel.FUNCTION` (requires Function-level key) or `AuthorizationLevel.ADMIN` for administrative functions. For internal services, consider using Azure API Management as a gateway with client certificate or OAuth 2.0 authentication. Priority: **HIGH**.

---

### VULN-003 — HIGH: Exception Messages Exposed in HTTP 500 Response

**Location**: `HttpTriggeredAffiliateData.java` lines 58–63

```java
return request.createResponseBuilder(HttpStatus.INTERNAL_SERVER_ERROR)
        .body("Exception:" + e.getMessage())
        .build();
```

**Risk**: Internal exception messages, including potential stack traces and internal API URLs, are returned directly to the HTTP caller in the 500 response body. This information can be used by attackers to learn about internal system topology.

**Remediation**: Return a generic error message to the caller. Log detailed error information via the ExecutionContext logger (routed to Application Insights). Priority: **HIGH**.

---

### VULN-004 — HIGH: No SSL/TLS on Redis Connection

**Location**: `AffiliateCacheService.java` line 68

```java
try (Jedis jedis = new Jedis(REDIS_HOST, REDIS_PORT, REDIS_SSL_FLAG)) {
```

**Risk**: While `REDIS_SSL_FLAG` is a configurable boolean, Jedis 2.9.0's SSL support has known limitations. If `REDIS_SSL_FLAG=false`, cache data (affiliate configuration, cache keys) is transmitted in plaintext over the network. Azure Cache for Redis requires SSL on port 6380 for all non-development tiers.

**Remediation**: Ensure `REDIS_SSL_FLAG=true` in all non-local environments and upgrade to Jedis 5.x for proper Azure Cache for Redis TLS support. Priority: **HIGH**.

---

### VULN-005 — MEDIUM: No Cache Entry TTL

**Location**: `AffiliateCacheService.java` line 74

```java
jedis.set(ConstantsAzFunctions.CACHE_AFFILIATE_KEY + inputAffiliate, 
          jsonResponse.getJSONObject(...).toString());
```

**Risk**: Cache entries for deleted or decommissioned affiliates persist indefinitely. If an affiliate is removed from SQL Server (a Delete event is filtered out at `SqlTriggerBindingAffiliateData.java` line 39), the cache entry will serve stale configuration to the portal until the Redis instance is flushed.

**Remediation**: Use `jedis.setex(key, ttlSeconds, value)` with a configurable TTL (e.g., 86400 seconds = 24 hours). Implement a Delete handler in the SQL trigger to explicitly delete the cache key when an affiliate is removed. Priority: **MEDIUM**.

---

### VULN-006 — MEDIUM: KeyVaultSecretProvider In-Memory Cache Has No TTL

**Location**: `KeyVaultSecretProvider.java` lines 15, 47–55

```java
private static Map<String, String> secretsMap = new HashMap<>();
// ...
secretsMap.put(secretName, secret.getValue());
return secret.getValue();
```

**Risk**: Secrets retrieved from Key Vault are cached in a static `HashMap` with no expiry. If a Redis password or other secret is rotated in Key Vault, the function app continues using the old secret until the app is restarted. In a high-availability environment with multiple warm function instances, all instances must be restarted to pick up the rotated secret.

**Remediation**: Add a TTL to the in-memory secret cache (e.g., invalidate after 1 hour) or use the Azure SDK's built-in `SecretCache`. Priority: **MEDIUM**.

---

### VULN-007 — MEDIUM: Delete Operation Not Handled in SQL Trigger

**Location**: `SqlTriggerBindingAffiliateData.java` lines 39–41

```java
if (change.getOperation() != SqlChangeOperation.Update || 
    change.getItem().szaffiliate_virtual_directory == null || 
    change.getItem().szaffiliate_virtual_directory.isEmpty()) {
    return;   
}
```

**Risk**: Insert and Delete operations are silently ignored. New affiliates are not cached until their record is first updated. Deleted affiliates leave stale cache entries. This creates a window where the portal may serve incorrect affiliate configuration.

**Remediation**: 
- For Insert: Call `affiliateCacheService.createRestRequestBody()` and populate cache
- For Delete: Call `jedis.del(CACHE_KEY + affiliate)` to remove the cache entry
Priority: **MEDIUM**.

---

### VULN-008 — LOW: `HttpExample` Placeholder Function in Production Build

**Location**: `Function.java` — `@FunctionName("HttpExample")`

**Risk**: The "Hello World" function is deployed to production alongside business functions. It accepts anonymous requests and echoes back input. While low-risk, it represents unnecessary attack surface and may confuse security scanning tools.

**Remediation**: Delete `Function.java` from the project. Priority: **LOW**.

---

### VULN-009 — LOW: Jedis 2.9.0 (7+ Years Outdated)

**Location**: `pom.xml` line 79

```xml
<dependency>
    <groupId>redis.clients</groupId>
    <artifactId>jedis</artifactId>
    <version>2.9.0</version>
</dependency>
```

**Risk**: Jedis 2.9.0 (released 2017) does not support Redis Cluster, Redis 6+ ACL authentication, or modern TLS configurations. It has known performance limitations for high-throughput scenarios. Current version is 5.x.

**Remediation**: Upgrade to `redis.clients:jedis:5.1.x`. Update `AffiliateCacheService` to use `JedisPool` for connection pooling and the new authentication API. Priority: **LOW** (but prerequisite for VULN-001 resolution).

---

### VULN-010 — LOW: `@Getter`/`@Setter` on Inner Classes May Expose Unintended Fields

**Location**: `SqlTriggerBindingAffiliateData.java` lines 59–67

The `SqlChangeAffliateItem` inner class uses `@AllArgsConstructor` and `@Getter`/`@Setter`. The `AffiliateItem` uses `@AllArgsConstructor` with public fields. Public fields (`iaffiliate_id`, `szaffiliate_munged_id`, etc.) should be private with Lombok-generated accessors.

**Remediation**: Add `@Getter @Setter` to `AffiliateItem` and make fields private. Minor code quality fix. Priority: **LOW**.

---

## 3. Technical Debt Summary

| Debt Item | Severity | Effort |
|---|---|---|
| Redis auth commented out | CRITICAL | LOW — uncomment + rotate credentials |
| Anonymous HTTP auth level | HIGH | LOW — change enum value |
| Exception messages in HTTP 500 | HIGH | LOW — use generic message |
| No Redis SSL enforced | HIGH | LOW — env var config |
| No cache TTL | MEDIUM | LOW — change `set()` to `setex()` |
| No Key Vault secret TTL | MEDIUM | LOW — add TTL to secretsMap |
| Insert/Delete trigger not handled | MEDIUM | MEDIUM — add handler logic |
| Jedis 2.9.0 | LOW | MEDIUM — version upgrade + API changes |
| HttpExample placeholder | LOW | LOW — delete file |
| No CodeQL scanning | HIGH | LOW — add workflow file |
| Stage/Prod CI/CD not configured | HIGH | LOW — add credentials to GitHub secrets |

---

## 4. Remediation Priority Matrix

| Priority | Action | Owner |
|---|---|---|
| P1 — Immediate | Uncomment Redis `jedis.auth()` and rotate Redis password | Dev + Security |
| P1 — Immediate | Change HTTP trigger auth level from ANONYMOUS to FUNCTION | Dev |
| P1 — Sprint 1 | Add CodeQL workflow | DevOps |
| P2 — Sprint 1 | Ensure `REDIS_SSL_FLAG=true` in all environments | DevOps + Dev |
| P2 — Sprint 1 | Replace exception message in HTTP 500 with generic message | Dev |
| P2 — Sprint 2 | Add TTL to Redis cache entries | Dev |
| P2 — Sprint 2 | Add Insert and Delete SQL trigger handlers | Dev |
| P3 — Sprint 3 | Upgrade Jedis to 5.x; implement JedisPool | Dev |
| P3 — Sprint 3 | Add TTL to KeyVaultSecretProvider.secretsMap | Dev |
| P3 — Sprint 3 | Delete `Function.java` (HttpExample) | Dev |
| P4 — Roadmap | Configure stage and prod GitHub Actions credentials | DevOps |
