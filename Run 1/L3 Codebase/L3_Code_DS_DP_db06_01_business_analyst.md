# DS_DP_db06 — Business Analyst Report

## Repository Overview

**Repo name:** DS_DP_db06  
**Server instance (inferred):** P-DB06 — `p-db06-ha.nam.wirecard.sys\db06` (production HA)  
**Evidence:** DB07 SSIS config `20210611-SQ-3087-configure ivr card activation dtsx.sql`, line 5: `CM.Vendor.ServerName = p-db06-ha.nam.wirecard.sys\db06`  
**Active date range:** November 2019 – July 2021  
**Script count:** ~55 SQL scripts + 2 PowerShell files + 2 maintenance files  
**Branching model:** Single `master` branch  
**Notable:** Only DS_DP node with non-SQL scripts (PowerShell `.ps1` files)

---

## Business Purpose

DB06 is the **reporting, analytics, compliance, and NACHA file extraction** node in the DS_DP cluster. It serves as the primary interface between the core card processing data (on DB02) and external financial reporting, regulatory submissions, and third-party data consumers. DB06 hosts multiple logically distinct databases serving different reporting and compliance functions.

---

## Primary Databases and Business Functions

### 1. `cf_report` — Compliance and Finance Reporting
This is the primary reporting database on DB06. Key functions:
- **BINBANK schema** — The `BINBANK` schema within `cf_report` manages BIN (Bank Identification Number) configurations, NACHA transaction mappings, and the transaction code lookup tables (`TCode_Lookup`, `nacha_bank_source`, `nacha_transaction_mapping`). This schema is the authoritative source for transaction classification used in regulatory filings.
- **Exception reporting** — `t_Report_Exception_list` tracks programs with account management exceptions for compliance review (e.g., Charter programs, AEP programs, DynCorp/Moocho programs)
- **Escheatment overview** — LBrands escheatment exception tracking
- **STARSf reporting** — Monthly STAR network settlement file reporting (`STARSf_Monthly` table + `rpt_StarSF` stored procedure)
- **Daily reconciliation** — `dim_transaction_type_12272016` dimension table for daily recon extracts
- **Travel expense spend reporting** — CONNS programs
- **Negative balance reporting** — `Monthly Negative Balance Writeoff` job

### 2. `Vendor` — IVR and Third-Party Data
The `Vendor` database hosts IVR (Interactive Voice Response) call log data:
- `IVR_CallLog` — All cardholder IVR interactions (card balance inquiry, activation, PIN changes, fraud reports)
- `IVR_CallLog_MenuChoices` — Menu path choices within each IVR session
- `IVR_Fraud_Call_Log` — IVR fraud call events

The Vendor database was significantly restructured in January 2020 (`NAMDATASVC-1681`) — migrating primary keys from GUID to `NUMERIC(19,0)` for performance. This is referenced in DB02 for the IVR activation backfill (21.5M records).

### 3. `ODS` — Operational Data Store (CCP)
DB06 hosts an `ODS` database that served as an interim data store for CCP (Card Carrier Processing) data before migration to the dedicated CCP database. Scripts moved `Billing_Audit`, `Billing_Detail`, `FVD_Deferred`, `FVD_Revenue`, and `package_execution` data from `ODS` to `CCP` in early 2020 (`NAMDATASVC-1936`).

### 4. `DBAdmin` — Instance Administration
Same pattern as other nodes — security audit, blocked IP audit.

### 5. `EcountIds` — Transaction Type Dimension
Referenced in DB06 scripts (`SQ-3539` DB06 version) as a target for transaction type dimension inserts. This dimension database cross-links to EcountCore and the data warehouse.

---

## NACHA / ACH Compliance Operations

DB06 is a critical node for **NACHA file generation and ACH reconciliation**:

1. **NACHA transaction mapping** — `cf_report.BINBANK.nacha_transaction_mapping` and `nacha_bank_source` tables control which transaction source codes map to which ACH entries in NACHA files
2. **NACHA file extract settings** — `SQ-190` (January 2021) updated the NACHA file extract to use source 6 (Interchange report) instead of source 5 (Network Settlement report)
3. **Same Day ACH transaction codes** — `SQ-3539` and `SQ-4038` added new transaction codes and updated NACHA mappings for Same Day ACH (May–July 2021)
4. **Risk adjustment credits** — `WDNAMCBTS-172` (September 2020) updated NACHA transaction mapping for risk adjustment entries, including Network Settlement data in the extract

These operations place DB06 directly in scope for **NACHA Operating Rules compliance** — specifically the rules governing Same Day ACH entry processing and file submission requirements.

---

## Maritime ATM and Cardtronics Integration

A distinctive function of DB06 is **maritime ATM transaction processing** for Cardtronics:
- `MaritimeATM_Terminal_ID` table — Terminal ID registry for maritime ATM locations
- `MaritimeATM_DeviceDetail` and `MaritimeATM_Partial*` ETL-related tables (DB07 SSIS package `SSIS-DB06-MaritimeATM_DeviceDetail`)
- `t_Report_Exception_list` includes maritime ATM program exceptions
- Cardtronics file type management (`NAMDATASVC-993` — ATM file type added March 2020)

This marine vessel / offshore location card acceptance is a niche but documented business line managed through DB06.

---

## Business User Synchronization

A notable feature unique to DB06 is the `uspSyncBusinessUsers` stored procedure (`SQ-501`, June 2021) on the `master` database. This procedure:
- Synchronizes Active Directory group membership to a `BusinessUsers` table
- Distinguishes between resource-limited and full-access business user groups
- Enables automated provisioning of SQL Server access based on AD group membership
- Uses `xp_logininfo` to enumerate AD group members

This is a **business-user self-service access control system** — allowing business analysts and report consumers to access DB06 reporting data based on their AD group membership rather than requiring individual DBA grants.

---

## Regulatory Relevance

| Regulation | Relevance | Evidence |
|---|---|---|
| NACHA Operating Rules | ACH file generation and transaction mapping | `nacha_transaction_mapping`, `nacha_bank_source`, SQ-190, SQ-3539 |
| Reg E (12 CFR 1005) | Consumer ACH protections | ACH return processing, Same Day ACH |
| PCI DSS v4.0.1 Req 10 | Audit and monitoring | IVR call logs, billing audit, exception reporting |
| State Unclaimed Property | Escheatment reporting | LBrands escheatment, Monthly Negative Balance Writeoff |
| UDAAP / Reg E disclosures | Fee transparency | BINBANK TCode_Lookup for cardholder statement descriptions |
| FFIEC IT Examination | IT controls | Monthly integrity reports via exception and reconciliation |

---

## Key Business Events (Chronological)

| Date | Ticket | Business event |
|---|---|---|
| 2019-11 | NATS-5501 | Old BIN bank record deleted |
| 2019-10-23 | NAMDATASVC-1468 | Cambridge project sources/facilities added |
| 2019-11-14 | NAMDATASVC-1562 | Charter program added to exception report |
| 2019-12-01 | NATS-6006 | Maritime ATM Cardtronics data cleanup |
| 2020-01-22 | NAMDATASVC-1681 | IVR CallLog schema migration (GUID → NUMERIC keys) |
| 2020-03-17 | NAMDATASVC-1917 | STARsf Monthly table + stored procedure created |
| 2020-03-04 | NAMDATASVC-1936 | ODS data migrated to CCP database |
| 2020-08 | WDNAMCBTS-172 | NACHA transaction mapping updated for risk adjustments |
| 2020-10-28 | SQ-361 | Transaction code descriptions updated |
| 2021-01-07 | SQ-190 | NACHA file extract source changed (source 5→6) |
| 2021-05-11 | SQ-3539 | Same Day ACH transaction codes added |
| 2021-06-09 | SQ-501 | Business user AD sync stored procedure created |
| 2021-07-02 | SQ-4038 | Same Day ACH NACHA mapping added |
