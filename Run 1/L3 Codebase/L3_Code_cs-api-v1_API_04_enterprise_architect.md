# Enterprise Architect View — cs-api-v1_API

## Platform Generation
**Gen-2 (Spring Boot modernisation of Gen-1 SOAP service)**

The `card-management-ws` module contains the original Gen-1 business logic (Apache Axis SOAP, Spring XML config, C-Base xPlatform RPC). The `card-management-boot` module wraps this in Spring Boot 3.x with Azure cloud integration, making it Gen-2 in terms of deployment and operations, while the core logic and API surface remain Gen-1 SOAP.

The V1 API surface itself (`accountInquiry` only) is a deliberate subset — it was the first generation of the CS API, designed for simple card inquiry with no mutation operations.

## Domain
- **Domain**: Customer Service — Cardholder Account Inquiry
- **Bounded context**: CS API V1 — read-only card account lookup for authorised applications
- **Business capability**: Allow client applications to query cardholder balance, transactions, and registration without direct access to the C-Base platform

## Role in Ecosystem
```
External Client Applications (affiliates)
        │  SOAP over HTTPS (application_id authentication)
        ▼
Azure API Management (APIM — external-facing)
        │  Routes to backend
        ▼
cs-api-v1_API (Spring Boot / WAR)
  cardmanagementws (context path /CardManagement)
        │
        ├── AffiliateService → CbaseApp SQL Server
        │     (validate application_id, check cs_api_v1 flag)
        │
        ├── PuidLookup → JobSvc SQL Server
        │
        └── xPlatform (EMember, EDevice) → C-Base Core Platform
```

## Version Evolution: V1 vs V2 vs V3
| Aspect | V1 | V2 | V3 |
|---|---|---|---|
| Operations | accountInquiry only | accountInquiry + updateAccountProfile | accountInquiry, update, reissue, escalation, payout |
| App ID lookup | AffiliateService (cs_api_v1_app_id) | Static XML configMap | AffiliateService (cs_api_v3_app_id) |
| Search criteria | card_number or PUID only | card_number or PUID only | + PPD, mobile phone |
| Card masking | XXXXXXXX + last 8 | XXXXXXXX + last 8 | First 4 + XXXXXXXX + last 4 |
| Comment history | No | No | Yes |
| Ship date | No | No | Yes |
| PPD details | No | No | Yes |
| Merchant name control | No | No (always XXXX) | Yes (affiliate flag) |
| Platform calls | EMember/EDevice (direct xPlatform) | EMember/EDevice (direct xPlatform) | REST client to ecount-core-rest-api |
| Spring framework | 2.x (legacy WAR) / Spring Boot 3.x (Boot) | 2.5.x (WAR only) | Spring Boot 3.5.x |
| Java version | 21 | 1.5 | 21 |
| Deployment | WAR + Boot JAR | WAR only | WAR + Boot JAR |
| CI/CD | GitHub Actions with APIM | GitHub Actions (CodeQL only) | GitHub Actions with APIM + rollout |
| Azure App Config | Yes | No | Yes |
| Pact contract testing | Referenced (PACT_PACTICIPANT) | No | Referenced (PACT_PACTICIPANT) |

## Dependencies
| Upstream System | Interface | Version Risk |
|---|---|---|
| C-Base xPlatform | Proprietary Java RPC (xplatform 6.5.8) | Proprietary dependency; upgrade tied to C-Base platform changes |
| xAffiliate Service | Hibernate + SQL Server | Internal library 4.0.1 |
| Azure App Configuration | Spring Cloud Azure 5.23.0 | Current; managed identity auth |
| Azure Key Vault | Via App Config integration | Current |

## Patterns
- **SOAP-over-HTTP Service Locator**: Apache Axis servlet with Spring endpoint support
- **Dependency Injection**: Spring `@Configuration` classes (`AccountManagementConfig`, `ECountSystemConfiguration`)
- **Conditional Configuration**: `ECountSystemConfigCondition` — only initialises ecount system config if `bootAddress` is set
- **Request Context Holder**: `StaticRequestContextHolder` + `ProgramIdAwareGlobalRequestIDGenerator` for MDC correlation
- **Published to APIM**: WSDL published to Azure API Management for external client discovery

## Status
- **Active / Production** — Full CI/CD pipeline, Azure APIM integration, Java 21, Spring Boot 3.x
- The Spring Boot module represents the target deployment model; the WAR module is the legacy fallback
- SNAPSHOT version (`3.1.3-SNAPSHOT`) suggests active development

## Migration Blockers to Gen-3 (Full REST/JSON)
1. **SOAP contract**: Clients are bound to the WSDL. Migration to REST requires client-side changes and a versioned API transition period.
2. **xPlatform RPC dependency**: Must be replaced with the REST-based `ecount-core-rest-api` (used by V3) — this is a significant effort.
3. **Affiliate permission check naming**: `cs_api_v1_app_id` and `cs_api_v1` metadata keys are V1-specific; V3 uses `cs_api_v3_*`. Any migration must map or consolidate these.
4. **Instance-field concurrency issue**: `AccountManagementImpl` uses instance-level output fields — must be refactored to be fully stateless before any further modernisation.
