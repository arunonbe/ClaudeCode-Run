# cbts-client_LIB — Data Architect View

## Data Stores

This library contains **no data stores of its own**. It is a pure HTTP client library (JAR). All persistence occurs in:

- **CBTS Service** (remote REST API) — owns the canonical store for Remitters, Beneficiaries, Rates, Transfers, and Orders.
- **Cambridge Global Payments** — the ultimate record of FX rates, bookings, and international payment instructions (reached via CBTS).

The library's only local state is in-memory, within the `CBTSClient` instance (connection parameters, credentials). There is no local database, cache, or file system usage.

## Schema & Tables

Since this is a client library, there is no DDL. The data contracts are modelled as Java POJOs, which represent the JSON request/response structures exchanged with the CBTS REST API.

### Remitter (`Remitter.java`)
| Field | Type | Notes |
|---|---|---|
| `remitterId` | String | UUID-style identifier assigned by CBTS |
| `firstName` | String | Required (server-validated) |
| `lastName` | String | Required (server-validated) |
| `address` | Address | Required; addressLine1 required |
| `accountIdentifier` | String | Prepaid account/card number |
| `enabled` | boolean | Active/deactivated flag |
| `brand` | String | Program ID (e.g., "04017711") |
| `firstNameRecurring` | String | First 100 chars of recurring remitter name |
| `lastNameRecurring` | String | Chars 101–200 of recurring remitter name |
| `recurringRemitterAddr` | Address | Address for recurring remitter profile |

### Beneficiary (`Beneficiary.java`)
| Field | Type | Notes |
|---|---|---|
| `beneficiaryId` | String | UUID-style, assigned by CBTS |
| `remitterId` | String | FK to Remitter |
| `firstName` | String | PII |
| `lastName` | String | PII |
| `address` | Address | PII — cardholder address |
| `phoneNumber` | String | PII |
| `email` | String | PII |
| `bankCurrency` | String | ISO currency code |
| `paymentMethod` | PaymentMethod | WIRE or EFT |
| `swiftBicCode` | String | Bank identifier |
| `bankName` | String | |
| `bankAddress` | Address | |
| `accountNumber` | String | Sensitive — bank account number |
| `routingCode` | String | Sensitive — bank routing number |
| `regulatory` | Map<String,String> | Country-specific regulatory KV pairs |
| `enabled` | boolean | Active flag |

### Rate (`Rate.java`)
| Field | Type | Notes |
|---|---|---|
| `rateId` | String | UUID-style |
| `value` | BigDecimal | FX rate value |
| `amount` | BigDecimal | Payment amount in payer currency |
| `payersCurrency` | String | ISO currency code (e.g., "USD") |
| `beneficiariesCurrency` | String | ISO currency code (e.g., "CNY") |
| `requestType` | RequestType | ONE_TIME or RECURRING |
| `status` | RateStatus | NEW, BOOKED, EXPIRED, PAYMENT_REQUESTED, CANCELLED, PENDING_CONFIRMATION |
| `brand` | String | Program ID |
| `remitterId` | String | FK to Remitter |
| `indicative` | Boolean | If true, rate is not persisted |
| `paymentAmount` | BigDecimal | Amount in beneficiary currency |
| `bookingId` | String | Cambridge booking reference |

### Transfer (`Transfer.java`)
| Field | Type | Notes |
|---|---|---|
| `transferId` | String | Client-supplied UUID (idempotency key) |
| `rateId` | String | FK to Rate |
| `beneficiaryId` | String | FK to Beneficiary |

### Order / LookupOrderResponse (`Order.java`, `LookupOrderResponse.java`)
| Field | Type | Notes |
|---|---|---|
| `orderNumber` | String | External order reference |
| `entryDate` | String | Date of order |
| `buyCurrency` | String | |
| `buyAmount` | String | |
| `sellCurrency` | String | |
| `sellAmount` | String | |
| `exchange` | String | FX rate used |
| `ourAction` | String | Onbe's action on the order |
| `payments` | List<Payment> | Associated payment instructions |

### Address (`Address.java`)
| Field | Type |
|---|---|
| `addressLine1` | String |
| `addressLine2` | String |
| `addressLine3` | String |
| `city` | String |
| `province` | String |
| `countryCode` | String |
| `postalCode` | String |

### Enumerations
- **`PaymentMethod`**: `WIRE` ("W"), `EFT` ("E") — (`PaymentMethod.java`)
- **`RequestType`**: `ONE_TIME` ("one-time"), `RECURRING` ("recurring") — (`RequestType.java`)
- **`RateStatus`**: `NEW`, `BOOKED`, `EXPIRED`, `PAYMENT_REQUESTED`, `CANCELLED`, `PENDING_CONFIRMATION` — (`RateStatus.java`)
- **`TransferStatus`**: `PROCESSED`, `FAILED` — (`TransferStatus.java`)
- **`IsoCurrencyCode`**: Comprehensive enum of ~150 ISO 4217 currency codes with descriptions — (`IsoCurrencyCode.java`)

## Sensitive Data Handling

The following sensitive fields are present in the data model and are transmitted to CBTS in plain JSON bodies (serialised via Gson):

| Data Element | Class / Field | Classification |
|---|---|---|
| Bank account number | `Beneficiary.accountNumber` | Sensitive financial data |
| Bank routing code | `Beneficiary.routingCode` | Sensitive financial data |
| SWIFT/BIC code | `Beneficiary.swiftBicCode` | Semi-public but operationally sensitive |
| IBAN (in transit) | `IbanValidationResponse.iban` / `CBTSClient.validateIban()` | Sensitive bank identifier |
| Personal name | `Beneficiary.firstName`, `lastName` | PII |
| Physical address | `Beneficiary.address`, `Remitter.address` | PII |
| Phone number | `Beneficiary.phoneNumber` | PII |
| Email address | `Beneficiary.email` | PII |
| Card account identifier | `Remitter.accountIdentifier` | Payment instrument reference |
| FX amounts | `Rate.amount`, `paymentAmount` | Financial amount |

**Critical finding**: `Beneficiary.toString()` (`Beneficiary.java`, lines 181–199) emits ALL of the above fields (including `accountNumber` and `routingCode`) into the log stream. `CBTSClient.createUpdateBeneficary()` calls `log.info("Create/Update a beneficiary: " + bene.toString())` at line 249, meaning bank account numbers and routing codes are written to application logs at INFO level.

Similarly, the IBAN value is logged at INFO before validation (`CBTSClient.java`, line 491): `log.info("IBAN value for validateIban " + iban)`.

## Encryption & Protection

| Mechanism | Present | Details |
|---|---|---|
| TLS in transit | Yes (partial) | `CBTSClient.initSSLContext()` (lines 126–151) initialises TLS 1.2 but installs a **trust-all X509TrustManager** that accepts any server certificate — effectively disabling certificate validation |
| mTLS / client certificate | No | Only HTTP Basic authentication is used |
| Field-level encryption | No | All fields are sent as plaintext JSON |
| Credential vault | No | `USERNAME` and `PASSWORD` are hardcoded string literals in `CBTSClient.java` (lines 94–95) |
| Log masking | No | Sensitive fields appear verbatim in log output |
| HTTPS enforcement | Partial | The test `URIBase` (`CBTSClientTest.java`, line 47) uses `http://` (plain HTTP) against the QA environment |

## Data Flow

```
Calling Application (OP / Batch)
        |
        |  instantiates CBTSClient with uriBase, credentials, timeouts
        v
CBTSClient.java  (in-memory only)
        |
        |  HTTP Basic auth over TLS 1.2 (self-signed certs accepted)
        |  JSON serialisation via Gson
        |  CORRELATION-ID header propagated from MDC
        v
CBTS REST Service  (e.g., q-na-app08.nam.wirecard.sys:9443)
        |
        v
Cambridge Global Payments  (FX booking and wire settlement)
```

Data returned flows back: Cambridge → CBTS → JSON response body → Gson deserialisation → Java POJO → calling application.

## Data Quality & Retention

- **No input validation** is performed by this library beyond null/empty checks in `isOrderExists`. All field format, range, and referential integrity checks are delegated to the CBTS service, which returns structured `ErrorResponse` objects (errorcode, errorkey, errormessage, errorField).
- **`BeneficiaryRule`** objects returned by `getBeneRules` carry `validationRegEx` and `isRequired` flags that the calling application is expected to use for pre-submission validation, but enforcement is optional from the library's perspective.
- **No data retention logic** exists in this library; it is stateless after each method call completes.
- **Error response normalisation**: `getErrorResponse()` (`CBTSClient.java`, line 446–458) strips hyphens from the raw error JSON before deserialising (`structuredError.replaceAll("-", "")`). This is a fragile pattern that could corrupt numeric values or field names containing hyphens.

## Compliance Gaps

| Gap | Detail | Relevant Standard |
|---|---|---|
| TLS certificate validation disabled | `X509TrustManager` accepts all certificates, making the connection vulnerable to MITM attacks | PCI DSS v4.0.1 Req 4.2.1, NIST CSF PR.DS-2 |
| Hardcoded credentials in source | `USERNAME`/`PASSWORD` literals in `CBTSClient.java` lines 94–95 | PCI DSS v4.0.1 Req 8.3, NIST CSF PR.AC-1 |
| Sensitive data in logs (bank account, IBAN, PII) | `Beneficiary.toString()` and IBAN logged at INFO level | PCI DSS v4.0.1 Req 3.3, GDPR Art 5(1)(f) |
| HTTP (non-TLS) in test config | Test URIs use `http://` scheme | PCI DSS v4.0.1 Req 4.2 |
| No OFAC pre-screening | Beneficiary data sent to Cambridge without sanctions check in the client | OFAC SDN compliance expectation |
| Windows-1252 source encoding | `pom.xml` line 20: `<project.build.sourceEncoding>Windows-1252</project.build.sourceEncoding>` — `IsoCurrencyCode.java` already shows garbled characters (e.g., "Bol?viano", "S?o Tom?") indicating encoding corruption in currency descriptions | Data quality risk for non-Latin currencies |
