# card-notification-restful_API — Business Analyst View

## Business Purpose

This service is Onbe's (formerly North Lane / Citi Prepaid) **SMS Pull Notification gateway**. It enables prepaid cardholders to query their card account status via inbound SMS text messages. Cardholders send keyword commands (e.g., BAL, PAY, TRANS, HELP, START, STOP) to a short code (445544, or 8997/7283 for FTEU carriers). The service receives those messages from an SMS aggregator (SAP Mobile Services / Sinch), looks up the cardholder's account data from the core prepaid platform (ECount/CBase), and sends an SMS reply back through the aggregator.

The service is the bridge between the external SMS channel and the internal prepaid card platform. It is not a push notification service; it is a **pull** model where the cardholder initiates the interaction.

---

## Business Capabilities

| Capability | Description | Key Classes |
|---|---|---|
| SMS Opt-In (START) | Enroll a mobile number for text alerts | `CardNotificationServiceImpl` → `CardNotificationProfileInsertDAO` → SP `dbo.sms_cardnotification_profile_insert` |
| SMS Opt-Out (STOP) | Un-enroll a mobile number | Same DAO, return codes 3 and 4 indicate successful stop / already stopped |
| Balance Inquiry (BAL) | Return current available balance | `CardNotificationMessageBalance.getMessageByActionType()` using `AccountBalance.getAvailable()` |
| Last Payment Inquiry (PAY) | Return most recent credit/payment transaction | `CardNotificationMessagePayment` via `AccountJournalPaymentTxPredicate` (amount > 0) |
| Last Transaction Inquiry (TRANS) | Return most recent debit transaction matching configured source types | `CardNotificationMessageTransaction` via `AccountJournalPaymentTxPredicate` with pipe-delimited source type filter |
| Help (HELP) | Send static help text to cardholder | Inline in `CardNotificationServiceImpl`, carrier-variant messages (standard vs FTEU) |
| Internal Test Endpoint | Developer test path that echoes responses instead of forwarding to SAP | `JaxRsCardNotificationService.processMO_InternalTesting()` at `@Path("/Internal")` |

---

## Business Entities

| Entity | Description | Source |
|---|---|---|
| **Cardholder / Member** | Prepaid card account holder identified by mobile phone number | Retrieved from xSearch-XMLRPC layer via `FindMemberByMobilPhone`; modelled as `MemberInquiryValue` |
| **Account / Device** | Prepaid card device (ECount EDevice); carries balance, journal, definition | `com.cbase.business.ecount.EDevice`, `AccountDetail` |
| **Account Balance** | Available balance amount stored in cents integer | `AccountBalance.getAvailable()` |
| **Account Journal** | Transaction history entries used for payment and transaction lookups | `AccountJournalList`, filtered by `AccountJournalPaymentTxPredicate` |
| **SMS Profile** | Per-program configurable SMS message templates (variables: CARD_NUMBER, BAL_AMOUNT, CUR_AMOUNT, DATE, TIME, CS_PHONE, DATE_RANGE_MONTH) | `AppSmsMsgProfile`, `AppSmsMsgProfileCollection` from DB table `app_sms_msg_profile` |
| **SMS_MO (Mobile Originated)** | Inbound XML message from SAP/Sinch aggregator; contains MSISDN, originating address, message body, operator parameters | `com.ecount.model.SMS_MO` |
| **SMS_MT (Mobile Terminated)** | Outbound message sent back to SAP/Sinch for delivery to cardholder | `com.ecount.model.SMS_MT` |
| **CardNotificationProfile** | Enrollment record stored in DB when cardholder sends START/STOP | Written via `dbo.sms_cardnotification_profile_insert` |
| **CardNotificationLog** | Audit log of every SMS interaction | Written via `dbo.sms_cardnotification_log_insert` |
| **Program / Affiliate** | Prepaid program (client) configuration; controls which programs have SMS Pull enabled via `SMSPULLENABLEDPROGRAMS` attribute | `AffiliateService.getAffiliateForValue()` |

---

## Business Rules & Validations

1. **Member Lookup by Mobile Number** — The mobile phone number extracted from MSISDN (characters 2–12) must resolve to at least one member via xSearch-XMLRPC. If not found, a "phone not found" error SMS is returned (`error.cardnotification.invalidmobilephone` in `messages.properties`).

2. **Program SMS Pull Eligibility** — Members are only processed if their program is in the `SMSPULLENABLEDPROGRAMS` affiliate list with value "Y". This is validated in `CardNotificationMemberValidator.validateMember()`. Programs not in this list receive no balance/payment/transaction responses.

3. **Active Account Only** — `CardNotificationMemberValidator` line 27: `"active".equalsIgnoreCase(member.getUserStatus())`. Inactive, suspended, or closed accounts are filtered out.

4. **Carrier-Variant Messaging (FTEU)** — Messages differ for T-Mobile FTEU (operator ID 185, originating address 8997) and AT&T FTEU (operator ID 78, originating address 7283). These carriers do not charge message rates so the standard "Msg & data rates may apply" disclaimer is omitted. Comparison is by `==` reference equality (see Technical Debt section).

5. **AUTO-ENROLL on BALANCE** — When a cardholder sends BAL without being enrolled, the service automatically issues a START enrollment before returning the balance. If the profile insert returns code 2 (new enrollment), a welcome message is appended to the response.

6. **Action Type Validation** — Only START, STOP, HELP, BALANCE, PAYMENT, TRANSACTION are valid. Any unrecognised action returns `msg.cardnotification.unknowncommand`.

7. **Message Template Required** — If `AppSmsMsgProfileCollection` cannot be retrieved for a given program, the service returns `error.cardnotification.invalidaccount`. Logged as missing config in `app_sms_msg_profile` table.

8. **Last Transaction Source Type Filter** — The `cardnotification.lasttransactionsourcetypes` property (config file `CardNotification.yaml`) controls which transaction source activity codes are eligible. This is a pipe-delimited list of ~18 values including retail-purchase, cash-advance, ATM variants, POS, etc.

---

## Business Flows

### Inbound SMS Processing Flow
```
Cardholder → SMS Carrier → SAP/Sinch Aggregator
  → POST /Cardnotification/CardnotificationService (URL-encoded XmlMsg=<SMS_MO XML>)
  → JaxRsCardNotificationService.processMO()
    → URL-decode → JAXB unmarshal to SMS_MO
    → CardNotificationUtils.getCardnotificationRequestFromMoRequest()
      → Extract mobile number (MSISDN chars 2-12)
      → Detect carrier (FTEU check via originating address + operator ID)
      → Map command text to action type (BAL→BALANCE, PAY→PAYMENT, etc.)
    → CardNotificationServiceImpl.cardNotificationInquiry()
      → Check Ehcache for member by MOBILE_ key
      → If miss: xSearch-XMLRPC FindMemberByMobilPhone
      → Validate member against SMS-pull-enabled programs + active status
      → Execute action-specific logic (START/STOP/HELP/BALANCE/PAYMENT/TRANSACTION)
      → Retrieve AccountDetail via EDevice.processInquiry()
      → Format message via CardNotificationMessageFactory + AppSmsMsgProfile template
      → Return CardNotificationResponse (array of MobileResponse)
    → For each MobileResponse: build SMS_MT, POST to SAP/Sinch MT URL
      (Basic HTTP auth: sapmtusername/sapmtpassword)
    → AOP AfterReturning: CardNotificationLoggingInterceptor writes to sms_cardnotification_log
```

### Opt-In / Opt-Out Flow
- START → `CardNotificationProfileInsertDAO.execute(mobile, "START", date)` → return code 1 = already enrolled, 2 = new enrollment
- STOP → same DAO → return code 3 = opted out, 4 = already opted out

---

## Compliance & Regulatory Concerns

| Area | Concern | Evidence |
|---|---|---|
| **TCPA / Carrier Compliance** | Service implements opt-in (START) and opt-out (STOP) as required by US carrier regulations. Stop messages must be honoured. | `messages.properties`: "You have cancelled North Lane Text Services" / "You have already opted out" |
| **Reg E (Electronic Fund Transfers)** | Balance, payment, and transaction disclosures via SMS must be accurate and timely. No specific error rate monitoring is implemented. | N/A — no SLA enforcement in code |
| **PCI DSS** | Card numbers are masked to last-four digits only (`EcountUtils.getLastFourDigitsCC(member.getCardNumber())`). Mobile numbers are logged to the `sms_cardnotification_log` table — mobile numbers constitute personal data. | `CardNotificationServiceImpl` line 425; `CardNotificationLogInsertDAO` logs `mobile_phone` |
| **GDPR / CCPA** | Mobile numbers (MSISDN) are stored in `sms_cardnotification_log` and `sms_cardnotification_profile` tables. These are PII. No data retention or deletion capability is visible in the codebase. | `CardNotificationLogInsertDAO`, `CardNotificationProfileInsertDAO` |
| **UDAAP** | Static error messages reference "MyPaymentVault" and "North Lane" brands in `messages.properties`. If the brand has changed to Onbe, these messages are inaccurate and could be a UDAAP concern. | `messages.properties` lines 3, 4, 8–14 |
| **Short Code Compliance** | Short code 445544 is referenced in `messages.properties` STOP message. Short code must be registered and maintained with US carriers. | `messages.properties` line 12 |
| **Carrier FTEU** | T-Mobile and AT&T Free-to-End-User short codes (operator IDs 185 and 78) have special message format requirements that are partially implemented. | `CardNotificationUtils.getCardnotificationRequestFromMoRequest()` lines 161–167 |

---

## Business Risks

1. **Brand Inconsistency** — `messages.properties` references "North Lane", "MyPaymentVault", and a legacy Citi Prepaid SMS gateway URL (`citi_uat_487792`). If Onbe has rebranded, customer-facing SMS messages will display incorrect brand names, creating confusion and UDAAP exposure.

2. **Hardcoded Sinch/SAP URL in Internal Test Path** — `JaxRsCardNotificationService.processMO_InternalTesting()` has `http://sms-pp.sapmobileservices.com/cmn/citi_uat_487792/citi_uat_487792.sms` hardcoded. If this internal test endpoint is reachable in production, it could accidentally deliver messages to the UAT aggregator.

3. **No Rate Limiting or Abuse Prevention** — Any caller who knows the endpoint can send arbitrary mobile numbers. There is no authentication on the inbound endpoint, no rate limit, and no captcha/token requirement.

4. **Mobile Number as Primary Cardholder Identifier** — The service identifies cardholders purely by mobile number. If a mobile number is recycled by a carrier and re-issued to a different person, that new subscriber could query the previous subscriber's card balance.

5. **Carrier Comparison Bug** — String comparison using `==` instead of `.equals()` for carrier values ("TMobileFTEU", "ATTFTEU") means the FTEU message variant will never be selected correctly (see Technical Debt). This causes incorrect regulatory messaging for FTEU subscribers.
