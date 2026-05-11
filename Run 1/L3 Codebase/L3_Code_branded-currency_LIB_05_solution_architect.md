# branded-currency_LIB — Solution Architect View

## Technical Architecture

### Module Structure
```
branded-currency (root POM, v3.0.3, packaging=pom)
├── branded-currency-common (JAR)
│   └── src/main/java/com/ecount/one/service/brandedcurrency/
│       ├── core/CoreObject.java                          — DataSource interface
│       ├── dao/BrandedCurrencyDAO.java                   — Aggregate DAO interface
│       ├── purchase/
│       │   ├── payment/Payment.java, PaymentVO.java, PaymentDAO.java, PaymentConstraint.java
│       │   └── certificate/Certificate.java, CertificateVO.java, BasketCertificateVO.java,
│       │                    CertificateDAO.java, CertificateTemplate.java, BasketCertificateList.java
│       ├── transaction/
│       │   ├── UserTransaction.java, UserTransactionVO.java, UserTransactionImpl (in impl)
│       │   ├── ClaimTransaction.java, ClaimTransactionVO.java
│       │   ├── CertificatePurchaseTransaction.java, CertificatePurchaseTransactionVO.java
│       │   ├── AddFundsTransaction.java, AddFundsTransactionVO.java
│       │   ├── BulkPurchaseTransaction.java
│       │   ├── Constraint.java, ConstraintVO.java
│       │   ├── CreditCardVO.java
│       │   ├── TransactionDAO.java, TransactionStatusVO.java, TransactionResponse.java
│       │   ├── TransactionDeviceVO.java, TransactionResponseType.java
│       │   └── velocity/Velocity.java, VelocityVO.java
│       ├── user/UserDAO.java, UserGroup.java
│       ├── email/IEmailSchedule.java, EmailScheduleVO.java
│       ├── notification/IStopNotificationClaimedCode.java
│       ├── helper/ParameterHelper.java
│       └── exception/ServiceException.java, ChainedException.java
│
└── branded-currency-impl (JAR)
    └── src/main/java/com/ecount/one/service/brandedcurrency/
        ├── core/CoreObjectImpl.java
        ├── dao/BrandedCurrencyDAOFactory.java
        │    └── spring/SpringBrandedCurrencyDAO.java
        ├── purchase/
        │   ├── payment/PaymentImpl.java, PaymentConstraintImpl.java
        │   │    └── spring/ (CheckPaymentConstraints, ClaimPayment, CreatePaymentHistory,
        │   │                  CreateReissuedPaymentReference, SpringPaymentDAO, UpdatePayment)
        │   └── certificate/CertificateImpl.java
        │        └── spring/ (CreateCertificate, GetCertificateDetail, GetCertificateDetailIVR,
        │                      GetCertificateTemplates, GetTemplateDetail, SpringCertificateDAO,
        │                      UpdateCreateCertificateInfo)
        ├── transaction/
        │   ├── UserTransactionImpl.java
        │   ├── ClaimTransactionImpl.java, CertificatePurchaseTransactionImpl.java,
        │   │   AddFundsTransactionImpl.java, BulkPurchaseTransactionImpl.java, ConstraintImpl.java
        │   ├── spring/ (CheckServicePermission, CreateTransactionDevice,
        │   │            CreateUserTransactionHistoryItem, SpringTransactionDAO,
        │   │            UpdateTransactionStatus2)
        │   └── velocity/VelocityImpl.java
        │        └── spring/ (GetGroupServiceConstraintInfo, GetGroupServiceConstraintInfoDetail,
        │                      GetUserServiceConstraints, GetUserTransactionVelocity)
        ├── user/spring/ (GetClaimedPayments, GetMemberIdFromCode, GetUnclaimedPayments,
        │                 GetUserGroups, SetUserGroup, SpringUserDAO, UpdateUserEcountId)
        ├── email/EmailScheduleImpl.java
        │    └── spring/ (CreateEmailAction, EmailSchedule, GetScheduleDetail, GetTemplateName)
        └── notification/StopNotificationClaimedCodeImpl.java
             └── spring/GetEventHandlerIdForCertificateId.java
```

### Inheritance Hierarchy
```
CoreObject (interface)
└── CoreObjectImpl
    ├── PaymentImpl implements Payment
    │   └── CertificateImpl implements Certificate
    ├── UserTransactionImpl implements UserTransaction
    │   ├── ClaimTransactionImpl implements ClaimTransaction
    │   ├── AddFundsTransactionImpl implements AddFundsTransaction
    │   └── CertificatePurchaseTransactionImpl implements CertificatePurchaseTransaction
    │       └── BulkPurchaseTransactionImpl implements BulkPurchaseTransaction
    ├── VelocityImpl implements Velocity
    ├── ConstraintImpl implements Constraint
    ├── PaymentConstraintImpl implements PaymentConstraint
    ├── EmailScheduleImpl implements IEmailSchedule
    └── StopNotificationClaimedCodeImpl implements IStopNotificationClaimedCode
```

### VO Hierarchy
```
PaymentVO
├── CertificateVO
│   ├── BasketCertificateVO (adds fee, basketId)
│   └── CertificateTemplate (adds certificateTemplateId, description; extends PaymentVO)
└── UserTransactionVO
    ├── ClaimTransactionVO
    ├── AddFundsTransactionVO
    └── CertificatePurchaseTransactionVO
```

---

## API Surface

This is a **library** with no HTTP, messaging, or RPC API surface. The public API is the set of Java interfaces defined in `branded-currency-common`:

### Primary Entry Points

#### `BrandedCurrencyDAO` (via `BrandedCurrencyDAOFactory.getInstance()`)
```java
PaymentDAO     getPaymentDAO()
CertificateDAO getCertificateDAO()
TransactionDAO getTransactionDAO()
UserDAO        getUserDAO()
IEmailSchedule getEmailSchedules()
```

#### `Certificate` / `CertificateImpl`
```java
void init(CertificateVO) throws ServiceException
boolean isActive()
int isGreaterThanMonthOld()
int isFutureDate()
void activateStrategicDelay()
void updateStatus(int paymentId, int actionCode, String actionData) throws ServiceException
CertificateVO getCertificateVO()
```

#### `ClaimTransaction` / `ClaimTransactionImpl`
```java
void init(ClaimTransactionVO)
void addSourcePayment(PaymentVO)
void setDestinationEcard(String ecardId, boolean createCard)
void setDestinationEcard(String ecardId, boolean createCard, Dictionary addenda)
void setDestinationEcard(String ecardId, boolean createCard, Dictionary addenda, int amount)
void setDestinationDDA(String ddaId, boolean createCard, Dictionary addenda, int amount)
void setDestinationDDA(String ddaId, boolean createCard, Dictionary addenda, int fee, int amount)
void setDestinationIEFT(String ieftId, Dictionary addenda, int amount)
void setDestinationIEFT(String ieftId, Dictionary addenda, int fee, int amount)
void setNewDestinationEcard()
void setNewDestinationEcard(Dictionary addenda)
TransactionStatusVO execute()
TransactionStatusVO execute(String description, String transferId)
```

#### `CertificatePurchaseTransaction` / `CertificatePurchaseTransactionImpl`
```java
void init(CertificatePurchaseTransactionVO)
void setFundingEcardDeviceId(String)
TransactionStatusVO execute()
```

#### `AddFundsTransaction` / `AddFundsTransactionImpl`
```java
void init(AddFundsTransactionVO)
void setFundingSource(ExtendedRegistration) throws Exception
void setDestinationEcard(String ecardId)
TransactionStatusVO execute()
```

#### `UserDAO`
```java
Map updateUserDeviceId(int userId, String deviceId)
List<CertificateVO> getUnclaimedPayments(String memberId)
List<CertificateVO> getClaimedPayments(String memberId)
String getMemberIdFromCode(String verificationCode)
Integer setUserGroup(Integer appId, Integer userId, Integer groupId, String caller)
List<UserGroup> getUserGroups(Integer appId, Integer userId)
```

#### `TransactionDAO`
```java
Map checkServicePermission(int userId, String creditCardImprint, String ipAddress, int serviceType, int amount)
Map createTransactionDevice(int transactionId, String deviceId, int amount, int fee, char debitCreditFlag)
Map createUserTransactionHistoryItem(...)
Map getGroupServiceConstraintInfo(int constraintId)
Map getGroupServiceConstraintInfoDetail(int constraintId)
Map updateTransactionStatus2(int transactionId, int resultCode, String resultMessage, String ecountTransferId)
Map getUserTransactionVelocity(int userId, String creditDebitFlag)
Map getUserTransactionVelocity(int userId, String creditDebitFlag, String memberId)
ConstraintVO getUserServiceConstraints(int userId, int serviceId, int unitOfMeasure)
```

---

## Security Posture

### Critical Issues

1. **PAN in memory unmasked** (`CreditCardVO._number`, `getNumber()`): Full Primary Account Number stored as a Java `String`. Java strings are immutable and may remain in the heap until GC. No `char[]` wiping, no tokenization, no masking. **PCI DSS Req. 3.4 failure.**

2. **CVV in memory** (`CreditCardVO._cvCode`, `getCVCode()`): CVV/CVC stored as a `String`. **PCI DSS Req. 3.3 failure** — SAD must not be stored after authorization.

3. **Plaintext database password in VCS** (`brandedCurrencyTestContext.xml` lines 27–33):
   ```xml
   <property name="username"><value>[REDACTED — rotate immediately]</value></property>
   <property name="password"><value>[REDACTED — rotate immediately]</value></property>
   ```
   Also a commented-out block with `[REDACTED — rotate immediately]/[REDACTED — rotate immediately]`. Both are committed to the repository.

4. **SQL statement content in logs** (`UpdateTransactionStatus2SpringImpl`, lines 84–98): The `log.info()` call constructs and logs the full SQL statement including `transactionId`, `resultCode`, `resultMessage`, and `ecountTransferId`. Transfer IDs and status messages appear in application logs.

5. **No authentication/authorization in library**: The library accepts caller-provided `userId`, `memberId`, `serviceType` without any verification. Authorization is entirely the caller's responsibility.

6. **`Dictionary` / raw `Hashtable` as addenda container**: Using legacy `java.util.Dictionary` / `Hashtable` (not `Map<String,Object>`) prevents type-safe addenda handling and may allow unexpected key types.

### Medium Issues

7. **No TLS enforcement**: The jTDS JDBC connection string does not specify `ssl=require` or `encrypt=true`. Communication with `cbaseapp` SQL Server may be unencrypted.

8. **IP address logging**: Caller's `ipAddress` is stored in `user_transaction_history` (passed to `dbo.create_user_transaction_history_item`). Under GDPR, IP addresses are PII and their retention must be governed.

9. **`DriverManagerDataSource` (no pool, no connection security)**: Uses Spring's non-pooling `DriverManagerDataSource` — no connection validation, no timeout settings, no encryption parameters.

10. **Exception messages may leak system details**: `ServiceException.toString()` includes the full exception message from the underlying cause, which may expose SQL error text, table names, or system internals to callers.

---

## Technical Debt

### High Severity

1. **Deprecated Java Date API** (`PaymentVO.java`, lines 161–162, 195–209; `PaymentImpl.java`, `CertificateImpl.java`):
   - `getDate()`, `getMonth()`, `getYear()` are deprecated since Java 1.1. Must be replaced with `java.time.LocalDate` / `ZonedDateTime`.

2. **Raw types throughout all DAO interfaces and implementations**:
   - `PaymentDAO`, `TransactionDAO`, `CertificateDAO` return `Map` (not `Map<String,Object>`).
   - `Dictionary` and `Hashtable` (non-generic) used in `UserTransactionImpl`, `ClaimTransactionImpl`, `UserTransactionVO`.
   - This prevents compile-time type safety and enables `ClassCastException` at runtime.

3. **New-in-method DAO instantiation** (anti-pattern):
   - `CertificateImpl.setCertificateDetails()` creates `new GetCertificateDetailSpringImpl(this.getDataSource())` directly.
   - `UserTransactionImpl.checkVelocity()` creates `new VelocityImpl(this.getDataSource())`.
   - `PaymentConstraintImpl.getFailedConstraints()` creates `new CheckPaymentConstraintsSpringImpl(this.getDataSource())`.
   - This makes unit testing impossible without a real DataSource and prevents Spring from managing lifecycle.

4. **Static singleton `BrandedCurrencyDAOFactory`**:
   - `BrandedCurrencyDAOFactory.getInstance()` is a JVM-static singleton that holds a single `BrandedCurrencyDAO` instance.
   - Multiple Spring contexts in the same JVM will share this singleton — a classloader pollution risk.
   - Each call to `getBrandedCurrencyDAO().getCertificateDAO()` creates a **new `SpringCertificateDAO` instance** (not cached), allocating objects on every call.

5. **`BrandedCurrencyDAOFactory` referenced in `brandedCurrencyDAOFactory` bean AND directly via `getInstance()`**:
   - The Spring context configures a `brandedCurrencyDAOFactory` bean via `factory-method="getInstance"`, but implementation classes also call `BrandedCurrencyDAOFactory.getInstance()` directly — bypassing Spring injection entirely in some paths.

6. **`CertificateImpl.getCertificateVO()`** (lines 265–293): The return method body consists entirely of commented-out field assignments. The method simply returns `this.certificateVO` from state already loaded in `setCertificateDetails()`. The large commented-out block is dead code that should be removed.

### Medium Severity

7. **`CheckPaymentConstraintsSpringImpl`** (lines 76–87): Uses dynamic SQL string concatenation with `"declare @SAVEERROR int; execute @SAVEERROR = ? ?, ?;"` — the stored procedure name is injected via `PreparedStatement.setInt(1, userId)` but the overall statement string is hardcoded. This pattern (re-used in `CheckServicePermissionSpringImpl`) is not a prepared statement in the traditional sense; it is a `declare/execute` block — SQL Server will compile it anew each call.

8. **`StopNotificationClaimedCodeImpl`** — instance-level mutable state shared across calls:
   - `private List<TransactionStatusVO> statusList = new ArrayList<>()` is an instance variable. If the same `StopNotificationClaimedCodeImpl` bean were reused (even though it's `scope="prototype"`), the status list would accumulate across multiple `stopNotification()` calls. A new list should be created each time `stopNotification()` is called.
   - `private static DataSource dataSource` — the `DataSource` field is declared `static`, meaning it is shared across all instances of `StopNotificationClaimedCodeImpl`. This is incorrect and contradicts the Spring prototype scope.

9. **`UserTransactionImpl.addSourceCreditCard()`** (lines 552–572): Method signature has 23 parameters. No builder pattern, no VO, no validation.

10. **Inconsistent exception handling**: Some methods throw checked `ServiceException`, others catch and wrap exceptions silently. No consistent error contract.

11. **`PaymentVO.isGreaterThanMonthOld()`** duplicated in `PaymentImpl` and `CertificateImpl** — the same logic exists in three places (`PaymentVO`, `PaymentImpl`, `CertificateImpl`) with identical implementation.

12. **`ClaimTransactionVO.DDA_NAME`, `ECARD_NAME`, `EIEFT_NAME`** are `public static String` (mutable) — should be `public static final String`.

### Low Severity

13. **`ParameterHelper.getStringParameter()` null guard** (line 79): `value == null ? null : (String)value` is checked twice (redundant null check after the required check).
14. **`TransactionResponseType` enum** — present in common but not referenced in any Spring impl class (possibly dead code from a partially implemented response handling layer).
15. **`BasketCertificateList`** — present in common package; not referenced in any impl class visible in this repository.
16. **Test context references hardcoded Windows paths** (`D:/c-base/config/ecount-config.xml`) — not portable.

---

## Gen-3 Migration Requirements

To migrate `branded-currency_LIB` to a Gen-3 (cloud-native / modern Spring Boot microservice) architecture, the following work is required:

### Must-Have (Blockers)

1. **Replace ECountCore / MoneyTransferHelper**: Abstract money movement behind an internal API (REST/gRPC) or event stream. The Gen-3 service cannot import `com.ecount:xplatform` directly — that dependency must be exposed as a service call.

2. **Replace CBase MemberManager**: Member lookup must be via a Gen-3 Identity/Member service API, not a direct Java API call.

3. **Replace jTDS with Microsoft JDBC**: Replace `net.sourceforge.jtds.jdbc.Driver` with `com.microsoft.sqlserver:mssql-jdbc`. Enable TLS for the connection string.

4. **Externalize and vault all credentials**: Remove `brandedCurrencyTestContext.xml` credentials from VCS. Use a secrets vault (Azure Key Vault, HashiCorp Vault, or AWS Secrets Manager) for all database passwords. Use Spring Boot `@ConfigurationProperties` for environment-specific config.

5. **Replace `DriverManagerDataSource` with connection pool**: Use HikariCP (Spring Boot default) with connection validation, timeout, and encryption settings.

6. **Implement PAN tokenization**: `CreditCardVO` must never store full PAN or CVV. Replace with a token received from the PSP/tokenization service. The `addSourceCreditCard()` method must be re-designed to accept a token, not raw card data.

7. **Replace Spring XML with Spring Boot auto-configuration**: Convert `brandedCurrencyContext.xml` to `@Configuration` classes with `@Bean` methods. Remove `ClassPathXmlApplicationContext` usage. Eliminate the static singleton `BrandedCurrencyDAOFactory`.

8. **Enable CI test execution**: Refactor DAOs to use mockable Spring injection so that unit tests can run without a live database. Use Testcontainers or a local SQL Server Docker image for integration tests.

### Should-Have

9. **Replace deprecated Java Date API**: All `java.util.Date` usages → `java.time.LocalDate` / `ZonedDateTime`. Fix `isGreaterThanMonthOld()`, `isFutureDate()`, `isActive()`.

10. **Replace raw `Map` returns with typed DTOs**: All DAO interfaces should return typed response objects, not `Map`. This eliminates `ClassCastException` risk and enables OpenAPI documentation.

11. **Replace `Dictionary` / `Hashtable` with `Map<String,Object>`**: Modernize addenda handling.

12. **Add input validation layer**: Validate `verificationCode` format, `amount` range (positive integer), `memberId` UUID format at the service boundary.

13. **Add structured logging**: Replace plain `log.error("message: " + value)` with `log.error("message: {}", value)` (SLF4J parameterized logging) throughout. Mask sensitive fields (transferId, echeckId) in log output.

14. **Fix `StopNotificationClaimedCodeImpl` static field bug**: Remove `private static DataSource dataSource` — use the inherited `dataSource` from `CoreObjectImpl` correctly.

15. **Add distributed tracing**: Instrument with OpenTelemetry / Spring Cloud Sleuth for end-to-end claim transaction visibility.

### Nice-to-Have

16. **Add circuit breaker**: Wrap ECountCore and MemberManager calls with Resilience4j `@CircuitBreaker`.
17. **Add metrics**: Instrument transaction counts, claim latency, failure rates with Micrometer.
18. **Replace `Dictionary` addenda with proper domain events**: The PPD/xPPD addenda pattern is a Gen-1 construct; Gen-3 should use domain events or structured request objects.

---

## Code-Level Risks

### Risk 1: Static `DataSource` in `StopNotificationClaimedCodeImpl` (HIGH)
**File**: `branded-currency-impl/.../notification/StopNotificationClaimedCodeImpl.java`, line 29
```java
private static DataSource dataSource;
```
The `DataSource` is declared `static` but set via instance constructor. In a multi-context or hot-reload scenario, the last context to initialize wins, potentially routing all instances to the wrong datasource. This is a classloader-level data corruption risk.

### Risk 2: Transfer-ID Logging (HIGH)
**File**: `branded-currency-impl/.../transaction/spring/UpdateTransactionStatus2SpringImpl.java`, lines 84–98
```java
log.info("\n\ndeclare @confirmation_code varchar; ... execute @return_code = " + SQL + " " + transactionId + "," + resultCode + ",'" + resultMessage + "'," + ...);
```
The full SQL with parameter values (including `ecountTransferId`) is logged at INFO level. Transfer IDs and transaction details appear in logs. If logs are shipped to an external system, this constitutes data leakage.

### Risk 3: Silent Claim Failure (HIGH)
**File**: `branded-currency-impl/.../transaction/ClaimTransactionImpl.java`, lines 401–419
```java
} catch (Exception e) {
    log.error("postProcess: " + stat.getCode(), e);
}
return stat;
```
If `dbo.claim_payment` throws an exception (e.g., deadlock, network error), the exception is caught and logged, but `stat` still holds the pre-failure code. The caller receives a `TransactionStatusVO` that does not reflect the actual failure. Money may have moved but the payment record remains unclaimed.

### Risk 4: No-Pool DataSource Under Load (HIGH)
**File**: `brandedCurrencyContext.xml`, line 10
```xml
<bean id="CbaseappDataSource" class="org.springframework.jdbc.datasource.DriverManagerDataSource">
```
`DriverManagerDataSource` creates a new JDBC connection for every call. Under concurrent load, this will exhaust the SQL Server connection limit and cause `Cannot get a connection` errors with no graceful degradation.

### Risk 5: `CheckPaymentConstraintsSpringImpl` SQL Pattern (MEDIUM)
**File**: `branded-currency-impl/.../purchase/payment/spring/CheckPaymentConstraintsSpringImpl.java`, lines 76–85
```java
String sql = "declare @SAVEERROR int;" +
           "execute @SAVEERROR = ? ?, ?;" +
           "select @SAVEERROR as return_code";
PreparedStatement preparedStatement = connection.prepareStatement(sql);
preparedStatement.setInt(1, userId);
preparedStatement.setString(2, verificationCode);
```
The `?` in position 1 is being set as `userId` (int), but the SQL template has `execute @SAVEERROR = ? ?, ?` — the first `?` is the stored procedure name position, which would need to be the proc name, not the userId. This appears to be a miscounted parameter binding. The stored procedure name `dbo.check_claim_payment_constraints` is missing from the SQL string; the `?` is the proc name. This pattern also does not prevent injection if the procedure name itself were dynamic, but since it's hardcoded in the class, the risk is construction error rather than injection.

### Risk 6: Duplicate Logic Across Inheritance Tree (LOW-MEDIUM)
`isGreaterThanMonthOld()`, `isActive()`, `activateStrategicDelay()`, and `isFutureDate()` are implemented identically in `PaymentVO`, `PaymentImpl`, and `CertificateImpl`. Any bug fix must be applied in three places. `PaymentImpl` and `CertificateImpl` should delegate to `super` or the logic should live only in `PaymentVO`.

### Risk 7: `CertificateImpl.updateStatus()` Does Not Persist State Change (MEDIUM)
**File**: `CertificateImpl.java`, line 295–302
```java
public void updateStatus(int paymentId, int actionCode, String actionData) throws ServiceException {
    Map result = brandedCurrencyDAOFactory.getBrandedCurrencyDAO()
            .getPaymentDAO().createPaymentHistory(paymentId, actionCode, actionData);
}
```
`updateStatus()` only appends a history row — it does not update the `lastAction` field on the payment record itself. Whether `dbo.create_payment_action_item` also updates `last_action` on the payment is unknown from library code alone. If it does not, calls to `activateStrategicDelay()` (which sets `lastAction = 1000` in memory) followed by `updateStatus()` will leave the database inconsistent with the in-memory state.
