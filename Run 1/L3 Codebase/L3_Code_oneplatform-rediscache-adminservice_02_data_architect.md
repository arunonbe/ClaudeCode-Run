# Data Architect — oneplatform-rediscache-adminservice

## Data Stores
| Store | Type | Connection |
|-------|------|------------|
| `cbaseapp` (primary) | SQL Server (Microsoft SQL Server via mssql-jdbc) | `q-lis-db01.nam.wirecard.sys:2231` (dev/default); `P-LIS-DB03` (prod implied) |
| `Ecountcore` (secondary) | SQL Server | `q-lis-db02.nam.wirecard.sys:2231` (dev); read-only label/country queries |
| Azure Redis Cache | Redis (Jedis client, SSL/TLS) | `radis-az1-cluster-qa-ss.redis.cache.windows.net:6380` (qa/default) |
| Azure Blob Storage | Object storage (`data` container) | Connection string resolved from Key Vault (`recipientweb-blob-connectionstring`) |

## Schema / Key Structures

### SQL Tables (cbaseapp)
- `dbo.affiliate` — columns: `id` (PK), `iaffiliate_id` (Integer), `szaffiliate_virtual_directory` (String). Affiliate IDs > 8 digits are treated as program affiliates.
- `BrandAffiliate` (via `BrandAffiliateRepository`) — queried via `getBrandAttributeAffiliate(affiliateId, virtualDirectory)` returning `BrandAffiliateDTO` (affiliateId, affiliate_skin_name, default_skin_name).
- `AppProfileLabel` (via `AppProfileLabelRepository`) — queried for program labels (currency, bank, intl_program, program_platform) keyed by programId, product, brand, affiliateId.

### SQL Tables (Ecountcore)
- International countries table — queried via `getInternationalCountries()` returning `InternationalCountryDTO` (countryCode2Digit, countryCode3Digit, dialCode, and display fields).

### Redis Key Taxonomy
| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `recipientweb:affiliate:{name/id}` | String | No TTL set | Pointer → primary key |
| `recipientweb:primary:{id}` | String | No TTL set | JSON-serialized `AffiliateResponse` |
| `recipientweb:content:{programName}` | Hash | No TTL set | Blob path → serialized tag map |
| `recipientweb:programSetup:{programId}` | String | No TTL set | JSON map of label → value |
| `recipientweb:programSetting:{programId}` | String | No TTL set | JSON `ProgramSettingResponse` |
| `intlCountry:list` | String | No TTL set | JSON array of all countries |
| `intlCountry:map` | Hash | No TTL set | Code → JSON country object |

### Azure Blob Storage
- Container: `data`, path prefix: `xContent/recipient/`
- Files with `.properties` extension are excluded from caching.
- Blob index tags are the payload; blob content is not read.

## Sensitive Data Classification
- No PAN, CVV, or SAD flows through this service.
- `AffiliateResponse` may contain affiliate IDs, skin names, currency codes, and program platform identifiers — considered business-confidential configuration but not personally identifiable.
- Database credentials are externalized to Azure Key Vault in production; **dev profile contains plaintext username/password (`b2cstage`)** committed to source.
- Redis password (`recipientweb-redis-password`) resolved from Key Vault at runtime.
- Blob connection string (`recipientweb-blob-connectionstring`) resolved from Key Vault at runtime.

## Encryption
- SQL Server connections: TLS 1.2 enforced (`sslProtocol=TLSv1.2; encrypt=true`).
- Redis connections: TLS (`ssl=true`, port 6380) in QA/prod; plaintext in dev (port 6379).
- Azure Key Vault integration uses Managed Identity (`ManagedIdentityCredentialBuilder`) — no stored credentials.
- Data at rest in Redis: Azure Redis Cache uses AES-256 encryption at the infrastructure layer; no application-layer encryption applied to cached values.

## Data Flow
```
cbaseapp (SQL) ──────────────────────────────────────┐
Ecountcore (SQL) ────────────────────────────────────► CacheAdminService → Redis Cache
Azure Blob Storage (xContent tags) ─────────────────┘

Redis Cache ────────────────────────────────────────► oneplatform-rest_API (read path)
```

## Data Quality and Retention
- No TTL is set on any Redis key — data persists until explicitly purged or Redis is flushed. This is intentional (static program configuration) but creates staleness risk if DB changes are not followed by a cache warm-up.
- Cache warm-up is triggered manually via HTTP POST; no automated scheduler present in this service.
- On `updateProgram`, the existing hash key is deleted before re-writing, providing an atomic delete-then-set pattern (non-atomic between delete and writes — brief gap possible).

## Compliance Gaps
- **PCI DSS Req 3.4**: No TTL or rotation policy on Redis keys storing program configuration.
- **PCI DSS Req 6.3**: Dev credentials in source (`application-dev.properties`) — should be excluded or replaced with placeholder.
- **PCI DSS Req 10**: No audit log of cache administration operations (who triggered which cache warm-up).
- **Key Vault fallback**: `DefaultAzureCredentialBuilder` falls back gracefully but introduces risk if misconfigured — alert/monitor on fallback events needed.
