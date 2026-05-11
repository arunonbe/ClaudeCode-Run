# Solution Architect View — xplatform_LIB

## Technical Architecture
- **Language:** Java 21 (compiler target and source)
- **Build:** Maven, parent POM `prepaid-parent:6.0.13`
- **Packaging:** JAR library
- **Architecture style:** Layered library — business managers over DAOs over Spring JDBC / Hibernate
- **Key patterns:** Factory + Cache (`AffiliateFactory`), Manager/Impl (`MemberManagerImpl`), DAO/Spring pattern
- **Frameworks:** Spring JDBC, Hibernate Core (ORM), XStream (XML), MSAL4J (Azure AD), CBTS RPC client
- **Domain packages:** `com.cbase.business.*` (all business domains), `com.cbase.core.*` (request context, caching)

## API Surface
Public API is the set of Java interfaces and manager classes:
- `AffiliateFactory.getAffiliate(int, Dictionary)` / `getAffiliate(int, RequestContext)` — affiliate resolution with caching
- `IMemberManager` — member search, PUID lookup, basic member operations
- `EManageManagerImpl` — EManage orchestration (pre-check definitions, job account map)
- `AccountHistoryViewManager` — device/account history queries
- `TicketManager` — CSA ticket operations
- `EmailNotificationTest` — notification service (integration test present)
- `LoginManager` — authentication (integration test present)
- All value objects (`Affiliate`, `BasicMemberDetail`, `BasicRegistration`, `JobAccountMapDetails`, etc.)

## Security Posture

### Authentication
- Library-level: no authentication logic — authentication is the caller's responsibility
- `msal4j` dependency present — suggests token-based auth for Azure-integrated operations, but implementation details are in the consuming services
- `RequestContext` carries an `agent` string used throughout — agent is set by the calling service, not verified within this library

### Cryptography
- Crypto is delegated to `xplatformlibrary` (`DES3Cipher`, `RsaCipher`, `JsafeCipher`, etc.)
- This library does not perform its own encryption/decryption of persisted data
- JKS keystore access (for SSO token operations) is implemented in xsso_SVC, not here

### Secrets Management
- No hardcoded credentials detected in source files reviewed
- JNDI DataSources (`JobSvcDataSource`, `EcountCoreDataSource`) — credentials managed by Tomcat container configuration
- Azure AD (`msal4j`) — client ID / tenant / secret expected to be externalised; not visible in this repo

### CVE Exposure
- `cbtsclient 2.1.5` (Wirecard CBTS) — a proprietary client library; CVE status cannot be assessed from the repo alone; vendor support is uncertain
- `XStream` — historically high-CVE library (XXE, deserialization RCE); version managed by parent POM; must verify parent POM version and XStream version in use
- `Hibernate Core` — version managed by parent; Hibernate has had SQL injection and RCE CVEs; version must be verified
- `dom4j` (transitive) — historically vulnerable to XXE; version managed by parent

## Technical Debt
| Item | Severity | Detail |
|---|---|---|
| SNAPSHOT version in production path | High | `6.5.9-SNAPSHOT` — non-deterministic builds; downstream services may pick up unintended changes |
| Wirecard CBTS client (`cbtsclient 2.1.5`) | High | Vendor-heritage dependency; support and patch status unknown |
| Raw Dictionary/Hashtable usage | Medium | `AffiliateFactory` uses untyped `Dictionary` for context — pre-generics API |
| SwarmCache (JGroups multicast) | Medium | Legacy distributed cache; not cloud-native; multicast may not be available in containerised environments |
| No API versioning | Medium | All method signatures are direct Java; no REST or versioned contract |
| Enforcer exclusion list is long | Low | `banTransitiveDependencies` with 8 exclusions — indicates accumulated dependency sprawl |
| `maven.test.skip` default in README | Medium | Tests are documented to be skipped; JaCoCo coverage data is therefore not generated in standard builds |

## Gen-3 Migration Requirements
1. Decompose the monolithic library into domain-specific services (affiliate-service, member-service, payment-service)
2. Replace XStream with a maintained XML/JSON serialisation library (e.g., Jackson)
3. Replace SwarmCache with a cloud-native caching solution (e.g., Redis, Azure Cache)
4. Resolve the CBTS client dependency — assess vendor roadmap or replace with a supported payment network integration
5. Promote SNAPSHOT to a release version and enforce semantic versioning
6. Re-enable and enforce test execution in CI (`maven.test.skip=false`)
7. Implement OpenTelemetry or similar for distributed tracing across library calls

## Code-Level Risks
| Risk | File:Line | Detail |
|---|---|---|
| Untyped `Dictionary` context | `AffiliateFactory.java:18,70` | Raw `Dictionary` passed as context — type-unsafe, error-prone |
| Singleton factory with mutable state | `AffiliateFactory.java:21` | `_singleton` is static and set lazily — potential race condition without synchronization verification |
| `EManageManagerImpl` scope="prototype" | `applicationContext-xSSO.xml` (consumer) | Prototype scope means a new instance per injection — state management responsibility on caller |
| XStream deserialization | Multiple consumers | XStream used to deserialize XML from external sources — XXE and deserialization attack surface if not configured with security settings |
