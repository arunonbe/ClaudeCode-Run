# DS_ETL_great-plains-to-oas-coda — Business Analyst View

## Business Purpose
A **temporary SSIS ETL project** created to extract financial data from Microsoft Great Plains (now Dynamics GP) and deliver it to two downstream Finance systems: **OAS** (Order Accounting System) and **CODA** (financial ledger/accounting system). The README explicitly labels this a "temporary project to track development." It supports Finance reconciliation and general ledger posting workflows for the eCount/NorthLane prepaid business.

## Capabilities
1. **SSIS_CODA_GPFeed.dtsx** — Daily GP-to-CODA feed:
   - Loops over a configurable date range (pStartDate to pEndDate, or rolling daily).
   - For each date, calls stored procedure `dbo.sys_interface` on the ATLYS_RvCR database to retrieve a file list.
   - Iterates over each file record and exports data to a date-stamped flat file in a UNC path.
   - Contains a VB.NET Script Component (Citigroup copyright 2012 assembly) for custom formatting logic.

2. **SSIS_RfCks.dtsx** — Refund Checks feed:
   - Reads a CSV file (`C:\GIT\rfcks.csv`) containing check/refund transaction data.
   - Fields: Tx Descr, Amount, Acct, Tx Date, Bank Day, Bank Date, Id, Program Id, Created, Issued Date, Date, Check Status, Dda Number (and more).
   - Moves refund check records into a downstream system (exact target not visible in the first 150 lines reviewed).

## Key Entities
| Entity | Source | Notes |
|---|---|---|
| GP Financial Transactions | ATLYS_RvCR (Great Plains tables) | Sourced via `dbo.sys_interface` stored procedure |
| CODA Feed File | UNC flat file output | Daily date-stamped export |
| Refund Check Records | CSV flat file (`C:\GIT\rfcks.csv`) | Amount, Acct, Tx Date, Bank Day, Check Status, DDA Number, Program Id |
| Region | `uiRegionId` variable (default -29) | Filters GP data by region |

## Business Rules
1. The GP feed runs daily by default; a `pOverwriteDates` flag (Boolean, default true) allows backfilling a date range via `pStartDate`/`pEndDate`.
2. The output folder path is constructed as `{pFolderPath}{MM}{DD}{YYYY}\{filename}` — one folder per date.
3. The stored procedure `dbo.sys_interface` on ATLYS_RvCR accepts `@s_id=null`, `@ctype='R'`, `@region_id`, `@end_date`, `@report='CODA'` — the 'R' ctype and 'CODA' report type determine the specific financial records extracted.
4. Refund check data is sourced from a static CSV file on a developer workstation (`C:\GIT\rfcks.csv`) — this path is hardcoded and is likely a development artifact only.

## Data Flows
```
Great Plains DB (ATLYS_RvCR on q-db04)
    |
    v [dbo.sys_interface SP — returns file list]
SSIS For Loop (date iteration)
    |
    v [Foreach ADO Enumerator — iterate file rows]
Script Component (VB.NET — custom formatting)
    |
    v [Flat File Destination]
Date-stamped UNC folder
    |
    v [FTP upload — pFTPFolder parameter, currently empty]
CODA / OAS Finance system
```

```
CSV File (C:\GIT\rfcks.csv) — Refund Checks
    |
    v [SSIS_RfCks.dtsx]
Target DB / system (not fully visible in reviewed source)
```

## Compliance Relevance
- Contains financial transaction data including amounts, account numbers, DDA numbers, and check status — potential scope for **Reg E**, **SOC 1**, and **NACHA** record-keeping requirements.
- DDA Number field in the refund checks CSV could be a sensitive bank account reference.
- No PAN fields observed; scope for PCI DSS is limited unless prepaid card numbers are embedded in GP records.
- The "temporary" label in README suggests this process may have been intended for decommission; its ongoing operational status is unclear.

## Risks (Business)
1. **Temporary project with no decommission date** — may have been running in production for years with no formal ownership.
2. CSV input file hardcoded to `C:\GIT\rfcks.csv` on a local machine — no operational file management process visible.
3. FTP destination parameter (`pFTPFolder`) is empty — if FTP upload was intended, it may silently fail to deliver to CODA/OAS.
4. Creator identity (`WIRECARD\julia.ginzburg`) and creation dates (Jan–Jul 2019) predate Onbe; no current owner identified.
5. Region ID hardcoded as `-29` in variable default; incorrect region scope could cause Finance misreporting.
