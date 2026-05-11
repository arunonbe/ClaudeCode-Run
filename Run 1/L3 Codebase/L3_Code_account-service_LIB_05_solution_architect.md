# account-service_LIB — Solution Architect View

## Technical Architecture

### Module Structure

```
accountservice (pom, 4.0.33-SNAPSHOT)
├── account-common (jar)
│   ├── com.ecount.account.constants   — Constants, validation messages, error codes
│   ├── com.ecount.account.domain      — Shared domain objects (ACHTransferDetail, Notification, SmsQueueMessage)
│   ├── com.ecount.account.exception   — AccountServiceException
│   ├── com.ecount.account.service     — IAccountService, IAccountServiceCacheManager (interfaces)
│   └── com.ecount.account.value       — Input/Output value objects for all 11 operations
│   └── com.ecount.core.value          — AutoReorder, BulkUserRegistration, InventoryNotification, ManualReorder
│
└── account-svc (jar)
    ├── com.ecount.account.context     — AccountServiceContext (all external service references)
    ├── com.ecount.account.crcp        — CrcpNotificationService, CrcpServiceConnector + models
    ├── com.ecount.account.dao.jdbc    — DAO implementations + stored procedure wrappers
    ├── com.ecount.account.domain      — Action delegate implementations (AddFunds, RegisterUser, etc.)
    ├── com.ecount.account.helpers     — Delegate interfaces + implementations (EMember, Device, Transfer, Event, etc.)
    ├── com.ecount.account.library     — Business libraries (Validation, Enrollment, Allotment, PaymentSelection, etc.)
    ├── com.ecount.account.service     — AccountServiceImpl, AccountServiceCacheManagerImpl
    ├── com.ecount.account.sms         — SmsNotificationService, SmsQueueService + models
    └── com.ecount.account.util        — EmailValidator, InternationalFlagService, ProgramIdUtils, CacheUtil
```

### Architectural Pattern

The library implements a **Delegate/Command pattern** within a Spring IoC container:
- `AccountServiceImpl` is the facade — it holds references to one `IAccountServiceActionDelegate` per operation.
- Each delegate (`AddFunds`, `RegisterUser`, `IssueCard`, etc.) implements `IAccountServiceActionDelegate.execute(AccountServiceBaseInput, agent, affiliate)`.
- All delegates access external services through `AccountServiceContext`, which is a Spring-injected "service locator" holding all dependency references.
- Input validation is performed on value objects (`input.validate()`) before delegates are invoked.

**AccountServiceContext** (`AccountServiceContext.java`) is a central "mega-context" bean with 25+ injected dependencies — a monolithic service locator anti-pattern that creates tight coupling and makes unit testing difficult.

### Static `accountContext` Field

A critical architectural defect: in both `AddFunds.java` and `RegisterUser.java`, `AccountServiceContext accountContext` is declared `private static AccountServiceContext` (line 74/57 respectively). This means the context is shared across all instances of `AddFunds`/`RegisterUser`. While Spring wires it per-bean, `static` fields break standard Spring lifecycle (injected via `setAccountContext()` which sets a static field). This is thread-unsafe if multiple Spring contexts exist in the same JVM and is a standard Spring anti-pattern.

---

## API Surface

The public API contract is `IAccountService` (`account-common/src/main/java/com/ecount/account/service/IAccountService.java`):

```java
RegisterUserOutput registerUser(RegisterUserInput input, String agent, String affiliate);
ExtendedRegisterUserOutput extendedRegisterUser(ExtendedRegisterUserInput input, String agent, String affiliate);
UpdateUserOutput updateUser(UpdateUserInput input, String agent, String affiliate);
ExtendedUpdateUserOutput extendedUpdateUser(ExtendedUpdateUserInput input, String agent, String affiliate);
IssueCardOutput issueCard(IssueCardInput input, String agent, String affiliate);
AddFundsOutput addFunds(AddFundsInput input, String agent, String affiliate);
StopPaymentOutput stopPayment(StopPaymentInput input, String agent, String affiliate);
SendNotificationOutput sendNotification(SendNotificationInput input, String agent, String affiliate);
SetLocationCodeOutput setLocationCode(SetLocationCodeInput input, String agent);
SetInventoryLocationAttributesOutput setInventoryLocationAttributes(SetInventoryLocationAttributesInput input, String agent, String affiliate);
WithdrawOutput withdraw(WithdrawInput input, String agent, String affiliate);
```

The secondary cache management interface is `IAccountServiceCacheManager` (methods not visible in the read files but the implementation is `AccountServiceCacheManagerImpl`).

**No REST/HTTP API surface is exposed** — this is a Java library, not a web service. Callers invoke via Java method calls within the same JVM.

### Key Input/Output Fields by Operation

| Operation | Notable Input Fields | Notable Output Fields |
|---|---|---|
| `addFunds` | `emember_id`, `amount` (int cents), `tx_id` (UUID), `program_id`, `direct_claim_flag`, `settlement_date`, `dda_number`, `promotion_id`, `taxable` | `txID`, `echeckID`, `vExpressURL`, `completedEventID`, `claimCode` |
| `registerUser` | `partner_user_id`, `registration` (ExtendedRegistration), `secure_profile`, `promotion_id`, `plastic_only` | `ememberID`, `ecountID`, `ibanNumber`, `vExpressURL`, `completedEventID` |
| `withdraw` | `emember_id`, `amount` (long), `withdraw_type`, `dda_number`, `express_flag`, `comment` | (WithdrawOutput) |
| `stopPayment` | `affiliate`, `recipient`, `orig_transfer`, `reversal_activity`, `orig_amount`, `payment_settlement_dt` | (StopPaymentOutput) |

---

## Security Posture

### Authentication & Authorization
- No authentication/authorization logic is present within this library. The `agent` and `affiliate` strings passed to every method are forwarded to downstream XML-RPC calls; they serve as tenant/agent identifiers, not as security credentials.
- OAuth2 client credentials are used for outbound SMS and CRCP calls (`sms.client.secret`, `crcp.client.secret`). These are injected via Spring properties; the source of these properties (Vault, Kubernetes Secrets, etc.) is outside this library's scope.

### Input Validation
- `RegisterUserInput.validate()`: Defaults missing fields (country, phone, email) rather than rejecting them. A missing phone defaults to `610-941-4600` — this is a data integrity risk, not a security control.
- `ValidationLibrary`: Validates partner user IDs for scientific notation (anti-Excel injection), validates character sets in names, enforces password alphanumeric + length requirements.
- `EmailValidator`: Regex-based email validation. The `none@ecount.com` sentinel is explicitly blocked.
- No SQL injection risk in DAO layer: all queries use `JdbcTemplate` with parameterized `?` placeholders (`SmsNotificationConfigDao`, `SmsQueueDao`, `ClaimCodeIssuanceInfoDao`).
- `CrcpNotificationService.sanitizeLog()`: Strips CR/LF (log injection prevention) and ANSI escape sequences from log output.

### Secrets Management
- OAuth secrets (`smsClientSecret`, `crcpClientSecret`) are stored as String fields. The CRCP service logs secrets as `maskSecretForLog()` (returns length only). The SMS service does **not** mask secrets in logs.
- No evidence of StrongBox being called for in-process secret retrieval (StrongBox client is injected but not directly used in the visible code paths).

### Transport Security
- All outbound HTTP calls (`CrcpServiceConnector`, `SmsServiceClient`, `InternationalFlagService`) should use HTTPS. The URLs are injected via properties; enforcement of TLS is assumed at the network level.

### Code Injection / Log Forging
- `CrcpNotificationService.sanitizeLog()` mitigates log injection. However, `AccountServiceDAOJDBCImpl` and `AddFunds` log inputs without sanitization at DEBUG level.

---

## Technical Debt

| Item | Location | Severity | Description |
|---|---|---|---|
| **Static `accountContext` field** | `AddFunds.java:74`, `RegisterUser.java:57` | Critical | `private static AccountServiceContext accountContext` — breaks Spring lifecycle, thread-unsafe with multiple contexts, cannot be mocked per-instance. |
| **Tests skipped in CI** | `.gitlab-ci.yml`, `github-package-publish.yml` | Critical | All CI pipelines skip tests. There are 16 test classes but they never run in CI, providing zero regression protection. |
| **Hardcoded fallback phone** | `RegisterUserInput.validate():89` | High | `registration.setPhone("610-941-4600")` — hardcoded US phone fallback creates invalid cardholder records. |
| **`ThreadLocal<Logger>` anti-pattern** | `AccountServiceImpl`, `AddFunds`, `RegisterUser`, `AccountServiceDAOJDBCImpl` | Medium | Logger held in ThreadLocal instead of `static final` — non-standard, wasteful, and can cause classloader leaks in JEE containers. |
| **Mega-Context anti-pattern** | `AccountServiceContext.java` | Medium | 25+ injected fields on a single context bean — a service locator anti-pattern that hides dependencies and makes testing difficult. |
| **`@SuppressWarnings("unchecked")` raw types** | `SmsNotificationConfigDao.java:144,276` | Medium | Raw `RowMapper` types used instead of generic `RowMapper<NotificationProgramPromotion>`. Indicates legacy Java 1.4-era code style. |
| **SMS secret not masked in logs** | `SmsNotificationService.java` | Medium | `smsClientSecret` is accessible via getter and could be inadvertently logged by callers. No log masking applied unlike CRCP service. |
| **Typo in class name** | `GetCliamablePaymentExpiryDate.java` | Low | Class name is misspelled ("Cliam" instead of "Claim") — propagated through context references. |
| **Commented-out code** | `CardBlockCodes.java:31-41`, `appCtx-AccountService.xml:71`, `cacheManager.xml` | Low | Extensive commented-out code throughout. |
| **`validateEmailAddress` stub** | `ValidationLibrary.java:376` | Low | Method returns `true` unconditionally: `//TODO: implement email address validation`. Email format validation does not actually execute for basic registration validation. |
| **`Vector` and raw `Dictionary`** | `ValidationLibrary.java`, `RegisterUserInput.java`, `AddFundsInput.java` | Low | Uses legacy Java 1.0 `java.util.Vector` and `java.util.Dictionary`. Should be replaced with `List` and `Map`. |
| **`new HashMap()` without generics** | `AddFunds.execute():403` | Low | `Map addendaQuick = (Map) ActionMemo.arrayToDictionary(...)` uses raw types. |
| **`XStream` deserialization** | `pom.xml` dependency `com.thoughtworks.xstream:xstream` | Medium | XStream is known for deserialization vulnerabilities if untrusted input is processed. Verify usage is limited to trusted data. |

---

## Gen-3 Migration Requirements

To migrate this library to a Gen-3 microservice pattern, the following work items are required:

### 1. Protocol Migration (XML-RPC → REST/gRPC)
- Replace `MemberXMLRPCClient`, `DeviceXMLRPCClient`, `TransferXMLRPCClient`, `EventXMLRPCClient`, `ProfileXMLRPCClient`, `StrongBoxXMLRPCClient` with REST clients (e.g., Spring WebClient or Feign) calling Gen-3 equivalents.
- This is a **dependency on Gen-3 versions of the core services** being available first.

### 2. Spring Boot Migration
- Replace Spring XML context files with `@Configuration` Java classes.
- Adopt Spring Boot 3 with auto-configuration.
- Replace `commons-dbcp` with HikariCP.
- Replace jTDS with `com.microsoft.sqlserver:mssql-jdbc`.

### 3. Architectural Refactoring
- Decompose `AccountServiceContext` (mega-context) into typed, scoped dependencies injected directly into each delegate.
- Convert `static accountContext` fields in `AddFunds` and `RegisterUser` to instance fields (`private AccountServiceContext accountContext`).
- Replace `ThreadLocal<Logger>` with `private static final Logger`.

### 4. Test Coverage
- Enable and fix test execution in CI before any migration (currently skipped in both GitLab and GitHub).
- Add integration tests with test containers (SQL Server or H2 for query validation, WireMock for XML-RPC and REST mocks).

### 5. Eliminate Cbase/Citi Platform Dependencies
- Replace `com.cbase.business.*` classes with in-house or Gen-3 implementations:
  - `TransferManagerImpl` / `ECoreTransfer` → Gen-3 transfer service client
  - `VirtualExpressLoginHelper` → Gen-3 virtual express service
  - `AffiliateLocaleSkinHelper` / `AffiliateMapSkin` → Gen-3 affiliate service
  - `DebitAPIController/Helper`, `StrategyProfileHelper` → Gen-3 debit/card service
- Replace `com.citiprepaid.service.*` validators with standard Spring validation or in-house implementations.

### 6. Notification Architecture
- The `SmsQueueService` + `sms_notification_queue` DB table pattern is a viable Gen-3 building block but requires an accompanying queue worker service.
- The `CrcpNotificationService` (REST + OAuth2 + idempotency key + JSON payload) is already Gen-3-aligned and should be preserved/promoted.
- Consider replacing `SmsNotificationService` (legacy direct send) with the CRCP path entirely.

### 7. Configuration & Secrets
- Move OAuth secrets to a secrets manager (Vault, Azure Key Vault, Kubernetes Secrets) rather than property injection.
- Externalize the hardcoded phone fallback `610-941-4600` and sentinel email patterns to configuration.

### 8. Data Layer
- Replace stored procedure-heavy ACH detail flow with event-driven data capture (Kafka/Kinesis).
- Apply field-level encryption or tokenisation to PII fields in `claim_code_issuance_info` and `sms_notification_queue` before Gen-3 deployment.

---

## Code-Level Risks

### Risk 1: Static `accountContext` Field — Thread Safety
**File**: `AddFunds.java:74`, `RegisterUser.java:57`
```java
private static AccountServiceContext accountContext;
```
`setAccountContext()` sets a static field. If multiple Spring `ApplicationContext` instances exist (e.g., in tests or multi-tenant hosting), all instances of `AddFunds` share the same context reference. Last-writer wins, causing unpredictable behaviour.

### Risk 2: Claimable Payment Partial Commit
**File**: `AddFunds.java:238-379`
The claimable choice flow calls `CreateClaimablePayment.execute()` (an external stored procedure), then attempts to insert `ClaimCodeIssuanceInfo` and `ClaimablePaymentAddenda` in separate DAO calls. Each is wrapped in individual try-catch blocks that log and continue. If the SP succeeds but the DAO inserts fail, a claim code is issued with no audit trail and no addenda — a financial integrity risk.

### Risk 3: Null-Safe Logging Bypass in `SmsNotificationConfigDao`
**File**: `SmsNotificationConfigDao.java:213`
`LOG.error("Error getting template config for programId={}, promotion={}, eventId={}", programId, promotion, eventId, e)` — the exception is passed as the fifth argument to SLF4J's four-argument format call. In SLF4J, the last argument is treated as the throwable, so this is correct. However, earlier in the same method `LOG.info("Getting subscriber_id from event_id: {}", eventId)` logs the `eventId` without any sanitisation.

### Risk 4: `InternationalFlagService` — No Timeout on HTTP Client Creation
**File**: `InternationalFlagService.java:22`
```java
HttpClient client = HttpClient.newHttpClient();
```
A new `HttpClient` is created on every call to `fetchInternationalLabelsFromRedis()`. `HttpClient.newHttpClient()` uses a 10-second connect timeout (set on the request), but the client itself has no connection pooling since it is not reused. Under high throughput this creates excessive OS socket handles. Should be a singleton/cached client.

### Risk 5: `XStream` Deserialization
`com.thoughtworks.xstream:xstream` is a declared dependency in `account-svc/pom.xml`. XStream has a well-documented history of remote code execution vulnerabilities when deserializing untrusted XML. The specific usage is not visible in the read files (`DOMParserWrapper`, `XMLParserFactory`, `IBMDOMParser` may use it), but its presence on the classpath in a payments library is a PCI DSS-relevant risk that should be reviewed and replaced if possible.

### Risk 6: Missing Null Check on `restrictedEmailSuffix`
**File**: `ValidationLibrary.java:543`
```java
log.get().debug("restrictedEmailDomainList : "+restrictedEmailDomainList.toString());
```
If `restrictedEmailDomainSuffix` is null (not configured), `restrictedEmailDomainList` is null and calling `.toString()` on it at line 543 will throw a `NullPointerException` at DEBUG log level (only thrown when DEBUG is enabled, making this intermittent). Line 541 correctly handles null by assigning null to the array, but line 543 calls `.toString()` unconditionally before the null check at line 546.

### Risk 7: `SNAPSHOT` Dependency on Parent POM
**Root `pom.xml:8-9`**:
```xml
<groupId>com.parents</groupId>
<artifactId>prepaid-parent</artifactId>
<version>6.0.13</version>
```
The parent version `6.0.13` is a release (not a snapshot), which is correct. However the project itself is `4.0.33-SNAPSHOT`. The enforcer rule `requireReleaseDeps` excludes the parent group from the snapshot check. If any non-excluded dependency uses a SNAPSHOT version, the build will fail — but the enforcer exclusion list is broad (`org.springframework*` is excluded), potentially masking snapshot Spring versions.
