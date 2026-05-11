# Business Analyst View — cross-border-transfer-service_SVC

## 1. Business Purpose

The Cross-Border Transfer Service (CBTS) is Onbe's managed cross-border money-remittance platform. It acts as a middleware orchestrator between Onbe's internal systems (prepaid card programs, disbursement clients) and Cambridge Global Payments (now a Corpay division) to deliver international wire transfers in multiple currencies. The service supports one-time and recurring payment request types and is consumed by brands including Disney, RCCL, OnbeSunrise, OnbeFITB, ChicagoParkDistrict, Brightspot, and Onbe core programs (`application-qa.yml`, lines 152–238).

## 2. Business Capabilities

| Capability | Description |
|---|---|
| FX Rate Quoting | Requests a spot FX rate from Cambridge for a currency pair and amount |
| Rate Booking | Locks a quoted rate, recording the Cambridge `orderNumber` (booking ID) |
| Rate Cancellation | Cancels a booked or new rate both at Cambridge and locally; also runs automatically via batch |
| Remitter Management | Creates, edits, deactivates sender (remitter) profiles at Cambridge and locally |
| Beneficiary Management | Creates, edits, deactivates recipient (beneficiary) profiles including bank details, routing, SWIFT/BIC |
| Transfer Execution | Instructs Cambridge to execute a wire payment against a booked rate for a beneficiary |
| Reconciliation File Processing | Ingests Cambridge-generated CSV payment-history files via SFTP and stores them locally |
| Reject File Processing | Ingests Cambridge reject-reason files, marks transfers accordingly |
| Beneficiary Rules Lookup | Fetches Cambridge's field-level regulatory requirements for a country/currency pair (cached 14 days) |
| Bank Search | Searches Cambridge's bank directory by country and keyword |

## 3. Core Business Entities

| Entity | Class | Table | Key Attributes |
|---|---|---|---|
| Remitter | `Remitter.java` (persistence, line 19) | `REMITTER` | `remitterId`, `firstName`, `lastName`, `address`, `accountIdentifier`, `brand`, `gatewayRemitterId`, `enabled` |
| Beneficiary | `Beneficiary.java` (persistence, line 27) | `BENEFICIARY` | `beneficiaryId`, linked `Remitter`, `accountNumber`, `routingCode`, `swiftBicCode`, `bankName`, `bankCurrency`, `paymentMethod` (WIRE/EFT), `regulatory` map |
| Rate | `Rate.java` (persistence, line 22) | `RATE` | `rateId`, `amount`, `payersCurrency`, `beneficiariesCurrency`, `requestType`, `value`, `paymentAmount`, `status` (NEW/BOOKED/EXPIRED/PAYMENT_REQUESTED/CANCELLED), `gatewayRateId`, `gatewayBookingId`, `brand` |
| Transfer | `Transfer.java` (persistence, line 20) | `TRANSFER` | `transferId`, linked `Rate`, linked `Beneficiary`, `feeAmount`, `status` (PROCESSED/FAILED/CANCELLED/RETURNED/PROCESSING), `gateway` (CAMBRIDGE), `gatewayTransferId` |
| ReconFile | `ReconFile.java` (persistence, line 24) | `RECON_FILE` | `orderNumber`, `payeeId`, `payeeName`, `paymentCurrency`, `localCurrency`, `rate`, `bookedPaymentAmount`, `bookedSettlementAmount`, `settlementDate` |
| TransferReturn | `TransferReturn.java` (persistence, line 31) | `TRANSFER_RETURN` | `dealNumber`, `wireNumber`, `paymentReference`, `fxRate`, `returnedUSD`, `closed` |
| Address | `Address.java` (persistence) | `ADDRESS` | `addressLine1-3`, `city`, `province`, `countryCode`, `postalCode` |
| BeneficiaryRegulatoryRule | `BeneficiaryRegulatoryRule.java` | `BENEFICIARY_REGULATORY_RULE` | `RULE_KEY` / `VALUE` key-value map per beneficiary |

## 4. Business Rules

- **Rate expiry and auto-cancellation**: A Spring Batch job (`AUTOMATIC_RATE_CANCELLATION`) reads all rates in `NEW` or `BOOKED` status that have not yet been used and cancels them both at Cambridge and locally (`AutomaticRateCancellationProcessor.java`, line 64–82). Rates in status `PAYMENT_REQUESTED` or `CANCELLED` are excluded.
- **Spot rate lifecycle**: `RateStatus` enum defines: `NEW → BOOKED → PAYMENT_REQUESTED → CANCELLED/EXPIRED` (`RateStatus.java`, lines 7–11).
- **Transfer lifecycle**: `TransferStatus` enum defines: `PROCESSING → PROCESSED / FAILED / CANCELLED / RETURNED` (`TransferStatus.java`, lines 7–11).
- **Routing/SWIFT validation**: `BeneficiaryValidatorImpl` enforces routing code ≤ 50 characters, SWIFT/BIC ≤ 12 characters (`BeneficiaryValidatorImpl.java`, lines 38–46).
- **Address region required**: For US and CA beneficiaries, the `province` field is mandatory (`BeneficiaryValidatorImpl.java`, lines 30–35).
- **Payment method**: Currently `WIRE` ("W") and `EFT` ("E") — `PaymentMethod.java` line 3–5. All configured country-currency pairs in `application-qa.yml` (lines 388–430) map to `WIRE`.
- **Brand-to-client mapping**: A `brands` YAML map (40+ BIN prefixes) routes each Onbe brand to a named Cambridge client configuration (one-time vs. recurring) (`application-qa.yml`, lines 151–238, `TokenServiceImpl.java`, lines 72–88).
- **Settlement method**: Hard-coded to `"C"` (Cambridge collection) (`application-qa.yml`, line 431).
- **Duplicate recon detection**: Unique constraint `UDX_ORDER_NUMBER` on `RECON_FILE.ORDER_NUMBER` prevents double-import (`db.changelog-1.2-reconfileupdate.xml`, line 39).

## 5. Key Business Flows

### 5.1 Rate Quote and Book Flow
1. Caller `POST /rates` with amount, currencies, brand, and requestType.
2. `CreateRateHandler` → `SpotServiceImpl.getSpotRate()` → Cambridge `/api/{clientCode}/0/quotes/spot`.
3. Rate stored with `status=NEW`, `gatewayRateId` (Cambridge quoteId).
4. Caller `POST /rates/{rateId}/book`.
5. `BookRateHandler` → `SpotServiceImpl.bookDeal()` → Cambridge `/api/{clientCode}/0/quotes/{quoteId}/book`.
6. Rate updated to `status=BOOKED`, `gatewayBookingId` (Cambridge orderNumber) stored.

### 5.2 Transfer Execution Flow
1. Caller `POST /transfers` with `rateId` and `beneficiaryId`.
2. `CreateTransferHandler` validates that rate is `BOOKED` and beneficiary is `enabled`.
3. `SpotServiceImpl.instructDeal()` → Cambridge `/api/{clientCode}/0/order-book`.
4. Transfer stored with `status=PROCESSING`; on Cambridge success, updated to `PROCESSED`.

### 5.3 Reconciliation File Import Flow
1. Cambridge deposits a CSV `PaymentHistory-*.csv` on its SFTP server.
2. Batch job `IMPORT_CAMBRIDGE_RECON_FILE` downloads via SFTP (PGP-encrypted), decrypts using BouncyCastle.
3. `ImportCambridgeReconFileReader` parses CSV rows; `ImportCambridgeReconFileWriter` upserts into `RECON_FILE`.
4. File moved to `processed` or `failed` directory; email notification sent.

### 5.4 Reject File Processing Flow
1. Cambridge deposits a `Cambridge_Reject_File-*.csv` on its SFTP server.
2. Batch job `IMPORT_CAMBRIDGE_REJECT_FILE` ingests records and updates affected Transfer records to `FAILED`.
3. `PUBLISH_CAMBRIDGE_REJECT_FILE` batch job publishes a summary reject file back to eCount SFTP.

### 5.5 Rate Auto-Cancellation Batch Flow
1. `AutomaticRateCancellationReader` reads all `Rate` records in eligible statuses.
2. `AutomaticRateCancellationProcessor.process()` calls Cambridge request-cancellation then book-cancellation, then marks rate `CANCELLED` locally.
3. Failures are accumulated in `unableToCancelList` and emailed.

## 6. Compliance and Regulatory Observations

### OFAC / Sanctions Screening
**No OFAC or sanctions screening code is present in this repository.** The service does not perform name or country screening of remitters or beneficiaries before submission to Cambridge. It is assumed that screening is delegated entirely to Cambridge Global Payments or to an upstream service. This is a **material gap**: Onbe, as the instructing party, bears regulatory responsibility for OFAC compliance regardless of the downstream processor's checks. Internal compliance review recommended.

### Regulatory Field Map
`BeneficiaryRegulatoryRule` entity and the `BENEFICIARY_REGULATORY_RULE` table store key-value regulatory fields per country (e.g., tax IDs, purpose codes). These are passed through to Cambridge's template guide requirements. The values are not validated for format or completeness by CBTS itself — validation is outsourced to Cambridge's beneficiary-rules API (`GetBeneficiaryRulesServiceImpl`).

### Wire Transfer Rules
- Payment method `WIRE` is the only configured method for all active country/currency pairs.
- No FinCEN travel rule implementation (5 USD/3 USD threshold tagging) is visible in the codebase.
- No CTR (Currency Transaction Report) generation capability exists in the service.

### Data Residency / Privacy
- PII (first name, last name, address, phone, email, account number, routing code) is stored unencrypted at rest in SQL Server.
- No GDPR right-to-erasure or data-masking mechanism is implemented in the service.

## 7. Business Risks

| Risk | Severity | Detail |
|---|---|---|
| No OFAC screening | Critical | No sanctions/watchlist check before Cambridge submission; see section 6 |
| Credentials in source-controlled YAML | Critical | Full Cambridge API signatures, DB passwords, SMTP passwords in `application-qa.yml` (lines 26–385) |
| PII stored unencrypted | High | Account numbers, routing codes, names stored in plaintext in SQL Server |
| No idempotency control on transfer creation | High | No duplicate-transfer guard on `POST /transfers`; double-submission risk |
| Java 1.8 stated in README vs. Java 21 in pom.xml | Medium | README (`README.md` line 6) says Java 1.8; `pom.xml` line 35 targets Java 21 — documentation is misleading |
| Payment method validation commented out | Medium | `BeneficiaryValidatorImpl.java` lines 24–26 comment explains payment-method validation was removed |
| Rate cancellation failure is non-blocking | Medium | `AutomaticRateCancellationProcessor` catches exceptions and continues; Cambridge may retain open positions |
