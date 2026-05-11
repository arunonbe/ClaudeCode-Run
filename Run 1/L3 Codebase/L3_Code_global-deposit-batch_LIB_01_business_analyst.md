# Business Analyst Report — global-deposit-batch_LIB

## 1. Executive Summary

`global-deposit-batch_LIB` is a Java Spring Batch library that processes bulk global deposit (cross-border fund transfer / ACH load) operations for Onbe's prepaid card platform. Originally developed under the Wirecard brand (`com.wirecard.globaldepositsbatch` package namespace, Wirecard SCM URLs), the library manages three distinct batch job pipelines for processing international electronic funds transfers (iEFT) — specifically recurring global deposits, migration of global deposit records, and processing of cross-border transfer rejection files from the Cambridge FX partner (CBTS).

The library is structured as a multi-module Maven project (version `2.0.4-SNAPSHOT`) with six sub-modules, targeting Java 8 and Spring Boot 2.3.4. It is classified as a `_LIB` repository, indicating it is a shared library consumed by other services rather than a standalone deployable service.

---

## 2. Business Capabilities

### 2.1 Batch Job 1: Recurring Global Deposit Service

**Class**: `RecurringGlobalDepositServiceBatchApp.java`
**Config**: `RecurringGlobalDepositServiceConfig.java`

Processes recurring iEFT (international electronic funds transfer) transactions from the `core_ieft_transaction_journal` database table. For each record:
1. Reads pending iEFT records from the database
2. Calls the Cambridge CBTS (Cross-Border Transfer Service) to execute currency exchange and transfer
3. Updates the transaction status in the database:
   - Status 1 (`tx_status=1`): Successfully transferred
   - Status 5 (`tx_status=5`): Failed due to invalid data (per `RecurringGlobalDepositServiceProcessor.java` line 57)
   - Status 6 (`tx_status=6`): Unexpected error (line 63)
4. Manages addenda records in `core_ieft_transaction_journal_addenda` for NACHA addenda data (field type 185)

**Business process**: This is the primary ACH/iEFT load mechanism for global prepaid card funding. Supports recurring deposits where cardholders have scheduled regular funding.

### 2.2 Batch Job 2: Global Deposit Reject Process

**Class**: `GlobalDepositRejectProcessBatchApp.java`
**Config**: `GlobalDepositRejectProcessConfig.java`

Processes rejection files from Cambridge FX (CBTS) for cross-border transfers that were returned/rejected. The input files are CSV files named `cambridge-rejected-transactions-*.csv` (evidenced by test data files in `global-deposits-batch-qa/src/test/resources/`).

**CSV structure** (from `GlobalDepositRejectsItemReader.java` line 47):
```
transferId, returnedUsd, amount, fee, returnReason, fxRate
```

Processing flow:
1. Read CSV reject files from `input` directory
2. Update corresponding records in the database to "rejected" status
3. Move processed files to `processed` or `failed` directory
4. The `GlobalDepositRejectsMoveFileStepListener` handles file movement after step completion

**Business process**: Handles the return/rejection lifecycle for cross-border transfer failures (e.g., invalid beneficiary, compliance rejection, FX rate rejection). Directly relevant to NACHA Reg E return processing obligations.

### 2.3 Batch Job 3: Global Deposit Migration

**Class**: `GlobalDepositMigrationBatchApp.java`
**Config**: `GlobalDepositMigrationConfig.java`

Migrates global deposit records from a legacy data model to the current platform. This is a one-time or periodic data migration job that reads `GlobalDepositMigrationRecord` objects, processes them, and writes them to the target schema.

**Business process**: Supports data migration activities, likely associated with Wirecard → Onbe platform migration.

---

## 3. CBTS Integration

The library integrates with the **Cambridge Global Payments Cross-Border Transfer Service (CBTS)** via two client modules:

### 3.1 CBTS Direct Client (`global-deposits-batch-cbts-client`)
- `CbtsClient.java`: HTTP client to CBTS API
- `RateServiceImpl.java`: Rate retrieval and transfer booking
- Endpoints (from `application.yml` lines 31–35):
  - Rate URL: `/rates`
  - Book rate URL: `/rates/{rateId}/book`
  - Transfer URL: `/transfers`
- Base URL: `https://cbts-dev.amer1.wirecard.com/cross-border-transfer-service`

### 3.2 xPlatform CBTS Client (`global-deposits-batch-xplatform-client`)
- `IEFTServiceImpl.java`: Registers beneficiaries and remitters, executes on-demand cancellations
- `XplatformIEFTManager.java`: Manages the actual iEFT operations through the xPlatform layer
- Methods: `registerBeneficiary()`, `registerRemitter()`, `cancelOnDemand()` (`IEFTServiceImpl.java` lines 24, 44, 58)

The dual-client architecture suggests a transition from a direct CBTS integration to an xPlatform-mediated integration.

---

## 4. Regulatory Relevance

### 4.1 NACHA

This library is directly relevant to NACHA Operating Rules:
- **Addenda records**: The `core_ieft_transaction_journal_addenda` table with `field_type = 185` maps to NACHA addenda type code 185 for cross-border entries (`RecurringGlobalDepositServiceProcessor.java` lines 20–23)
- **Return processing**: The reject process batch job implements NACHA R-code return handling from Cambridge FX
- **Timing obligations**: NACHA requires ACH returns to be processed within 2 business days. The batch job's timing and scheduling configuration directly affects compliance with this requirement

### 4.2 Reg E

Regulation E governs electronic fund transfers for consumer accounts:
- Failed/rejected transfer records (tx_status=5, 6) must be communicated to cardholders per Reg E Section 205.6 (liability limits) and 205.11 (error resolution)
- The reject CSV processing pipeline produces the data needed to trigger Reg E error resolution notifications

### 4.3 OFAC / Sanctions

Cross-border fund transfers are subject to OFAC sanctions screening. The `CbtsGatewayCommunicationException` and `InvalidDataException` in the CBTS client module (`global-deposits-batch-cbts-client`) may surface CBTS-side sanctions screening rejections.

### 4.4 PCI DSS

The `core_ieft_transaction_journal` table processes fund transfer records that may contain account identifiers. The CBTS integration transmits financial transaction data to an external service, requiring PCI DSS Requirement 4.2 compliance for data in transit.

---

## 5. Data Entities and Models

### 5.1 Prototype Data Records

| Class | Key Fields | Description |
|---|---|---|
| `RecurringGlobalDepositRecord` | `rowId`, `rateId`, and other iEFT fields | A single iEFT journal entry for recurring processing |
| `GlobalDepositRejectRecord` | `transferId`, `returnedUsd`, `amount`, `fee`, `returnReason`, `fxRate`, `created` | A rejected transfer record from Cambridge CSV |
| `GlobalDepositMigrationRecord` | (migration-specific fields) | Legacy record for migration |

### 5.2 CBTS Data Models

| Class | Description |
|---|---|
| `Rate` | FX rate from CBTS |
| `RateStatus` | Rate booking status |
| `Transfer` | Transfer execution response |
| `RequestType` | CBTS request type enum |
| `ErrorResponse` | CBTS error structure |

---

## 6. Operational Parameters

From `application.yml` (lines 47–60), the batch job configuration:

| Job | Parameter | Default Value |
|---|---|---|
| Recurring Global Deposit | `page-size` | 1 |
| Recurring Global Deposit | `max-item-count` | 1,000,000 |
| Recurring Global Deposit | `chunk-size` | 10 |
| Global Deposit Reject | `chunk-size` | 10 |
| Global Deposit Migration | `page-size` | 100 |
| Global Deposit Migration | `max-item-count` | 1,000,000 |
| Global Deposit Migration | `chunk-size` | 10 |

The `max-item-count` of 1,000,000 indicates these batch jobs are designed to process very high volumes of transactions.
