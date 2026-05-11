# api-config-repo — Business Analyst View

## Business Purpose

This repository is the centralised externalised configuration store for the Onbe (formerly Wirecard North America / Citi Prepaid / NorthLane) B2C prepaid card platform. It does not contain application code. Its sole purpose is to hold environment-specific property files, XML rule definitions, logging configuration, and Postman test collections that are read at runtime by a large suite of Java web services. A GitHub Actions workflow synchronises the `config/` folder to an Azure Storage File Share (`east-soap-config`) on every push to `master`, making the files available to on-premises and cloud-hosted application servers without redeployment.

## Business Capabilities

The configuration repository enables the following platform business capabilities:

| Capability | Services Configured |
|---|---|
| Prepaid card account management (B2C cardholder API) | accountmanagementapi, CSWS (v1 and v3), clientapi |
| Cardholder portal (self-service web) | oneplatform (OP), op508 (ADA-compliant 508 portal), enroll (GE enrollment) |
| Client administration portal | clientzone (CZ), clientzoneHub, cz-hub |
| Card services administration | CSA (Card Services Admin) |
| Debit/card inquiry | debitapi, rebate-cardinquiry |
| International Electronic Funds Transfer (IEFT) | IEFTRules (60+ country rule sets) |
| IVR card services | ivrws |
| Notification delivery (email, SMS) | notificationStrategy (mailer, rulesEngine, eventHandler), cardnotification |
| Order and request processing | service/order, service/request |
| Job scheduling and batch processing | service/jobscheduler, service/jobAgent, service/jobManager, service/autofile |
| Secure key/cryptographic operations | service/httpCryptoService, core2/Strongbox |
| Core ledger and card processor integration | core2/ecountcore (FDR integration), core2/profile |
| Payment disbursement | service/payment, dfapiclient (Citi DFAPI wire/ACH) |
| Banker (fund management) | service/banker |
| Directory/service registry | service/directory |
| Message centre | service/message |
| Repository/registry | service/repository |
| e-Delivery (electronic statement delivery) | service/edelivery, cz/edeliveryrequest |
| Inventory management (physical card stock) | inventoryMgmt |
| KYC / identity verification | Integration URLs and client credentials for Azure-hosted KYC portal |
| Accept prechecks (check payment acceptance) | AcceptPrechecks, FDVSPrecheck |
| MFA / adaptive authentication | service/mfa (Citi RSA AA, CitiMFA) |

## Business Entities

Based on the configuration files, the platform operates with the following core data entities:

- **Cardholder / Member** — identified by `memberId` (UUID), account number (16-digit DDA), and program ID (8-digit).
- **Program** — 8-digit prepaid program identifier grouping business rules, branding, and payout configuration.
- **Card / Account** — prepaid card with DDA number, PIN, CVV, provision status, and access level.
- **Order** — disbursement instruction (card load, bulk order, package assignment, etc.).
- **Request** — transaction request with addenda metadata (VIN, invoice number, KYC status, etc.).
- **Transfer (IEFT)** — cross-border electronic funds transfer with country-specific validation rules.
- **Notification** — templated email or SMS event driven by cardholder account activity.
- **Job** — scheduled or real-time processing job managed by the job scheduler service.
- **Check** — physical or virtual check processed via AcceptPrechecks / FDVSPrecheck (Certegy).
- **Inventory Item** — physical card package tracked by inventoryMgmt.

## Business Rules & Validations

### Input Validation (accountmanagementapi, clientapi)
Field-level regex rules are externalised into `APIValidation.properties` and `clientapi.properties`:
- First name: letters, spaces, hyphens, periods — max 25 chars.
- SSN: exactly 9 digits (presence in config signals PII handling in scope).
- Account number: 16 digits required.
- PIN: 4 digits.
- CVV: 3–4 digits.
- Routing number: 9 digits.
- Email: standard RFC-style pattern with a maximum of 50 chars.
- Postal code: 5–6 alphanumeric.
- `newPinValue=[0-9]{4}` — PIN change must be numeric 4-digit.

### OFAC / Sanctions Email Restrictions
Restricted email domain suffixes `.cu,.ir,.kp,.sy,.ua` appear consistently across accountmanagementapi, CSWS, clientzone, CSA, oneplatform, and account service — blocking account operations for cardholders with email addresses associated with sanctioned territories (Cuba, Iran, North Korea, Syria, Ukraine).

### IEFT Country Eligibility
`IEFTCountries.xml` lists over 160 allowed destination countries for international transfers. Country-specific XML rule files enforce: channel type (ACH vs Wire), payment currency (USD, EUR, XCD, TTD, DKK, MXN, NOK, NZD, SEK, THB, TRY, JMD), and field-level IBAN/SWIFT/routing requirements.

### Account Status Lifecycle
`accountstatus=CLOSED|ACTIVE|Activate|activate|ACTIVATE` — the API recognises multiple case variants of activation status, indicating a legacy mixed-case issue.

### MFA / OTP
`mfaSwitch=ON` in MFA and clientzone configs. `otpRequired` is environment-toggled (Y/N). CitiMFA app IDs (CSIAppID 159547 for CZ, 158929 for OP) control OTP expiry (10 minutes).

### Delivery Code Rules
Express delivery code `069` (4-business-day); standard `000` (7–10 business day). FedEx programs use different SLA descriptions.

### KYC Gate
`kyc.portal.url` and associated OAuth client credentials enforce identity verification before card activation for designated programs via the Azure-hosted Activation Portal API.

## Business Flows

1. **Card Issuance**: Client submits `createAccount` or `issueCard` via accountmanagementapi → order service (`ordersvc.onbe.io`) → FDR card processor (via `ecountcore/FDRConfig`) → Strongbox (PIN generation) → card inventory management.
2. **Cardholder Activation**: Cardholder accesses oneplatform → KYC portal redirects to Activation Portal API → MFA OTP challenge → card activation via `pvproc.url` (FiServ `cardactivation`).
3. **Fund Load (addFunds)**: accountmanagementapi `addFunds` → order service → banker service for fund authorisation → JMS queue (TIBCO EMS or IBM MQ) → core ledger update.
4. **International Transfer (IEFT)**: Cardholder initiates transfer in OP → IEFT country rules validated → DFAPI client submits wire/ACH to Citi DFAPI SOAP endpoint → JMS response on IBM MQ.
5. **Notification**: Account/order events publish to JMS (TIBCO `notificationsvc.event2` / `notificationsvc.message2`) → notificationStrategy evaluates rules engine → mailer delivers via Mailgun API.
6. **Batch Processing**: Job scheduler (`jobschedulersvc.onbe.io`) dispatches autofile jobs → job agent consumes IBM MQ queue → autofile service processes bulk disbursement files.
7. **Check Precheck**: Client submits check via AcceptPrechecks → Certegy check verification → accept/decline decision.

## Compliance & Regulatory Concerns

| Area | Evidence in Config |
|---|---|
| PCI DSS | VISA JWE feature flags (`returnVisaJWE`, `returnEncryptedCard`, `returnCVV`); JWE DDA encryption (`jwe.encryptDDA=Y`, `jwe.secretKey` present); CVV inquiry security method; `cvvValue` regex in validation |
| OFAC / Sanctions | Hardcoded restricted email domain list (`.cu,.ir,.kp,.sy,.ua`) enforced at all portals and APIs |
| Reg E (NACHA / ACH) | ACH channel config in DFAPI, IEFT rules, prepaidJMS TIBCO queues (`citi.prepaid.na`), order service JMS |
| GLBA / Privacy | KYC portal OAuth integration; `ssnValue` regex in validation; email domain restriction for account lock |
| AML / CTF | OFAC country restrictions enforced in country selection — Cuba, Iran, North Korea, Syria, Ukraine blocked |
| eDelivery / ESIGN | `eDelivery.required=Y` in clientzone; edelivery service SOAP endpoint configured for production (`edvap1p`) |
| MFA (FFIEC) | Adaptive Authentication (RSA AA) and CitiMFA OTP enforced at OP and CZ portals |

## Business Risks

1. **Credentials in version control**: Multiple property files contain plaintext passwords, API keys, shared secrets, and JWE encryption keys (see Security Posture in File 05). This creates direct PCI DSS and GLBA exposure if the repository is accessible beyond authorised personnel.
2. **QA / Stage configuration mixed with production endpoints**: `eDeliveryPassword` in `edelivery.properties` points to a production endpoint (`edvap1p`). The `fdrODSDS.password` in `ecount-db.properties` appears to be production credentials for the FDR ODS system.
3. **Legacy mixed-case account status**: The `accountstatus` field accepts `Activate`, `activate`, and `ACTIVATE` — indicating inconsistent status normalisation that could lead to business logic gaps.
4. **Google reCAPTCHA secret key in config**: `google.secret.key` is stored in plaintext in oneplatform properties, exposing the ability to bypass CAPTCHA verification.
5. **Biocatch fraud-scoring integration**: Configured but switch is `OFF` (`biocatch.switch=N`), meaning real-time fraud scoring is not active for QA/stage cardholder flows.
6. **OFAC country list is email-domain-only**: Sanction screening is limited to email suffix checking — not a full OFAC SDN list check — which may be insufficient for a regulated payments business.
7. **Western Union integration URL present**: `westernUnion.URL` and `westernUnion.statickey` (plaintext credential) are present in oneplatform config, indicating a cross-border transfer feature that may carry regulatory obligations.
