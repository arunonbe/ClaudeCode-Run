# Business Analyst — oneplatform-rediscache-adminservice

## Business Purpose
Internal administrative microservice that pre-populates and manages the Azure Redis Cache used by the recipient-facing OnePlatform web application (MyPaymentVault / mypaymentvault.com). It acts as a cache-warming and cache-management tool, removing the need for the live API to incur cold-read latency against SQL Server.

## Capabilities
- **Affiliate cache warm-up**: Reads affiliate/skin configuration from `cbaseapp` (SQL Server) and writes JSON blobs to Redis under `recipientweb:affiliate:*` and `recipientweb:primary:*` keys.
- **Program content cache warm-up**: Reads xContent blob tags from Azure Blob Storage (`data` container, `xContent/recipient/` hierarchy) and writes Redis hash entries under `recipientweb:content:*`.
- **Program setup caching**: Reads program-level label values (currency, bank, international flag, platform) from `Ecountcore` DB and writes under `recipientweb:programSetting:*` and `recipientweb:programSetup:*`.
- **International countries caching**: Reads country data and caches a full list (`intlCountry:list`) and a hash map (`intlCountry:map`) keyed by 2-digit, 3-digit, and dial codes.
- **Azure Front Door / CDN cache purge**: Triggers AFD endpoint purge via Azure Resource Manager SDK on demand.
- **Ad-hoc cache inspection and deletion**: GET/DELETE endpoints to inspect or remove keys by Redis pattern.

## Key Entities
| Entity | Source | Cache Key Pattern |
|--------|--------|-------------------|
| Affiliate (skin) | `cbaseapp.dbo.affiliate` | `recipientweb:affiliate:{name}` → `recipientweb:primary:{id}` |
| Brand Attribute | `cbaseapp.dbo` (BrandAffiliateDTO) | embedded in affiliate JSON |
| Program Setup Labels | `Ecountcore` DB (AppProfileLabel) | `recipientweb:programSetup:{programId}` |
| Program Settings | `Ecountcore` DB | `recipientweb:programSetting:{programId}` |
| xContent blob index tags | Azure Blob Storage | `recipientweb:content:{programName}` (hash) |
| International Countries | `Ecountcore` DB | `intlCountry:list`, `intlCountry:map` |

## Business Rules
- Affiliate IDs must be at least 9 digits; shorter IDs are excluded from the bulk warm-up query (`length(CAST(a.iaffiliate_id AS STRING)) > 8`).
- Program IDs must be at least 5 characters; the 3rd character encodes product, the 5th character encodes brand.
- ProgramRegion is derived: `intlprogram=yes` + `platform=EcountCore` → `usdx`; `intlprogram=yes` + `platform=NexPay` → `international`; otherwise `default`.
- AFD purge is asynchronous; the API response warns that propagation takes ~15 minutes.
- Cache operations are async, using Java 21 virtual threads via `Executors.newVirtualThreadPerTaskExecutor()`.
- Semaphore limits parallel affiliate batch caching to 10 concurrent virtual threads.

## Key Flows
1. **Affiliate warm-up**: `POST /adminservice/affiliates` → `AffiliateCachingService.cacheAffiliates()` → query `cbaseapp`, batch into chunks of 5, process via virtual threads → write Redis.
2. **Program content warm-up**: `POST /adminservice/programs` → `CacheAdminService.getPrograms()` → list blobs in `xContent/recipient/` → for each blob, read index tags → write Redis hash.
3. **Single affiliate update**: `POST /adminservice/affiliate/{name}` → query SQL → read xContent from Redis → build `AffiliateResponse` JSON → write Redis.
4. **AFD purge**: `POST /adminservice/fdcache/purge` with body `{contentPaths:[...]}` → `CachePurgeService.purgeCache()` → AzureResourceManager.cdnProfiles...purgeContent().

## Compliance Relevance
- Serves affiliate/program configuration that controls cardholder experience (payment selection, IEFT, card management) — indirectly supports PCI DSS Requirement 6 (secure systems).
- Uses Azure Key Vault (via Managed Identity) for all credentials; no secrets hardcoded in production properties. Development profile (`application-dev.properties`) contains plaintext DB credentials (`b2cstage`) — **PCI DSS risk in source control**.
- Redis connection uses TLS (`sslflag=true`, port 6380) in non-dev environments.
- SQL connections use TLS 1.2 (`sslProtocol=TLSv1.2`).
- No PAN, cardholder PII, or payment instrument data flows through this service.

## Risks
- Dev profile credentials (`b2cstage`) committed to source (`application-dev.properties`).
- No authentication/authorization on the admin REST endpoints — access control must be enforced at the network/ingress layer.
- `e.printStackTrace()` calls in production paths may leak stack traces to logs.
- `AsyncConfig.javaold` and `ExecutorServiceConfig.javaold` files indicate abandoned code left in source tree.
- `spring.main.allow-circular-references=true` required in dev profile suggests Spring bean wiring issues.
