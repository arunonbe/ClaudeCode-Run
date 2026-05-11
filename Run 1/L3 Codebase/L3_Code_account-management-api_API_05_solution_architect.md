# account-management-api_API — Solution Architect View

## Technical Architecture

### Module Layout
```
accountmanagementapi/                          (root POM, version 3.1.8)
├── accountmanagementapi-impl/                 (service + domain logic)
│   ├── domain/                                (Input/Output POJOs)
│   ├── service/                               (18 service implementations)
│   ├── helper/                                (AccountHelper, JWEHelper, CardEncryptionHelper, ...)
│   ├── affiliate/dao/                         (JDBC: CheckClaimableFlagQuery, PromotionBelongToProgramSP)
│   ├── instant/issue/dao/                     (ManageCardDao, InstantIssueCardDetailRowMapper)
│   ├── oauth/                                 (EndClientOAuthTokenProvider)
│   ├── exception/                             (BusinessValidationException, SystemFailureException, ...)
│   └── validator/                             (input validators)
├── accountmanagementapi-ws/                   (SOAP interface + handler)
│   ├── ws/                                    (AccountManagementApiWebServiceImpl, ProvisionServiceApiWebServiceImpl)
│   ├── handler/                               (AccountManagementHandlerImpl — orchestration)
│   ├── request/ + response/                   (SOAP message POJOs)
│   └── domain/                                (SOAP domain objects: Card, Load, Registration, ...)
├── accountmanagementapi-war/                  (WAR packaging — legacy)
│   └── WEB-INF/ web.xml, Spring XMLs, Axis
├── accountmanagementapi-boot/                 (Spring Boot executable JAR)
│   ├── config/                                (Java @Configuration classes replacing XML)
│   ├── datasources/                           (auto-configured JDBC datasources)
│   ├── health/                                (HealthCheck @RestController)
│   └── resources/config/*.yaml               (classpath config files)
└── accountmanagementapi-sasi/                 (disabled — commented out in root POM)
```

### Request Processing Pipeline

```
SOAP Request
  → AuthenticationCheckFilter (com.citi.prepaid.security.api.filter)
  → AxisServlet (/services/*)
  → AccountManagementApiWebServiceImpl
      → AccountManagementHandler (AOP proxy: GlobalRequestIDInterceptor + AuditMethodInterceptor)
          → AccountManagementHandlerImpl
              → Input validation (Validator beans)
              → [ServiceClass].execute(memberID, input)
                  → SecurityValidator.authorize() [AOP proxied via AuditMethodInterceptor]
                  → TestAPI.testMode() check
                  → SynchronousOrderProcessor.processSweepRequest()
                  → Response assembly (card data, claim codes, VirtualExpressURL)
              → ServiceOutput → Response POJO
  → SOAP Response
```

### Key Design Patterns
- **Template Method**: `AccountManagementApiServiceImpl` is an abstract base class with `process()` as the template. Subclasses override `execute()` and optionally `validateAPISecurity()` and `performRecipientScreening()`.
- **Strategy via Security Feature Flags**: Card number return format (plain / AES-encrypted / Visa JWE) is selected by security domain feature authorization — no if/else on fixed config but on runtime-authorized security features.
- **AOP Proxy Chain**: All handler and security validator beans are wrapped in `ProxyFactoryBean` with named interceptors.
- **Setter Injection throughout**: No constructor injection; all service beans use setter-based DI configured in `AccountManagementApiConfiguration` — a pre-Spring 4.x pattern.
- **Synchronous blocking HTTP Invoker**: Remote calls are fully synchronous; no reactive or async patterns.

## API Surface

### SOAP Web Service
- Endpoint: `/services/AccountManagementApiWebServices`
- WSDL: `wsdl.xml` (root), `accountmanagementapi-boot/wsdl/wsdl.xml`
- Interface: `AccountManagementApiWebService extends java.rmi.Remote`
- Operations (18): `createAccount`, `updateAccountStatus`, `updateRegistration`, `updateProvisionStatus`, `addFunds`, `linkCard`, `assignPackage`, `createPackage`, `createBulkOrder`, `setPin`, `withdraw`, `activationStatusInquiry`, `activateCard`, `cardInquiry`, `cvvInquiry`, `getBalance`, `getRequestStatus`, `stopPayment` (handler has stopPayment but WebService interface has it commented out)

### REST Endpoints (Spring Boot only)
- `GET /hc` — Health check (returns `"OK"` or `"DOWN"`)
- `GET /actuator/health` — Spring Boot Actuator health
- `GET /actuator/info` — Spring Boot Actuator info

### Common Request Parameters (ServiceInput base class)
- `partner_user_id` — partner-side account identifier
- `program_id` — Onbe program identifier (composite: product/brand/affiliate)
- `promotion_id` — promotion within program
- `transaction_id` — idempotency key
- `accountNumber` — ecount DDA account number
- `relationshipId` — End Client relationship ID (newer addition)
- `message_id` — correlation ID returned in response

### Notable Security Feature Gates (api-security.yaml)
- `Return-Card-Number` — enables card number in `CreateAccountOutput` / `CardInquiryOutput`
- `Return-VISA-JWE` — card number wrapped in Visa JWE (AES-256-GCM)
- `Return-Encrypted-Card` — card number AES-CBC encrypted
- `Return-CVV` — enables CVV in `CvvInquiryOutput` (encrypted)

## Security Posture

### Authentication & Authorization
- `AuthenticationCheckFilter` from `api-security-lib:3.0.1` applied to all URLs (`/*`) — validates caller identity
- `CandidateStore.getCandiate()` retrieves the authenticated `EntityCandidate` from thread-local context
- Each API method registers itself as a Security Domain (`DomainPropertyType.API=AccountManagement`, `DomainPropertyType.METHOD=<methodName>`) during Spring `initialize()` via `entityModel.register(domain)`
- Per-operation authorization via `SecurityValidator.authorize(candidate, domain)` — if false, throws `BusinessValidationException(ACCESS_DENIED)`
- Sensitive data return is gated by additional feature-level domain authorization (e.g., `Utility.createProgramDomain(securityAPIName, securityMethodName, programId, securityFeatureNameReturnCVV)`)

### Encryption
- **CVV**: AES/CBC/PKCS5Padding, 256-bit key derived from SHA-256(sharedSecret), random 16-byte IV prepended to ciphertext, Base64 output (`CardEncryptionHelper`)
- **Card number (Visa JWE)**: AES-256-GCM with A256GCMKW key wrapping, per Visa JWE spec (`JWEHelper`)
- **DDA**: JWE encryption when `jwe.encryptDDA=Y`
- **In-transit**: TLS (Wirecard NAM CA imported for internal service trust)
- **Secret storage**: Azure Key Vault via Managed Identity (non-local environments); connection string for local

### Known Security Issues
1. **Shared secret logged at DEBUG** (`CvvInquiryService` line 64): `log.debug(">>> Retrieved Shared Secret : " + profile.getSharedSecret())` — if `com.citi` DEBUG logging is active, program shared secrets appear in logs.
2. **Hardcoded DDA encryption key**: `jwe.secretKey` in `accountmanagementapi.yaml` has a default value in source code. PCI DSS Req 3.6 requires cryptographic key management outside of source repositories.
3. **BouncyCastle 1.60**: This is a 2018 release with known CVEs (`.trivyignore` suppresses some). The `AESFastEngine` class used in `JWEHelper` is deprecated in newer BouncyCastle versions.
4. **Recipient screening non-blocking**: `performRecipientScreening()` catches all exceptions and continues — OFAC/AML screening failures do not block account creation.
5. **TestAPI bean present in all service instances**: Can simulate processing failures, delays, or timeouts. No production environment guard in code.
6. **`allow-circular-references: true`**: Masks Spring context initialization issues.
7. **`axis.disableServiceList: 1`**: Axis service listing is disabled (good), but Axis's attack surface (arbitrary SOAP endpoints) remains present.

## Technical Debt

| Item | Severity | Evidence |
|---|---|---|
| Apache Axis SOAP (2003-era) | Critical | `AxisServlet`, `server-config.wsdd`, `org.apache.axis.*` in `WebConfiguration` |
| Spring HTTP Invoker for RPC | High | `SynchronousOrderProcessor`, `OrderService` interface used as remote proxy — Java serialization over HTTP (deprecated in Spring 6) |
| Setter-only Spring DI (no constructor injection) | Medium | All `set*()` methods in service classes; `AccountManagementApiConfiguration` |
| `allow-circular-references: true` | High | `application.yml` line 37 |
| `allow-bean-definition-overriding: true` | Medium | `application.yml` line 36 |
| BouncyCastle 1.60 | High | `pom.xml` `bouncycastle.version=1.60`; `.trivyignore` present |
| Duplicate `process()` logic | Medium | `processWebRequest()` in `CreateAccountService` duplicates 400+ lines of `process()` from `AccountManagementApiServiceImpl` |
| `TestAPI` in production bean graph | Medium | `AccountManagementApiConfiguration.testAPI()` bean wired into every service |
| `java.rmi.Remote` interface | Medium | `AccountManagementApiWebService extends java.rmi.Remote` — RMI semantics for a SOAP service |
| `jakarta.servlet.http.HttpUtils` shim | Low | `accountmanagementapi-ws/src/main/java/jakarta/servlet/http/HttpUtils.java` — suggests a patched or shimmed Jakarta class for Axis compatibility |
| Spring XML context files | Medium | `accountmanagementapi-implContext.xml`, `accountmanagementapi-wsContext.xml` still exist in WAR module alongside Java configuration |
| Raw unchecked Map usage | Low | `PromotionBelongToProgramSP.execute()` uses raw `Map in = new HashMap()` and `Map out` without generics |
| Bare `catch(Exception ex){}` | High | `logActionResults()` in `AccountManagementApiServiceImpl` line 462 silently swallows exceptions during logging |

## Gen-3 Migration Requirements

The following items must be addressed to migrate this service to a fully Gen-3 posture:

### Must-Do (Blockers)
1. **Replace Apache Axis with CXF or Spring-WS** (or REST migration): Requires new endpoint implementations and partner client coordination. The WSDL must be preserved or versioned carefully.
2. **Replace Spring HTTP Invoker**: Order Service, Job Service, and Banker Service must expose REST or gRPC APIs. This is a multi-team coordination item.
3. **Resolve circular bean dependencies**: Remove `allow-circular-references: true` by refactoring bean initialization order or splitting configuration classes.
4. **Upgrade BouncyCastle**: Minimum upgrade to 1.77+ to address known CVEs. Verify `JWEHelper` API compatibility.
5. **Remove hardcoded `jwe.secretKey` default from source**: Enforce fail-fast if secret not present in Key Vault.
6. **Eliminate TestAPI from production bean graph**: Restrict to test/dev profiles via `@Profile("!production")`.

### Should-Do (Quality & Compliance)
7. **Fix recipient screening to be blocking**: Non-blocking OFAC screening (`performRecipientScreening()` catching all exceptions) violates AML compliance expectations. Screening failure should return an appropriate error code.
8. **Remove debug logging of shared secrets**: Remove `log.debug(">>> Retrieved Shared Secret : " + ...)` from `CvvInquiryService` and any similar patterns.
9. **Switch to constructor injection**: Refactor all service beans to use constructor injection for mandatory dependencies.
10. **Eliminate duplicated `processWebRequest()`**: `CreateAccountService.processWebRequest()` is a ~400-line copy of the parent `process()` method with minor variation. Extract or refactor.
11. **Add `@Profile` guards on JNDI bean definitions**: `EcountCoreDataSource` and `CbaseappDataSource` JNDI beans should be WAR-only profile to prevent confusion in Boot deployment.
12. **Consolidate to single packaging target**: Once Tomcat VM deployment is decommissioned, remove `accountmanagementapi-war` module.

### Nice-to-Have
13. **Upgrade to newer security library pattern**: Replace `AuthenticationCheckFilter` + `CandidateStore` + `SecurityValidator` with Spring Security if appropriate for the platform.
14. **Structured logging**: Replace `log.info("key=" + value)` string concatenation with structured MDC-based logging throughout.
15. **PACT provider verification**: `VERIFY_PROVIDER_PACT: false` in `deployment.yml` — enable once provider PACT contracts are established.

## Code-Level Risks

### Critical
- **`catch(Exception ex){}`** in `AccountManagementApiServiceImpl.logActionResults()` (line 462): An unchecked exception during log assembly silently swallows errors. If the `ProcessSweepResponse` object graph is malformed, no error propagates.
- **`performRecipientScreening()` non-blocking** (`CreateAccountService` lines 103–121): All exceptions caught and logged only. Screening failure is invisible to the caller and does not prevent account creation.
- **Shared secret at DEBUG log level** (`CvvInquiryService` line 64): AES shared secret for CVV encryption exposed in logs when DEBUG is active.

### High
- **`processWebRequest()` bypasses `validateAPISecurity()` and `testAPI()`** (`CreateAccountService` lines 221–226): These calls are commented out in `processWebRequest()`, meaning ClientZone requests skip security validation entirely. This is an access control bypass for a specific entry point.
- **Integer overflow on withdraw amount**: `withdrawaction.setAmount((int)withdrawInput.getAmount())` in `WithdrawService` line 114 casts a `double` or `long` to `int`. If the amount exceeds `Integer.MAX_VALUE` (2,147,483,647 cents = ~$21M), the cast silently wraps to a negative or wrong value.

### Medium
- **`SimpleDateFormat` thread-safety**: `RegistrationInput.parseDateOfBirth()` creates new `SimpleDateFormat` instances per call (safe) but is non-threadsafe if ever refactored to a shared instance.
- **`SKEW_SECONDS = 60` in `EndClientOAuthTokenProvider`**: Clock skew of only 60 seconds may cause token expiry edge cases in high-latency environments.
- **`PromotionBelongToProgramSP` using raw `Map`**: Unchecked cast from `out.get("countValue")` to `Integer` — will throw `ClassCastException` if stored procedure returns a different type.
- **`ClaimableFlagQueryException` swallowed downstream**: If `CheckClaimableFlagQuery.execute()` throws, the exception propagates upward through the service but there is no explicit handler in `AccountManagementApiServiceImpl.process()` for this type — it will become a `SystemFailureException`.

### Low
- **`account.mngmt` app name in request IDs** (`RequestAwareGlobalRequestIDGenerator` line via `AccountManagementApiConfiguration`): Truncated name may cause confusion in log correlation.
- **WSDL placeholder namespace**: `wsdl.xml` uses `http://example.com/soap` as the target namespace — this appears to be a placeholder/stub WSDL, not the operational WSDL. The actual operational WSDL is served dynamically by Axis from `server-config.wsdd`.
