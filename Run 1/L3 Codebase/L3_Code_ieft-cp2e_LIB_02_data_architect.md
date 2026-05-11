# Data Architect — ieft-cp2e_LIB

## Data Flow Overview

The library operates at the intersection of three data stores: the eCount Core SQL Server database, the StrongBox secure vault (XML-RPC), and the CP2E flat-file output. No data is persisted by the library itself; it is a read-extract-enrich-write pipeline.

## Data Sources

### 1. eCount Core SQL Server (`ecountcore` database)

Connection is resolved at runtime via the Director service; connection string is never hardcoded in application code. The data source is configured in `cp2eExtract.xml` (lines 16–23) using `DirectorConfiguredDBCPdatasourceCreator` which pulls the connection string from the Director service at `http://ppamwdcddcor1:80/service/dispatch.asp` (cp2eExtract.properties, line 1).

**Stored procedures invoked:**

| Procedure | Purpose |
|-----------|---------|
| `ieft_cfx_process_check_last_OTT_status` | Returns 1 if a prior OTT extraction failed, preventing duplicate double-spend. |
| `ieft_cfx_process_generate_file_sequence` | Allocates a monotonically increasing `request_file_id` (sequencing for Citibank). |
| `ieft_cfx_process_batch_extract` | Streams all pending AutoClaim wire records; accepts cutoff timestamp to prevent concurrency with live load. |
| `ieft_cfx_process_batch_extract_ott` | Streams a specific OTT request batch by `request_file_id`. |
| `ieft_cfx_process_upd_file_gen_flag` | Marks the OTT batch as successfully file-generated. |
| `ieft_get_migration_records` | Used by `Cp2eMigrateData` to find legacy `ZZ` country records requiring backfill. |
| `ieft_migration_update_country` | Updates country code in `CORE_IEFT_TRANSACTION_JOURNAL` during migration. |

**Key columns extracted per record** (inferred from `cp2eTemplate.xml` field mappings):

| Column / Field | Classification | CP2E field |
|----------------|---------------|-----------|
| `ieft_account_reference` | Functional key for StrongBox lookup | — |
| `transaction_ref` | Payment reference (non-PAN) | CP2E 1/1/5 |
| `amount` | Payment amount | CP2E 1/1/9 |
| `currency` | ISO 4217 code | CP2E 1/1/12 |
| `CustName` | Payee name | CP2E 1/1/14 |
| `individual_name` | Beneficiary name | CP2E 1/2/9, 1/9 |
| `TransDate` | Transaction date | CP2E 1/1/4 |
| `DebitAccNo` | Debit account number (Onbe/Citi) | CP2E 1/1/11 |
| `beneficiary_bank_name`, `beneficiary_bank_address1/2`, `beneficiary_bank_city` | Bank details | CP2E 4 |
| `CustAddr1`, `CustAddr2` | Customer address | CP2E 2 |
| `payment_memo`, `payment_detail1–7` | Payment detail narratives | CP2E 3 |

### 2. StrongBox Secure Vault

The StrongBox vault stores **Sensitive Authentication Data (SAD)** and bank account details for payees. `StrongBoxLookupHelper` (lines 63–68) reads back a structured map keyed on `ieft_account_reference` which returns a nested object graph that is flattened into the `cp2eRecord` Hashtable via `putDataIntoRecord()`.

**Fields retrieved from StrongBox:**

| Field key | Sensitivity | Usage |
|-----------|-------------|-------|
| `bank.accountNumber` | **HIGH** — full bank account number | CP2E 1/2/8 TgtAcct |
| `bank.routingNumber` | Moderate — bank routing/sort code | CP2E 1/3/10 TgtBankCde |
| `bank.accountType` | Low | CP2E 1/1/18 CustAcctTyp |
| `currency` | Low | Multi-field logic |
| `paymentDetails.TgtBnkCtryCde` | Moderate | Country routing logic |
| `address1`, `address2`, `city` | PII — payee address | CP2E 1/4 |
| `paymentDetails.payment_detail1–7` | Moderate | Payment narrative |
| `paymentDetails.bank_detail2–6` | Moderate | SWIFT / intermediary bank codes |

> **PCI DSS Note**: Bank account numbers (DDA/routing) sourced from StrongBox are written in full to the CP2E output file. The CP2E file itself is therefore **sensitive data in transit and at rest**. Handling of this file (transfer to Citibank via NDM/MFT, storage at `D:/c-base/runtime/ndmroot/cititest/program/ieft_cp2e/`, cp2eExtract.properties line 4) must be covered by file-level encryption and strict access controls aligned with PCI DSS Requirement 3.4.

## Data Entities

### CP2E Output File Entity Model

```
File Header (type 0)
  ├── Transaction Group (type 01)
  │   ├── Record 01: Core transaction (amount, CCY, debit acct, name)
  │   ├── Record 02: Beneficiary bank + account + country
  │   ├── Record 03: Payment details (SWIFT codes, bank codes)
  │   ├── Record 04: Beneficiary address
  │   └── Records 05–09: Summary, FX, advices, line items
  ├── Transaction Group (type 02)
  │   └── Records 01–04: Originator address, SWIFT, bank info
  ├── Transaction Group (type 03, 04, 05, 06, 07, 08)
  │   └── Payment details, intermediary banks, regulatory data
File Footer (type 9)
  └── Total record count, transaction count, total amount
```

## Sensitive Data Classification

| Data Element | PCI DSS Scope | GDPR/CCPA Scope | Protection Required |
|---|---|---|---|
| Bank account numbers (DDA) from StrongBox | Yes — Primary Account equivalent for ACH | Yes — financial data | Encrypt at rest and in transit; mask in logs |
| Routing numbers | Partial | Yes | Restrict access |
| Beneficiary name + address | No (not payment card data) | Yes — PII | GDPR Article 6 lawful basis required |
| Payment amounts | No | Potentially | Internal access control |
| IEFT account reference | Internal identifier | No | Audit trail |

## Data Quality Risks

1. **SQL injection risk**: `Cp2eExtractFile.java` line 153 constructs a JDBC query by concatenating a `Timestamp` string directly into the SQL: `"exec ieft_cfx_process_batch_extract " + request_file_id + ", '" + autoClaimExtractCutoff.toString() + "'"`. While `request_file_id` is an integer and `autoClaimExtractCutoff` is a `java.sql.Timestamp`, this pattern should be replaced with parameterized queries.

2. **Stale migration code**: `Cp2eMigrateData.java` uses string concatenation in a JDBC update: `"exec ieft_migration_update_country '" + strongBoxRef + "', '" + origCountry + "'"` (line 71). If `strongBoxRef` could contain special characters, this is exploitable.

3. **No retry on partial file failure**: If StrongBox calls partially fail mid-file, the file may contain fewer records than expected with no explicit row-count reconciliation against the extract procedure.

4. **Thread-safety gap**: `StrongBoxLookupHelper.sbClient` is a static field initialized in the constructor without synchronization (comment at line 39: "Not so much but I don't care"). Under concurrent initialization, two threads could both read `sbClient == null` and create competing clients.
