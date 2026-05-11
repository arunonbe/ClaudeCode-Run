# Business Analyst Report: DS_DB_ATL_atlys_rvcr

## Repository Identity

| Field | Value |
|---|---|
| Repository name | DS_DB_ATL_atlys_rvcr |
| Full meaning | Atlys Reward Value Credit (global/shared variant) |
| Database project type | SQL Server Data Tools (SSDT) `.sqlproj` |
| Source files | ~20 tables, ~35 views, ~45+ stored procedures, ~20 functions, Security files |
| Special role | **Router/dispatcher database** — stored procedures route to company-specific databases |

---

## Business Purpose

The `atlys_rvcr` database is the **global application-tier database** for the Atlys financial reporting web application. Unlike `atlys_rv_nus` (which is a company-specific US database with full data), `atlys_rvcr` serves as the **entry point** that:

1. Authenticates and authorizes users via `ATLYS_E.dbo.sys_chkuser` and `sys_chkuserrights`
2. Routes reporting requests to the correct company-specific database (`atlys_rv_nus`, NCA, or other regional databases)
3. Aggregates results across multiple company databases for multi-region reports
4. Maintains shared operational tables (settlement, FDR staging, GL batch view, comparison metrics)
5. Provides the scheduling framework (`tblJobs`, `sys_jobrun`) for automated data collection

The naming convention `cr` likely stands for "credit" or "credit revenue" — this variant handles the credit/debit card revenue reporting layer that aggregates across multiple regional databases.

---

## Business Processes Supported

### 1. Multi-Company Report Routing
Every major stored procedure (`sys_revenue`, `sys_bank_reconcile`, `sys_import`, `sys_glbatch`, `sys_gp`, etc.) follows the same pattern:
- Check user authorization
- If `@ctype = 'C'` (Company): look up the company's database name via `ATLYS_E.dbo.sys_cinfo` and route the call there
- If `@ctype = 'R'` (Region): iterate through all companies in the region via `ATLYS_E.dbo.sys_regioncinfo` and aggregate results

This architecture enables a single Atlys web application to serve multiple geographic regions and company configurations from one entry point.

### 2. Automated Job Scheduling
`tblJobs` defines scheduled jobs with execution procedures, business day schedules, and region assignments. `sys_jobrun` and `sys_jobrerun` execute these jobs by date range, driving automated balance reconciliation and GL data collection. JIRA ticket `NAMDATASVC-2120` (referenced in `sys_jobrun.sql` line 3) documents a specific business rule: include Friday's GL data in Monday's runs before 4 PM.

### 3. Settlement Data Import and Reconciliation
`tblSettle` and `tblSettleDtl` store FDR settlement data. `sys_fdr` and `sys_fdr_calc` process FDR reports. `sys_bank_reconcile` and variants perform bank-to-settlement reconciliation.

### 4. GL Batch Management
`sys_glbatch`, `sys_glbatchbin`, `sys_glbatchfeetax`, `sys_glbatch_complete` manage the GL batch lifecycle from staging to completion for Great Plains posting.

### 5. Revenue and GP Reporting
`sys_revenue`, `sys_gp`, `sys_gp_details_cross_tab`, `sys_gp_details_variance`, `sys_fvd_calc`, `sys_comm` provide comprehensive financial reporting, routing to company databases and aggregating multi-region results.

### 6. FDR Interface Management
`tblInterface` and `tblInterfaceXLS` store FDR file interface format definitions. `sys_interface` and `sys_filemap` manage the import process for FDR settlement files.

### 7. eCount Data Import
`sys_import_txn` imports transaction data from eCount company databases into the local staging tables (`tblEC_Accts`, `tblEC_Iss`, `tblEC_Ordersvc1-4`, `tblEC_Txns`). These staging tables serve as landing zones for eCount raw data before analytical processing.

### 8. Bank Calendar Management
`tblBankHolidays`, `tblBankWorkdays`, `sys_bank_dates`, `sys_holidays` manage the bank business day calendar, used throughout financial period calculations.

---

## Data Stored and Processed

| Category | Tables |
|---|---|
| Settlement | `tblSettle`, `tblSettleDtl` |
| eCount staging | `tblEC_Accts`, `tblEC_Iss`, `tblEC_Ordersvc1-4`, `tblEC_Txns` (+ error tables for each) |
| FDR processor data | `tblFDR_CD083`, `tblFDR_DD442`, `tblFDR_SD090`, `tblFDR_SD091`, `tblFDR_SD902` |
| Interface/file config | `tblInterface`, `tblInterfaceXLS`, `tblFLXC`, `tblFLXCtx`, `tblFLXCtx_add` |
| Scheduling | `tblJobs`, `tblJobRerun` |
| Bank calendar | `tblBankHolidays`, `tblBankWorkdays` |
| Compare/metrics | `tblCompareBuckets`, `tblCompareMetrics`, `tblCompareMetrics2`, `tblCompareMetricsComponents`, `tblCompareMetricsMap` |

The eCount staging tables (`tblEC_*`) use a `spid` column (SQL Server process ID) as part of their clustered index, indicating they are **session-scoped temporary tables** implemented as permanent tables. They hold data only during a specific data import session, identified by the SQL Server process ID. This is an unusual pattern that creates data isolation challenges in concurrent execution.

---

## Business Rules in SQL

1. **Access control gate on every procedure**: All procedures check `USER_NAME() <> 'dbo'` before calling `ATLYS_E.dbo.sys_chkuser`. The `dbo` user bypasses all access checks — a significant security consideration.

2. **Company type routing**: Procedures distinguish between `@ctype = 'C'` (company-level) and `@ctype = 'R'` (region-level), with region-level calls iterating through all companies in the region.

3. **Dynamic stored procedure invocation**: `sys_jobrun` dynamically invokes the procedure stored in `tblJobs.exec_proc` using `EXEC @p`. The `tblJobs` table has a CHECK constraint verifying that `exec_proc` is a valid procedure name: `[exec_proc] IS NULL OR object_id([exec_proc],N'P') IS NOT NULL`.

4. **Friday GL data rule**: `sys_jobrun` (line 58–60) includes a special case: for GL balance reconciliation jobs, if the current time is before 4 PM and the date range spans multiple days, Monday's run also collects Friday's GL data.

5. **Settlement ICA/BIN reconciliation**: `sys_bank_reconcile` variants compare FDR settlement data by ICA/BIN against Great Plains cash balances.

---

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | `tblSettle.ICA_BIN` contains BIN data. Same CDE boundary analysis as `atlys_rv_nus`. No PANs found. |
| **NACHA** | `sys_bank_reconcile_sweep_breakage_*` procedures track ACH-related breakage. |
| **Reg E** | Maintenance fee and cardholder fee revenue calculations. |
| **SOX** | GL batch processing and bank reconciliation are financially significant automated processes. |

---

## Integration with Services

- **ATLYS_E**: Access control functions (critical dependency)
- **Company databases** (`atlys_rv_nus`, NCA, and others): Called dynamically via `sys_cinfo` routing
- **Great Plains ERP**: GL batch destination; bank recon source
- **FDR processor**: Settlement file import source
- **Atlys WAPP**: Primary application consumer
- **eCount Core databases**: Source for `sys_import_txn` (loads `tblEC_*` staging tables)
