# Business Analyst — oneplatform-azureaffiliate-function

## Business Purpose
This Azure Functions application automates affiliate configuration cache maintenance for the OnePlatform Recipient Web (Gen-3). When affiliate or affiliate-locale records change in the SQL Server database, the function automatically propagates those changes to a Redis cache and an Azure Blob storage content layer, ensuring that the Recipient Web always serves current affiliate branding, locale, and configuration data without manual cache invalidation.

## Capabilities
1. **SQL Trigger — Affiliate Data** (`SqlTriggerBindingAffiliateData`): Monitors the `[dbo].[affiliate]` table. On INSERT/UPDATE/DELETE, calls a REST API to refresh affiliate data and (commented-out) updates Redis cache.
2. **SQL Trigger — Affiliate Locale / Skin** (`SqlTriggerBindingAffiliateLocaleAffiliate`): Monitors `[dbo].[affiliate_locale_affiliate]` table. On INSERT/UPDATE, queries the `affiliate_locale_skin` table for the skin name associated with the changed record, then calls the REST API to refresh affiliate data.
3. **Blob Trigger — Content Update** (`UpdateBlobData`): Triggers when a `.properties` file is uploaded to the Azure Blob container `data/xContent/{folder}/{name}.properties`. Parses the file into key-value pairs, validates a `coverage` field, sets blob index tags, updates Redis cache with content metadata, and issues a CDN purge via Azure Front Door.
4. **CDN Purge**: `callPurgeRestAPI()` sends a POST to a configured purge endpoint to invalidate Azure Front Door CDN edge cache for updated content paths.

## Entities / Domain Objects
- `SqlChangeAffliateItem` (sic) — change wrapper with `Operation` (Insert/Update/Delete) and `AffiliateItem` (affiliate_id, short_name, munged_id, virtual_directory).
- `SqlChangeAffiliateLocaleItem` — change wrapper for locale/skin with `affiliate_id`, `locale_id`, `is_default`, `skin_id`, `default_skin_id`.
- Blob content metadata: key-value pairs from `.properties` files with a `coverage` field (required).
- Redis cache entries: `recipientweb:affiliate:{id}`, `recipientweb:primary:{id}`, `recipientweb:content:{coverage}`.

## Business Rules
1. Only `Update` operations on `affiliate` table trigger cache refresh; Insert and Delete are logged but ignored.
2. Only non-Delete operations on `affiliate_locale_affiliate` with non-zero `skin_id` trigger skin refresh.
3. The `coverage` field is mandatory in all `.properties` blob content files; missing coverage throws `IllegalArgumentException`.
4. Non-`.properties` blob files (e.g., images, JSON) trigger only a CDN purge — no Redis update.
5. HTTP retry logic: up to 3 retries (`HTTP_MAX_RETRY_COUNT = 3`) with `Retry-After` header respect for 429 responses.
6. Redis password is retrieved from Azure Key Vault when SSL is enabled; not used when SSL is off.

## Key Flows
1. **Affiliate DB change → cache refresh**:  
   SQL Server change capture → SQL Trigger → `SqlTriggerBindingAffiliateData.run()` → REST API call to affiliate data endpoint → (cache update commented out in current code).

2. **Locale/skin DB change → cache refresh**:  
   SQL Server change capture → SQL Trigger → `SqlTriggerBindingAffiliateLocaleAffiliate.run()` → DB query for skin name → REST API call → (cache update commented out in current code).

3. **Blob upload → content cache + CDN purge**:  
   Blob upload to `data/xContent/{folder}/{name}.properties` → `UpdateBlobData.run()` → parse properties → set blob index tags → update Redis hash → (CDN purge via Front Door API for non-properties files only).

## Compliance Relevance
- Configuration data is non-PCI (affiliate branding, locale, skin); not cardholder data.
- Azure Key Vault integration for Redis credentials follows secrets management best practices.
- Database credentials (`recipientweb-dbuserid`, `recipientweb-dbpassword`) retrieved from Key Vault for locale/skin lookups.

## Risks
1. **Cache update logic is commented out**: `affiliateCacheService.updateCache(...)` calls in `SqlTriggerBindingAffiliateData` and `SqlTriggerBindingAffiliateLocaleAffiliate` are commented out. The SQL triggers call REST APIs but do not update Redis, defeating the stated purpose of the function.
2. **Jedis 2.9.0 (2018)**: outdated Redis client; does not support newer Redis features or TLS 1.3.
3. **No authentication on REST API calls**: `callRestAPI()` makes unauthenticated POST requests; no auth token or mTLS.
4. **Silent exception swallowing**: `SqlTriggerBindingAffiliateData.processChange()` catches `Exception` and logs `e.getMessage()` only (not stack trace).
