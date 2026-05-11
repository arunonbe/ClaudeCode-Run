# Data Architect Analysis — exemplar-cross-border-transfer-service_WAPP

## Partial Clone Limitation

Several modules are missing from the local clone due to Windows MAX_PATH. The data module (`cross-border-transfer-service-data`), persistence module (`cross-border-transfer-service-persistence`), and DB scripts module (`cross-border-transfer-service-db-scripts`) are not present. Data architecture analysis is inferred from available batch source code, `CambridgeClient.java`, and `pom.xml` dependencies.

---

## Overview

This service manages the data lifecycle of **cross-border remittance transactions**, acting as an orchestrator between Onbe's internal systems and the Cambridge Payments API. The data architecture combines:
- A SQL Server relational store (managed via Liquibase, `pom.xml` line 156) for transaction persistence.
- Spring Batch for batch job state management.
- SFTP file exchange with Cambridge (PGP-encrypted).
- Spring Cloud Config for externalised configuration.
- AWS S3 for file staging (`aws-java-sdk-s3` dependency, `pom.xml` line 193).

---

## Cambridge API Data Model (Inferred from `CambridgeClient.java`)

### Outbound Requests to Cambridge

| Request Object | Purpose | Sensitive Fields |
|----------------|---------|-----------------|
| `TokenRequest` | Auth token request | Client credentials |
| `SpotRateRequest` | FX spot rate quote | Currency pair, amount |
| `RemitterRequest` | Create/edit sender | Full name, address, ID documents (likely SSN/passport) |
| `BeneficiaryRequest` | Create/edit receiver | Full name, address, bank account, SWIFT/IBAN |
| `TransferRequest` | Instruct transfer | Amount, currency, remitter ID, beneficiary ID, deal ID |

### Inbound Responses from Cambridge

| Response Object | Purpose |
|----------------|---------|
| `TokenResponse` | Access token |
| `SpotRateResponse` | FX quote (quoteId, rate, expiry) |
| `BookDealResponse` | Booked deal confirmation |
| `InstructDealResponse` | Transfer instruction confirmation |
| `RequestCancellationResponse` | Cancellation request acknowledgement |
| `BookCancellationResponse` | Cancellation confirmation |
| `RemitterResponse` | Remitter record |
| `BeneficiaryResponse` | Beneficiary record |
| `BeneficiaryRulesResponse` | Country-specific beneficiary validation rules |
| `RateResourceResponse` | Rate details for a quote |

---

## Batch File Exchange Data Model

### Cambridge Reconciliation File
Imported by `ImportCambridgeReconFileBatchApp` / `ImportCambridgeReconFileReader` / `ImportCambridgeReconFileWriter`. Contents: transaction-level reconciliation data (deal numbers, amounts, statuses) delivered from Cambridge via SFTP.

Transformation:
- Download from Cambridge SFTP (`CambridgeSftpCommonChannelConfig`)
- PGP decrypt (`PGPDecryptionTasklet`)
- Parse records (`ImportCambridgeReconFileReader` — JSON line format via `JsonLineMapper`)
- Write to local database (`ImportCambridgeReconFileWriter`)
- Move file to archive (`ImportCambridgeReconFileMoveFileListener`)

### Cambridge Reject File
Similar pipeline to recon file but for rejected transactions (`ImportCambridgeRejectFileBatchApp`).

### Publish Recon File
Reads reconciliation records from database (`PublishCambridgeReconFileReader` → `CambridgeReconRecordsRowMapper`), writes to a file, PGP-encrypts, and uploads to Ecount SFTP (`EcountSftpCommonChannelConfig`).

### Publish Reject File
Similar pipeline for rejected records; includes a `PublishCambridgeRejectFileProcessor` step suggesting transformation logic.

---

## Key Data Entities (Inferred)

| Entity | Module | Description |
|--------|--------|-------------|
| `CambridgeReconRecord` | batch | Reconciliation record from Cambridge (deal ID, amount, status, dates) |
| `CambridgeRejectedRecord` | batch | Rejected transfer record |
| `AutomaticRateCancellationRecord` | batch | FX rate bookings due for automatic cancellation |
| Remitter | data (missing) | Sender identity and payment details |
| Beneficiary | data (missing) | Recipient identity and bank details |
| Transfer/Deal | data (missing) | FX deal and transfer record |
| FX Rate | data (missing) | Spot rate quote with expiry |

---

## Database Architecture (Inferred)

- **Database:** SQL Server (mssql-jdbc 9.2.1.jre11, `pom.xml` line 182)
- **Migration tool:** Liquibase (`pom.xml` line 156)
- **Migration app:** `cross-border-transfer-service-db-app` — standalone Spring Boot app for running migrations
- **H2 in-memory DB** — for testing (`h2:1.4.200`, `pom.xml` line 175)

**Note:** DB scripts module (`cross-border-transfer-service-db-scripts`) not present due to path length issue. Schema cannot be directly inspected.

---

## File Exchange Architecture

```
Cambridge SFTP Server
    |
    +--(PGP encrypted files)--> CambridgeSftpCommonChannelConfig (download)
                                    |
                                    v
                                PGPDecryptionTasklet (decrypt)
                                    |
                                    v
                                JsonLineMapper / FlatFileItemReader (parse)
                                    |
                                    v
                                SQL Server (persist)

SQL Server
    |
    v
CambridgeReconRecordsRowMapper / PublishCambridgeReconFileReader (read)
    |
    v
PGPEncryptionTasklet (encrypt)
    |
    v
EcountSftpCommonChannelConfig (upload to Onbe SFTP)
```

---

## Data Security and Compliance Observations

1. **PGP encryption** — `PGPUtils.java`, `PGPDecryptionTasklet`, `PGPEncryptionTasklet`, `PgpConfig` all present, confirming file exchange uses PGP. This is appropriate for financial file transfers.
2. **Cambridge API tokens** — `CMG-AccessToken` in HTTP headers; tokens should be short-lived and stored in a secrets manager, not in application properties.
3. **Remitter/beneficiary data** — `RemitterRequest` and `BeneficiaryRequest` objects likely contain full name, address, and bank account data. These are Category 1 PII and must be encrypted at rest and in transit.
4. **IBAN/SWIFT data** — Beneficiary bank data (IBAN, SWIFT, account numbers) is regulated financial data under Reg E and international payment rules. Retention and logging must be carefully controlled.
5. **Bootstrap credentials** — `bootstrap.yml` line 5 contains `password: [REDACTED — rotate immediately]` for the Spring Cloud Config server. This is a development/example credential that must be replaced before production deployment and must not appear in logs.
6. **Automatic rate cancellation** — the `AutomaticRateCancellationRecord` entity holds FX deal IDs and expiry information. Failure to process this batch correctly results in financial loss (expired deals charged at market rates).
