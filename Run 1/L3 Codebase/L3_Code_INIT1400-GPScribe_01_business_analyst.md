# Business Analyst — INIT1400-GPScribe

## Overview

`INIT1400-GPScribe` is a **SQL Server Agent job and stored procedure set** that replaces a legacy Scribe 1.2 data integration job (Initiative 1400). Its purpose is to automate the daily import of invoice/sales transaction data from a CRM source system (`Dev_Swiftgift_CRM`) into Microsoft Dynamics GP (Great Plains) ERP via the eConnect API. The repository contains five SQL script files that together define the complete integration pipeline.

## Business Purpose

Onbe (or its subsidiary operating under the "Swift/Swiftgift" brand) generates sales invoices in a CRM system. These invoices must flow into Dynamics GP to:
- Create official sales order processing (SOP) invoice records for finance and accounting.
- Update customer accounts, item inventory counts, and revenue ledger entries.
- Support accounts receivable and revenue recognition processes.

Previously, Scribe 1.2 (a third-party ETL/integration product) performed this import. INIT1400 replaces Scribe with a native SQL Server Agent job and T-SQL stored procedures, eliminating the Scribe license dependency and providing more control over error handling and filtering.

## Workflow

The integration runs in two sequential steps, both executing in the context of the `SWIFT` database on SQL Server instance `P-AZ-GPSQL-VM01`:

### Step 1 — Import Data Into Staging (`DYNO_Scribe_West_DataImport`)

1. Queries the remote CRM system at IP `10.10.150.7` via a SQL Server Linked Server using `OPENQUERY`.
2. Reads unprocessed invoice records from `[Dev_Swiftgift_CRM].[dbo].[CRM_Invoice_Report]` (filter: `Processed IS NULL OR Processed = 0`).
3. Inserts those records into the local staging table `[SWIFT].[dbo].[CA_tblStg_ScribeInvoice]`, with `Processed = 'N'` and `UserId = 'eConnect'`.
4. After staging, calls a remote stored procedure `[10.10.150.7].[Dev_Swiftgift_CRM].[dbo].[INTI1400_UpdateProcessedFlag]` to mark the source records as processed, passing a pipe-delimited (`|`) list of document numbers to avoid re-importing the same invoices.

### Step 2 — Import Scribe Data into GP (`DYNO_Scribe_West_InvoiceImport`)

1. Reads staged invoices from `CA_tblStg_ScribeInvoice` that have not yet been processed (`Processed <> 'Y'`) and whose `DOCUMENT_DATE` falls within the prior business day (handling Monday as prior-2-days to account for weekends).
2. Filters out:
   - Items listed in the `OASIS_Exclusion` table (e.g., `ACHFEE`, `ATM FEES`, `AUTORENEW`, `CARD`, `LOAD`, `REISSUE`, `PUSHPAYFEE`, `VPLUSFEE`, `CHECKFEE`, `PPVENMOFEE`).
   - Inactive items (not in `IV00101` active items).
   - Inactive customers (not in `RM00101` active customers).
   - Documents already imported into GP `SOP10100`/`SOP30200` within the last 3 months (deduplication guard).
3. For each qualifying invoice, calls eConnect stored procedures:
   - `taSopLineIvcInsert` — creates a GP SOP line item (one call per line item).
   - `taSopHdrIvcInsert` — creates the GP SOP invoice header.
4. Captures eConnect return codes and error strings; logs errors to `CA_tblScribeInvoice_ErrorLog`.
5. On complete or partial failure per invoice, deletes the partially imported records from GP SOP tables (`SOP10100`, `SOP10200`, `SOP10202`, `SOP10106`, `SOP10107`, `SOP10101`, `SOP10102`) to prevent orphaned/partial invoices.
6. Updates the staging table `CA_tblStg_ScribeInvoice.Processed = 'Y'` for successfully imported line items.

## Schedule

- **SQL Agent Job Name**: `INIT1400`
- **Server**: `P-AZ-GPSQL-VM01`
- **Schedule Name**: `Daily GP Scribe Import`
- **Frequency**: Weekly, `freq_interval=126` (Mon=2 + Tue=4 + Wed=8 + Thu=16 + Fri=32 + Sat=64 = 126), i.e., Monday through Saturday
- **Time**: 10:30 AM (`active_start_time=103000`)
- **Start Date**: 2024-11-12
- **Job Owner**: `NAM\David.Laumonier`

## Data Entities

| Entity | System | Purpose |
|--------|--------|---------|
| `CRM_Invoice_Report` | Dev_Swiftgift_CRM (10.10.150.7) | Source invoice and sales data from CRM |
| `CA_tblStg_ScribeInvoice` | SWIFT DB | Staging table bridging CRM data to GP import |
| `CA_tblScribeInvoice_ErrorLog` | SWIFT DB | Persistent eConnect error log |
| `OASIS_Exclusion` | SWIFT DB | Fee/item exclusion list (configurable) |
| `SOP10100` | SWIFT / GP | GP Sales Order Processing — invoice headers |
| `SOP10200` | SWIFT / GP | GP SOP — line items |
| `SOP10202`, `SOP10106`, `SOP10107`, `SOP10101`, `SOP10102` | SWIFT / GP | GP SOP — distribution, tax, commissions, etc. |
| `IV00101` | SWIFT / GP | GP Inventory — active item list |
| `RM00101` | SWIFT / GP | GP Receivables — active customer list |
| `DYNAMICS..taErrorCode` | DYNAMICS DB | eConnect error code descriptions |

## Business Significance

This job is on the **revenue recognition critical path** for the Swiftgift/West entity. Failure of the job means:
- Sales invoices from the CRM system do not flow into GP, creating a reconciliation gap between the CRM and the general ledger.
- Finance teams cannot post revenue or generate accounts receivable invoices until the batch is manually recovered.
- On Monday, the lookback is extended by one day (Saturday data included) to compensate for no Sunday run.

## OASIS Exclusions and Regulatory Context

The `OASIS_Exclusion` table controls which item numbers are excluded from GP import. The comment history in `DYNO_Scribe_West_InvoiceImport.sql` shows that multiple INIT references added items over time:
- INIT-1094 (2024-09-11): Added exclusion for `ACHFEE`, `ATM FEES`, `AUTORENEW`; added CRDAPI data import.
- INIT-1400 (from 2024-10-28 through 2024-11-26): Core initiative, with iterative fixes to currency logic, quantity precision, duplicate key handling, and cleanup of partial imports.

Fee codes like `ACHFEE`, `PUSHPAYFEE`, `VPLUSFEE`, `CHECKFEE` suggest the CRM records fees charged to cardholders for payment processing. These are excluded from the GP SOP import, likely because they are processed through a separate billing or revenue stream.
