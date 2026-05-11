# Enterprise Architect View — cs-api-v2_API

## Platform Generation
**Gen-1** — Pure legacy WAR deployment, no Spring Boot, no cloud integration, Java 5, Spring 2.5.x, Apache Axis 1.4. This is the oldest deployed generation of the CS API still in this repository set, representing the original Wirecard/eCount-era implementation with no modernisation.

## Domain
- **Domain**: Customer Service — Cardholder Account Inquiry and Profile Update
- **Bounded context**: CS API V2 — read + limited write access to cardholder data for client applications
- **Business capability**: First generation of mutating CS API; allows external clients to update cardholder registration without direct platform access

## Role in Ecosystem
```
Client Applications
        │  SOAP
        ▼
Apache Axis (CardManagementV2/services/AccountManagement)
        │
        ├── Static configMap (applicationContext-xCSAPI.properties)
        │     application_id → program_id (static mapping, no dynamic lookup)
        │
        ├── EMember / EDevice → C-Base xPlatform (v2.4.5)
        │
        └── PuidLookup / BalanceLookup / StatusList
              (JobSvc + EcountCore SQL Server via JNDI)
```

## Version Evolution: What Changed V1 → V2 → V3

### V1 → V2
| Change | Description |
|---|---|
| New operation | `updateAccountProfile` added — first write operation in CS API |
| New type | `AccountProfile` request type with all cardholder address/contact fields |
| New type | `ResultCode` response type with string code and description |
| Validation | `ZipValidation`, email format, phone digit count, name character restrictions |
| Context path | `/CardManagementV2` (V1 used `/CardManagement`) |
| No new read capability | `accountInquiry` logic is nearly identical to V1 |
| Performance regression | Per-request `ClassPathXmlApplicationContext` introduced (not in V1 which used `ServletEndpointSupport`) |

### V2 → V3
| Change | Description |
|---|---|
| Dynamic app_id lookup | V3 uses `AffiliateService.getAffiliateForValue("cs_api_v3_app_id", ...)` instead of static XML map |
| Affiliate permission flags | V3 checks `cs_api_enabled`, `cs_api_v3` flags — V2 has no such gate |
| Extended search criteria | V3 adds PPD and mobile phone search in `accountInquiry` |
| Comment history | V3 returns `CommentHistory[]` — V2 has none |
| Ship date | V3 returns card ship date — V2 has none |
| PPD details | V3 returns `PaymentDetail[]` with PPD promotion data — V2 has none |
| Audit trail | V3 `updateAccount` writes a comment for address changes — V2 has none |
| Card reissue | V3 adds `reissueCard` operation — V2 has none |
| Escalation | V3 adds `handleEscalation` — V2 has none |
| Merchant name control | V3 checks affiliate flag — V2 always masks |
| Platform client | V3 uses ecount-core-rest-api (HTTP REST) — V2 uses xPlatform (proprietary RPC) |
| Card masking | V3 uses first-4 + XXXXXXXX + last-4 — V2 uses XXXXXXXX + last-8 |
| Payout | V3 has a payout sub-service — V2 has none |
| Internationalisation | V3 adds Canada + international support — V2 supports US/CA only with V2 validation |

## Dependencies
| Dependency | Notes |
|---|---|
| C-Base xPlatform 2.4.5 | Older version than used in V1 (6.5.x) / V3 (6.5.x) |
| Spring 2.5.4 | EOL |
| Apache Axis 1.4 | EOL |
| SQL Server (jTDS) | JNDI-managed |

## Patterns
- **Monolithic action class**: All business logic in a single 860-line `AccountManagementImpl.java` — no separation of concerns
- **Service Locator (anti-pattern)**: `getProperties()` creates a new Spring context as a factory — bypasses IoC
- **Static utility methods**: `validatePhone`, `matchesPattern`, `containsChar`, etc. as static methods on the implementation class — no interface, not testable in isolation
- **Static configMap authentication**: Application IDs hard-coded in XML

## Status
**Legacy / Sunset Candidate**
- No active CI/CD deployment pipeline
- Java 5 target, Spring 2.5.x, Axis 1.4 — three generations behind current standards
- No Spring Boot modernisation module (unlike V1 and V3)
- V3 supersedes all V2 capabilities
- Clients still on V2 should be prioritised for migration to V3

## Migration Blockers to V3 / Gen-3
1. **Static configMap**: Client application_ids must be migrated to the dynamic AffiliateService (`cs_api_v3_app_id` attribute type in CbaseApp)
2. **`ResultCode` vs `Response`**: V2 returns `ResultCode` (string code) from updateAccountProfile; V3 returns `Response` (int code). API contract change requires client update.
3. **Different error codes**: V2 uses 34001/34002 for inquiry errors; V3 uses similar but not identical ranges and messages. Clients may have error-code-dependent logic.
4. **No deployment automation**: Manual deployment process not documented in this repo.
5. **No test coverage**: Only integration test skeletons; no unit tests verifiable without a running server.
