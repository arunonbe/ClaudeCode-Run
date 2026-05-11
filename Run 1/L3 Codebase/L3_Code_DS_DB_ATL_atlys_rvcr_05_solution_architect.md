# Solution Architect Report: DS_DB_ATL_atlys_rvcr

## Technical Debt Summary

| Debt Item | Severity | File/Location |
|---|---|---|
| No CI/CD pipeline | Critical | Root — no pipeline file |
| `dbo` user bypasses all access controls | Critical | All ~45 stored procedures |
| `sys_execsqlviewtext` — `@ViewName` not validated via `sys_chkstr` | High | `sys_execsqlviewtext.sql` line 41 |
| `Prod_Support_Update` — broad INSERT/UPDATE on all tables | High | `Security/Permissions.sql` |
| No data retention for settlement/FDR staging data | Medium | No purge SPs found |
| Session-scoped `tblEC_*` tables as permanent tables — orphan row accumulation | Medium | `tblEC_Accts.sql`, `tblEC_Txns.sql`, `tblEC_Iss.sql`, `tblEC_Ordersvc1-4.sql` |
| `tblJobs.exec_proc` — dynamic EXEC without runtime privilege check | Medium | `tblJobs.sql`, `sys_jobrun.sql` |
| No foreign key constraints anywhere | Low | All tables |
| No column-level encryption | Low | All tables |
| SSDT target version SQL 2016 potentially stale | Low | `atlys_rvcr.sqlproj` |
| No error handling in most routing stored procedures | Medium | All router SPs |
| ATLYS_E is undocumented critical dependency | High | All ~45 stored procedures |

---

## Security Vulnerability Assessment

### SQL Injection — MEDIUM RISK

**`sys_execsqlviewtext.sql` (lines 23–127)**: This procedure builds and executes dynamic SQL. Input validation via `ATLYS_E.dbo.sys_chkstr` is applied to most string parameters at lines 23–30. However:

- `@ViewName` is used in `OBJECT_ID(@ViewName)` without the same `sys_chkstr` validation (line 41)
- `@FuncName` is derived via string concatenation: `SET @FuncName = 'dbo.sys_get' + REPLACE(REPLACE(@ViewName, 'dbo.', ''), '_', '')` (line 35)
- A maliciously crafted `@ViewName` could potentially inject SQL through the derived `@FuncName` string used in subsequent dynamic SQL construction

**Recommendation**: Apply `sys_chkstr` to `@ViewName` at the same entry point as other parameters (after line 22). Add explicit schema validation: `SELECT @ViewValidated = name FROM sys.views WHERE name = @ViewName AND schema_id = SCHEMA_ID('dbo')` before using the view name in dynamic SQL. Return an error if `@ViewValidated IS NULL`.

### Access Control Bypass — CRITICAL RISK

**All ~45 stored procedures**: The pattern `IF USER_NAME() <> 'dbo' BEGIN [auth check] END` appears in every stored procedure. The `dbo` user has unrestricted access to execute any stored procedure, modify any data, and route any request to any company database — all without logging a user identity to the access control system.

In a PCI DSS Level 1 environment, shared or privileged accounts must be subject to the same access logging as normal accounts. The `dbo` bypass effectively creates an unlogged, unaudited superuser path through the entire Atlys financial reporting system.

**Recommendation**: Remove the `dbo` bypass from all stored procedures. If deployment automation requires `dbo`-level access, create a dedicated service account with `dbo` role membership for deployments only, and ensure FortiDB DAM captures all activity from this account. Add `sys_chkuser` audit logging even for `dbo`-equivalent accounts.

### Excessive Permission Grants — MEDIUM RISK

**`Security/Permissions.sql`**: `Prod_Support_Update` is granted INSERT and UPDATE on all base tables including `tblSettle`, `tblFDR_*`, `tblJobs`, and `tblEC_*`. This means production support can:

- Modify FDR settlement amounts
- Add or modify scheduled job definitions (altering automated financial processes)
- Insert arbitrary session data into staging tables

In a PCI DSS Level 1 environment, these permissions should be time-limited, require dual authorization, and be logged by FortiDB with alerting. Confirm that the FortiDB DAM policy covers `Prod_Support_Update` actions on `tblSettle` and `tblJobs` specifically.

### Hardcoded Credentials

**None found** in the reviewed source files. No passwords, API keys, or connection strings are embedded in SQL files. All authentication uses Windows AD integration (`FROM WINDOWS` in login creation files).

---

## Complete Object Inventory with Purpose

### Tables (~20)

| Table | Purpose |
|---|---|
| `tblBankHolidays` | Bank holiday calendar — inputs to business day calculation |
| `tblBankWorkdays` | Bank business day calendar — used in period calculations |
| `tblCompareBuckets` | Comparison bucket config for period comparison UI |
| `tblCompareMetrics` | Comparison metric definitions |
| `tblCompareMetrics2` | Extended comparison metrics (v2 config) |
| `tblCompareMetricsComponents` | Component-level breakdown of comparison metrics |
| `tblCompareMetricsMap` | Maps metrics to display configuration |
| `tblEC_Accts` | eCount account data staging — session-scoped (spid in clustered index) |
| `tblEC_Accts_Errors` | eCount account import error log |
| `tblEC_Iss` | eCount issuance data staging — session-scoped |
| `tblEC_Iss_Errors` | eCount issuance import error log |
| `tblEC_Ordersvc1–4` | eCount order service data staging (4 variants) — session-scoped |
| `tblEC_Ordersvc1–4_Errors` | eCount order service import error logs |
| `tblEC_Txns` | eCount transaction data staging — session-scoped; includes source, facility, card_type |
| `tblEC_Txns_Errors` | eCount transaction import error log |
| `tblFDR_CD083` | FDR CD083 clearing report staging |
| `tblFDR_DD442` | FDR DD442 detail report staging |
| `tblFDR_SD090` | FDR SD090 summary settlement staging |
| `tblFDR_SD091` | FDR SD091 summary variant staging |
| `tblFDR_SD902` | FDR SD902 summary staging |
| `tblFLXC` | Flex context configuration |
| `tblFLXCtx` | Flex context entries |
| `tblFLXCtx_add` | Additional flex context entries |
| `tblInterface` | FDR file interface field definitions — rec_type, position, length, type, formula |
| `tblInterfaceXLS` | Excel interface field definitions |
| `tblJobRerun` | Job rerun tracking state |
| `tblJobs` | Scheduled job definitions — exec_proc, bus_days, region_id; CHECK constraint on exec_proc |
| `tblSettle` | FDR settlement data — ICA_BIN, PROCESSOR, NET_SPEND, INTER_REV, CHARGEBACK, c_id |
| `tblSettleDtl` | Settlement detail records |

### Stored Procedures (~45)

| Procedure | Purpose |
|---|---|
| `sys_audit` | Audit reconciliation router — routes to company DB |
| `sys_bal_reconcile` | Balance reconciliation router |
| `sys_bank_dates` | Bank business day calendar calculator |
| `sys_bank_reconcile` | Bank/settlement reconciliation router |
| `sys_bank_reconcile_ddaj` | Bank recon with DD-AJ adjustment variant |
| `sys_comm` | Commission reporting router |
| `sys_comm_calc` | Commission calculation router |
| `sys_comm_type_cross_tab` | Commission type cross-tab router |
| `sys_compare` | Period comparison router |
| `sys_compare_by_month` | Monthly comparison router |
| `sys_compare_metrics` | Comparison metrics execution |
| `sys_cscall_detail` | CS call detail router |
| `sys_cube_reconcile` | Cube reconciliation router |
| `sys_cube_reconcile_hist` | Historical cube reconciliation router |
| `sys_custl_entry` | Customer liability entry router |
| `sys_durbin` | Durbin Amendment analysis router |
| `sys_execlview` | Execute list-based view |
| `sys_execsqlviewtext` | Dynamic SQL view execution — SQL injection risk on @ViewName |
| `sys_fdr` | FDR processing router |
| `sys_fdrcosts` | FDR cost allocation router |
| `sys_fdr_calc` | FDR cost calculation router |
| `sys_filemap` | File import mapping router |
| `sys_flxctx` | Flex context management |
| `sys_fvd_calc` | FVD calculation router |
| `sys_fvd_cross_tab` | FVD cross-tab router |
| `sys_fvd_details_cross_tab` | FVD detail cross-tab router |
| `sys_glbatch` | GL batch router |
| `sys_glbatchbin` | GL batch by BIN router |
| `sys_glbatchfeetax` | GL batch fee/tax router |
| `sys_glbatch_complete` | GL batch completion router |
| `sys_gllinks` | GL links management router |
| `sys_glmap` | GL account mapping router |
| `sys_gp` | Gross Profit report router |
| `sys_gp_calc` | GP calculation router |
| `sys_gp_details_cross_tab` | GP details cross-tab router |
| `sys_gp_details_variance` | GP variance router |
| `sys_holidays` | Holiday management |
| `sys_import` | Data import router — handles both 'C' and 'R' ctype |
| `sys_import_holidays` | Holiday import |
| `sys_import_txn` | Transaction import router — loads tblEC_* staging tables |
| `sys_interface` | Interface data management |
| `sys_issuance` | Issuance reporting router |
| `sys_ivr` | IVR cost router |
| `sys_jobrerun` | Job rerun management |
| `sys_jobrun` | Job scheduler — dynamic EXEC of tblJobs.exec_proc; JIRA NAMDATASVC-2120; Friday GL rule |
| `sys_metrics` | Performance metrics router |
| `sys_metrics_calc` | Metrics calculation router |
| `sys_negbal` | Negative balance router |
| `sys_periods` | Reporting period management |
| `sys_plastics` | Plastics reporting router |
| `sys_products` | Products management router |
| `sys_program_analysis` | Program analysis router |
| `sys_prog_costs` | Program cost router |
| `sys_que` | IVR queue router |
| `sys_reports` | Report dispatcher router |
| `sys_revenue` | Revenue reporting router — handles report types '', 'A', 'T', 'N', 'M' |
| `sys_revenue_gl_cross_tab` | Revenue GL cross-tab router |
| `sys_revenue_type_cross_tab` | Revenue type cross-tab router |
| `sys_smots` | SMOTS report router |
| `sys_sys_paths` | System path management |
| `sys_tb` | Trial balance router |
| `sys_usage` | Usage reporting router |
| `sys_usage_type` | Usage type management |

---

## Remediation Priority List

### Priority 1 — Critical (Immediate)

1. **Add CI/CD pipeline**: Create an Azure DevOps pipeline or Jenkinsfile for SSDT build, DACPAC validation, and deployment with change management gates. For a PCI DSS Level 1 financial entry-point database, automated deployment is a compliance requirement.

2. **Remove `dbo` access control bypass**: Apply `sys_chkuser` authentication to all callers including `dbo`. Create a dedicated deployment service account instead of relying on the `dbo` bypass for automated operations. This affects all ~45 stored procedures.

### Priority 2 — High (Next Sprint)

3. **Fix `sys_execsqlviewtext` SQL injection risk**: Apply `sys_chkstr` validation to `@ViewName` parameter. Add schema-based object validation (`sys.views`) before using the view name in dynamic SQL construction (`sys_execsqlviewtext.sql` lines 35, 41).

4. **Review and restrict `Prod_Support_Update` permissions**: Restrict UPDATE/INSERT grants to specific columns on specific tables. For settlement and job schedule data, consider removing direct table access entirely and exposing only stored procedure access.

5. **Document ATLYS_E dependency**: Create a formal dependency map identifying ATLYS_E objects used by `atlys_rvcr` (`sys_chkuser`, `sys_chkuserrights`, `sys_cinfo`, `sys_regioncinfo`). Define SLA and change communication requirements between the ATLYS_E and atlys_rvcr teams.

### Priority 3 — Medium (Backlog)

6. **Implement session data cleanup job**: Create a SQL Agent job that runs daily to identify and delete orphaned rows in `tblEC_*` tables where the `spid` no longer corresponds to an active SQL Server session. Schedule during off-peak hours.

7. **Implement data retention policy**: Define and implement purge procedures for `tblSettle`, `tblSettleDtl`, and `tblFDR_*` tables beyond the defined retention period. For PCI DSS compliance, data not required for business or regulatory purposes must be purged on a defined schedule.

8. **Add error handling to routing stored procedures**: Many routing stored procedures have no TRY/CATCH wrapper. Add structured error handling to capture and log failures in the routing layer, particularly for region-level (multi-company) aggregation procedures where a single company DB failure should not silently suppress all other results.

9. **Add runtime privilege check for `tblJobs.exec_proc` dynamic execution**: In `sys_jobrun`, validate that the executing user has EXECUTE permission on the target procedure before dynamically calling it, rather than relying solely on the CHECK constraint at INSERT/UPDATE time.

10. **Upgrade SSDT target SQL Server version**: Update `atlys_rvcr.sqlproj` to target the current SQL Server version in use in production to prevent schema drift and enable use of newer SQL Server features during development.
