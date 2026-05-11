# card-notification_API — Business Analyst View

## Business Purpose

card-notification_API is an SMS Pull service that allows prepaid cardholders to text a short code (e.g., "BAL", "PAYMENT", "TRANSACTION", "HELP") from their registered mobile phone and receive near-real-time card account information back via SMS. The service is deployed as a SOAP/JAX-RPC web service and acts as a back-end inquiry engine sitting between an SMS gateway (e.g., SAP) and the eCount core platform. The README explicitly describes this as: "a SOAP API that services clients who want their cardholders to have the ability to text a short code such as 'BAL' from their mobile phone to pull their Prepaid balance information."

## Business Capabilities

| Capability | Action Type Constant | Description |
|---|---|---|
| Balance Inquiry | `BALANCE` | Returns the current available balance for the cardholder's prepaid card |
| Last Payment | `PAYMENT` | Returns the most recent credit/load transaction against the account |
| Last Transaction | `TRANSACTION` | Returns the most recent debit transaction filtered by configured source types |
| Help / Customer Service | `HELP` | Returns the customer service phone number for the relevant program |

All four capabilities are routed through the single operation `cardNotificationInquiry` defined in `CardNotificationService.java` (line 11).

## Business Entities

- **Cardholder / Member** (`MemberInquiryValue`): A registered prepaid card account holder whose mobile number is on file. Identified by `memberId`, `ebn` (DDA/account number), `deviceId`, `cardNumber`, and `userStatus`.
- **Program** (`programId`): The client program to which the cardholder belongs, derived from the EBN via `EcountUtils.getProgramFromDDA()`. Controls which SMS message templates apply.
- **Mobile Response** (`MobileResponse.java`): The outbound SMS payload containing `programId`, `mobileNumber`, `actionType`, `carrier`, `smsData` (the formatted SMS text), and `timestamp`.
- **Account Journal** (`AccountJournal`): The transaction/journal record from eCount core used to satisfy PAYMENT and TRANSACTION queries.
- **SMS Message Profile** (`AppSmsMsgProfile` / `AppSmsMsgProfileCollection`): Per-program configuration stored in the `app_sms_msg_profile` table that governs message templates, variable ordering, and look-back date range.
- **Affiliate / Program Metadata**: Program-level settings retrieved via `AffiliateService`, including the `SMSPULLENABLEDPROGRAMS` flag and affiliate presentation data (e.g., customer service phone number for HELP).

## Business Rules & Validations

1. **Mobile number must be registered**: `intRetrieveMember()` in `CardNotificationServiceImpl.java` calls xSearch-xmlrpc to look up members by mobile number. If not found, error message `error.cardnotification.invalidmobilephone` is returned (defined in `messages.properties` line 1).
2. **Program must be SMS Pull enabled**: `getSmsPullEnabledProgram()` (line 269) retrieves the list of programs where affiliate attribute `SMSPULLENABLEDPROGRAMS = Y`. Members whose program is not in this list are rejected with `error.cardnotification.invalidaccount`.
3. **Account must be active**: `CardNotificationMemberValidator.validateMember()` (line 33) filters members by `userStatus.equalsIgnoreCase("active")`. Suspended or closed accounts are excluded.
4. **Program must have SMS message configuration**: If `AppSmsMsgProfileClass.retrieve()` returns null, the service returns `error.cardnotification.invalidaccount` (line 200 of `CardNotificationServiceImpl`).
5. **PAYMENT predicate**: `AccountJournalPaymentTxPredicate.evaluate()` (line 55) — a payment is any journal entry where `amount > 0`.
6. **TRANSACTION predicate**: Same predicate (line 58) — a transaction must match one of the pipe-delimited source types configured in `cardnotification.lasttransactionsourcetypes`.
7. **HELP app_id is hard-coded to 6**: `CardNotificationMessageHelp.java` line 34 contains `new Integer(6)` — a known TODO comment acknowledges this as a deficiency.
8. **Cache staleness**: `ehcache.xml` documents that a suspended user can still access SMS Pull until their cached member data expires (up to 2 weeks TTL). This is explicitly acknowledged as a known business risk in the cache configuration comments.

## Business Flows

### SMS Pull — Happy Path

```
SMS Gateway (e.g., SAP)
  --> SOAP call: cardNotificationInquiry(mobileNumber, actionType, carrier)
    --> [Cache check] MemberInquiryValue by MOBILE_{mobileNumber}
    --> [Cache miss] xSearch-xmlrpc: FindMemberByMobilPhone(mobileNumber)
    --> Validate: program in SMSPULLENABLEDPROGRAMS list
    --> Validate: member.userStatus == "active"
    --> [Cache check] AppSmsMsgProfileCollection by MSG_{programId}
    --> [Cache miss] AppSmsMsgProfileClass.retrieve(programId)
    --> EDevice.processInquiry() --> account balance, journal, definition
    --> CardNotificationMessageFactory.getMessageProcessor(actionType)
    --> Format SMS text using AppSmsMsgProfile template
    --> AOP: CardNotificationLoggingInterceptor.afterReturning()
         --> dbo.sms_cardnotification_log_insert (stored proc)
  <-- CardNotificationResponse[MobileResponse[]]
SMS Gateway
```

### Error Paths
- Mobile number not found → returns `error.cardnotification.invalidmobilephone`
- Backend system down → returns `error.cardnotification.systemdown`
- No SMS config for program → returns `error.cardnotification.invalidaccount`
- Invalid/unsupported action type → no message processor found, `smsData` is null

## Compliance & Regulatory Concerns

- **PCI DSS — Sensitive Authentication Data handling**: The service retrieves and processes the card number (`member.getCardNumber()`). In `CardNotificationServiceImpl.java` line 216, the card number is masked to last four digits via `EcountUtils.getLastFourDigitsCC()` before being passed to message construction. Full PAN is never included in the SMS text itself. However, the full card number is held in `MemberInquiryValue` in the in-memory/disk EHCache for up to 2 weeks (`timeToLiveSeconds=1209600` in `ehcache.xml`), creating a PCI DSS CDE exposure risk in the cache store.
- **Reg E (Electronic Fund Transfer Act)**: The service surfaces balance, payment, and transaction data to cardholders via SMS. Accuracy and availability of this data has Reg E implications if cardholders rely on it for disputes or error resolution.
- **GLBA / Privacy**: Mobile phone numbers (PII) are cached with member data and logged to `sms_cardnotification_log` table. The mobile number is also logged in plain text in `JaxRpcCardNotificationService.java` (line 42): `logMessage.append(" MobileNumber = " + request.getMobileNumber())`.
- **UDAAP**: Error messages reference "Citi Prepaid" branding (in `messages.properties` lines 1–4). If this service is used for non-Citi programs, the hard-coded brand name in error messages could constitute misleading communications.

## Business Risks

1. **Hard-coded Citi Prepaid branding in error messages** (`messages.properties`): Error messages referencing "Citi Prepaid" and the phone number 866-326-8689 are returned regardless of the cardholder's actual program. This is a material UDAAP and client SLA risk.
2. **Suspended account access window**: Per `ehcache.xml` comments, a suspended account holder can continue to receive SMS responses for up to 2 weeks if their member data is cached.
3. **Single operation API**: No support for push notifications, alerts, or enrollment — this is purely a pull-inquiry service.
4. **Hard-coded affiliate app ID = 6** in `CardNotificationMessageHelp.java` line 34 — incorrect customer service numbers could be returned for HELP requests.
5. **No authentication on the SOAP endpoint**: `web.xml` and `server-config.wsdd` contain no authentication or authorization handlers applied to the `CardNotificationService` endpoint. The Axis `AdminService` has `enableRemoteAdmin=false`, but the main service has `allowedMethods=*` with no auth chain.
