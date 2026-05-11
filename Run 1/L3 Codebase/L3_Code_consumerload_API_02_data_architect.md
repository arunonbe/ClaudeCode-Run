# consumerload_API — Data Architect View

## Data Stores

This service does not own or manage any database schema directly. It acts as an orchestration layer that reads and writes data through the eCore/cbase platform libraries. Two JDBC data sources are declared in the deployment descriptor:

| JNDI Name | Declared In | Purpose |
|---|---|---|
| `jdbc/JobSvcDataSource` | `web.xml` (resource-ref) and `META-INF/context.xml` (ResourceLink) | Used by `GetPuid` (`com.cbase.business.ecount.data.GetPuid`) to perform the `partner_user_id` + `program_id` → internal `memberId` lookup. Also referenced in `appCtx-jobsvc-ds.xml` loaded at startup. |
| `jdbc/CbaseappDataSource` | `META-INF/context.xml` (ResourceLink) | Loaded via `appCtx-cbaseapp-ds.xml`; used by cbase platform calls (member inquiry, transfer, profile retrieval). |

Both data sources are configured as container-managed (Tomcat JNDI) resource links — actual connection pool parameters are outside this repository, defined at the application server level.

The `com.ecount.services.comment` library (`comment.xml` Spring context) owns a separate persistence store for the audit/auto-comment trail; its schema is not visible in this repository.

## Schema & Tables

No DDL or ORM mapping files exist in this repository. Data access is entirely mediated by the `cbase` and `xPlatform` proprietary platform libraries. The following logical data objects are read/written based on code evidence:

| Logical Entity | Platform Object | Key Fields Accessed |
|---|---|---|
| Member PUID lookup | `GetPuid.execute(program_id, partner_user_id, null)` → `GetPuidValue.getMemberId()` | program_id, partner_user_id → member_id |
| Member basic inquiry | `MemberManagerImpl.InquiryBasic(member)` → `MemberInquiryBasicResult` | `addenda["kyc_status"]` |
| Member extended inquiry | `MemberManagerImpl.InquiryExtended(member)` → `MemberInquiryExtendedResult` | `ExtendedRegistration` (firstName, lastName, email, address), `registration` |
| Member secure profile | `MemberManagerImpl.InquirySecureProfile(member)` → `SecureUserProfile` | `date_of_birth`, `federal_id` (SSN) |
| eCard device | `DeviceManagerImpl.getDefaultEcard(member)` → `AccountDefinitionECard` | card block-code (active/blocked), card ID |
| Credit card device | `DeviceManagerImpl.getDefaultCreditCard(member)` → `AccountDefinitionCreditCard` | card number (masked on read), card type, expiry, CVV |
| Direct deposit account | `DeviceManagerImpl.getDirectDepositBankAccount(memberId)` → `BankAccount` | accountNumber, routingNumber |
| Program membership profile | `AppProfileProgramMembership.retrieve(...)` | `recurring_limit_min_cc`, `recurring_limit_max_cc`, `recurring_limit_min_dd`, `recurring_limit_max_dd` |
| Program strategy | `AppProfileProgramStrategyClass.retrieve(...)` | `max_amt_per_day`, `max_amt_per_month`, `max_balance` |
| Promotion/KYC feature flag | `AppPromotionFeatureProfileClass.retrieveAll(...)` | promo ID `"0"`, feature ID `"14"` → string `"1"` = KYC enabled |
| Transfer | `ITransferManager.addFundsCreditCardToECard(...)` → `TransferCommitResult` | caller, cCardId, eCardId, amount, fee, strategy, addenda (`partner-payment-id`) |

## Sensitive Data Handling

| Data Element | Classification | How It Flows |
|---|---|---|
| Full PAN (credit card number) | PCI SAD | Accepted in `CreditCard.cardNumber` in SOAP request body; passed through `LoadFundsUsingCCInput.creditCard.cardNumber`; forwarded to `CreditCard.setNumber()` for storage/update via `DeviceManagerImpl.createSecureCreditCard()` / `updateSecureCreditCard()`. |
| CVV / CV2 | PCI SAD | Accepted in `LoadFundsUsingCCRequest.cvv`; passed to `CreditCard.setCvCode(sInput.getCvv())` and forwarded to `ITransferManager.addFundsCreditCardToECard()`. |
| SSN (`federal_id`) | PII / GLBA | Accepted in `SecureKYCInfo.ssn`; mapped in `UpdateKYCInfoService.populateSecureRegistration()` → `secureProfile.setFederal_id(kycInfo.getSsn())`; written to the member's secure profile via `MemberManager.UpdateSecureProfile()`. |
| Date of Birth | PII / GLBA | Accepted in `SecureKYCInfo.dob` as string `MMDDYYYY`; parsed to `java.util.Date` in `InputHelper.getDateOfBirth()`; stored via `SecureUserProfile.setDate_of_birth()`. |
| Bank account number | PCI-adjacent / GLBA | Returned in `GetACHInfoResponse.accountNum` in full — no masking applied. |
| Bank routing number | PCI-adjacent / GLBA | Returned in `GetACHInfoResponse.routingNum` in full. |
| Masked PAN (last 4) | Display-safe | `GetDefaultCreditCardService.maskThefirst12NumbersCC()` returns `XXX...XXXX` (all digits except last 4 replaced with `X`). This is the correct behavior. |

## Encryption & Protection

- **No application-level encryption is implemented** in this codebase. There are no `javax.crypto`, `java.security`, or any encryption library imports anywhere in the source.
- Transport security (TLS) is delegated to the servlet container (Tomcat). No evidence of mutual TLS or certificate pinning at the application layer.
- CVV and PAN are handled in plaintext `String` objects throughout the Java heap. No use of char arrays, SecureString, or field-level encryption.
- The `SecureUserProfile` object that stores SSN is provided by the `cbase` platform library; whether it encrypts at rest is opaque to this service.
- The `print(Object obj)` debug-logging method using XStream (`ConsumerLoadWebServiceImpl` line 237; `ConsumerLoadService` line 51) will serialize sensitive field values to log output if debug logging is enabled for `AccountHelper.class` (`Log log = LogFactory.getLog("AccountHelper.class")`).

## Data Flow

```
SOAP Client
  │  SOAP/HTTP (no auth)
  ▼
ConsumerLoadWebServiceImpl (consumerload-ws)
  │  ValidationHelper → HashMap parameter map
  │  InputHelper → ServiceInput objects
  │  CVV, PAN, SSN, DOB in plaintext Java objects
  ▼
Service classes (consumerload-impl)
  ├─ AccountHelper.getMemberId() ──→ GetPuid ──→ jdbc/JobSvcDataSource (SQL)
  ├─ AccountHelper.isAccountActive() ──→ IDeviceManager ──→ ECoreDevice ──→ cbase eCore (remote call)
  ├─ ProfileHelper.isKYCEnabled() ──→ AppPromotionFeatureProfileClass ──→ eCore profile
  ├─ LoadFundsUsingCCService:
  │    accountHelper.getCreditCardLoadFee() ──→ Fee.getTxFeeAmount() ──→ eCore fee engine
  │    accountHelper.createCreditCard() / updateCreditCard() ──→ IDeviceManager ──→ eCore (PAN + CVV transmitted)
  │    transferManager.addFundsCreditCardToECard() ──→ ITransferManager ──→ ECoreTransfer ──→ eCore (PAN + CVV)
  │    commentHelper.autoComment() ──→ ICommentService ──→ RDBMS (comment store)
  └─ GetACHInfoService:
       deviceManager.getDirectDepositBankAccount() ──→ eCore (returns account + routing number in plaintext)
```

## Data Quality & Retention

- **No data retention policy** is implemented or configured within this service. Retention of the member profile, transaction records, and comment audit trail is delegated to the eCore/cbase platform.
- **Validation gaps**:
  - SSN Luhn check is present but commented out (`ValidationHelper.validateSSN()` defined but never invoked).
  - No duplicate-transaction detection: `transactionId` (partner-payment-id) is passed as an addendum but there is no idempotency check at the service layer.
  - No amount range validation on the `getCCLoadFee` call (amount minimum set to 0; a zero-amount fee query is accepted).
- **Log retention**: XStream XML serialization of full request/response objects (including PAN, CVV, SSN) will be written to the log4j log file at `D:/c-base/config/ConsumerLoad/log4j.xml`. Retention of that log is outside the application's control.

## Compliance Gaps

| Gap | Evidence | Risk |
|---|---|---|
| PAN and CVV in debug logs | `ConsumerLoadWebServiceImpl.print()` called with full request objects before masking, lines 30, 59, 87, 120, 167 | PCI DSS Req. 3.3 (no CVV storage) and Req. 10.3 (log protection) |
| Full bank account + routing number returned unmasked | `GetACHInfoResponse.accountNum` / `routingNum` fields, `OutputHelper.populateGetACHInfoResponse()` | GLBA / NACHA; should return only last 4 of account number |
| SSN validation disabled | `ValidationHelper` line 159 — `validateSSN()` call commented out | BSA / CIP: invalid SSNs may be stored and used for KYC |
| No transport-layer enforcement at application level | No HTTPS or mutual-TLS enforcement in `web.xml` or Spring config | PCI DSS Req. 4.2 |
| No encryption of sensitive fields in memory or in transit at app layer | No crypto imports anywhere | PCI DSS Req. 3.5 |
| eCore credentials (`consumerload.agent`, `consumerload.memberId`, `consumerload.userId`) sourced from flat properties file | `consumerload-wsContext.xml` line 8: `file:D:/c-base/config/ConsumerLoad/ConsumerLoad.properties` | Secret management gap; hardcoded file path is Windows-only |
