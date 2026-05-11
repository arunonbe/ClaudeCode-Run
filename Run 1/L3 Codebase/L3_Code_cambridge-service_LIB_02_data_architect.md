# cambridge-service_LIB — Data Architect View

## Data Stores

This library has **no local data store** of any kind. It is a pure SOAP client integration library. There are no:
- Database connections or JPA/Hibernate entities
- File-based caches or queues
- In-memory stores (no Redis, Hazelcast, Ehcache)
- Message broker bindings

All data persisted in this domain lives within the Cambridge FX platform, accessed exclusively via SOAP/WS over HTTPS. The consuming service is responsible for any local persistence of order numbers, beneficiary IDs, tokens, or audit records.

---

## Schema & Tables

No local schema exists. The "schema" for this library is the Cambridge SOAP XML contract. Key message types derived from the WSDL (auto-generated with Apache Axis2 1.7.5, May 2017):

### Beneficiary Domain
| Class | Namespace Prefix | Key Fields |
|---|---|---|
| `BeneficiaryCore` | `ns7` | `beneficiaryId` (String), `beneficiaryName` (String), `currency` (String ISO-4217), `paymentMethods` |
| `BeneficiaryComplete` extends `BeneficiaryCore` | `ns7` | Adds: `alerts`, `bankDetails`, `beneficiaryAddress`, `compliance`, `contact`, `defaultInternalComment`, `defaultPaymentReference`, `mailing`, `regulatoryFields` |
| `BankAccountInformation` extends `BankInformation` | `ns7` | `accountNumber` (String), `routingNumber` (String), SWIFT/BIC, institutionName, address |
| `BeneficiaryCompliance` | `ns7` | `classification` (enum), `payPurpose` (String) |
| `BeneficiaryAlerts` | `ns7` | Alert notification settings |
| `BeneficiaryContact` | `ns7` | Contact details |
| `BeneficiaryMailing` | `ns7` | Mailing preferences |
| `ArrayOfRegulatoryField` | `ns7` | Country-specific regulatory fields |
| `ValidationRuleSpec` | `ns7` | `fieldName`, `validationRegex`, `valueRange`, `suggestedValues` |

### Bank Domain
| Class | Namespace Prefix | Key Fields |
|---|---|---|
| `Bank` | bankservice ns | `bankDetails` (contains `institutionName`, `address`), `branchName` |
| `BankInformation` | base API ns | `institutionName`, `SWIFTBIC`, `address` (AddressFourLine) |
| `GetBankDetailsRequest/Response` | bankservice ns | Request: securityToken, bank identifier; Response: `Bank` object |
| `SearchBanksRequest/Response` | bankservice ns | Request: securityToken, address criteria, countryISO2; Response: `ArrayOfBank` |

### Trade Domain
All trade data types live in `org.datacontract.schemas._2004._07.cambridge_service_integration_api_tradeservice`:
- `GetRateRequest`, `GetRateAmount` — amount (BigDecimal), lockSide, paymentCurrency, settlementCurrency
- `BookDealRequest` — securityToken, quoteIds (ArrayOfstring), correlationId
- `CancelDealRequest` — securityToken, quoteId, correlationId
- `InstructPaymentRequest` — securityToken, beneficiaryId, dealNumber, paymentAmount (BigDecimal), paymentMethod (enum WIRE)
- `InstructPaymentSettlementRequest` — same fields as above

### Common Types
| Class | Package | Purpose |
|---|---|---|
| `SecurityToken` | `cambridge_service_integration_api` | Wraps token string passed on every request |
| `AddressFourLine` / `AddressTwoLine` | `cambridge_service_integration_api` | Two address variants used by banks and beneficiaries |
| `ClientIdentifier` | `cambridge_service_integration_api` | Optional client context for requests |
| `OperationStatus` | `cambridge_service_integration_api` | Uniform success/error response wrapper (fields: `success`, `errors`) |
| `Pagination` / `PaginationTotal` | `cambridge_service_integration_api` | Paging parameters for list operations |
| `SettlementMethod` | `cambridge_service_integration_api` | Enum for settlement types |
| `SimpleValidationResult` | `cambridge_service` | Basic validation outcome |
| `ApprovalStatus` | `cambridge_logic_query_beneficiary` | Enum for beneficiary approval states |
| `MatchCS` / `SearchCriteriaMatchCS` | `cambridge_logic_query` | Search operator enums (Contains, StartsWith, etc.) |

### Microsoft Serialization Types
The package `com.microsoft.schemas._2003._10.serialization` contains auto-generated primitive wrappers (`Guid`, `DateTime`, `Decimal`, `Base64Binary`, `ArrayOfstring`, etc.) matching the .NET WCF DataContract serialization schema. These are data exchange artefacts generated from the Cambridge WCF service WSDL.

---

## Sensitive Data Handling

The following sensitive data fields are present in the data model and are transmitted over the wire:

| Field | Class | Sensitivity Level | Current Handling |
|---|---|---|---|
| `accountNumber` | `BankAccountInformation` | HIGH — bank account number | Passed as plain-text XML element in SOAP body; no masking in library |
| `routingNumber` | `BankAccountInformation` | HIGH — ABA routing number | Plain-text XML element; no masking |
| `SWIFTBIC` | `BankInformation` | MEDIUM — bank identifier | Plain-text XML element |
| `sharedSecretKey` | `CambridgeServiceContext` | CRITICAL — HMAC signing key | Injected via Spring property `${sharedSec}` from external properties file; not committed in source, but no in-memory protection |
| `token` | `SecurityToken` | HIGH — bearer session credential | Short-lived but passed in every SOAP request; no expiry management in library |
| `beneficiaryId` | Various | MEDIUM — internal ID | Used as a persistent reference; one value hard-coded in `App.java` (line 157: `873f8ed7339e4178a3c0983f656cd38d`) |
| `beneficiaryName` | `BeneficiaryCore` | MEDIUM — PII | Plain-text transmission |
| Address fields | `AddressFourLine`, `AddressTwoLine` | MEDIUM — PII | Plain-text transmission |
| `payPurpose` | `BeneficiaryCompliance` | LOW-MEDIUM | Plain-text; value `"Payroll"` in demo code |

**No field-level encryption is applied.** Protection relies entirely on transport-layer TLS (HTTPS enforced via WS-Policy `HttpsToken` in all stub operations).

---

## Encryption & Protection

### Transport Security
All four stub classes (`SSOServiceStub`, `TradeServiceAPIStub`, `BankServiceAPIStub`, `BeneficiaryServiceAPIStub`, `RegEDisclosureServiceAPIStub`) apply WS-SecurityPolicy `TransportBinding` with:
- `sp:HttpsToken` (RequireClientCertificate="false") — TLS required, no mutual TLS
- `sp:Basic256` algorithm suite — AES-256 / SHA-256 cryptographic policy
- `sp:Strict` layout — strict WS-Addressing enforcement
- `wsaw:UsingAddressing` — WS-Addressing mandatory

This is enforced via inline WS-Policy XML embedded in each `populateAxisService()` method, applied to every SOAP operation.

### Authentication Signature
`CambridgeServiceHelper.getDigitalSignature()` computes:
```
hash(sharedSecretKey | "returnurl" | returnURL | "username" | userName | "timestamp" | timestamp)
```
Using `java.security.MessageDigest` with algorithm from `${algorithm}` property. The hash is hex-encoded. The algorithm name is not validated in code, creating risk of weak algorithm injection (e.g., MD5 or SHA-1) via misconfiguration.

### No Message-Level Encryption
No WS-Security message-level encryption (`sp:EncryptedParts`) is present — protection is transport-only.

### Secret Key Management
The `sharedSecretKey` is injected via Spring's `PropertyPlaceholderConfigurer` from a file at the hardcoded path `d:/c-base/config/service/cambridgeService/cambridgeService.properties` (line 9 of `appContext-CambridgeService.xml`). This is a **Windows drive-letter absolute path**, indicating local filesystem deployment. No vault integration (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) is evident.

---

## Data Flow

```
Consumer Service
      |
      v
App.java / CambridgeServiceImpl
  (Spring IoC: appContext-CambridgeService.xml)
      |
      |-- SSOServiceImpl --> SSOServiceStub
      |       |                 |
      |       v                 v SOAP/HTTPS
      |   (token string)    Cambridge SSO endpoint
      |                     https://isbeta.cambridgefxonline.com/Service.svc/sso
      |
      |-- TradeServiceImpl --> TradeServiceAPIStub
      |       |                     |
      |       v                     v SOAP/HTTPS
      |   (quoteId, orderNumber)  Cambridge Trade endpoint
      |                           https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiTrade
      |
      |-- BeneficiaryServiceImpl --> BeneficiaryServiceAPIStub
      |       |                           |
      |       v                           v SOAP/HTTPS
      |   (beneficiaryId)          Cambridge Bene endpoint
      |                            https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiBene
      |
      |-- BankServiceImpl --> BankServiceAPIStub
      |       |                   |
      |       v                   v SOAP/HTTPS
      |   (Bank[])           Cambridge Bank endpoint
      |                      https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiBank
      |
      |-- RegEDisclosureServiceAPIStub
              |
              v SOAP/HTTPS
          Cambridge RegE endpoint
          https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiRegEDisclosure
```

All sensitive data flows outbound to Cambridge over HTTPS. No inbound data is stored locally by this library.

---

## Data Quality & Retention

- **No validation layer**: The library passes data to Cambridge without pre-validation. Field validation is delegated to Cambridge via `getDynamicValidationRules`. There is no local enforcement of required fields, format checks, or length limits.
- **No data retention**: As a client library, no data is retained. The consuming application bears full responsibility for logging, audit trails, and retention.
- **Idempotency**: `createOrUpdateBeneficiary` supports upsert semantics (update if beneficiaryId already exists). `bookDeal` is not idempotent — duplicate calls with the same quoteId will result in duplicate bookings or errors from Cambridge.
- **Error propagation**: `OperationStatus` contains `success` boolean and `errors` array. `TradeServiceImpl.instructPaymentSettlement()` (lines 263–264) checks `operationStatus.getSuccess()` and returns error strings — the only example of explicit business error handling in the library.

---

## Compliance Gaps

| Gap | Detail | Relevant Regulation |
|---|---|---|
| Bank account and routing numbers transmitted in plain XML | No field-level encryption; only TLS at transport layer | PCI DSS requirement for protection of sensitive financial data |
| No tokenisation or masking of account numbers | Full account numbers passed through `BankAccountInformation.accountNumber` without any masking | PCI DSS, GLBA |
| Shared secret stored in local filesystem properties file at a hardcoded Windows path | `d:/c-base/config/...`; no vault or HSM | NIST CSF PR.AC, PCI DSS key management requirements |
| No audit logging | No logging framework usage in any class; exceptions printed with `printStackTrace()` | PCI DSS requirement 10 (audit logging), SOC 2 CC7 |
| Weak algorithm configurable | `algorithm` injected as property; no validation preventing SHA-1 or MD5 | NIST CSF cryptographic standards |
| Reg E disclosure stub never implemented | `RegEDisclosureServiceAPIStub` exists with no `RegEDisclosureServiceImpl` | Reg E (12 CFR Part 1005, Subpart B) |
| PII (beneficiary name, address) transmitted without masking in SOAP body | Visible in transit logs and any intercepting proxy | GDPR Article 25, CCPA |
| Beta endpoints hardcoded | All default constructors resolve to `isbeta.cambridgefxonline.com` | Operational risk; production data must not flow to beta environments |
