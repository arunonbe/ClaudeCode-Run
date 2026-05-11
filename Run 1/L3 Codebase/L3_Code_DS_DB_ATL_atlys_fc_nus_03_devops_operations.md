# DevOps / Operations Analysis — DS_DB_ATL_atlys_fc_nus (atlys_fc_nus)

## Build Technology

SSDT `.sqlproj` project, MSBuild ToolsVersion 4.0, provider `Sql100DatabaseSchemaProvider`. Configurations identical to `atlys_fc_nca` and `atlys_e`. Active git branch: `development`. Build produces `atlys_fc_nus.sql` output.

---

## CI/CD Pipeline

**No CI/CD configuration present.** Identical finding to all other repos in this batch. No pipeline YAML, no publish profiles, no deployment scripts. Manual DBA deployment assumed.

---

## Environments

Security directory indicates the same multi-environment structure as `atlys_fc_nca`:

| Login / File | Implied environment |
|---|---|
| NAM_PROD / NAM_PROD_1 | Production |
| NAM_PROD_CPP | Production CPP |
| NAM_PROD_ITOPS / NAM_PROD_ITOPS_1 | Production IT Operations |
| NAM_UAT / NAM_UAT_1 | UAT |
| NAM_PPA_PRD_ATLYS / NAM_PPA_PRD_ATLYS_1 | PPA Production |

No APAC CPP variant, consistent with US regional scope. No ABAT variant. Same environment-in-project risk as other databases.

---

## Deployment Considerations

### Schema Synchronisation with atlys_fc_nca
Because `atlys_fc_nus` is a structural clone of `atlys_fc_nca`, any schema change or stored procedure update that is deployed to NCA must also be deployed to NUS. Without a coordinated CI/CD pipeline, there is significant operational risk that:
1. A bug fix deployed to NCA is not applied to NUS, leaving the US fee calculation engine running stale logic.
2. A new fee calculation feature is available in NCA but not yet in NUS, creating a feature discrepancy between regions.

Historical divergence between the two databases may already exist and would require a schema comparison audit to detect.

### Deployment Order Dependencies
Because `atlys_fc_nus` calls `ATLYS_E.dbo.*` functions, any `atlys_e` schema change that alters function signatures must be deployed to `atlys_e` before `atlys_fc_nus` is redeployed. Failure to maintain this ordering will cause stored procedure compilation errors in `atlys_fc_nus`.

---

## Operational Risks

### Risk 1 — Silent Calculation Error on Server Rename
**Same as `atlys_fc_nca` Risk 1.** The `@@SERVERNAME` prefix check in `sys_calc_dormancy` is present in the NUS database. Any server rename (e.g., a US-specific production server migration) that changes the first character away from Q, P, or C will silently break US dormancy fee calculations, causing incorrect amortisation entries in the GP GL for US programs. Given that US Reg E has specific timing requirements for dormancy fee recognition, an incorrect calculation here is both a financial and regulatory risk.

### Risk 2 — No Error Handling in Calculation Procedures
Same as `atlys_fc_nca`. Partial writes to `tblForecast_data` without TRY/CATCH and rollback.

### Risk 3 — BULK_LOGGED Recovery Model
Same as all other databases. US financial data not point-in-time recoverable during bulk operations.

### Risk 4 — No TDE
US financial data (fee rates, BIN data, commission amounts) in unencrypted database and backup files.

### Risk 5 — Duplicate Deployment Risk
Without a deployment pipeline that enforces simultaneous updates to NCA and NUS, the two databases will drift. A drift in dormancy schedule assumptions or fee calculation logic between NCA and NUS could create inconsistent treatment of similar programs across regions, leading to unexplainable variance in management reporting.

### Risk 6 — US Reg E Compliance Dependency on Data Accuracy
The `dorm_wait` values in `cursforecast` must be ≥12 for US programmes to comply with Reg E's dormancy fee restrictions. There is no validation in the `sys_calc_dormancy` procedure or in the `cursforecast` DDL constraining this value for US programmes. A misconfigured program could project dormancy fees before the Reg E 12-month threshold, potentially producing financial statements that overstate fee income and represent a regulatory violation.

**Recommendation:** Add a CHECK constraint or application-layer validation for US programs (country_code = 'US') that enforces `dorm_wait >= 12`.

### Risk 7 — State Escheatment Configuration Risk
`unclaimed_keep` and `unclaimed_months` assumptions in `cursforecast` vary by US state. There is no state-level validation preventing configuration errors. An incorrect `unclaimed_months` setting for a US program (e.g., setting 5 years when the program's state requires 3 years) would cause the financial forecast to understate escheatment liabilities.

---

## Monitoring Considerations
- FortiDB DAM agent present (FortiDBRptRole).
- GTS read-only DBA monitoring access (NAM_GTS_MSSQL_DBA_RO).
- No SQL Agent jobs in codebase.
- No alerting on Reg E threshold violations or escheatment configuration errors.
- **US-specific recommendation:** Implement a validation job that checks all US programs (`country_code = 'US'`) for `dorm_wait >= 12` and alerts the compliance team on any violations.
