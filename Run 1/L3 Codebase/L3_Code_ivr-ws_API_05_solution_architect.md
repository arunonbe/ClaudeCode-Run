# Solution Architect Analysis — ivr-ws_API

## 1. Complete Class and Method Inventory

### ivrapi-ws module — Service Interfaces and Implementations

**Base service classes** (`com.ecount.one.ivr.service`):
- `IService.java` — top-level service interface
- `ServiceImpl.java` — base implementation with `populateAccount()`, `processDeviceInquiry()`, `logMessage()`, `logSysMessage()`

**Account services** (`com.ecount.one.ivr.service.account`):
- `IAccountBalanceInquiryService` — interface with `balanceInquiry(application_id, card_number)`
- `AccountBalanceInquiryServiceImpl extends AccountServiceImpl` — implements balance inquiry
- `IAccountTransactionInquiryService` — interface with `transactionInquiry(application_id, card_number, journal_detail, start_date, end_date, max_items)`
- `AccountTransactionInquiryServiceImpl extends AccountServiceImpl` — implements transaction history
- `AccountServiceImpl extends ServiceImpl` — shared account service base

**ACH services** (`com.ecount.one.ivr.service.ach`):
- `IAchAccountSetupService` — interface with `achAccountSetup(application_id, card_number, bank_account_type, bank_name, bank_routing_number, bank_account_number)`
- `AchAccountSetupServiceImpl extends AchServiceImpl` — creates/updates bank account
- `IAchInquiryService` — interface with ACH inquiry method
- `AchInquiryServiceImpl extends AchServiceImpl` — returns linked bank account
- `IAchTransferSetupService` — interface with transfer setup
- `AchTransferSetupServiceImpl extends AchServiceImpl` — configures ACH transfer
- `AchServiceImpl extends ServiceImpl` — shared ACH service base

**Claimable payment services** (`com.ecount.one.ivr.service.claimable`):
- `IClaimablePaymentService` — interface
- `ClaimablePaymentServiceImpl extends ServiceImpl` — claimable payment operations

**Mobile phone services** (`com.ecount.one.ivr.service.mobilephone`):
- `IMobilePhoneNumberService` — interface with `mobilePhoneInquiry()` and `mobilePhoneUpdate()`
- `MobilePhoneNumberServiceImpl extends ServiceImpl` — implements both methods

**JAX-RPC endpoint wrappers** (`com.ecount.one.ivr.service.jaxrpc`):
- `JaxRpcAccountBalanceInquiryService`
- `JaxRpcAccountTransactionInquiryService`
- `JaxRpcAchAccountSetupService`
- `JaxRpcAchInquiryService`
- `JaxRpcAchTransferSetupService`
- `JaxRpcClaimablePaymentService`
- `JaxRpcMobilePhoneService`

**Validators** (`com.ecount.one.ivr.service.validator`):
- `IValidator` — base validator interface
- `IParameterValidator` — parameter validator interface
- `Validator` — base validator
- `ParameterValidator` — composed parameter validator
- `ApplicationIdValidator` — validates application ID against whitelist
- `CardNumberValidator` — validates card number format
- `BankAccountNumberValidator` — validates bank account number
- `BankAccountTypeValidator` — validates checking/savings type
- `BankNameValidator` — validates bank name
- `BankRoutingNumberValidator` — validates ABA routing number (9 digits)
- `AmountValidator` — validates monetary amount
- `ClaimCodeValidator` — validates claim code
- `MaximumItemsValidator` — validates max items count
- `MobilePhoneNumberValidator` — validates 10-digit US phone number
- `RecurringPercentageValidator` — validates percentage value
- `WithdrawTypeValidator` — validates withdrawal type

**Common data classes** (`com.ecount.one.ivr.common`):
- `AchDetail`, `BalanceDetail`, `CardDetail`, `ClaimDetail`, `PPDDetail`
- `SecurityDetail` — authentication data (phone numbers, ZIP)
- `TransactionDetail` — transaction record with `DescriptionLookup` inner class
- `Response`, `ResponseStatus` — base response types
- `RequestServiceContextLookup` — Spring context helper

**Utility** (`com.ecount.one.ivr.utility`):
- `Constants` — parameter type constants, bank account types, etc.
- `Utility` — `setResponse()` utility

**Exception** (`com.ecount.one.ivr.common.exception`):
- `ServiceRuntimeException` — wraps service-layer exceptions

**Jakarta compatibility shim** (`jakarta.servlet.http`):
- `HttpUtils.java` — custom HttpUtils class in `jakarta.servlet.http` package — this is a **compatibility shim** for the Jakarta EE migration

### ivrapi-boot module — Spring Boot configuration classes (`com.citi.prepaid.ivrapi`)

- `IVRApiBootApplication.java` — Spring Boot main class
- `AccountBalanceInquiryServiceConfig.java`
- `AccountServiceConfig.java`
- `AccountTransactionInquiryServiceConfig.java`
- `AchAccountSetupServiceConfig.java`
- `AchInquiryServiceConfig.java`
- `AchServiceBaseConfig.java`
- `AchTransferSetupServiceConfig.java`
- `ApplicationContextConfig.java` — imports legacy Spring XML context files
- `BrandedCurrencyConfig.java` — branded currency service configuration
- `ClaimablePaymentServiceConfig.java`
- `DataSourceConfig.java` — datasource configuration
- `ECountSystemConfiguration.java` — eCount system config from Azure App Config
- `MobilePhoneServiceConfig.java`
- `ValidatorConfig.java` — validator bean configuration
- `WebConfiguration.java` — MVC/SOAP web configuration
- `ECountConfigProperties.java` — typed properties from Azure App Config
- `CbaseAppDataSourceAutoConfiguration.java` — auto-configures cbaseapp datasource
- `HealthCheck.java` — custom health check controller
- `DefaultServiceImpl.java` — default service fallback

## 2. Security Vulnerability Analysis

### 2.1 HIGH: IVR Authentication Strength

The `SecurityDetail` object holds `phoneNumbers` (list) and `zipcode`. IVR authentication appears to rely on:
- Card number (DTMF entry)
- ZIP code (DTMF entry) OR phone number ANI match

For operations like **ACH account setup** (which exposes and captures full bank account numbers), this authentication level is potentially insufficient. Regulatory guidance (NACHA WEB/TEL rules) requires robust identity verification for online/phone ACH debit authorization.

**DTMF Security**: There is no explicit DTMF masking implementation visible in this service code. DTMF masking (replacing DTMF digits with silences in call recordings) must be enforced at the telephony platform layer, not this service. Confirm with the IVR telephony vendor that DTMF masking is active for card number, PIN, and bank account number entry.

### 2.2 HIGH: PIN Verification — Not in This Service

PIN verification for cardholder authentication is **not visible in this codebase**. This could mean:
1. PIN is verified at the IVR telephony platform before calling this service — acceptable if properly implemented.
2. PIN verification is in a separate service endpoint not captured here.
3. PIN is not used (only card number + ZIP) — **insufficient for financial operations under PCI DSS**.

**Action Required**: Confirm the IVR authentication flow with the IVR telephony vendor. Verify PIN challenge is in place and that PIN digits are not transmitted to this service.

### 2.3 HIGH: Session Token / Replay Attack Prevention

No session token or nonce is visible in the service contracts. The IVR calls the SOAP service with `card_number` + `application_id` on each call. There is no evidence of:
- Session-bound authorization tokens between IVR steps
- Replay protection for transaction-authorizing calls

If an attacker can construct valid SOAP requests (via APIM external endpoint), they could potentially query any cardholder's balance given a card number. The APIM gateway's API key management is the primary control here — this must be verified.

### 2.4 MEDIUM: `card_number` in Log Context

`MobilePhoneNumberServiceImpl.java` line 196:
```java
Object[] parameters = {getLogger().getName(), card_number, mobilePhoneNumber};
logSysMessage("mobilephone.syslog.update.message", parameters);
```
Card number is logged in the system log for mobile phone updates. While mobile phone update is not a financial operation, the card number is PCI CHD. Confirm log encryption and access controls.

### 2.5 MEDIUM: DEBUG Logging in Production

`application.yml` line 47:
```yaml
com.citi: DEBUG
com.onbe: DEBUG
```
DEBUG logging is enabled for the IVR service packages in the production configuration. This may produce verbose logs containing card numbers, balance amounts, or other sensitive data if any DEBUG-level log statements remain in the codebase. All DEBUG log calls in the service implementation classes that include cardholder data should be audited and removed or replaced with masked equivalents.

### 2.6 MEDIUM: `CardDetail.toString()` Expiry Date

`CardDetail.java` `toString()` method (lines 213–229) includes `<expiration>`. If any logger calls `cardDetail.toString()` or any reflection-based logging is used, the card expiry date appears in logs. Expiry is SAD under PCI DSS Req 3.3. Audit all usages of `CardDetail` in log statements.

### 2.7 LOW: `HttpUtils.java` Jakarta Shim

`ivrapi-ws/src/main/java/jakarta/servlet/http/HttpUtils.java` — A custom class placed in the `jakarta.servlet.http` package. This is a compatibility shim for the `javax.servlet.http.HttpUtils` class that was removed from Jakarta EE. Creating classes in `jakarta.*` namespaces is technically incorrect and may cause ClassLoader conflicts in newer Servlet containers. This should be replaced with proper Jakarta EE 10 compatible code.

## 3. Technical Debt Summary

| Item | Severity | Location |
|---|---|---|
| Card number logged in mobile phone update | HIGH | `MobilePhoneNumberServiceImpl.java:196` |
| DEBUG logging enabled in production | HIGH | `application.yml:47-48` |
| `CardDetail.toString()` includes expiry | HIGH | `CardDetail.java:213-229` |
| IVR authentication strength for ACH setup unclear | HIGH | Architecture |
| Session/replay attack prevention not visible | HIGH | Architecture |
| Log4j 1.x in `ivrapi-ws` module | CRITICAL | `ivrapi-ws` pom.xml (inherited) |
| `xplatform` SNAPHOT version | MEDIUM | `pom.xml:32` |
| Jakarta shim in `jakarta.*` package | MEDIUM | `ivrapi-ws/.../HttpUtils.java` |
| Wirecard CA cert bundled in image | MEDIUM | `bindings/ca-certificates/` |
| Tests skipped in CI | MEDIUM | `deployment.yml` MAVEN_ARGS |
| Postman tests not automated in CI | LOW | `integration-test/` |

## 4. Remediation Priorities

| Priority | Action |
|---|---|
| P0 | Remove card_number from mobile phone update sys log message |
| P0 | Audit all DEBUG log statements for CHD exposure; set production log level to INFO |
| P0 | Verify DTMF masking active at telephony layer for card number, PIN, bank account number |
| P0 | Confirm PIN verification is in IVR authentication flow before financial operations |
| P1 | Replace Log4j 1.x in ivrapi-ws with SLF4J + Logback |
| P1 | Override `CardDetail.toString()` to mask expiry and card_number in string output |
| P1 | Add replay protection / session tokens to SOAP calls for ACH operations |
| P2 | Fix `xplatform.version` SNAPHOT typo and pin to release version |
| P2 | Remove `HttpUtils.java` from `jakarta.*` package; use proper Jakarta API |
| P2 | Add CA cert rotation procedure documentation; plan cert removal after infrastructure migration |
| P2 | Integrate Postman tests via Newman in CI pipeline |
| P3 | Long-term: Replace JAX-RPC SOAP with REST + OpenAPI in coordination with IVR vendor |
