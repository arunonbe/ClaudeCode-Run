# Data Architect — oneplatform-azureaffiliate-function

## Data Stores

| Store | Technology | Purpose |
|---|---|---|
| Affiliate SQL Server DB | Azure SQL / SQL Server (connection string: `AffiliateDBConnectionString`) | Source of truth for affiliate and locale/skin configuration |
| Redis Cache | Jedis 2.9.0 | Caches affiliate config and content metadata for Recipient Web reads |
| Azure Blob Storage | azure-storage-blob 12.24.0 (connection: `AzureWebJobsStorage`) | Stores xContent properties files and sets blob index tags |
| Azure Key Vault | azure-security-keyvault-secrets 4.8.0 | Stores Redis password, DB user ID, DB password |

## Schema / Tables

### SQL Server (read by this function)
- `[dbo].[affiliate]` — SQL trigger source. Fields used: `iaffiliate_id`, `szaffiliate_short_name`, `iaffiliate_munged_id`, `szaffiliate_virtual_directory`.
- `[dbo].[affiliate_locale_affiliate]` — SQL trigger source. Fields: `affiliate_id`, `locale_id`, `is_default`, `skin_id`, `default_skin_id`.
- `[dbo].[affiliate_locale_skin]` — queried for skin name: `SELECT skin_name FROM [dbo].[affiliate_locale_skin] where skin_id = ?`.

### Redis Cache Key Pattern
| Key | Value |
|---|---|
| `recipientweb:affiliate:{affiliate_id}` | Pointer to primary key |
| `recipientweb:primary:{affiliate_id}` | Full affiliate JSON response |
| `recipientweb:content:{coverage}` | Hash of `{blobName: metaDataJson}` |

## Sensitive Data Handling
- **Database credentials**: retrieved from Azure Key Vault (`recipientweb-dbuserid`, `recipientweb-dbpassword`). Not hardcoded.
- **Redis password**: retrieved from Azure Key Vault (`recipientweb-redis-password`) when SSL enabled.
- **Connection strings**: passed via Azure Function application settings (environment variables `AffiliateDBConnectionString`, `AzureWebJobsStorage`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_SSL_FLAG`, `BASE_URL`, etc.).
- No cardholder data (PAN, account numbers) processed by this function.

## Encryption
- Redis: SSL/TLS controlled by `REDIS_SSL_FLAG` environment variable. When `true`, Jedis connects with SSL and authenticates with Key Vault-sourced password.
- Blob Storage: Azure Storage enforces HTTPS; no explicit encryption configuration in code.
- SQL Server: connection string is passed from environment; TLS support depends on the JDBC driver configuration (mssql-jdbc 12.4.2 supports TLS 1.2/1.3).
- Key Vault: accessed via `DefaultAzureCredentialBuilder` (Managed Identity preferred).

## Data Flow
```
SQL Server [dbo].[affiliate] change
  → Azure SQL Trigger binding → SqlTriggerBindingAffiliateData.run()
  → HTTP POST to BASE_URL + GET_AFFILIATE_DATA_URI + affiliate (REST API)
  → (updateCache commented out → Redis NOT updated currently)

Azure Blob upload: data/xContent/{folder}/{name}.properties
  → BlobTrigger → UpdateBlobData.run()
  → Parse .properties → validate coverage → set blob index tags
  → Jedis.hset("recipientweb:content:{coverage}", blobName, metaDataJson)

Non-properties blob upload:
  → HTTP POST purge to BASE_URL + POST_PURGE_CONTENT_URI
```

## Data Quality / Retention
- No TTL set on Redis keys; cache entries persist until explicitly deleted or Redis is flushed.
- Blob index tags are set atomically per blob file; no version history maintained.
- The `processPropertiesFile` method strips empty values and normalizes keys (hyphen → underscore, trim).

## Compliance Gaps
1. **Redis cache update is disabled**: the most critical data synchronization logic (`updateCache()`) is commented out in SQL trigger handlers. Affiliate config cache may be stale indefinitely.
2. **No TTL on Redis entries**: stale data risk if the function fails or is unavailable for an extended period.
3. **`AzureWebJobsStorage` connection string used for both trigger and blob client**: if this is a SAS URL, it may grant broader access than needed (principle of least privilege).
4. **`KeyVaultSecretProvider` is a singleton with an in-memory secrets cache**: if secrets are rotated, the cached value is never invalidated until the function app is restarted.
5. **SQL JDBC connection per request**: `SqlTriggerBindingAffiliateLocaleAffiliate.getSkinName()` opens a new JDBC connection using `DriverManager.getConnection()` for each change event. No connection pooling; potential connection exhaustion under high change volume.
