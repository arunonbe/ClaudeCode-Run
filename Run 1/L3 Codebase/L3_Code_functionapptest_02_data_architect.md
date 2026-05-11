# Data Architect Report — functionapptest

## 1. Data Entities

### 1.1 Affiliate SQL Entity (`[dbo].[affiliate]`)

The primary SQL entity watched by this function app is defined in the `SqlChangeAffliateItem.AffiliateItem` inner class (`SqlTriggerBindingAffiliateData.java` lines 80–86):

| Field | Type | Description |
|---|---|---|
| `iaffiliate_id` | String (numeric) | Affiliate primary key |
| `szaffiliate_short_name` | String | Short affiliate name/code |
| `iaffiliate_munged_id` | String | Obfuscated/hashed affiliate ID |
| `szaffiliate_virtual_directory` | String | Virtual directory path (portal routing key) |

The SQL trigger connection is configured via `AffiliateDBConnectionString` application setting (`SqlTriggerBindingAffiliateData.java` line 24).

### 1.2 Change Event Entity

The `SqlChangeAffliateItem` class (`SqlTriggerBindingAffiliateData.java` lines 62–68) wraps the affiliate item with a change operation indicator:

| Field | Type | Values |
|---|---|---|
| `Operation` | `SqlChangeOperation` enum | `Insert` (0), `Update` (1), `Delete` (2) |
| `Item` | `AffiliateItem` | The changed affiliate record |

### 1.3 Redis Cache Data

Data written to Redis via `AffiliateCacheService.updateCache()` (`AffiliateCacheService.java` lines 65–81):

| Key Pattern | Value |
|---|---|
| `CACHE_AFFILIATE_KEY + affiliateVirtualDirectory` | JSON string from `jsonResponse[SUCCESS_RESPONSE][AFFILIATE_KEY]` |

The `CACHE_AFFILIATE_KEY` constant is defined in `ConstantsAzFunctions.java`. The value is the enriched affiliate configuration JSON retrieved from the internal REST API.

### 1.4 REST API Data

The function calls an internal REST API at `BASE_URL + AFFILIATE_URI` with a POST body:
```json
{ "<INPUT_AFFILIATE_KEY>": "<affiliateVirtualDirectory>" }
```

The response is a JSON object containing a `SUCCESS_RESPONSE` object with an `AFFILIATE_KEY` sub-object. The full schema of this response is determined by the internal REST service, not by this function app.

---

## 2. Data Storage Systems

| Storage System | Role | Connection |
|---|---|---|
| Azure SQL Server (`[dbo].[affiliate]`) | Source of truth for affiliate configuration | `AffiliateDBConnectionString` app setting |
| Redis Cache | High-performance cache for portal lookup | `REDIS_HOST`, `REDIS_PORT`, `REDIS_SSL_FLAG` env vars |
| Azure Key Vault | Secrets storage | `KEY_VAULT_NAME` env var; DefaultAzureCredential |
| Azure Blob Storage | Persistent affiliate data store | `azure-storage-blob` SDK (UpdateBlobData function) |
| Internal REST API | Affiliate data enrichment service | `BASE_URL` env var |

---

## 3. Configuration and Secrets Management

### 3.1 Environment Variables

The following environment variables are consumed at runtime (`AffiliateCacheService.java` lines 23–27; `KeyVaultSecretProvider.java` line 21):

| Variable | Consumer | Sensitivity |
|---|---|---|
| `REDIS_HOST` | `AffiliateCacheService` | MEDIUM — Redis hostname |
| `REDIS_PORT` | `AffiliateCacheService` | LOW — port number |
| `REDIS_SSL_FLAG` | `AffiliateCacheService` | LOW — boolean |
| `BASE_URL` | `AffiliateCacheService` | MEDIUM — internal API base URL |
| `KEY_VAULT_NAME` | `KeyVaultSecretProvider` | MEDIUM — Key Vault name |
| `AffiliateDBConnectionString` | Azure Functions SQL binding | HIGH — database credentials |

### 3.2 Key Vault Integration

`KeyVaultSecretProvider.java` implements a singleton pattern for Key Vault secret retrieval:
- Uses `DefaultAzureCredentialBuilder` with fallback to `ManagedIdentityCredentialBuilder` (`KeyVaultSecretProvider.java` lines 36–43)
- Caches secrets in a `HashMap<String, String>` in memory — no TTL/expiry
- Vault URL constructed as `https://<KEY_VAULT_NAME>.vault.azure.net` (line 35)

**Note**: The Redis authentication call is commented out (`AffiliateCacheService.java` lines 71–72), so Key Vault secrets for Redis are **not currently used**, even though the infrastructure for Key Vault access exists. This is a security gap.

---

## 4. Data Flow

```
[SQL Server: dbo.affiliate (UPDATE)]
    |
    | Azure Functions SQL Trigger binding
    v
[SqlTriggerBindingAffiliateData.run()]
    |
    | Filter: Operation == Update AND szaffiliate_virtual_directory != null
    v
[AffiliateCacheService.createRestRequestBody(affiliate)]
    |
    | HTTP POST to BASE_URL + AFFILIATE_URI
    v
[Internal REST API]
    |
    | JSON response
    v
[AffiliateCacheService.callRestAPI()]
    |
    | jedis.set(CACHE_KEY + affiliate, jsonResponse[SUCCESS][AFFILIATE].toString())
    v
[Redis Cache]
    |
    | (Also: UpdateBlobData writes to Azure Blob)
    v
[Azure Blob Storage]
```

Manual refresh path:
```
[HTTP POST to /api/HttpAffiliateData]
    |
    | JSON body with affiliate identifier
    v
[HttpTriggeredAffiliateData.run()]
    → same flow as above from AffiliateCacheService
```

---

## 5. Data Sensitivity Assessment

| Data Element | Classification | Notes |
|---|---|---|
| `szaffiliate_virtual_directory` | INTERNAL | Portal routing key — business-sensitive |
| `iaffiliate_id` | INTERNAL | Numeric identifier |
| `iaffiliate_munged_id` | INTERNAL | Obfuscated identifier |
| Redis cache entries | INTERNAL | Affiliate config JSON |
| Azure SQL connection string | CREDENTIAL | HIGH — must be in Key Vault |
| REST API response data | INTERNAL | Enriched affiliate config |

### 5.1 Redis Authentication Gap

The Redis authentication call is commented out in `AffiliateCacheService.java`:

```java
// jedis.auth(keyVaultSecretProvider.getSecret(ConstantsAzFunctions.REDIS_SECRET_NAME));
jedis.connect();
```

If the Azure Cache for Redis instance is configured to require authentication (as it should be in any PCI DSS or SOC 2 compliant environment), this code will fail at the `jedis.connect()` call. Conversely, if the Redis instance has no authentication configured, that is a security misconfiguration.

**This gap must be resolved before production hardening.** The commented-out code suggests it was intentionally disabled during development, likely because the test Redis instance has no password.

---

## 6. Redis Data Architecture Concerns

### 6.1 No TTL on Cache Entries

`AffiliateCacheService.updateCache()` calls `jedis.set()` with only a key and value — no TTL is specified. This means cached affiliate entries never expire. If an affiliate record is deleted from SQL Server, its cache entry persists indefinitely (since Delete operations are filtered out of the trigger). This can lead to stale configuration being served even after an affiliate is decommissioned.

**Remediation**: Use `jedis.setex(key, ttlSeconds, value)` to set an appropriate TTL (e.g., 24 hours), or implement a cache invalidation handler for Delete operations.

### 6.2 Jedis Version 2.9.0 (Outdated)

The `redis.clients:jedis:2.9.0` dependency (`pom.xml` line 79) is from 2017. Current Jedis is 5.x. Version 2.9.0 does not support Redis Cluster mode, Redis 6+ ACL-based authentication, or modern TLS certificate validation. This limits the ability to use Azure Cache for Redis Enterprise tier features.

### 6.3 No Connection Pooling

A new `Jedis` instance is created per invocation (`AffiliateCacheService.updateCache()` lines 68–76: `try (Jedis jedis = new Jedis(...))`). For high-frequency cache updates, this creates TCP connection overhead on every function invocation. A `JedisPool` should be used instead.
