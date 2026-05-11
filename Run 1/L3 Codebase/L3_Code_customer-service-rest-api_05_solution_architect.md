# customer-service-rest-api — Solution Architect View

## Architecture Overview
Spring Boot 3.4.10 reactive (WebFlux) microservice. OpenAPI-first design: `openapi.yml` drives code generation. Thin controller delegates to a single service class which orchestrates calls to legacy backends. MapStruct handles all model transformations.

```
External Client
    |  HTTPS (APIM)
    v
AuthenticationFilter (WebFilter)
    |  External-Auth-Response header validation
    v
CustomerServiceController  (extends generated CustomerServiceApiController)
    |  delegates to CustomerServiceApiDelegate
    v
CustomerService.java
    |
    +-- updateAccountStatus()  --> UpdateAccountStatusService (AccountMgmtAPI)
    +-- accountInquiry()       --> SearchAccount (xPlatform + ECountCore + Comments + Affiliate)
    +-- reissueCard()          --> ReissueCard (xPlatform + ECountCore)
    +-- setPin()               --> SetPinService (AccountMgmtAPI)
    |
    +-- AccountStatusMapper    (MapStruct)
    +-- AccountInquiryMapper   (MapStruct)
    +-- ReissueCardMapper      (MapStruct)
    +-- SetPinMapper           (MapStruct)
    +-- MetadataMapper         (MapStruct)
```

## API Surface
| Path | Method | Auth Required | SAD Involved |
|---|---|---|---|
| `/v1/account-status` | PUT | Yes (JWT) | No |
| `/v1/account-inquiry` | GET | Yes (JWT) | No (PAN masked) |
| `/v1/reissue-card` | POST | Yes (JWT) | No |
| `/v1/set-pin` | PUT | Yes (JWT + CandidateStore) | Yes (PIN in body) |

## Security
- `AuthenticationFilter.java`: reads `External-Auth-Response` header (set by upstream API gateway/proxy). Validates `ValidationResult.IsValid()`. For paths in `candidateStore` config, initialises `JwtEntityCandidate` in `CandidateStore` singleton.
- `JwtSecurityValidator.java`: implements `SecurityValidator`; checks `EntityIdentification.isValid()` and `Entity.hasAccess(domain)` — domain-level access control (e.g., `AccountManagement/setPin`).
- `NoOpsSecurityEntityManager.java`: present — implies a no-op fallback entity manager (likely for health endpoints).
- Error responses use RFC 7807 ProblemDetail format (`SecurityExceptionProblemDetail`, `InternalErrorProblemDetail`, etc.).
- PIN value (`newPin`) is explicitly excluded from log statements (`CustomerService.java` line 143–145).
- Card number logged with last-4 masking (`getCardNumberLastFour()`, line 232).

## Technical Debt
| Item | File | Line | Description |
|---|---|---|---|
| `allow-circular-references: true` | `application.yml` | 75 | Spring bean graph has cycles |
| `allow-bean-definition-overriding: true` | `application.yml` | 76 | Overriding beans can hide misconfiguration |
| Hard-coded `commentService.setApplicationId(12)` | `CSConfig.java` | 139 | Magic number; undocumented |
| Hard-coded `escalation.status: 3` | `application.yml` | 146 | Magic number in config |
| `authSyncPrograms: 04014631` hard-coded | `application.yml` | 147 | Program code should be externalised per environment |
| Tests skipped in CI | `deployment.yml` | 21 | `-Dmaven.test.skip` means no regression gate |
| `insecure` TLS in Maven CI | `deployment.yml` | 21 | `-Daether.connector.https.securityMode=insecure` |
| `startup.sh` missing from repo | `Dockerfile` | 30 | Unknown runtime initialisation |
| SNAPSHOT version in CI-deployed artifact | `pom.xml` | 16 | `1.2.3-SNAPSHOT` deployed to external APIM |

## Gen-3 Migration Notes
- WebFlux reactive stack is forward-compatible with Gen-3 patterns.
- Dapr secret store (`dapr-components/`) is partially wired — `dapr-secrets.json` present locally. Full Dapr sidecar integration would replace environment-variable secret injection.
- Legacy `xplatform` and `xplatformlibrary` (RMI/XML-RPC) are the primary Gen-3 blockers; these need to be replaced with REST/gRPC equivalents (ECountCore REST client is the intended replacement path, already partially used).
- `StoredProcedure`-based comment DAOs (from `dao-util_LIB`) should be migrated to JPA Repository or ECountCore service calls.

## Code Risks
- `CustomerService.accountInquiry()` line 110: swallows non-`RemoteException` errors silently (`catch (Exception e) { log.error(...); }` without propagating — callers receive an empty `Mono`, leading to a silent no-response rather than a 500.
- `CandidateStore.getInstance()` is a static singleton (`AuthenticationFilter.java` line 43); in reactive context this is not thread-safe if multiple requests attempt concurrent writes — depends on `CandidateStore` internal synchronisation (from `api-security-lib`, source not in scope).
- `@SneakyThrows` used in multiple places (`CustomerService.java` lines 152, 185) — suppresses checked exceptions, making error propagation analysis difficult.
