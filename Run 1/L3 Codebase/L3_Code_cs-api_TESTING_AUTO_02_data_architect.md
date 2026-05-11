# Data Architect View — cs-api_TESTING_AUTO

## Data Stores
This repository does not own or manage any data stores. All data is either:
- Embedded in XML SOAP request fixture files under `SoapRequest/`
- Received transiently as SOAP XML responses from the live QA endpoints
- Not persisted anywhere by the test code

## Schema (SOAP Request Payloads)
The request fixtures reveal the schemas used by the CS API family:

### accountInquiry (V1)
Fields: `application_id`, `card_number`, `puid`, `balance_detail` (int), `journal_detail` (int), `registration_detail` (int), `start_date` (int YYYYMMDD), `end_date` (int YYYYMMDD), `max_items` (int)

### accountInquiry (V3)
Fields: same as V1 plus `ppd`, `mobile_phone` (both nullable)

### reissueCard
Fields: `application_id`, `puid`, `block_code`

### authenticationRequest (Payout)
Fields: `applicationId`, `userName`, `password`

### registrationRequest (Payout)
Fields: `applicationId`, `cardNumber`, `cvv`, `postalCode`, `emailAddress`, `phoneNumber`, `userName`, `password`

### payoutAccountInquiry
Fields: `application_id`, `card_number`, `dda_number`, `puid`, `ppd`, `mobile_phone`, `balance_detail`, `journal_detail`, `registration_detail`, `start_date`, `end_date`, `max_items`

### updateRegistrationRequest
Fields: `accountNumber`, `appId`, `updateRegistrationDetails` (complex type with address, name, phone, email fields)

## Sensitive Data — Locations (Values NOT Reproduced)
| Data Type | Classification | File | PCI/Reg Risk |
|---|---|---|---|
| Full Primary Account Number (PAN) | PCI SAD | SoapRequest/AccountInquiryV3.xml | PCI DSS Req 3.3/3.4 — MUST be removed |
| Full Primary Account Number (PAN) | PCI SAD | SoapRequest/RegistrationReq.xml | PCI DSS Req 3.3/3.4 — MUST be removed |
| CVV/CVC | PCI SAD | SoapRequest/RegistrationReq.xml | PCI DSS Req 3.3 — MUST be removed, never store post-auth |
| Plaintext password | Credential | SoapRequest/AuthenticationReq.xml | NIST CSF — rotate immediately |
| Plaintext password | Credential | SoapRequest/RegistrationReq.xml | NIST CSF — rotate immediately |
| Email address (internal domain) | PII/GDPR | SoapRequest/RegistrationReq.xml | GDPR/CCPA |
| Email address (legacy domain) | PII | SoapRequest/UpdateRegReq.xml | GDPR/CCPA |
| Full name (first, last, middle) | PII | SoapRequest/UpdateRegReq.xml | GDPR/CCPA |
| Address (street, city, state, ZIP) | PII | SoapRequest/UpdateRegReq.xml | GDPR/CCPA |
| Phone numbers | PII | SoapRequest/UpdateRegReq.xml | GDPR/CCPA |
| DDA number | Financial identifier | SoapRequest/PayoutAccountInquiry.xml | PCI/Reg E |
| Application IDs (API keys) | Credential | Multiple XML files | Rotate if live |
| PUID values | Cardholder identifier | Multiple XML files | PII concern |

## Encryption
No encryption of any kind is present in this repository. All fixture data is plaintext XML. The transmission to the QA endpoint uses HTTPS (port 4005/4007), which provides transport-layer encryption only.

## Data Flow
```
[Test XML Fixture] --HTTP POST (SOAP/XML)--> [QA Endpoint: webservice-qa.wirecard.com:4005 or :4007]
                                                     |
                                             [XML Response]
                                                     |
                                          [XmlPath parse in Java]
                                                     |
                                          [Pattern.compile regex assertion]
```

## Data Quality
- No data quality controls exist within the test suite itself.
- No schema validation of response XML.
- Test assertions verify only a single string field per test.
- No checks on response structure completeness, null handling, or error scenarios.

## Compliance Gaps
1. **PAN and CVV in source control** — violates PCI DSS Requirement 3 and should be treated as a breach event until confirmed as test-only data. The repository owner must declare whether these are live or synthetic values.
2. **No data masking** — test fixtures should use synthetic card numbers (e.g., Luhn-valid BIN 411111xxxxxx0000 pattern) and synthetic CVV (e.g., 000).
3. **GDPR/CCPA** — real-looking personal names and email addresses committed to source control represent a data minimisation violation even in test contexts.
4. **No secrets management** — application IDs functioning as API keys are committed in plaintext. These should be injected via environment variables or a secrets vault at test runtime.
5. **Legacy external domain** — email addresses referencing wirecard.com domain represent stale test data from the Wirecard era that has not been cleaned up post-acquisition.
