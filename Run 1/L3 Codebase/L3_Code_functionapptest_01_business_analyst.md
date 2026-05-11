# Business Analyst Report — functionapptest

## 1. Executive Summary

`functionapptest` is a **Java Azure Functions application** that acts as a real-time cache synchronization service for affiliate configuration data on the Onbe recipient web platform. Despite its name suggesting a test or sandbox role, the repository contains a GitHub Actions CI/CD pipeline that deploys to a named Azure Function App (`func-az1-rcpweb-qa-ss`) in the QA environment, indicating it is operational infrastructure — not merely a test harness.

The application is part of the `com.onbe.recipientweb.functions` namespace, version `1.0.1`, and is targeted at Java 17 with Azure Functions runtime v4. It bridges the `[dbo].[affiliate]` SQL Server table and a Redis cache cluster, ensuring that affiliate configuration data served to the recipient-facing web portal is kept current.

---

## 2. Business Capabilities

### 2.1 Defined Azure Functions

| Function Name | Trigger Type | Class | Business Purpose |
|---|---|---|---|
| `HttpExample` | HTTP GET/POST (Anonymous) | `Function.java` | Baseline "Hello World" test function — not a business function |
| `HttpAffiliateData` | HTTP POST (Anonymous) | `HttpTriggeredAffiliateData.java` | Manually trigger cache refresh for a specific affiliate |
| `SqlTriggerBindingAffiliateData` | SQL Change Feed on `[dbo].[affiliate]` | `SqlTriggerBindingAffiliateData.java` | Automatically refresh cache when affiliate record is updated in SQL Server |
| `SqlTriggerBindingAffiliateLocaleAffiliate` | SQL Trigger (inferred from filename) | `SqlTriggerBindingAffiliateLocaleAffiliate.java` | Automatically refresh cache on affiliate locale changes |
| `UpdateBlobData` | (inferred trigger type) | `UpdateBlobData.java` | Update Azure Blob Storage when affiliate data changes |

### 2.2 Affiliate Cache Synchronization

The core business capability is **real-time affiliate configuration cache management**:

1. When an affiliate record is updated in the `[dbo].[affiliate]` SQL table, the SQL trigger function fires automatically
2. The function calls a REST API (`BASE_URL` + `/affiliate` endpoint) to retrieve current affiliate data
3. The enriched JSON response is stored in Redis cache under the key `CACHE_AFFILIATE_KEY + affiliateVirtualDirectory`
4. The recipient web portal reads from Redis cache for fast affiliate configuration lookup

This eliminates the need for direct database queries on every affiliate configuration lookup from the web portal, improving performance and reducing database load.

### 2.3 HTTP-Triggered Manual Refresh

The `HttpAffiliateData` function provides an **on-demand cache refresh** capability (`HttpTriggeredAffiliateData.java`). Operators or automated tools can POST a JSON body containing an affiliate identifier to force a cache update without waiting for a SQL change event.

### 2.4 Blob Storage Update

The `UpdateBlobData.java` function updates Azure Blob Storage, suggesting that affiliate configuration data is also persisted to blob for downstream consumption (e.g., static site generation, CDN pre-warming, or configuration file distribution).

---

## 3. Business Context: Recipient Web Platform

The function app belongs to the `com.onbe.recipientweb` namespace, situating it within **Onbe's recipient web portal** — the cardholder-facing web application where payment recipients access their disbursements. Affiliate configuration controls how the portal appears and behaves for different client programs (branding, available features, locale settings).

The `[dbo].[affiliate]` table contains:
- `iaffiliate_id` — numeric affiliate identifier
- `szaffiliate_short_name` — short name/code
- `iaffiliate_munged_id` — obfuscated/hashed identifier
- `szaffiliate_virtual_directory` — virtual directory path (the primary routing key for the web portal)

The `szaffiliate_virtual_directory` value is the key by which the web portal routes requests to the correct affiliate configuration.

---

## 4. Regulatory Relevance

### 4.1 PCI DSS

While this function app does not directly handle PANs or SAD, it manages affiliate configuration that controls the cardholder web portal:
- **Requirement 6.3** (Secure development): Azure Functions deployments should follow secure SDLC practices
- **Requirement 6.4** (Web-facing application protection): The portal driven by this configuration is cardholder-facing and must be protected
- **Requirement 8.6** (Authentication for service accounts): The function app uses Azure Managed Identity for Key Vault access — which is the correct approach for PCI DSS service account management

### 4.2 GDPR / CCPA

The affiliate table referenced (`[dbo].[affiliate]`) and the REST API calls may involve processing of configuration data that includes cardholder portal routing logic. If affiliate data maps to client programs that serve European or California residents, appropriate data handling policies must be applied.

---

## 5. Operational Impact

| Scenario | Impact |
|---|---|
| Redis cache stale | Recipients see outdated affiliate portal configuration (wrong branding, features, locale) |
| Redis connection failure | Cache update fails silently; portal may fall back to direct DB or serve stale data |
| SQL trigger backlog | Cache updates delayed; SQL change feed may accumulate a queue |
| Function App cold start | First request after inactivity has latency; portal routing may be slow |

---

## 6. Known Gaps

1. **The `HttpExample` function** (`Function.java`) is a boilerplate "Hello World" function that should be removed from production code. It accepts anonymous HTTP requests and echoes the input name — it has no business purpose and represents an unnecessary attack surface.

2. **Redis authentication is commented out** in `AffiliateCacheService.java` lines 71–72:
   ```java
   // jedis.auth(keyVaultSecretProvider.getSecret(ConstantsAzFunctions.REDIS_SECRET_NAME));
   ```
   This means Redis connections are made **without authentication**. This is a significant security gap if the Redis instance is not otherwise protected.

3. **SQL trigger only fires on Update operations** — Insert and Delete operations are filtered out (`SqlTriggerBindingAffiliateData.java` line 39): `if (change.getOperation() != SqlChangeOperation.Update ...`. New affiliate records added to the database will not have their cache populated automatically until the first manual trigger or the record is subsequently updated.
