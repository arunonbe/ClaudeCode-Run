# Enterprise Architect — oneplatform-azureaffiliate-function

## Platform Generation
**Gen-3** — This is a cloud-native Azure Functions application:
- Java 17.
- Azure Functions v4 serverless runtime.
- Azure Key Vault for secrets management.
- Azure Blob Storage and Redis Cache as infrastructure.
- Azure SQL trigger bindings (event-driven, CDC-style).
- CI/CD via GitHub Actions.

This is a supporting microservice in the Gen-3 Recipient Web platform.

## Business Domain
**Platform Operations / Configuration Management** — Automates affiliate configuration cache synchronization between the SQL Server source-of-truth database and the Redis cache / Blob Storage layer used by the Recipient Web.

## Role in the Platform
Cache warming and invalidation sidecar for the Gen-3 Recipient Web. It ensures affiliate branding and configuration changes propagate to the distributed cache without human intervention. It is not in the cardholder request path; it is an asynchronous background service.

## Dependencies

### Upstream (triggers this function)
- Azure SQL Server `[dbo].[affiliate]` and `[dbo].[affiliate_locale_affiliate]` tables (SQL change feed).
- Azure Blob Storage `data/xContent/` container (blob upload trigger).

### Downstream (this function writes to)
- Redis Cache (affiliate and content entries).
- Azure Blob Storage (blob index tags).
- Azure Front Door (CDN purge API).
- Recipient Web REST API (affiliate data endpoint — unauthenticated).

### Infrastructure
- Azure Key Vault.
- Azure Functions runtime.

## Integration Patterns
- **Event-driven**: SQL trigger bindings (Azure SQL CDC-like mechanism via `azure-functions-java-library-sql`).
- **Blob trigger**: event-driven on storage upload.
- **REST (synchronous)**: outbound HTTP calls to Recipient Web API and CDN purge endpoint.
- **Cache-aside**: Redis updated after REST API confirms latest data.

## Strategic Status
**Active Gen-3 component** — but with significant functional gaps:
- The core cache-update logic is commented out in SQL trigger handlers; the function currently calls REST APIs but does not update Redis.
- This is either intentional (REST API handles its own caching) or a work-in-progress; needs clarification with the owning team.

## Migration Blockers
Not applicable (this IS the Gen-3 component). Blockers for this function reaching full operational status:
1. **Commented-out cache update code** must be resolved (either re-enabled or intentionally removed with documentation of why).
2. **Authentication on Recipient Web REST API calls** must be implemented.
3. **Jedis 2.9.0 → Jedis 4.x or Lettuce** upgrade needed for Redis 6+ compatibility and TLS 1.3.
4. **Connection pooling** for SQL JDBC queries in `SqlTriggerBindingAffiliateLocaleAffiliate`.
