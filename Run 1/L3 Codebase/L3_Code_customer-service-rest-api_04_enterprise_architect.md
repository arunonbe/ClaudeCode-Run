# customer-service-rest-api — Enterprise Architect View

## Platform Generation
- **Generation:** Gen-2 / transitional. Spring Boot 3.4.10 (modern), Java 21, reactive WebFlux — but integrates with legacy eCount xPlatform (Gen-1) via RMI/XML-RPC, and Citi AccountManagementAPI SOAP-style libraries. Dapr integration partially configured for Gen-3 readiness.
- **Version:** 1.2.3-SNAPSHOT (pre-release).

## Domain
- **Payments Domain → Customer Service Subdomain.**
- Supports B2C disbursements lifecycle: card activation, account inquiry, card reissue, PIN management.
- Positioned as the external API surface for partner/client systems to manage prepaid cardholder accounts.

## Role in the Ecosystem
| Role | Detail |
|---|---|
| API Provider | Exposes 4 REST operations to clients via external APIM |
| Backend consumer | Delegates to legacy eCount xPlatform, ECountCore REST, Citi AccountManagementAPI (CMS) |
| Data aggregator | Combines data from cbaseapp DB, jobsvc DB, legacy services into unified responses |

## Dependency Map
### Upstream (callers)
- External client / partner systems via APIM (JWT/token auth via `External-Auth-Response` header).

### Downstream (called)
| Service | Interface | Notes |
|---|---|---|
| eCount xPlatform | `xplatform` lib (v6.4.29), `SearchAccount`, `ReissueCard` via RMI | Legacy Gen-1 |
| xPlatformLibrary | `xplatformlibrary` v4.2.0 | Legacy Gen-1 |
| AccountManagementAPI (Citi CMS) | `accountmanagementapi-impl` v3.1.7, `UpdateAccountStatusService`, `SetPinService` | Citi-originated prepaid library |
| ECountCore REST API | `ecount-core-rest-api` v3.0.4, `MemberService`, `DeviceService` | Modern REST client |
| csapi-v3 | `csapi-v3-api` v3.1.8, REST client | Ecount CS API v3 |
| xAffiliate service | `xaffiliate-service` v4.0.1 | Affiliate lookup |
| Comment service | `comment` lib v3.0.1 | CSA inquiry / comment management |
| cbaseapp SQL Server | HikariCP JDBC | Direct DB access for comment/affiliate data |
| jobsvc SQL Server | HikariCP JDBC | Job service data |
| Correlation Core | `correlation-core` v2.0.1 | Request correlation ID propagation |

## Architectural Patterns
- **Reactive REST (WebFlux):** `Mono<T>` return types throughout; non-blocking I/O.
- **OpenAPI-first:** Controller interfaces generated from `openapi.yml`; `CustomerServiceController` extends generated `CustomerServiceApiController`.
- **Delegate pattern:** Generated `CustomerServiceApiDelegate` implemented by `CustomerService.java`.
- **JWT-based authentication:** `AuthenticationFilter` validates `External-Auth-Response` header; `JwtSecurityValidator` performs domain/entity access check.
- **MapStruct mappers:** Domain boundary transformations (`AccountStatusMapper`, `AccountInquiryMapper`, `ReissueCardMapper`, `SetPinMapper`, `MetadataMapper`).
- **Circuit breaker:** Resilience4j (`resilience4j-circuitbreaker` v2.3.0) wrapping ECountCore HTTP calls; configured via `ecountcore.circuitbreaker.*` properties.

## Status
- Under active development (SNAPSHOT, recent bugfix branch in CI trigger).
- Published to external APIM on every main-branch push.
- CodeQL SAST and container scanning configured.

## Blockers
1. Legacy integration debt: `xplatform` and `xplatformlibrary` require numerous Spring exclusions (`pom.xml` lines 107–119), indicating version conflicts with modern Spring Boot 3.
2. `allow-circular-references: true` (`application.yml` line 75) — bean graph has cycles; architectural smell.
3. Tests skipped in CI — no automated regression gate.
4. `csapi-v3-rest-client` and comment DAOs access cbaseapp DB directly, bypassing service abstractions — tight DB coupling.
5. `startup.sh` missing from repo — opaque runtime initialisation.
