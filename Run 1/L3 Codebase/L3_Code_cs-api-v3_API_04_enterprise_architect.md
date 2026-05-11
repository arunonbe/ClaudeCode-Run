# Enterprise Architect View — cs-api-v3_API

## Platform Generation
**Gen-2** — Spring Boot 3.5.7 on Java 21. Containerised (Dockerfile). Azure App Configuration + Azure Key Vault via Managed Identity. Full CI/CD with canary rollout, APIM publishing, and CodeQL. The primary difference from pure Gen-3 targets is the retention of Apache Axis 1.x as the SOAP transport layer — the protocol surface is SOAP, not REST, and this is a deliberate backward-compatibility choice for existing client integrations.

## Domain
- **Domain**: Customer Service — Cardholder Account Inquiry, Profile Management, Card Operations, CS Escalation
- **Bounded context**: CS API V3 — full read/write access to cardholder data for authorised client applications and self-service portals
- **Business capability**: Complete CS API platform; replaces V1 and V2; adds payout portal operations, card reissue, escalation, international support

## Role in Ecosystem
```
External Client Applications / Payout Portal
        │  SOAP (HTTPS)
        ▼
Azure API Management (external gateway)
        │  WSDL published: wsdl.xml
        ▼
Spring Boot 3 / Apache Axis JAX-RPC
  AccountManagementJaxRPC (csapi-v3-ws)
  AccountManagementJaxRPC (csapi-v3-payout-ws)
        │
        ├── AffiliateService (xaffiliate-service)
        │     └── CbaseappDataSource (SQL Server / Hibernate)
        │           application_id → affiliate + permission flags
        │
        ├── MemberService / DeviceService (ecount-core-rest-api)
        │     └── ecount-core REST API (HTTP/HTTPS)
        │           member search, card inquiry, DDA inquiry, registration update
        │
        ├── ICommentService (comment library)
        │     └── CbaseappDataSource — comment history + audit writes
        │
        ├── PPDPromotionXref / PPD data (C-Base platform)
        │     └── CbaseappDataSource / xPlatform
        │
        ├── Redis HTTP — international program validation cache
        │
        └── CMS — ContentManagementServiceClient
              └── northlane.com CMS service (payout app content URLs)
```

## Version Evolution: V1 → V2 → V3

### V1 → V2
| Change | Description |
|---|---|
| New operation | `updateAccountProfile` — first write operation |
| New type | `AccountProfile` request with address/contact fields |
| New type | `ResultCode` response with string code |
| Validation | ZipValidation class; email, phone, name char validation |
| Context path | `/CardManagementV2` |
| Performance regression | Per-request ClassPathXmlApplicationContext introduced |
| Deployment | WAR only, no Spring Boot module |

### V2 → V3
| Change | Description |
|---|---|
| Dynamic app_id lookup | AffiliateService replaces static XML configMap |
| Affiliate flags | cs_api_enabled + cs_api_v3 checked per request; revocation without redeploy |
| Extended search | PPD and mobile phone search in searchAccount |
| Comment history | CommentHistory[] returned in searchAccount |
| Ship date | card ship_date returned in CardDetail |
| PPD details | PaymentDetail[] with PPD promotion data in transactions |
| Audit trail | updateAccount writes auto-comment for address changes |
| Card reissue | reissueCard operation added |
| Escalation | handleEscalation operation added |
| Merchant name | Controlled by cs_api_disp_merchant_name flag; V2 always masked |
| Platform client | ecount-core-rest-api (HTTP REST); V2 used xPlatform (RPC) |
| Card masking | First-4 + XXXXXXXX + last-4; V2 used XXXXXXXX + last-8 |
| Payout sub-service | payoutAccountInquiry + auth/registration operations |
| International support | CA provincial validation; international country/state/postal |
| KYC flag | kyc_required affiliate flag gates update authorisation path |
| Redis integration | International program lookup via Redis HTTP |
| Error codes | All integer (V2 used String "0"-"7" for updateAccountProfile) |
| Deployment | Spring Boot 3 + Docker + Azure; V2 was WAR-only on JBoss |
| CI/CD | Full GitHub Actions pipeline; V2 had CodeQL only |
| DDA support | DDA-only accounts supported; JWE-encrypted DDA numbers |

### V1 → V3 (same generation boundary)
V3 is a superset of V1 — it uses the same dynamic AffiliateService lookup model, the same Spring Boot 3 bootstrap, and the same Azure App Config pattern as V1. The key additions over V1 are all the V3-specific operations listed in the V2→V3 table above plus the comment service integration and payout sub-service.

## Dependencies
| Dependency | Version | Notes |
|---|---|---|
| Spring Boot | 3.5.7 | Current |
| Spring Cloud Azure | 5.23.0 | Azure managed services |
| xplatform | 6.5.8 | C-Base RPC — same as V1; maintained internal library |
| ecount-core-rest-api | 3.1.8 | REST replacement for direct xPlatform calls |
| xaffiliate-service | 4.0.1 | Same as V1 |
| comment | 3.0.1 | Internal comment service — unique to V3 |
| xsecurity-common/impl | 4.0.3 | JWE/JWT — unique to V3 payout |
| jjwt | 0.11.5 | JWT library |
| Resilience4j | Spring Boot managed | Circuit breaker — unique to V3 |
| Apache Axis | 1.4 (via WAR module) | SOAP transport — legacy retained for protocol compatibility |

## Patterns
- **Action class per operation**: SearchAccount, UpdateAccount, ReissueCard, HandleEscalation, PayoutSearchAccount, UpdateRegistrationAction — each a Spring-managed bean. Clean separation of concerns vs. V2 monolith.
- **Repository pattern**: ICommentService and its DAOs; AffiliateService stored procedure wrappers.
- **Service Locator (partially resolved)**: `AccountManagementJaxRPC` does `getBean("searchAccount")` — programmatic bean lookup. This is a legacy Axis integration pattern; the beans themselves are now proper Spring singletons.
- **Circuit Breaker**: Resilience4j wraps ecount-core REST calls — `inquiryEcardResilient()` for FiservDR programs.
- **Configuration as Code**: `AccountManagementBeanConfiguration.java` replaces all XML context files programmatically. Bean names are preserved exactly for backward compatibility with `getBean()` lookups.
- **Separation of WAR and Boot modules**: `csapi-v3-war` (deployable WAR) and `csapi-v3-boot` (Spring Boot executable JAR with full `@Configuration`) are distinct modules — supports both traditional and cloud-native deployment.

## Status
**Active Production — Current Platform Generation**
- Full CI/CD pipeline with canary rollout
- Java 21, Spring Boot 3.5.7 — current standards
- Docker containerised
- Azure APIM for external access
- Pact contract testing active
- V3 supersedes V1 and V2; clients on V1/V2 should migrate to V3

## Migration Considerations
1. **V1 → V3**: Primary API contract change is error codes for updateAccount (V1: same int codes; V3: same pattern). Affiliate flag `cs_api_v3` must be set for each migrating program_id.
2. **V2 → V3**: V2 `ResultCode` (String code) changes to V3 `Response` (int code) — breaking API contract change for `updateAccountProfile` callers.
3. **payout_API → V3 payout sub-service**: The standalone `csapiws-payout_API` WAR payout operations are also present in `csapi-v3-payout-ws` within this repo. Clients should migrate to the V3 payout endpoint.
