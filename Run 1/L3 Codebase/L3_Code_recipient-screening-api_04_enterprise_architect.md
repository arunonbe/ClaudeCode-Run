# Enterprise Architect View — recipient-screening-api

## Platform Generation

**Gen-3 (NexPay/Onbe)** — confirmed by:
- `com.onbe.*` package namespace
- Spring Boot 3.5.8 (latest Spring Boot 3.x line)
- Java 25 runtime
- Azure Key Vault for secrets management
- Azure API Management publication (`PUBLISH_TO_APIM: true`)
- OpenAPI-driven API design (generated stubs via code generation)
- OAuth 2.0 client credentials flow for service-to-service authentication

However, this Gen-3 service has significant Gen-2 infrastructure dependencies: both databases (`cbaseapp`, `EcountCore`) reside on `wirecard.sys` DNS domain servers (`p-lis-db02`, `p-lis-db03`), which are Gen-2 Wirecard/Northlane infrastructure. This creates a hybrid architectural position.

## Integration Patterns

1. **REST/HTTP with OAuth 2.0**: Inbound API (from NexPay payout orchestration services) and outbound to `om-recipientsanctioning-svc`. Both use REST+JSON with OAuth 2.0 bearer token authentication.
2. **Webhook**: Inbound asynchronous callbacks from the sanctions vendor via `POST /sanction/webhook`. Webhook validation is performed by `SanctionWebhookRequestValidator`.
3. **Spring Data JPA**: Outbound to SQL Server databases for configuration data and pending record management.
4. **ECountCore integration**: The service calls `ECountCoreService` to resolve DDA numbers to eCount member and device records. This is a bridge to Gen-1/Gen-2 data — the pattern for how ECountCore is accessed (REST? XML-RPC? JDBC?) is visible in `ECountCoreService.java` but not read in this analysis; it represents a critical cross-generation integration point.
5. **Feature-flag-driven behaviour**: The use of `@Value`-injected boolean flags (`isUpdateAccountInApiCallEnabled`, `isUpdateAccountInWebhookEnabled`) provides runtime control over the account-update pathway.

## External Dependencies

- **`om-recipientsanctioning-svc`**: External sanctions screening vendor API (or shared internal service). The module `om-recipientsanctioning-svc` contains a generated OpenAPI client. The vendor is not named in the code but the service is internal to Onbe's platform (`om-` prefix).
- **ECountCore service**: Gen-1/Gen-2 core account management system — DDA-to-member resolution.
- **Azure Key Vault**: Secrets management.
- **Azure API Management**: Internal API gateway.
- **SQL Server (`wirecard.sys`)**: Gen-2 infrastructure hosting `cbaseapp` and `EcountCore` databases.
- **Pact Broker**: Contract testing registry.

## Position in the Broader Platform

`recipient-screening-api` sits at the intersection of the Gen-3 payout orchestration layer and the Gen-1/Gen-2 account management layer. Its position in the disbursement flow:

```
[Payout Orchestrator (Gen-3)]
    → POST /api/v1/screening/request
    → [recipient-screening-api]
        → [om-recipientsanctioning-svc] (sanctions vendor)
        → [ECountCore] (account lookup and block)
        ← webhook ← [om-recipientsanctioning-svc]
    → [APIM / Internal consumers]
```

This service is a **critical control point** for OFAC compliance in the Gen-3 payout rail. Bypassing or disabling it could result in sanctions violations.

## Migration Blockers

- **Database dependency on `wirecard.sys`**: Until `cbaseapp` and `EcountCore` databases are migrated to Azure SQL (Gen-3), this service maintains an infrastructure dependency on Gen-2 on-premises servers.
- **ECountCore dependency**: Until ECountCore is replaced by a Gen-3 account management service, the DDA-to-member resolution pathway cannot be fully modernized.
- **`trustServerCertificate=true`**: The SQL connection string bypasses certificate validation, which must be resolved when migrating to Azure SQL with proper PKI.

## Strategic Status

**Actively developed, strategically critical.** The recent deployment tags (April 2026) confirm active production use. This service should:
1. Have its SQL Server dependency migrated to Azure SQL with proper TLS certificate validation.
2. Have its `SecurityConfig` updated to require authentication (`anyRequest().authenticated()` with appropriate OAuth 2.0 resource server configuration).
3. Be registered as a Pact provider for any downstream services that consume its API.
4. Receive formal penetration testing given its OFAC control significance.
