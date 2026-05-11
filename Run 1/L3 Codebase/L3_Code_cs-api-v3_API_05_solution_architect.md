# Solution Architect View — cs-api-v3_API

## Architecture
Multi-module Maven project (7 modules) producing both a WAR artifact and a Spring Boot executable JAR. Business logic is cleanly separated into action classes (one class per operation). The Spring Boot `@Configuration` class (`AccountManagementBeanConfiguration`) programmatically replaces all legacy XML context files, wiring 50+ Spring beans including the full AffiliateService stored-procedure stack and the CommentService DAO stack.

```
cs-api-v3_API/
├── csapi-v3-rest-client/         HTTP client wrappers (MemberServiceImpl, DeviceServiceImpl)
├── csapi-v3-api/                 Core action classes
│   └── src/main/java/com/ecount/one/cs/
│       ├── action/
│       │   ├── SearchAccount.java        (~867 lines — inquiry logic, PPD, comments, DDA)
│       │   ├── UpdateAccount.java        (~600 lines — update, Redis, KYC, audit comment)
│       │   ├── ReissueCard.java          Card reissue + audit
│       │   ├── HandleEscalation.java     CS escalation
│       │   ├── PayoutSearchAccount.java  Payout-specific inquiry
│       │   ├── BaseAction.java           Shared request context init, affiliate ID generator
│       │   ├── helper/SQLInjectionScrubber.java
│       │   ├── helper/ProgramIdAwareGlobalRequestIDGenerator.java
│       │   └── validation/ActionValidator.java
│       └── value types (AccountInquiry, AccountProfile, CommentHistory, PaymentDetail, ...)
├── csapi-v3-ws/                  SOAP endpoint + legacy XML context files
│   └── AccountManagementJaxRPC.java   (Axis JAX-RPC servlet handler)
├── csapi-v3-war/                 WAR packaging + Dockerfile
├── csapi-v3-payout-ws/           Payout sub-service
│   └── action/PayoutSearchAccount.java, UpdateRegistrationAction.java, XSecurity.java
├── csapi-v3-payout-war/          Payout WAR packaging
├── csapi-v3-boot/                Spring Boot entry point
│   └── config/
│       ├── AccountManagementBeanConfiguration.java   (~700 lines — ALL bean wiring)
│       ├── ECountSystemConfiguration.java            xPlatform bootstrap
│       ├── XmlContextImportConfiguration.java        Legacy XML import shim
│       └── datasources/                              HikariCP DataSource configs (3)
├── applicationContext-CSWS.properties   (QA config artifact — COMMITTED — contains JWE keys)
└── wsdl.xml                             (Published to APIM)
```

## API Surface
```
WSDL: /services/AccountManagement?wsdl (published via APIM as CardManagementAPIV3)
Endpoint: POST /services/AccountManagement

Operations:
1. searchAccount
   Input:  application_id, card_number, puid, ppd, mobilePhone,
           balance_detail, journal_detail, registration_detail,
           start_date, end_date, max_items
   Output: AccountInquiry (Balance, CardDetail+shipDate, TransactionDetail[]+PPD,
           PaymentDetail[], CommentHistory[], Registration, Response)
   Errors: 34001 (invalid app_id), 34002 (missing identifier), 34003–34009

2. updateAccount
   Input:  AccountProfile (application_id or program_id, puid, address, name,
           phones, email, country — international supported)
   Output: Response (code int, message String)
   Errors: 35001 (invalid app_id), 35002 (parse error), 35003 (email), 36010 (access denied)

3. reissueCard
   Input:  application_id, card_number or puid
   Output: Response

4. handleEscalation
   Input:  EscalationRequest (application_id, puid, escalation details)
   Output: Response

Payout WSDL: /CardManagementPayoutV3/services/AccountManagement
Payout operations: payoutAccountInquiry, authenticationReq, forgotUserNameReq,
                   registrationReq, updatePasswordReq, updateRegistrationReq
```

## Security Architecture
| Control | Implementation | Assessment |
|---|---|---|
| Application authentication | AffiliateService dynamic lookup (`cs_api_v3_app_id`) | Strong — revocable without redeploy |
| Authorisation | `cs_api_enabled` + `cs_api_v3` + `kyc_required` flags per affiliate | Fine-grained; three-level gate |
| Merchant name control | `cs_api_disp_merchant_name` flag per affiliate | Affiliate-controlled |
| Transport | HTTPS at container/APIM level | Adequate if TLS 1.2+ enforced at APIM |
| Card masking | First-4 + XXXXXXXX + last-4 | PCI DSS compliant for display masking |
| DDA encryption | JWE (AES/HMAC-SHA256) via JweHelper | Implemented; key material committed to repo — critical gap |
| SQL injection | SQLInjectionScrubber (quote equalisation + wildcard strip) for PPD/phone search | Present for high-risk search paths |
| Input validation | ActionValidator (length, format, charset) | Comprehensive |
| OFAC email restriction | RestrictedEmailDomainName list checked on update | Present; list in config (not OFAC API) |
| Payout auth | XSecurity service + JWE token | Implemented |
| Secrets management | Azure App Config + Key Vault (Managed Identity) | Strong for JDBC; gap for JWE keys |
| Rate limiting | None at application layer; APIM rate limiting assumed | Relies entirely on APIM policies |
| Request correlation | ProgramIdAwareGlobalRequestIDGenerator + Log4jMDCWriter | MDC-based; affiliate ID in every log line |

## Critical Findings

### JWE Encryption Keys Committed to Source Control
`applicationContext-CSWS.properties` (at repository root, committed) contains:
- `jwe.secretKey` — AES key for DDA number encryption
- `jwe.secretToken` — JWE token signing key

These are production-equivalent keys that anyone with repository access can read. Any DDA number encrypted with these keys can be decrypted. **Immediate action required**: rotate both keys, store in Azure Key Vault, remove the file from the repository (including git history), and update the App Config references.

### SearchAccount Action Class Size
`SearchAccount.java` is ~867 lines with multiple distinct responsibilities: affiliate lookup, member search (PUID / PPD / mobile / DDA paths), device inquiry (standard + FiservDR resilient paths), balance assembly, PPD data assembly, comment history assembly, and card masking. This is approaching the same monolith pattern as V2's AccountManagementImpl. The inquiry orchestration should be extracted into separate sub-services or a builder pattern.

### Per-Request Bean Lookup in JAX-RPC Handler
`AccountManagementJaxRPC` uses `ApplicationContext.getBean("searchAccount")` per request (Axis service locator pattern). Since the beans are Spring singletons, this is not a per-request instantiation problem (unlike V2), but it is a code smell — the actions should be injected directly into the Axis servlet handler.

### `allow-circular-references: true` in Spring Boot 3
Spring Boot 3 disabled circular reference support by default. The forced re-enablement in `application.yml` indicates a wiring issue in the legacy XML context or the Axis integration. This should be investigated and resolved by breaking the circular dependency.

## Technical Debt Inventory
1. **Apache Axis 1.4 retention**: EOL SOAP framework running on Java 21. The protocol boundary is maintained for client compatibility, but Axis itself has security vulnerabilities and no vendor support. A JAX-WS or REST migration path should be planned.
2. **`applicationContext-CSWS.properties` in repo root**: A QA-environment config file committed to the repository root. Contains encryption keys and internal hostnames. Must be removed from version control.
3. **`allow-bean-definition-overriding: true`**: Required to allow Boot-defined beans to override JNDI-based beans imported from XML. Indicates not all XML context loading has been eliminated.
4. **SearchAccount size**: ~867 lines; multiple search paths could be separate strategy implementations.
5. **Jakarta Servlet shim**: `csapi-v3-payout-ws` includes a `jakarta/servlet/http/HttpUtils.java` — a manual backport/shim of a removed API. This is a compatibility patch that should be addressed at the dependency level.
6. **Payout credentials in plain XML comment** (csapiws): The standalone csapiws-payout_API repo carries this risk; within V3 itself the payout config is clean.

## V3 Spring Boot Migration Assessment
The `csapi-v3-boot` module represents a complete and well-executed migration from XML-based Spring context loading to Java `@Configuration`. All bean names are preserved for compatibility with Axis `getBean()` lookups. The `AccountManagementBeanConfiguration` class (~700 lines) correctly wires:
- Full AffiliateService stored-procedure stack (17+ StoredProcedure beans)
- Full CommentService DAO stack (10+ DAO beans)
- 3 HikariCP DataSources (CbaseApp, JobSvc, EcountCore)
- Hibernate SessionFactory for AffiliateService
- Resilience4j circuit breaker for ecount-core REST clients
- Request ID generation with MDC propagation
- All action beans (searchAccount, updateAccount, reissueCard, handleEscalation, payoutSearchAccount)

This is the reference pattern for how other legacy CS WAR services should be migrated to Spring Boot.
