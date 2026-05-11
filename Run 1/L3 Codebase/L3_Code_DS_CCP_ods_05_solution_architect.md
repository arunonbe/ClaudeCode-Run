# Solution Architect Report — DS_CCP_ods

## Technical Debt Inventory

| Item | Severity | Location |
|---|---|---|
| PAN stored as VARCHAR (no column encryption) | CRITICAL | `FISRptCardholderActivity.PAN`, `FISRptCardholderActivityArchive.PAN`, `FISRptCardHolderActivityStaging.PAN`, `RptNetworkUnposted.[Card Number]` |
| `report` login and `NAM\PROD` group hold UNMASK privilege | HIGH | `Security\ODS_Unmask.sql` lines 6–10 |
| No retention/purge schedule for PAN-bearing tables | HIGH | `FISRptCardholderActivity`, `FISRptCardholderActivityArchive`, `RptNetworkUnposted` |
| `SqlServerVerification=False` in SSDT project | MEDIUM | `ods.sqlproj` line 23 |
| Duplicate `mtd` case in `util_get_date_range` | MEDIUM | `util_get_date_range.sql` lines 82 and 101 |
| Multi-mode monolithic `RptNetworkSettlementReport` | MEDIUM | `RptNetworkSettlementReport.sql` |
| Staging tables have no PKs | MEDIUM | All `*Staging` tables |
| Archive tables have no PKs | LOW-MEDIUM | `FISRptCardholderActivityArchive`, `FISRptDailyFeeArchive`, etc. |
| No SQL Server Audit spec for PAN column access | HIGH | Database-level configuration gap |
| No row-count validation in import procedures | MEDIUM | All `sp_FISRpt_Import*` procedures |
| `spVerifyImport` silently suppresses email failure | MEDIUM | `spVerifyImport.sql` line 160 |
| CROSS APPLY with no index on left table | LOW | `sp_FISRpt_ImportDailyCardholderActivity.sql` — LEFT JOIN comment line 120 |
| `NOLOCK` hints used in SSISDB catalog queries | LOW | `DS_CCP_db09` job scripts — dirty reads on SSISDB |

## Security Vulnerabilities Found

### 1. PAN Stored Without Encryption (CRITICAL — PCI DSS Req 3.5)
`FISRptCardholderActivity.PAN` (VARCHAR(19)) and `RptNetworkUnposted.[Card Number]` (VARCHAR(20)) store full Primary Account Numbers. Dynamic Data Masking (`partial(0, "xxxxxxxxxxxx", 4)`) is applied but DDM is not encryption — the underlying data is stored in cleartext. Any user with direct SQL access (bypassing DDM via UNMASK), any database backup, any DBA with database access, or any SQL dump can read full PANs.

**PCI DSS Requirement 3.5** requires all stored PANs to be rendered unreadable using at least one of: one-way hashes, truncation, index tokens, or strong cryptography (AES-256). DDM does not meet this requirement.

**Remediation**: Implement SQL Server Always Encrypted on PAN columns, or tokenise PANs before storage (store only tokens + last-4), or truncate to first-6/last-4 if full PANs are not required for downstream processing.

### 2. Broad UNMASK Grant (HIGH — PCI DSS Req 7)
File `Security\ODS_Unmask.sql` assigns the `ODS_Unmask` role (which grants `UNMASK` permission) to both the `report` login and `NAM\PROD` Windows group. The `report` login is used for report generation — it is effectively a shared service account. `NAM\PROD` is a broad Windows group. Granting full PAN visibility to these accounts violates the principle of least privilege under PCI DSS Requirement 7 (restrict access to cardholder data by business need-to-know).

**Remediation**: Audit which report objects actually need PAN visibility. For most reporting purposes, masked PANs (first-6/last-4) are sufficient. Revoke UNMASK from the `report` login unless a specific, documented need is established and approved.

### 3. No SQL Server Audit for PAN Access (HIGH — PCI DSS Req 10.2)
PCI DSS Requirement 10.2 requires audit logging of all access to cardholder data, including reads. No SQL Server Audit specification (`CREATE SERVER AUDIT` / `CREATE DATABASE AUDIT SPECIFICATION`) is present in the SSDT project. DDM bypass is not logged. PAN reads by the `report` login are not individually attributed.

**Remediation**: Create a SQL Server Audit specification targeting `SELECT` on `FISRptCardholderActivity` and `RptNetworkUnposted`. Alternatively, implement application-level audit logging in the SSIS packages.

### 4. Dynamic SQL with User-Facing Parameter in `spVerifyImport` (LOW)
`spVerifyImport` constructs a `LIKE` pattern from `@execution_params` using `CHARINDEX` and `SUBSTRING` (line 47). While this is not direct user input, the `@execution_params` value comes from the `package_execution` table, which is populated by the `set_package_execution` stored procedure. If the `execution_params` column is ever populated with malicious content, this could affect behavior. The current code does not construct dynamic SQL, so SQL injection risk is low, but input validation is absent.

### 5. `FISRptCardHolderActivityStaging` — PAN in Staging (MEDIUM — PCI DSS Req 3)
The staging table `FISRptCardHolderActivityStaging` receives raw PAN values from FIS files before the transform procedure moves them to the production table. If the transform fails or is delayed, PANs accumulate in the staging table. The staging table may not have the same access controls, auditing, or masking as the production table. No DDM is confirmed on the staging table (DDL not read in full, but staging tables typically omit DDM).

## Stored Procedure Summary

| Procedure | Purpose |
|---|---|
| `get_FilesToArchive` | Returns file retention config for SSIS archival packages |
| `get_package_last_execution_date` | Returns last run date for named SSIS package from `package_execution` |
| `RptBankList` | Returns bank name list for UI parameter dropdowns |
| `RptNetworkImportProcess` | Transforms `RptNetworkImportStaging` → `RptNetworkImport` |
| `RptNetworkSettlementReport` | Multi-mode: Interchange report ETL, Interchange report RM, Network Settlement RM, date header — controlled by `@report` parameter |
| `rpt_FIS_Client_Fee_Summary` | Client fee summary report from `FISRptDailyFee` |
| `rpt_FIS_ProcessorSettlement` | FIS processor settlement report |
| `rpt_Unposted_Transactions` | Unposted transaction report from `RptNetworkUnposted` |
| `set_package_execution` | UPSERT into `package_execution` for scheduling |
| `sp_FileIOLog_GetOlderId` | Returns oldest FileIOLog IDs older than specified days |
| `sp_FileIOLog_GetStatus` | Returns file status (used by SSIS to check if file already processed) |
| `sp_FileIOLog_Insert` | Inserts new file tracking record (called by SSIS on file arrival) |
| `sp_FileIOLog_SetStatus` | Updates file status in FileIOLog (used by SSIS on completion) |
| `sp_FISRpt_ImportDailyCardholderActivity` | Staging→production transform for FIS cardholder activity; handles date parsing, sign inversion, cross-year boundary edge cases |
| `sp_FISRpt_ImportDailyFee` | Staging→production transform for FIS daily fee data |
| `sp_FISRpt_ImportDailyProcessorSettlement` | Staging→production transform for FIS processor settlement |
| `sp_FISRpt_ImportDailyWrapper` | Orchestrates all three daily FIS import procedures in sequence |
| `sp_FISRpt_ImportPlusISAFee` | Staging→production transform for FIS Plus ISA fees |
| `sp_RptNetworkUnposted_Data_Transform` | Transforms unposted transaction staging to production |
| `spVerifyImport` | Validates prerequisite file receipt before report generation; sends alert emails |
| `usp_SQLAgentFail_Notification` | 5-minute polling monitor for SQL Agent job failures; sends HTML alert email |
| `util_get_date_range` | Utility: returns start/end date pair for named frequency; supports daily, weekly, biweekly, MTD, YTD, LOP, quarterly, and others |

## Recommended Remediation Priority

| Priority | Action |
|---|---|
| P1 — Immediate | Implement column-level encryption (Always Encrypted) or tokenisation for PAN columns in `FISRptCardholderActivity`, archive, staging, and `RptNetworkUnposted` |
| P1 — Immediate | Establish and document a PAN data retention schedule; implement an automated purge procedure for records older than the retention period |
| P1 — Immediate | Implement SQL Server Audit specification for SELECT on PAN-bearing tables |
| P1 — Immediate | Review and restrict UNMASK grants; document business justification for any retained grants |
| P2 — Short-term | Fix duplicate `mtd` case in `util_get_date_range` — determine which calculation is correct and remove the other |
| P2 — Short-term | Add PKs to staging tables to enable duplicate detection |
| P2 — Short-term | Add PKs to archive tables for operational manageability |
| P2 — Short-term | Enable `SqlServerVerification=True` in SSDT project to catch compilation errors at build time |
| P3 — Medium-term | Refactor `RptNetworkSettlementReport` into separate procedures per report mode |
| P3 — Medium-term | Add row-count assertions in import wrapper procedures to detect empty-staging scenarios |
| P3 — Medium-term | Implement alert escalation if `spVerifyImport` email recipient is empty (currently silently suppressed) |
