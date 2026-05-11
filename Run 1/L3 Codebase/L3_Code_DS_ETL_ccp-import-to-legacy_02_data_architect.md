# DS_ETL_ccp-import-to-legacy — Data Architect Report

## 1. Data Architecture Overview

This repository implements a **unidirectional ETL pipeline** that imports data from the CCP (Card Client Platform / Sunrise CCP) into a legacy SQL Server staging database, which then feeds the eCount (ECNT/ECAN) legacy platform. The data flow is entirely inbound — no data is written back to CCP from this pipeline.

| Attribute | Value |
|-----------|-------|
| Platform | Microsoft SQL Server Integration Services (SSIS) — SQL Server 2012 (11.0.5058.0) |
| Project name | `ccp.import2012` |
| Package format | SSIS 2012 Project Deployment Model (`.dtsx`) |
| Package count | 10 packages |
| Source data | Flat files (pipe-delimited `.txt`) from CCP export pipeline |
| Staging database | `CCP` on `d-na-db01.nam.wirecard.sys\db01,2232` |
| Target platform | Legacy eCount (ECNT/ECAN databases) |
| Connection manager | `CCP-SQLDB.conmgr` — OLE DB to `CCP` database using `SQLNCLI11.1` with Windows Integrated Security |

---

## 2. Data Sources and File Formats

All source data originates from flat files produced by `DS_CCP_ccp-export-to-legacy`. Files are placed in `C:\ETL\In\WDCCP\` on the SSIS server.

| Package | Source File Pattern | Format | Key Data Fields |
|---------|-------------------|--------|----------------|
| `Import_bin_account.dtsx` | `sunrise_wdccp_customer_<date>.txt` | Pipe-delimited | `RecordType (1)`, `ProgramCurrency`, `AccountIdentifier (32)`, `AccountCreateDate`, `CardNumber (4)` |
| `Import_bin_cardstatus.dtsx` | `sunrise_wdccp_cardstatus_<date>.txt` | Pipe-delimited | `RecordType`, `Date`, `AccountIdentifier (32)`, `CardNumber (4)`, `CardExpirationDate` |
| `Import_bin_transaction.dtsx` | `sunrise_wdccp_postedtran_<date>.legacy.txt` | Pipe-delimited | `RecordType`, `UniqueTransactionId (32)`, `SettlementDate`, `TransactionDate`, amounts (decimal 19/5) |
| `Import_bin_balances.dtsx` | CCP balance export | Pipe-delimited | Balance amounts per account |
| `Import_billing_audit.dtsx` | CCP billing audit export | Pipe-delimited | Billing audit records |
| `Import_billing_detail.dtsx` | CCP billing detail export | Pipe-delimited | Billing detail records |
| `Import_fvd_revenue.dtsx` | CCP FVD revenue export | Pipe-delimited | Face value discount revenue |
| `Import_fvd_deferred.dtsx` | CCP FVD deferred export | Pipe-delimited | Deferred revenue records |
| `Import_fvd_singleload.dtsx` | CCP FVD singleload export | Pipe-delimited | Single-load FVD records |
| `Import_fiserv_inventory.dtsx` | Fiserv inventory export | Pipe-delimited | Card inventory from Fiserv/embosser |

---

## 3. Sensitive Data Classification

| Data Element | Package | Classification | PCI/Regulatory Risk |
|---|---|---|---|
| `AccountIdentifier (32 chars)` | `Import_bin_account`, `Import_bin_cardstatus` | **POTENTIAL CDE** | If this is a tokenised PAN or account surrogate linked to a PAN, it is in scope for PCI DSS Req 3. Requires formal QSA scoping |
| `CardNumber (4 chars)` | `Import_bin_account`, `Import_bin_cardstatus` | **POTENTIAL PARTIAL PAN** | If this is last-4 digits of PAN, it is permissible to store. If it is a BIN prefix or full 4-digit segment that, combined with `AccountIdentifier`, reconstructs the full PAN, this is CDE-in-scope |
| `CardExpirationDate` | `Import_bin_cardstatus` | **SAD (Sensitive Authentication Data)** | Expiration date is SAD under PCI DSS Req 3.3. Storing post-authorisation is prohibited unless specific exemptions apply |
| `UniqueTransactionId (32 chars)` | `Import_bin_transaction` | MEDIUM | Transaction GUID — not directly PCI SAD but links to card transaction history |
| `SettlementDate`, `TransactionDate` | `Import_bin_transaction` | LOW | Date fields |
| Transaction amounts (decimal 19/5) | `Import_bin_transaction`, `Import_bin_balances` | MEDIUM — financial | GLBA |
| FVD revenue/deferred amounts | `Import_fvd_*` | MEDIUM — financial | SOX (ASC 606 deferred revenue) |
| Fiserv card inventory | `Import_fiserv_inventory` | MEDIUM | Card stock data — inventory counts, not PANs |

---

## 4. Target Data Stores

| Store | Type | Population |
|-------|------|-----------|
| `CCP` database on `d-na-db01.nam.wirecard.sys\db01,2232` | SQL Server — OLE DB | Staging target; packages load data here via `CCP-SQLDB.conmgr` |
| Legacy eCount (`ECNT`, `ECAN`) | SQL Server | Downstream from `CCP` staging; loaded by legacy import stored procedures |

The connection manager `CCP-SQLDB.conmgr` uses:
- Server: `d-na-db01.nam.wirecard.sys\db01,2232`
- Database: `CCP`
- Authentication: `Integrated Security=SSPI` (Windows domain authentication)
- Provider: `SQLNCLI11.1` (SQL Server Native Client 11 — legacy driver; EOL)

---

## 5. Data Flow Architecture

```
CCP Platform (Sunrise)
    |
    v [DS_CCP_ccp-export-to-legacy pipeline — separate repo]
Flat files: C:\ETL\In\WDCCP\sunrise_wdccp_*.txt
    |
    +-- Import_bin_account.dtsx --------+
    +-- Import_bin_cardstatus.dtsx -----+
    +-- Import_bin_transaction.dtsx ----+
    +-- Import_bin_balances.dtsx -------+--> CCP database (staging)
    +-- Import_billing_audit.dtsx ------+       on d-na-db01
    +-- Import_billing_detail.dtsx -----+
    +-- Import_fvd_revenue.dtsx --------+
    +-- Import_fvd_deferred.dtsx -------+
    +-- Import_fvd_singleload.dtsx -----+
    +-- Import_fiserv_inventory.dtsx ---+
    |
    v [Legacy import stored procedures]
Legacy eCount platform (ECNT/ECAN databases)
```

---

## 6. Data Quality and Retention

- No data quality rules (row counts, hash checks, schema validation) are defined in the `Project.params` file — the only parameters are `MailServerAccount` (`NoReply@wirecard.com`) and `NotifyEmailAddress` (`namds@wirecard.com`) for failure notification.
- No explicit error handling rows or audit tables are defined in the visible configuration.
- File existence check is implied by the `NotifyEmailAddress` parameter description ("Email(s) to notify when file does not exist").
- No defined data retention policy for staging data in the `CCP` database.
- Source flat files from the CCP export pipeline: no archive/deletion policy visible in this repository.

---

## 7. Compliance Gaps

| Gap | Regulation | Severity |
|-----|-----------|----------|
| `CardExpirationDate` stored post-authorisation | PCI DSS Req 3.3 (SAD storage prohibition) | CRITICAL — requires QSA review |
| `AccountIdentifier (32)` + `CardNumber (4)` — PAN linkage risk | PCI DSS Req 3.2 (PAN storage) | HIGH — requires formal CDE scoping by QSA |
| SQLNCLI11.1 driver (EOL) | Security best practice | MEDIUM |
| `namds@wirecard.com` hardcoded notification address | Data governance | MEDIUM — Wirecard-era email address in active use |
| No data quality controls | SOX (financial data accuracy) | MEDIUM — `Import_fvd_*` packages feed deferred revenue |
| No staging data retention policy | GDPR Art 5(e), PCI DSS Req 3.1 | MEDIUM |
| Integrated Security only — no certificate-based auth | PCI DSS Req 8 | LOW |
