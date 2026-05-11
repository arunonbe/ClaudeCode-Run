# account-management-payout_API — Business Analyst View

## Business Purpose

This service is the **mobile payout API layer** that sits between mobile cardholder apps and the legacy eCount/CBase prepaid platform. It exposes a SOAP-over-HTTP interface that enables mobile users to check card activation status, activate prepaid cards, and set PINs. Per the README, it "supports our mobile payout app using two specific APIs — AccountManagement and CSAPI V3 APIs which allow mobile users to check balances and register cards."

The service is registered externally via Azure API Management (APIM) and is accessed by external callers through the path `/services/AccountManagementApiWebServices`.

---

## Business Capabilities

The WSDL (`accountmanagementapi-payout-war/wsdl/wsdl.xml`) and the live service interface (`AccountManagementApiWebService.java`) define three **active** operations:

| Operation | Description |
|---|---|
| `activationStatusInquiry` | Checks whether a prepaid card is active or inactive. Returns the account DDA number (JWE-encrypted) and the BIN/bank name. Optionally validates the cardholder postal code before returning. Triggers a KYC check for programs with `kyc_required = Y`. |
| `activateCard` | Activates a prepaid card. Supports two paths: card-number + CVV + postal code, or JWE-encrypted DDA account number. Validates the postal code against the FDR (First Data Resources) data store before activating. |
| `setPin` | Sets the card PIN on behalf of a cardholder. Accepts an account number (JWE-encrypted) or a partner user ID. Enforces a one-PIN-set-per-24-hour limit. Uses a 7-second async executor with a PROCESSING state if the downstream FDR call times out. |

One additional operation is defined in the handler and implementation but **commented out** as inactive:
- `updateRegistration` — Updates cardholder registration data (name, address, DOB, SSN) by sending a `ProcessSweepRequest` through the Order Service JMS bus.

A large block of additional service methods (createAccount, addFunds, linkCard, assignPackage, createPackage, createBulkOrder, withdraw, updateAccountStatus, updateProvisionStatus, stopPayment, getRequestStatus) exists in `AccountManagementHandlerImpl.java` but is entirely disabled — wrapped inside a large block comment attributed to "JIRA 476 changes."

---

## Business Entities

| Entity | Java Class | Description |
|---|---|---|
| Card | `ActivateCardInput`, `Card.java` | Prepaid card with card_number, CVV, postal code, activation status |
| Account | `ServiceInput`, `ActivationStatusInquiryOutput` | Account identified by DDA number (encrypted) or partner_user_id, scoped to a program_id |
| Registration | `RegistrationInput.java` | Cardholder PII: firstName, lastName, address1–4, city, state, postal, country, homePhone, emailAddress, DOB, SSN |
| Program | `ServiceInput.program_id` | 8-digit program identifier; the first 8 digits of a DDA number double as the program ID |
| UserMapping | `UserMapping` (from `job-common`) | Maps a partner_user_id + program_id to an internal eCount/eMember ID |
| KYC | `KYC.java` (from `cbase` layer) | Know-Your-Customer status object; triggers external KYC portal call and writes to `kyc_status` table |
| Addenda | `AddendaInput.java` | Key-value memo attachments on registration actions |
| Withdraw | `WithdrawInput.java` | Withdrawal request with sub-types: ACH (1), Check (2), CheckVoid (5), ACHVoid (6) |
| ACH | `WithdrawACHInput.java` | account_holder_name, routing_number, account_number, account_type (C/S), bank_name |

---

## Business Rules & Validations

Evidence sourced from `AccountManagementHandlerImpl.java`, `SetPinService.java`, `ActivationStatusInquiryService.java`, `ActivateCardService.java`, and `validation.xml`.

1. **Program-Account binding**: `isAccountBelongToProgram()` — Account number must start with the 8-digit program_id prefix. Throws `ACCOUNT_NUMBER_PROGRAM_ID_MISMATCH` if mismatch detected (`AccountManagementApiServiceImpl.java` line 379).
2. **Mutual exclusion — account number vs. partner_user_id**: Either account number OR partner user ID must be supplied, not both (`isAccountNumberPartnerUserIdPassed()`, line 386).
3. **DDA encryption enforcement**: When `jwe.encryptDDA = Y`, clear-text DDA numbers starting with `0401` or `0601` with length ≤ 16 are rejected (`JweDDAHelper.java` line 92). Token expiry is enforced against the `jwe.expirationTime` configuration value.
4. **JWE token expiry**: Encrypted DDA tokens contain a `TIME` field; tokens older than the configured expiration period are rejected with "Validity of encrypted DDA expired" (`JweDDAHelper.java` line 105).
5. **PIN set frequency**: Maximum one PIN change per 24-hour period. Downstream FDR enforces this; the service traps "Set PIN failed:" errors and maps them to `BusinessValidationType.OVER_PIN_SET_LIMIT` (`SetPinService.java` line 91).
6. **PIN set timeout**: The PIN set call to FDR uses a 7-second executor timeout (`SetPinService.java` line 73). On timeout, code 2 / PROCESSING is returned so the mobile client can poll.
7. **Postal code validation** (optional): When `validate_postal = 1` is sent in `activationStatusInquiry`, the postal code is compared against the value stored in FDR via `FDRCardAccountDetailInquiryDAO`. Mismatch returns `INVALID_POSTAL` (code 1) (`ActivationStatusInquiryService.java` line 124).
8. **KYC check gate**: For programs where `kyc_required = Y` (read from the Affiliate metadata store, field `kyc_required`, application ID 6), the KYC portal is called before returning activation status. If the KYC portal reports the cardholder must complete KYC, `activationStatus` is replaced with "KYC IS REQUIRED" / `CAN_NOT_PROCEED` (`ActivationStatusInquiryService.java` lines 175–212).
9. **Date format constraints**: DOB must be formatted `MM/dd/yyyy`; card expiry `MMyy` (`validation.xml`).
10. **ACH bank account types**: Only `C` (checking) or `S` (savings) are valid (`BankAccountType.java`).
11. **Security API authorization** is wired but commented out for active operations (see `AccountManagementApiServiceImpl.java` line 148 — "Commented for JIRA 476"). The authorization path via `SecurityValidator.authorize()` is inactive for the three live endpoints.

---

## Business Flows

### Flow 1: Activation Status Inquiry
1. Mobile app calls `activationStatusInquiry(card_number, cvv, postal_code, validate_postal)`.
2. Handler (`AccountManagementHandlerImpl.setPin()`) decrypts DDA if encrypted.
3. Validator runs against required fields.
4. If `validate_postal = 1`, `FDRCardAccountDetailInquiryDAO.getDetailsOfCard()` is called; postal mismatch returns INVALID_POSTAL.
5. `AccountHelper.getActivationStatus()` queries the eCount/eCore layer for the card status.
6. Affiliate metadata is queried for `kyc_required` flag.
7. If KYC required: `AMPayoutHelper.checkKYCStatus()` calls the KYC portal; if KYC is pending, returns code 900 + app error message.
8. On success, DDA number is JWE-encrypted and returned together with `activationStatus` and `binBankName`.

### Flow 2: Activate Card
1. Mobile app sends either card_number + CVV + postal, or encrypted DDA account number.
2. Handler selects path: if card_number path, validator `activateCardRequestValidator` runs against card fields. If DDA path, DDA is JWE-decrypted.
3. Postal code compared via FDR; mismatch returns INVALID_POSTAL.
4. `AccountHelper.updateCardStatus()` or `updateCardStatusUsingDDANumber()` calls eCore to flip the activation code.
5. If `AccountDefinitionECard` returned, success response populated.

### Flow 3: Set PIN
1. Mobile app sends encrypted account_number + new_pin.
2. JWE decryption of account number. Program_id derived from first 8 chars.
3. `AccountHelper.getUserMappingForEcountID()` resolves eMember ID.
4. `AccountHelper.pinset()` invoked in a bounded executor (7-second timeout).
5. FDR RPC called to set PIN; timeout returns PROCESSING; "Set PIN failed:" returns OVER_PIN_SET_LIMIT.

---

## Compliance & Regulatory Concerns

1. **PAN / CVV handling**: Card numbers and CVVs flow in clear text within SOAP XML payloads inside the network boundary. The WSDL schema shows `card_number` and `cvv` as plain `xsd:string`. This is a PCI DSS Requirement 4 concern if TLS termination occurs anywhere before this service (the Tomcat `server.xml` only configures port 80 — unencrypted HTTP).
2. **PIN handling**: `new_pin` is transmitted as an `xsd:string` in the WSDL. PIN is not shown to be encrypted in transit within the SOAP message itself. PCI DSS Requirement 3.3 and PIN security (PCI PTS / ISO 9564) require PIN blocks to be encrypted.
3. **SSN in registration**: `RegistrationInput.java` (line 57) stores SSN. It is wrapped in a `SecureUserProfile` and transmitted to the `ActionSecureMemo`, which encrypts it for storage. However, SSN appears in the input domain object in clear text.
4. **DDA number encryption**: JWE encryption (AES-256-GCM via Nimbus JOSE JWT) is conditionally applied (`jwe.encryptDDA` flag). When disabled, raw account numbers traverse unencrypted.
5. **KYC integration**: The KYC portal is called via `KYCHelper.invokeKYCPortal()` using Microsoft MSAL credentials (`kyc.ms.client.secret`, `kyc.ms.client.id`). The KYC status insert is persisted to the `kyc_status` SQL table, which creates a record linking cardholder PII to KYC outcomes — subject to GLBA/CCPA data retention requirements.
6. **Authentication filter**: `AuthenticationCheckFilter` (`com.citi.prepaid.security.api.filter.AuthenticationCheckFilter`) is applied to `/*` (`web.xml` line 38). However, API-level security authorization (`validateAPISecurity()`) is commented out for all active service methods.
7. **Logging of sensitive data**: `AccountManagementHandlerImpl` logs the encrypted DDA string (line 98: `log.info("AccountManagementHandlerImpl::setPin() - Encrypted DDA : "+request.getAccountNumber())`). If log shipping is not encrypted, this constitutes a PCI DSS concern. The decrypted DDA is also logged at line 100.
8. **NACHA/ACH**: `WithdrawACHInput` captures routing number and bank account number. Although withdrawal service is currently disabled (JIRA 476), the data model and validators are fully present.
9. **Reg E**: Withdrawal types Check (2) and ACH (1) with void paths (5, 6) indicate the service was (and may be again) handling consumer fund disbursements subject to Regulation E.

---

## Business Risks

1. **Massive dead code / zombie features**: The majority of the `AccountManagementHandlerImpl` and `AccountManagementApiServiceImpl` business logic is commented out under "JIRA 476 changes." There is no documentation explaining if these features are permanently removed, temporarily disabled, or being migrated. Reactivation without re-review of all validators and security gates poses a significant operational and compliance risk.
2. **Security authorization bypassed**: `validateAPISecurity()` is commented out for all three active operations (`SetPinService.java` line 43, `AccountManagementApiServiceImpl.java` line 148). This means program-level access control is not enforced at the API level.
3. **Single point of failure on FDR**: PIN setting uses a single-threaded executor with a 7-second timeout. Under sustained load, the executor pool will exhaust and clients will receive PROCESSING responses, requiring retry logic.
4. **Incomplete KYC integration**: The KYC flow can raise a `KYCProcessException` that maps `def = null`, yet the success code path (`if (def instanceof AccountDefinitionECard)`) will simply not execute, returning an empty/zero-code response rather than a clean error — potential client confusion.
5. **Stale WSDL endpoint**: The WSDL service address (`wsdl.xml` line 252) hardcodes `https://d-app02.nam.wirecard.sys:9326/...` — a legacy wirecard.sys domain — while the live service deploys to AKS (Kubernetes). This suggests the WSDL is not being regenerated automatically on deployment.
6. **No retry or circuit-breaker**: Integration with the Order Service JMS bus and eCore/FDR uses raw Spring remoting with no circuit breaker, backoff, or dead-letter handling.
