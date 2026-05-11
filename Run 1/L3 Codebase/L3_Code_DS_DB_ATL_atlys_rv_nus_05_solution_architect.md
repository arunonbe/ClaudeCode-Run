# Solution Architect Report: DS_DB_ATL_atlys_rv_nus

## Technical Debt Summary

| Debt Item | Severity | File/Location |
|---|---|---|
| No CI/CD pipeline | Critical | Root — no pipeline file |
| `sys_execsqlviewtext` — potential SQL injection risk | High | `sys_execsqlviewtext.sql` line 41 |
| `trg_revenue` — no error handling | High | `revenue.sql` lines 47–74 |
| 4+ abandoned GL map table variants | Medium | `tblGLMap_new`, `tblGLMap_new_new`, `tblGLMap_old`, `tblGLMap_old_old` |
| `tblfdrcosts_copy` — orphaned backup table | Low | `tblfdrcosts_copy.sql` |
| `tblGP_lines062019` — date-named orphaned table | Low | `tblGP_lines062019.sql` |
| SSDT target version SQL 2016 potentially stale | Low | `atlys_rv_nus.sqlproj` |
| No data retention / purge procedures | Medium | No purge SPs found |
| Single `development` branch — no release branching | High | `.git/packed-refs` |
| Shallow git clone | Medium | `.git/shallow` |
| `NOT FOR REPLICATION` columns — subscriber DBs undocumented | High | `revenue.sql`, `tblAuditLog.sql` |

---

## Security Vulnerability Assessment

### SQL Injection — MEDIUM RISK

**`sys_execsqlviewtext.sql` (lines 23–127)**: This procedure builds and executes dynamic SQL. Input validation is applied to most string parameters via `ATLYS_E.dbo.sys_chkstr` (lines 23–30). However:

- `@ViewName` is used in `OBJECT_ID(@ViewName)` without the same `sys_chkstr` validation (line 41)
- `@FuncName` is derived from `@ViewName` via string concatenation: `SET @FuncName = 'dbo.sys_get' + REPLACE(REPLACE(@ViewName, 'dbo.', ''), '_', '')` (line 35)
- If the caller does not sanitize `@ViewName` before passing it to this procedure, SQL injection is theoretically possible through the derived object name logic

**Recommendation**: Apply `sys_chkstr` validation to `@ViewName` as well. Also add explicit schema validation (`SELECT 1 FROM sys.views WHERE name = @ViewName AND schema_id = SCHEMA_ID('dbo')`) before using the view name in dynamic SQL.

### Hardcoded Credentials
**None found** in the reviewed source files. No passwords, API keys, or connection strings are embedded in SQL files.

### Excessive Permission Grants — MEDIUM RISK
The `Prod_Support_Update.sql` security file grants INSERT and UPDATE on all base tables to `Prod_Support_Update`. Combined with `Prod_Support_execute` having EXECUTE on all stored procedures, production support has a very broad permission footprint. In a PCI DSS Level 1 environment, production support access should be time-limited, require dual authorization, and be fully logged. Confirm that the FortiDB DAM policy covers these accounts.

### Revenue Trigger — SILENT FAILURE RISK
`trg_revenue` (`revenue.sql` lines 47–74) uses `LEFT OUTER JOIN` and `ISNULL` for all lookups. If configuration data is missing (e.g., no entry in `vAffiliates` for a program, or no entry in `vProducts` for a product), the trigger silently assigns empty strings for GL codes rather than raising an error. This can result in revenue entries with no GL classification, which would fail or be misclassified during GL batch processing.

**Recommendation**: Add a validation step in the trigger or a post-insert validation stored procedure to detect revenue entries with empty `gl_acct_num` and alert the finance team.

---

## Complete Object Inventory with Purpose

### Stored Procedures (80)

| Procedure | Purpose |
|---|---|
| `sys_audit` | Runs audit reconciliation between eCount data and Atlys records |
| `sys_bal_reconcile` | Balance reconciliation reporting |
| `sys_bank_dates` | Returns bank business day calendar |
| `sys_bank_reconcile` | Bank/settlement reconciliation |
| `sys_bank_reconcile_ddaj` | Bank recon with DD-AJ adjustment variant |
| `sys_bank_reconcile_sweep_breakage_detail` | Sweep breakage bank recon detail |
| `sys_bank_reconcile_sweep_breakage_fc_detai` | Sweep breakage FC recon detail |
| `sys_bank_reconcile_sweep_breakage_fc_summary` | Sweep breakage FC recon summary |
| `sys_bank_reconcile_sweep_breakage_summary` | Sweep breakage recon summary |
| `sys_comm` | Commission reporting |
| `sys_comm_calc` | Commission calculation |
| `sys_comm_type_cross_tab` | Commission type cross-tab report |
| `sys_compare` | Period comparison reporting |
| `sys_compare_by_month` | Monthly comparison report |
| `sys_costs_rates` | Cost rate management |
| `sys_cscall_detail` | CS call detail report |
| `sys_cube_reconcile` | Cube/SSAS reconciliation |
| `sys_cube_reconcile_hist` | Historical cube reconciliation |
| `sys_custliability` | Customer liability (deferred revenue) report |
| `sys_custl_entry` | Customer liability entry management |
| `sys_defrev` | Deferred revenue reporting |
| `sys_defrev_details_cross_tab` | Deferred revenue detail cross-tab |
| `sys_durbin` | Durbin Amendment interchange analysis |
| `sys_execcview` | Execute a view with context switch |
| `sys_execlview` | Execute a list-based view |
| `sys_execsqlviewtext` | Dynamic SQL view text execution (SQL injection risk noted) |
| `sys_fdr` | FDR settlement data processing |
| `sys_fdrcosts` | FDR cost allocation |
| `sys_fdr_calc` | FDR cost calculation |
| `sys_fee_entry` | Fee revenue entry management |
| `sys_filemap` | File import mapping |
| `sys_first_issue` | First issue date tracking |
| `sys_formsecurity` | Form-level security check |
| `sys_fvd_calc` | Face Value Discount calculation |
| `sys_fvd_cross_tab` | FVD cross-tab report |
| `sys_fvd_details_cross_tab` | FVD detail cross-tab |
| `sys_glbatch` | GL batch processing (router) |
| `sys_glbatchbin` | GL batch by BIN |
| `sys_glbatchfeetax` | GL batch fee/tax |
| `sys_glbatch_complete` | Mark GL batch as complete |
| `sys_gllinks` | GL links management |
| `sys_glmap` | GL account mapping |
| `sys_gl_entry` | GL journal entry |
| `sys_gp` | Gross Profit report |
| `sys_gp_calc` | GP calculation |
| `sys_gp_details_cross_tab` | GP details cross-tab (primary GP report) |
| `sys_gp_details_variance` | GP variance analysis |
| `sys_import` | Data import (router to company DBs) |
| `sys_import_diff` | Import differential analysis |
| `sys_import_ic_calc` | Import interchange calculation |
| `sys_import_txn` | Transaction data import |
| `sys_interface` | Interface data management |
| `sys_issuance` | Issuance reporting |
| `sys_ivr` | IVR cost reporting |
| `sys_metrics` | Performance metrics |
| `sys_metrics_calc` | Metrics calculation |
| `sys_negbal` | Negative balance management |
| `sys_periods` | Reporting period management |
| `sys_plastics` | Plastic card production reporting |
| `sys_prices` | Pricing management |
| `sys_products` | Product catalog management |
| `sys_program_analysis` | Program-level analysis report |
| `sys_program_filter` | Program filter for reports |
| `sys_prog_costs` | Program cost allocation |
| `sys_que` | IVR queue data |
| `sys_reports` | Report dispatcher |
| `sys_revenue` | Revenue reporting |
| `sys_revenue_gl_cross_tab` | Revenue by GL cross-tab |
| `sys_revenue_type_cross_tab` | Revenue by type cross-tab |
| `sys_smots` | SMOTS (Spend Month Over Time Series) report |
| `sys_tb` | Trial balance report |
| `sys_update_app` | Program application data update |
| `sys_update_cust_name` | Customer name update |
| `sys_update_first_issue` | First issue date update |
| `sys_update_last_rev` | Last revenue date update |
| `sys_usage` | Card usage reporting |
| `sys_usage_type` | Usage type management |

---

## Remediation Priority List

### Priority 1 — Critical (Immediate)

1. **Add CI/CD pipeline**: Create Jenkinsfile or Azure DevOps pipeline for SSDT build, DACPAC validation, and deployment with change management gates. For a PCI DSS Level 1 financial database, this is a compliance requirement.

2. **Fix `sys_execsqlviewtext` SQL injection risk**: Apply `sys_chkstr` to `@ViewName` parameter; add schema validation before using view names in dynamic SQL (`sys_execsqlviewtext.sql` lines 35, 41).

### Priority 2 — High (Next Sprint)

3. **Add error handling to `trg_revenue`**: Wrap trigger logic in BEGIN TRY/CATCH; validate that GL classification succeeds and raise an error if critical configuration data is missing.

4. **Document replication topology**: Identify all subscriber databases for the replication publication on `revenue`, `tblAuditLog`, and `tblAuditDetails`. Document the topology in a runbook.

5. **Implement release branching**: Separate `development` from production-deployed code.

6. **Add temporal table or audit trigger to `tblGLLinks`**: GL mapping changes have financial reporting impact; all changes must be audited with user/time.

### Priority 3 — Medium (Backlog)

7. **Clean up orphaned tables**: Remove or archive `tblGLMap_new`, `tblGLMap_new_new`, `tblGLMap_old`, `tblGLMap_old_old`, `tblfdrcosts_copy`, `tblGP_lines062019`.

8. **Implement data retention policy**: Define and implement purge procedures for `tblAuditLog`, `tblSpend`, `tblIssuance` historical data older than the defined retention period.

9. **Review Prod_Support_Update permissions**: Apply principle of least privilege; restrict UPDATE grants to specific columns or implement time-limited just-in-time access.

10. **Unshallow git clone** for complete audit history.

11. **Add revenue validation stored procedure**: Post-insert check for revenue entries with empty `gl_acct_num` to catch trigger classification failures.
