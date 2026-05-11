# Business Analyst Report — DS_ETL_ccp-import-to-legacy

## Repository Identity

**Repository:** DS_ETL_ccp-import-to-legacy  
**Classification:** ETL Pipeline — CCP to Legacy Platform Bridge  
**Technology:** Microsoft SQL Server Integration Services (SSIS) — SQL Server 2012 (11.0.5058.0)  
**Package count:** 10 SSIS packages (.dtsx files)  
**Project created:** April 2019 (WIRECARD\julia.ginzburg on workstation PF0VET79)  
**Project name:** `ccp.import2012`

---

## Business Purpose

DS_ETL_ccp-import-to-legacy is the **CCP-to-legacy bridge ETL pipeline**. As documented in the README:
> "SSIS project that takes content produced from the project (WDNAM >> CCP >> ETL >> CCP-Export-To-Legacy) and imports it into the legacy platform."

This pipeline is a **data migration/synchronisation bridge** that:
1. Receives data exported from the CCP (Card/Client Processing Platform) via the `DS_CCP_ccp-export-to-legacy` pipeline
2. Imports it into the legacy `ecount` platform databases (ECNT/ECAN)

This represents a **dual-platform operation period** during which Onbe was running both a legacy card processing platform (eCount) and the newer CCP system in parallel. The CCP-import-to-legacy pipeline ensures the legacy platform stays synchronised with CCP data.

---

## Import Packages and Business Processes

### 1. Import_bin_account.dtsx — Card Account Import
**Business process:** Imports card account records from CCP into the legacy system  
**Source file pattern:** `sunrise_wdccp_customer_<date>.txt` (pipe-delimited)  
**Key data fields:**
- `RecordType` (1 char)
- `ProgramCurrency`
- `AccountIdentifier` (32 chars — card account identifier)
- `AccountCreateDate`
- `CardNumber` (4 chars — likely last 4 digits of card number — **PCI-relevant**)

**CDE Flag:** `CardNumber` field and `AccountIdentifier` field are card-adjacent data. If `AccountIdentifier` is a tokenised PAN or account reference linked to a card, this table is CDE-scoped.

### 2. Import_bin_cardstatus.dtsx — Card Status Import
**Business process:** Imports card status updates (active, inactive, lost, stolen, expired) from CCP  
**Source file pattern:** `sunrise_wdccp_cardstatus_<date>.txt`  
**Key data fields:**
- `RecordType`
- `Date`
- `AccountIdentifier` (32 chars)
- `CardNumber` (4 chars)
- `CardExpirationDate` (date type — `DataType="133"`)

**CDE Flag:** `CardNumber` and `CardExpirationDate` together constitute **partial SAD (Sensitive Authentication Data)**. If `CardNumber` is the last 4 digits of the PAN rather than a surrogate, and `AccountIdentifier` links to the full PAN, the combination creates a data linkage risk. PCI DSS Req 3.3 prohibits storing SAD post-authorisation.

### 3. Import_bin_transaction.dtsx — Transaction Import
**Business process:** Imports posted transaction records from CCP into the legacy transaction history  
**Source file pattern:** `sunrise_wdccp_postedtran_<date>.legacy.txt` (pipe-delimited)  
**Key data fields:**
- `RecordType`
- `UniqueTransactionId` (32 chars)
- `SettlementDate`
- `TransactionDate`
- Transaction amounts (decimal precision 19/5)

### 4. Import_bin_balances.dtsx — Balance Import
**Business process:** Imports card account balance data from CCP

### 5. Import_billing_audit.dtsx — Billing Audit Import
**Business process:** Imports billing audit records from CCP for fee reconciliation

### 6. Import_billing_detail.dtsx — Billing Detail Import
**Business process:** Imports detailed billing records from CCP

### 7. Import_fvd_revenue.dtsx — Face Value Discount Revenue Import
**Business process:** Imports FVD (Face Value Discount) revenue records — the revenue recognition for gift card programs

### 8. Import_fvd_deferred.dtsx — FVD Deferred Revenue Import
**Business process:** Imports FVD deferred revenue records for ASC 606 deferred revenue accounting

### 9. Import_fvd_singleload.dtsx — FVD Single-Load Import
**Business process:** Imports single-load FVD records

### 10. Import_fiserv_inventory.dtsx — Fiserv Inventory Import
**Business process:** Imports card inventory data from Fiserv (card manufacturing/embossing provider) into the legacy system

---

## Data Pipeline Context

The CCP import pipeline is **downstream** of the CCP export pipeline:

```
[CCP Platform]
    ↓ DS_CCP_ccp-export-to-legacy (separate repo)
[Export files: C:\ETL\In\WDCCP\]
    ↓ DS_ETL_ccp-import-to-legacy (this repo)
[CCP-SQLDB (d-na-db01.nam.wirecard.sys\db01,2232)]
    ↓ Legacy import procedures
[Legacy eCount platform (ECNT/ECAN)]
```

The intermediate landing database is `CCP` on `d-na-db01.nam.wirecard.sys\db01`.

---

## Regulatory Relevance

### PCI DSS — HIGH PRIORITY
The `Import_bin_account.dtsx` and `Import_bin_cardstatus.dtsx` packages process card account identifiers and card numbers. If `CardNumber` (4-char field) is the last 4 digits of a PAN, it is permitted to store. However:
- `AccountIdentifier` (32 chars) could be a tokenised or partial PAN
- `CardExpirationDate` is SAD — storing it post-authorisation violates PCI DSS Req 3.3

The CCP export files (source files like `sunrise_wdccp_customer_20191105.txt`) originate from the Sunrise Banks CCP system. These files' data classification must be formally reviewed by the PCI QSA to determine CDE scope of this ETL pipeline.

### NACHA / ACH
The billing detail and FVD revenue imports support financial reconciliation for fee-charging activities that may involve ACH. Accuracy of billing data affects NACHA file content generated by the BINBANK pipeline.

### ASC 606 / SOX
`Import_fvd_deferred.dtsx` imports deferred revenue data. Deferred revenue is subject to ASC 606 revenue recognition standards. Incorrect imports directly affect financial statement accuracy and SOX compliance.

### GDPR / CCPA
Card account data with individual-level identifiers may constitute personal data under GDPR/CCPA. The pipeline processes European (EMEAM) accounts if CCP covers international programs. Notification data (`namds@wirecard.com`) is hardcoded.
