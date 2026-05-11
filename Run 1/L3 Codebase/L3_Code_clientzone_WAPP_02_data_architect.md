# clientzone_WAPP — Data Architect View

## Data Stores

ClientZone is itself stateless between requests except for HTTP session. It depends on **six named JDBC DataSources**, all Microsoft SQL Server, declared in `src/main/webapp/META-INF/context.xml` and referenced in `web.xml` `<resource-ref>` entries:

| JNDI Name | Purpose (inferred from usage) |
|---|---|
| `jdbc/CbaseappDataSource` | Primary application database — cardholder data, instant issue pre-registration, screen configs, eDelivery status, file attributes, virtual express, payment selection, affiliate skin. Beans: `callInquiryPaymentReasonsStoredProc`, `callInquiryScreenDriverFlagsStoredProc`, `callInquiryReversalReasonsStoredProc`, `callInquiryDisplayDefaultDataStoredProc`, `edeliveryResponseUpdateStatus`, `fileAttributesSP`, `extractFileAttributesSP`, `instantIssuePreregistrationDAO` |
| `jdbc/EcountCoreDataSource` | Core member/account store — member inquiry, DDA inquiry, check transactions, extended registration, deposit info, addenda, manage card, payment selection. Beans: `memberInquiryImpl`, `ddaOnlyMemberInquiryImpl`, `CheckTransactionsExtractSP`, `GetDDAUsingCheckNumberSP`, `AllCheckTransactionsExtractSP`, `addendaExtractSP`, `manageCardDao`, `initialDepositDao` |
| `jdbc/JobSvcDataSource` | Job service database — user-to-account mapping, symbol groups. Beans: `callJobAccountMapByPuIds`, `callJobAccountMapGetPUIDNotSpecified`, `retrievesymbolgroup` |
| `jdbc/OrderDataSource` | Order management database — order processing, currency profiles. Referenced via Spring context imports `appCtx-order-ds.xml`, `appCtx-OrderManagerImport.xml` |
| `jdbc/RequestDataSource` | Request/transaction tracking. Referenced via `appCtx-request-ds.xml`, `appCtx-RequestManagerImport.xml` |
| `jdbc/WebcertOmahaDataSource` | Check/ACH processing (Webcert/Omaha). Referenced in `context.xml` as `WebcertOmahaDataSource` |

Additionally, `context.xml` has a commented-out `GreatPlainsDataSource.USD` (and many other currency variants: GBP, EUR, SEK, DKK, CHF, AED, AUD, HKD, IDR, INR, MYR, PHP, SGD, TWD) indicating historical or potential multi-currency accounting integration.

A separate EhCache instance (`src/main/resources/com/ecount/service/ehCache-ytd.xml`) is used for year-to-date caching. `cacheManagerContext.xml` and `CacheManagerHelperImpl.java` support cache management at the application level.

---

## Schema & Tables

No DDL scripts are present in the repository; schema is owned by dependent service libraries and back-end database teams. However, the following tables/stored procedures are evidenced directly in the code:

| Table / SP | DataSource | Evidence |
|---|---|---|
| `instant_issue_preregistration` | CbaseappDataSource | `instantIssueContext.xml` line 17: `SELECT * FROM instant_issue_preregistration WHERE program_id = ? AND cardholderId = ?` |
| `user_validation_information` | (External, via xSecurity) | `SsoUserUtil.java` line 91: `UPDATE user_validation_information SET password='...' WHERE username='...'` |
| Various (via stored procs) | CbaseappDataSource | `CallInquiryPaymentReasons`, `CallInquiryScreenDriverFlags`, `CallInquiryReversalReasons`, `CallInquiryDisplayDefaultData`, `CallInquiryOAccountDetails`, `CallSaveOAccountDetails` — all in `com.ecount.service.instissueczscreencfgs.dao.jdbc` |
| Check transactions | EcountCoreDataSource | `CheckTransactionsExtractSP`, `AllCheckTransactionsExtractSP`, `GetDDAUsingCheckNumberSP` |
| Job account map | JobSvcDataSource | `CallJobAccountMapByPuIds`, `CallJobAccountMapGetPUIDNotSpecified` |
| File attributes | CbaseappDataSource | `FileAttributesSP`, `ExtractFileAttributesSP`, `RetrieveFileCountSP` |
| Virtual express | CbaseappDataSource | `UserVirtualExpressExtractSP`, `UserVirtualExpressInstallSP`, `UserVirtualExpressUpdateSP` |
| eDelivery response status | CbaseappDataSource | `EdeliveryResponseUpdateStatus` |
| Addenda | EcountCoreDataSource | `AddendaExtractSP` |
| Member inquiry | EcountCoreDataSource | `MemberInquiryImpl`, `DDAOnlyMemberInquiryImpl` |
| Payment selection | EcountCoreDataSource | `UserPaymentSelectionExtractSP` |
| Deposit info | EcountCoreDataSource | `InitialDepositDao` |
| Affiliate skin / map | CbaseappDataSource | `AffiliateMapSkin` |
| Admin TPIN | (via xSecurity DAO) | `insertUpdateAdminTPinStoredProc`, `retrieveAdminTPinStoredProc` referenced in `clientZoneUserManagement` bean |

---

## Sensitive Data Handling

### Data Types Present

| Sensitive Field | Class / Location | Notes |
|---|---|---|
| Full SSN | `PatriotActInfo.java` — `socialSecurityNumber`, `socialSecurityAreaNumber/Group/Serial` | Parsed from hyphenated format. Stored in HTTP session via `CardHolderInfo`. No at-rest encryption visible in this layer. |
| Date of Birth | `PatriotActInfo.java` — `birthDate`, `birthDay/Month/Year` | Also in HTTP session via `CardHolderInfo`. |
| Card Number (PAN) | `CardInfo.java` — `cardNumber` | Both raw (`cardNumber`) and display-masked (`cardNumberDisplay`) fields exist. `MaskHelper.maskCreditCardNumber()` produces masked values for display. |
| Private Label Card Number | `CardInfo.java` — `privateLabelCardNumber` | Raw field present alongside masked display field. |
| Bank Account Number | `MaskHelper.maskBankAccountNumber()` | Display function shows only last 4 digits ("ending XXXX"). |
| Password | `ClientZonePasswordUtil.java`, `user_validation_information` table (via `SsoUserUtil`) | Passwords are salted-hashed (`genSaltedHashPassword`) for storage. MD5-based encoder (`EcountMd5PasswordEncoder`) is still declared in `applicationContext-xsecurity-web.xml`. |
| OTP / PIN | `OtpServiceClient.java` — `pin` parameter | OTP PIN is logged (masked to first 2 chars + "****") before transmission. Full PIN appears in JSON request body at `requestBody.put("pin", pin)`. |
| SSO Encryption Key | `EncryptionUtil.getSsoEncryptionKey()` | Read from `D:\c-base\config\cz\clientzone.properties`. |
| Azure AD Client Secret | `ssoConfiguration` bean, `otpClientSecret` bean | Injected from `clientzone.properties` via `${sso.client.secret}`, `${otp.client.secret}`. Not in source code but pattern-matched by `EncryptionUtil.getSsoEncryptionKey()`. |
| Email address | `EmailInfo`, `AccountManagementAPIHelper`, `OtpServiceClient` | Transmitted as plain text in JSON to shared services. |
| Full name | `NameInfo`, `AuditInfo`, `SsoUserUtil`, `AccountManagementAPIHelper` | Used in audit events and SSO provisioning. |

### Masking Implementation

`MaskHelper.java` (`src/main/java/com/ecount/one/struts/action/helpers/MaskHelper.java`):
- `maskCreditCardNumber()`: two modes — `maskPattern=true` returns "-" + last 4; `maskPattern=false` returns "XXXXXXXX" + last 8 characters. Only 8 of 16 characters are masked in non-pattern mode.
- `maskBankAccountNumber()`: shows "ending " + last 4.
- `maskCheckAccountNumber()`: "X" × (length-4) + last 4 digits.

Note: the non-pattern mode exposes the last 8 digits of the PAN, which exceeds the PCI DSS Requirement 3.3 limit of displaying no more than the first 6 and last 4 digits combined.

---

## Encryption & Protection

### AES Encryption (`EncryptionUtil.java`)

- Algorithm: `AES` (`javax.crypto.Cipher.getInstance("AES")`)
- **Critical gap**: No IV or mode specified. Java defaults to `AES/ECB/PKCS5Padding`. ECB mode is deterministic and does not provide semantic security — identical plaintexts produce identical ciphertexts. This is a PCI DSS v4 violation for any PAN or sensitive authentication data encrypted with this utility.
- Key derivation: Base64-decoded raw bytes (`SecretKeySpec`). Key read from `D:\c-base\config\cz\clientzone.properties` via `getSsoEncryptionKey()`.
- Used in `SsoUserUtil` to encrypt plaintext passwords for Azure AD Graph API provisioning payload (`extension_*_czPassword` field).

### Password Hashing

- `EcountMd5PasswordEncoder` is declared as the `passwordEncoder` in `applicationContext-xsecurity-web.xml`. MD5 is cryptographically broken and does not meet modern standards (PCI DSS v4 Requirement 8 mandates strong, salted hashing).
- `ClientZonePasswordManager` and `genSaltedHashPassword` (referenced in `SsoUserUtil.java`) suggest a separate, potentially stronger hashing path exists for the v2 password policy.

### Transport Security

- `SSLLoginFilter` enforces HTTPS for all non-localhost requests.
- `forceHttps` in `authenticationEntryPoint` bean is set to `false` — indicating HTTPS enforcement is delegated to the filter rather than the security framework itself.

### Token / OAuth (MSAL4J)

- `SharedServiceConnector.java` uses `ConfidentialClientApplication` (MSAL4J) to acquire Azure AD tokens via client credentials flow for OTP and OMRCP shared services.
- Token is cached and re-used via `SilentParameters.builder(scope).build()` before falling back to a full acquire.
- `msal4j` version `1.14.3` is in `pom.xml`.

---

## Data Flow

```
Browser (HTTPS)
    |
    v
Tomcat (Apache Tomcat 8.5, Windows Server)
    |
Filter Chain: SSLLoginFilter → Acegi FilterChainProxy [XSSFilter, LocalFilter,
              OverrideUrlSessionFilter, HttpSessionContextIntegration,
              ssoRedirectFilter, authenticationProcessingFilter,
              ssoAuthenticationProcessingFilter, exceptionTranslationFilter,
              filterInvocationInterceptor]
    |
Struts 1.x ActionServlet (*.do)
    |
Spring ApplicationContext (Spring 2.0.8)
    |--- Action Helpers (CardholderHelper, InstantIssueHelper, etc.)
    |--- xPlatform / ECountBusinessObject SPI (ECoreMember, ECoreDevice, ECoreTransfer)
    |--- Order Service (OrderManager, RequestManager, SynchronousOrderProcessor)
    |--- Job Service (JobManagerClient)
    |--- Security Service (xSecurity, userManagement)
    |--- Debit API (IDebitService via debitapi-impl)
    |--- Account Management API (CreateAccountService)
    |--- eDelivery (Adobe IDP SOAP)
    |--- Repository Service
    |--- Comment Service
    |--- OTP Shared Service (REST/JSON via SharedServiceConnector + MSAL4J)
    |--- OMRCP Search (REST via CustomerServiceAction)
    |
JDBC (MS SQL Server via mssql-jdbc 6.1.0.jre8)
    |--- CbaseappDataSource
    |--- EcountCoreDataSource
    |--- JobSvcDataSource
    |--- OrderDataSource
    |--- RequestDataSource
    |--- WebcertOmahaDataSource
```

External inbound: Browser via HTTPS.
External outbound: Adobe IDP SOAP (eDelivery), Azure AD / MSAL4J token endpoint, OTP REST service (`otp.generate.url`, `otp.validate.url`), OMRCP search (`omrcp.seach.url`).

---

## Data Quality & Retention

- No explicit data retention policy or TTL logic is visible in the source code.
- `repoHomeMsgSearchDates` bean (`repo.homemessage.startdays` / `repo.homemessage.enddays`) controls the date window for home messages fetched from the repository service.
- `DateFilterInfo.java` and `DateRange.java` provide date-range filtering for order history searches.
- `PaginationInfo.java` and `PaginationHelper.java` support paged retrieval (default `RECORDS_PER_PAGE_DEFAULT = 10` in `ClientZoneConstants`).
- EhCache (`ehCache-ytd.xml`) caches YTD data; no TTL values are directly visible in the committed configuration.

---

## Compliance Gaps

1. **PCI DSS Requirement 3.3** — `MaskHelper.maskCreditCardNumber()` non-pattern mode exposes last 8 PAN digits (should be maximum last 4).
2. **PCI DSS Requirement 3.5** — `EncryptionUtil` uses AES/ECB without IV. ECB is not an approved mode for protecting stored sensitive data. Any PANs or SAD encrypted with this utility are not adequately protected.
3. **PCI DSS Requirement 8** — `EcountMd5PasswordEncoder` uses MD5, which is not an approved strong hashing algorithm for cardholder credentials.
4. **PCI DSS Requirement 6 (Struts 1.x)** — Apache Struts 1.3.10 has reached end-of-life with numerous unpatched CVEs (including CVE-2014-0094 class-pollution, CVE-2016-1181, etc.). `ParamFilter` in `web.xml` mitigates some Struts 1 class-pollution attacks via its `excludeParams` regex, but does not eliminate the CVE surface.
5. **PCI DSS Requirement 6 (Spring 2.0.8)** — Spring 2.0.8 is severely end-of-life. No security patches are available.
6. **PCI DSS Requirement 6 (Log4j 1.2.17)** — Log4j 1.x is EOL and subject to known vulnerabilities (e.g., CVE-2019-17571 SocketServer deserialization).
7. **Session serialization of SSN/PAN** — `CardHolderInfo` is `Serializable` and stored in HTTP session. If session persistence or clustering is enabled, SSN and PAN data could be written to disk or network storage without explicit encryption.
8. **OTP PIN in debug log** — `OtpServiceClient.validateOTP()` at `log.debug()` line 37 logs the sessionId and pin partially unmasked.
9. **`SsoUserUtil` SQL injection risk** — Line 91 builds an UPDATE statement via string concatenation: `"update user_validation_information set password='" + saltedHashedPwd + "' where username='" + username + "'"`. If username contains SQL metacharacters, this is injectable. This is a utility/migration tool, not a servlet, but still represents a risk if run against production.
