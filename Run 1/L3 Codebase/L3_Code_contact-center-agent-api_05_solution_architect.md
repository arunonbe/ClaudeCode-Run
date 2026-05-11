# contact-center-agent-api — Solution Architect View

## Technical Architecture

### Stack
| Layer | Technology |
|---|---|
| Runtime | Java 21, Spring Boot 3.5.7 |
| Web tier | Spring MVC (Servlet/blocking — `reactive: false` in OpenAPI gen) |
| API contract | OpenAPI 3.0.3, code-generated via `openapi-generator-maven-plugin 7.13.0` with `delegatePattern: true` |
| ORM / DB | Spring Data JPA / Hibernate; dual datasource (`CbaseJpaConfig`, `ECountJpaConfig`) |
| HTTP client | Spring `RestClient` (introduced in Spring 6.1 / Boot 3.2) — synchronous |
| Security | Custom servlet filters (`AuthenticationFilter`, `RequestAuditLoggingFilter`), no Spring Security |
| JWT | `io.jsonwebtoken:jjwt-api:0.12.6`, HMAC-SHA signing |
| Encryption | `javax.crypto.Cipher` AES/GCM/NoPadding |
| Config / Secrets | Azure App Configuration + Azure Key Vault via Spring Cloud Azure 5.23.0 |
| Cache | Spring `ConcurrentMapCacheManager` (default, in-process) |
| Container | Docker (Alpine JRE 21) |
| Orchestration | AKS |
| Testing | JUnit 5, Mockito, Testcontainers (MSSQL), MockServer |

### Code Structure
```
src/main/java/com/onbe/contactcenter/agent/
├── ContactCenterAgentApiApplication.java      # @SpringBootApplication entry point
├── config/                                     # Spring config beans
│   ├── CacheConfig.java                        # @EnableCaching
│   ├── ECountCoreClientConfig.java             # RestClient bean for ECount Core
│   ├── OtpClientConfig.java                    # RestClient bean for OTP service
│   └── properties/                             # @ConfigurationProperties records
├── context/
│   ├── RequestContext.java                     # Per-request state (DDA, memberId, auth type)
│   └── RequestContextHolder.java               # ThreadLocal wrapper
├── datasources/
│   ├── cbase/config/CbaseJpaConfig.java        # JPA config for cbaseapp
│   ├── cbase/model/                            # JPA entities: ServiceRecord, AffiliateDetailScreenGeneral, ApiRequestAuditLog ...
│   ├── cbase/repository/                       # Spring Data repos
│   ├── cbase/service/                          # Data-access services: AffiliateService, CommentHistoryService, RequestAuditService
│   ├── ecount/config/ECountJpaConfig.java      # JPA config for ecountCore DB
│   ├── ecount/model/                           # JPA entities: Card, CoreCardAccountEmbossHistory, ...
│   ├── ecount/repository/                      # Spring Data repos
│   └── ecount/service/                         # EmbossHistoryService, FeeInquiryService, ProfileService
├── domain/
│   ├── ecountcore/service/                     # ECountCoreService, DeviceService, MemberService, TransferService
│   └── otp/service/                            # OtpService, OtpServiceContext
├── security/
│   ├── AuthenticationFilter.java               # Priority tri-mode auth; @Order(HIGHEST_PRECEDENCE+1)
│   ├── RequestAuditLoggingFilter.java          # Audit logging; @Order(HIGHEST_PRECEDENCE)
│   ├── AesDecryptionService.java               # AES/GCM decryption
│   ├── JwtService.java                         # JWT generate + validate
│   └── BaseApiFilter.java                      # OncePerRequestFilter base
├── service/                                    # Delegate implementations (business logic)
│   ├── AccountInquiryService.java
│   ├── AuthenticationService.java
│   ├── CommentService.java
│   ├── PinResetService.java
│   ├── ReissueCardService.java
│   ├── UpdateRegistrationService.java
│   ├── WithdrawFundsService.java
│   ├── exception/                              # ServiceExceptionHandler (@RestControllerAdvice), custom exceptions
│   ├── mapper/RegistrationMappingUtil.java
│   └── validation/                             # RegistrationRequestValidator, UserLookupParameterValidator
└── util/
    ├── ApiConstants.java                       # Header name constants
    ├── DataConversionUtils.java                # Type conversion, masking, transaction type mapping
    └── ProgramID.java                          # Record: programId, product, brand, affiliate
```

---

## API Surface

### Inbound (Public API — openapi.yml)

All endpoints are fronted by APIM at `https://decagonapi.onbe.com`.

| Endpoint | Auth Required | Notes |
|---|---|---|
| `GET /v1/account-inquiry` | Token/EncDDA/DDA | Returns balance, card, transactions, program details |
| `POST /v1/comments` | Token/EncDDA/DDA | Submits cardholder comment to `service_records` |
| `GET /v1/comments` | Token/EncDDA/DDA | Fetches last 14 days of comments |
| `POST /user-auth/lookup` | None (pre-auth) | User identity lookup; returns masked email/phone |
| `POST /user-auth/send-otp` | None (pre-auth) | Triggers OTP delivery |
| `POST /user-auth/verify-otp` | None (pre-auth) | Validates OTP; returns JWT |
| `POST /v1/account/reissue` | Token/EncDDA/DDA | Reissues card with block code |
| `PUT /v1/account/registration` | Token/EncDDA/DDA | Updates cardholder registration fields |
| `POST /v1/account/withdraw` | Token/EncDDA/DDA | Issues paper check withdrawal |
| `POST /v1/account/pin-reset` | Token/EncDDA/DDA | Resets PIN attempt counter |
| `GET /hc` | None | Actuator health probe |
| `GET /metrics`, `GET /prometheus` | None | Actuator metrics |

**Important**: The `AuthenticationFilter` bypasses all authentication for endpoints not matching the filter path (base filter class `BaseApiFilter` determines which paths are skipped — not visible in the provided source but implied by actuator endpoints being unprotected).

### Outbound (Client APIs)

#### ECount Core REST (`ecountcore.yaml`)
Generated client package: `com.onbe.contactcenter.agent.domain.ecountcore.rest.api`

| Endpoint | Called By |
|---|---|
| `GET /device/dda/{dda}` | `DeviceService.getDeviceByDda` |
| `POST /device/inquiry/{deviceId}` | `DeviceService.getDeviceDetailsById` |
| `GET /device/{deviceId}` | `DeviceService.getDeviceById` |
| `GET /device/catalog?memberId=&deviceType=&detailLevel=` | `DeviceService.catalogInquiry` |
| `POST /device/control` | `DeviceService.control` |
| `POST /member/inquiry` | `MemberService.memberInquiry` |
| `POST /member/dda-only-inquiry` | `MemberService.memberInquiryDDAOnly` |
| `GET /member/basic/{memberId}` | `MemberService.getBasicMemberById` |
| `GET /member/extended/{memberId}` | `MemberService.getExtendedMemberById` |
| `GET /member/{memberId}/device/{deviceType}` | `MemberService.getMemberDeviceInfo` |
| `PUT /member/extended/{id}` | `MemberService.updateExtendedRegistration` |
| `POST /transfer/begin` | `TransferService.beginTransfer` |
| `POST /transfer/commit` | `TransferService.commitTransfer` |

#### OTP Service (`otpapi.yaml`)
Generated client package: `com.onbe.contactcenter.agent.domain.otp.rest.api`

| Endpoint | Called By |
|---|---|
| OTP generate | `OtpService.generateOtp` |
| OTP validate | `OtpService.validateOtp` |

---

## Security Posture

### Strengths
- **AES/GCM encryption** for DDA in the CHAT channel — industry-standard authenticated encryption.
- **JWT with HMAC-SHA** for session management — secret in Key Vault, 20-minute expiry.
- **Secrets from Azure Key Vault** — no plaintext secrets in repo or config files (placeholders only in `application.yml`).
- **PAN masking** (`DataConversionUtils.maskCardNumber`) before API responses — PAN is never returned in full.
- **Email/phone masking** in user-lookup responses.
- **DDA masking in logs** — `maskDda` called in `AuthenticationService`.
- **Filtered audit headers** — only `encryptedDDA` and `channel` logged, not `token` or `accountNumber`.
- **CodeQL SAST** on every push to main and weekly schedule.
- **Trivy vulnerability scanning** (`.trivyignore` present).

### Weaknesses / Gaps

#### 1. Static AES-GCM IV (`AesDecryptionService.java`, line 31)
```java
GCMParameterSpec parameterSpec = new GCMParameterSpec(TAG_LENGTH_BIT, encryptionConfigProperties.ivKey().getBytes());
```
The IV is loaded from a fixed Key Vault value. GCM nonce uniqueness is required for security — reusing the same IV with the same key enables attackers to XOR two ciphertexts and recover the key stream. **Severity: High.**

#### 2. `trustServerCertificate=true` in JDBC URLs (`app-config/prod/appsettings.json`)
Disables server certificate verification for SQL Server connections. This allows MITM attacks on DB connections and violates PCI DSS Requirement 4.2.1. **Severity: High.**

#### 3. Plain DDA in JWT payload (`JwtService.java`, lines 43-44)
```java
.claim("ddaNumber", ddaNumber)
```
JWT is base64-encoded, not encrypted. The DDA (16-digit account number) is readable by any party who intercepts the token without breaking the signature. The OpenAPI spec shows the `token` header is transmitted with every protected request. Consider using JWE (JWT Encryption) or storing DDA as an opaque reference. **Severity: Medium.**

#### 4. Plain DDA in `service_records.dda_number` (cbaseapp)
Written by `CommentHistoryRepository.insertComment`. This table also stores cardholder `problemDescription` (comment text), making it a PCI DSS CDE table requiring additional physical and logical access controls. **Severity: Medium.**

#### 5. Plain accountNumber auth mode (`AuthenticationFilter.java`, lines 80-83)
```java
} else if (StringUtils.hasText(accountNumber) && isValidAccountNumber(accountNumber)) {
    context.setAuthenticationType(RequestContext.AuthenticationType.ACCOUNT_NUMBER);
    context.setAccountNumber(accountNumber);
```
Any caller who knows a valid 16-digit DDA can authenticate without OTP. If the API is accessible from outside the APIM trust boundary this is a direct account access risk. **Severity: Medium** (depends on APIM policy enforcement).

#### 6. No Spring Security — custom filter chain only
The authentication is enforced by a custom servlet filter (`AuthenticationFilter`). There is no Spring Security, no `@PreAuthorize`, and no method-level security. All path-level access control is implicit (the filter rejects requests without valid auth context). Any new endpoint added to the OpenAPI spec would be unprotected unless the filter covers the path. **Severity: Medium.**

#### 7. `UserAuthenticationException` mapped to HTTP 500 (`ServiceExceptionHandler.java`, lines 131-142)
OTP send/verify failures map to `INTERNAL_SERVER_ERROR`. A caller cannot distinguish a legitimate server error from an authentication failure. This may assist enumeration-prevention but returns incorrect semantics per OpenAPI spec (which declares 401/400 for these cases). **Severity: Low.**

---

## Technical Debt

| Item | Location | Impact |
|---|---|---|
| `CMD ["$JAVA_ARGS"]` exec-form shell variable non-expansion | `Dockerfile`, line 39 | JVM heap limits not applied; potential OOM in production |
| Static AES-GCM IV | `AesDecryptionService.java` line 31 | Cryptographic weakness (see Security Posture) |
| `@SuppressWarnings("unchecked")` on `Map<String, Object>` cast | `PinResetService.java` line 62 | ECount Core control response is untyped `Object` — brittle cast |
| `setIfBlank` suppresses exceptions silently | `UpdateRegistrationService.java` lines 93-106 | Prefill errors in registration are swallowed; could cause incomplete data updates |
| `DeviceService.control` returns raw `Object` | `DeviceService.java` line 103, `ECountCoreService.control` line 193 | No type safety; callers must cast and suppress warnings |
| No distributed tracing | `pom.xml`, `logback-spring.xml` | No correlation IDs; debugging distributed failures requires manual log correlation |
| All CI tests skipped | `deployment.yml` line 31: `-DskipTests` | No test gate on the deployment pipeline |
| `skipIntegrationTests=true` default | `pom.xml` line 41 | Integration tests never run unless explicitly enabled |
| `show-sql: true` | `application.yml` line 25 | Hibernate SQL logging is enabled globally; may expose query structure and parameter values in non-local environments |
| `CommentHistoryRepository` bypasses ECount Core for comment writes | `CommentHistoryRepository.java` | Direct JDBC write to `cbaseapp` schema; tightly coupled to legacy DB schema |
| Fixed `checkOperator` UUID hardcoded in default `application.yml` | `application.yml` line 96 | `E45B78C8-D73E-46F4-A24B-0014E7A9E9D7` — same UUID present in QA `appsettings.json`; not overridden in prod `appsettings.json` (possible oversight) |

---

## Gen-3 Migration Requirements

To fully align with Gen-3 standards, the following changes are needed:

1. **Eliminate direct JDBC to `cbaseapp`**: Replace with a `cbase-service` API for `service_records` and program metadata. This decouples the cardholder servicing domain from direct schema access and enables independent scaling and security boundaries.

2. **Eliminate direct JDBC to `ecountCore` DB**: Replace emboss history and profile label reads with ECount Core REST API endpoints. Raises a request to the ECount Core team to expose `/device/{id}/emboss-history` and `/profile/{id}/labels`.

3. **Fix AES-GCM IV**: Coordinate with Decagon/MPV Chat Widget to adopt per-message random IVs (prepended to ciphertext). Update `AesDecryptionService` to extract IV from ciphertext prefix.

4. **Fix `trustServerCertificate`**: Deploy valid TLS certificates to `nam.wirecard.sys` SQL Server instances (infrastructure team dependency) and remove `trustServerCertificate=true` from JDBC URLs.

5. **Distribute secrets per service**: Create service-specific Key Vault secrets for DB credentials instead of sharing `managepaymentapi-*` names.

6. **Add distributed tracing**: Add `micrometer-tracing-bridge-otel` and an OTLP exporter dependency; configure correlation ID propagation. Align with Dynatrace OpenTelemetry setup.

7. **Replace in-process cache with distributed cache**: Add Azure Cache for Redis (or equivalent) for `appProfileLabelTypes` to support multi-pod consistency.

8. **Fix Dockerfile `CMD`**: Change to shell form or pass JVM args via `JAVA_TOOL_OPTIONS` environment variable so heap settings take effect.

9. **Re-enable CI test gate**: Remove `-DskipTests` from CI Maven args; at minimum run unit tests on every push.

10. **Encrypt JWT payload or use opaque session tokens**: Avoid embedding raw DDA in JWT. Options: JWE, or replace `ddaNumber` claim with a server-side session reference.

---

## Code-Level Risks

### Risk 1: Unchecked cast in PinResetService
**File**: `PinResetService.java`, line 62
```java
@SuppressWarnings("unchecked")
var res = (Map<String, Object>) eCountCoreService.control(inquiryControlRequest);
```
`DeviceService.control` returns `Object`. If ECount Core changes its response shape (e.g., returns a list instead of a map), this cast throws `ClassCastException` and the endpoint returns HTTP 500 with no useful diagnostic.

### Risk 2: Prefill exception suppression in UpdateRegistrationService
**File**: `UpdateRegistrationService.java`, lines 93-106
```java
} catch (Exception ignored) {
    // Be safe: do not propagate issues in prefill
}
```
Silent failure during prefill from existing registration means partial registration updates could proceed with null/blank fields instead of preserving the cardholder's existing data. Callers may not detect this.

### Risk 3: `show-sql: true` in application.yml
**File**: `application.yml`, line 25
Hibernate logs every SQL statement. In non-local environments this exposes query parameters (including DDA numbers and member IDs in query predicates) to the log output. The logback config does not filter Hibernate logs.

### Risk 4: `checkOperator` UUID not set in prod appsettings
**File**: `app-config/prod/appsettings.json` (absent entry) vs `app-config/qa/appsettings.json` line 16
The QA config sets `api.settings.withdrawFund-service.checkOperator = "E45B78C8-D73E-46F4-A24B-0014E7A9E9D7"`. The prod config does not have this key. The `application.yml` default is the same UUID. If prod requires a different operator device ID, the QA/default value would be silently used, potentially routing withdrawals to the wrong operator device.

### Risk 5: `cardPartnerUserId` missing from AccountInquiryResponse
**File**: `AccountInquiryService.java`, `openapi.yml` `CardDetail` schema
The `openapi.yml` `CardDetail` schema includes `partnerUserId` (example value `"398adf81"`), but `AccountInquiryService` does not populate this field when building `cardBuilder`. It will always return `null`. This may affect downstream consumers expecting it.

### Risk 6: ECount Core fallback DDA-only path ignores errors silently
**File**: `ECountCoreService.getAccountDetailByDda`, lines 38-59
The DDA-only fallback (`memberInquiryDDAOnly`) catches a broad `Exception` on the inner call and logs it, then falls through to return `Optional.empty()`. If the member inquiry endpoint is transiently failing, the account will appear not found rather than returning an error, which could mislead callers into thinking the account does not exist.

### Risk 7: `OtpClientConfig` not shown — potential missing bean
The `pom.xml` and `application.yml` reference OTP service configuration (`shared-services.otp-service`), and there is an `OtpClientConfig.java` file, but its contents were not in the main glob results (suggesting it may be a simple `RestClient` bean similar to `ECountCoreClientConfig`). If misconfigured, OTP calls will silently fail with a connection error rather than a clear startup failure.
