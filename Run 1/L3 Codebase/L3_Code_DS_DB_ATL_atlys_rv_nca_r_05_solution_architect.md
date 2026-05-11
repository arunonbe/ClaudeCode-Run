# Solution Architect Report: DS_DB_ATL_atlys_rv_nca_r

## Technical Debt Summary

This repository is a **view-only rollback variant** with limited intrinsic technical debt. Most debt relates to cross-database dependencies and deployment process gaps.

| Debt Item | Severity | File/Location |
|---|---|---|
| No CI/CD pipeline in repo | High | Root — no pipeline file |
| Cross-database linked server joins without error handling | Medium | All views referencing ECAN_R |
| Shared GL config across regional DBs (NCA reads from NUS_R) | Medium | `vRevenueD.sql` line 15, `vGP_nc.sql` line 127 |
| SSDT target version SQL 2016 potentially stale | Low | `atlys_rv_nca_r.sqlproj` line 8 |
| Shallow git clone — limited audit trail | Low | `.git/shallow` |
| Single `development` branch — no release branching | Medium | `.git/packed-refs` |

---

## Security Vulnerability Assessment

### SQL Injection Risk
**Risk Level: LOW** — This database contains only `CREATE VIEW` definitions. Views do not accept user-supplied parameters and therefore have no direct SQL injection surface. The consuming stored procedures (in `atlys_rvcr`) use `sp_executesql` with parameterization for dynamic SQL.

### Hardcoded Credentials
**None found.** No connection strings, passwords, or API keys appear in any of the 13 SQL files.

### Excessive Permission Grants
No `Security/` folder or permissions files exist in this repository. Permission management for this database is not tracked in source control, which is a gap. The consuming `atlys_rvcr` permissions model grants broad `EXECUTE` to `ATLYS_APP_GRP` on all stored procedures; it is unknown whether the same group has direct SELECT on this rollback database's views.

### Missing Encryption
No `ENCRYPTION` clause is present on any view definition. View text is readable by any user with `VIEW DEFINITION` permission. For a non-CDE database this is acceptable, but access should still be controlled.

### Linked Server Trust
The cross-database references to `ECAN_R` and `ATLYS_Rv_NUS_R` rely on the SQL Server linked server or database security context. If the linked server account has overly broad permissions on the Great Plains instance, a compromise of this reporting database could allow read access to the entire GP financial database.

---

## Complete Object Inventory with Purpose

### Views

| Object | File | Purpose | Notes |
|---|---|---|---|
| `dbo.vCosts` | `dbo/Views/vCosts.sql` | UNPIVOTs FDR transaction costs and GP operational costs (CS, Telco, IVR) into a row-per-metric format for cost analysis reporting | No sensitive data |
| `dbo.vCSCallTypes` | `dbo/Views/vCSCallTypes.sql` | Aggregates customer service call volume by call type for cost allocation | No sensitive data |
| `dbo.vGP_nc` | `dbo/Views/vGP_nc.sql` | Master gross profit analysis view (no commissions); 130 lines; 15+ UNION ALL segments joining issuance, plastics, revenue, costs, spend, virtual cards, and emboss data | Key analytical view; no sensitive data |
| `dbo.vIssuanceD` | `dbo/Views/vIssuanceD.sql` | Aggregates `tblIssuance` by program/date; joins to `vPeriods` for period assignment | No sensitive data |
| `dbo.vPeriods` | `dbo/Views/vPeriods.sql` | Simple date dimension: reporting period start (date1) and end (date2) dates | No sensitive data |
| `dbo.vPlasticsD` | `dbo/Views/vPlasticsD.sql` | Aggregates physical card production quantities from `tblPlastics` by program/date | No sensitive data |
| `dbo.vPrograms` | `dbo/Views/vPrograms.sql` | Program master from GP RM00101; includes program ID, name, parent, customer, manager, GFCID, and legal name; deduplicates on DEX_ROW_ID | Cross-DB: ECAN_R |
| `dbo.vRevenueD` | `dbo/Views/vRevenueD.sql` | Period-banded revenue detail with GL line codes; references `ATLYS_Rv_NUS_R.dbo.tblGLLinks` | Cross-DB: NUS_R |
| `dbo.vRevenueDSum` | `dbo/Views/vRevenueDSum.sql` | Summarizes revenue totals from `vRevenueT0` by program and period | No sensitive data |
| `dbo.vRevenueT0` | `dbo/Views/vRevenueT0.sql` | Union of three revenue sources: standard revenue table, FVD revenue, partner revenue | No sensitive data |
| `dbo.vRevenueT_FVD` | `dbo/Views/vRevenueT_FVD.sql` | Face Value Discount revenue from `tblFVD_Revenue`; filters to post-2007 non-zero amounts | No sensitive data |
| `dbo.vRevenueT_Partner` | `dbo/Views/vRevenueT_Partner.sql` | Partner/affiliate revenue from Great Plains SOP posted transactions; GL acct filter '5%' | Cross-DB: ECAN_R |
| `dbo.vSpendD` | `dbo/Views/vSpendD.sql` | Period-banded spend by type from `tblSpend` | No sensitive data |

---

## Remediation Priority List

### Priority 1 — High (Immediate Action)

1. **Add CI/CD pipeline definition**: Create a `Jenkinsfile` or Azure DevOps pipeline yaml for SSDT build and DACPAC deployment. This is essential for change management compliance in a PCI DSS Level 1 environment. Without it, deployments are ungoverned.

2. **Source-control permissions**: Add a `Security/Permissions.sql` file documenting all grants on this database's views, aligned with the pattern used in `atlys_rvcr/Security/Permissions.sql`. Without tracked permissions, access control cannot be audited.

### Priority 2 — Medium (Next Sprint)

3. **Resolve cross-database GL mapping coupling**: Move `tblGLLinks` to a shared reference database (e.g., a dedicated `atlys_config` DB) rather than having NCA reads from the NUS_R sibling. This eliminates a hidden inter-regional dependency.

4. **Add release branching**: Introduce `main`/`release` branches in git. The current single-branch `development` model provides no separation between in-progress work and production-deployed code.

5. **Document linked server accounts**: Identify and document the SQL Server service account used to resolve `ECAN_R` linked server connections. Ensure least-privilege access (read-only to the specific GP tables required).

### Priority 3 — Low (Backlog)

6. **Update SSDT target version**: Upgrade `Sql130DatabaseSchemaProvider` to match the actual production SQL Server version (2019 or 2022 if applicable).

7. **Unshallow the git clone**: Convert the shallow clone to a full clone to preserve complete commit history for audit and forensic purposes.

8. **Add view documentation headers**: Several views (e.g., `vCosts`, `vSpendD`, `vPeriods`) lack header comments. Add consistent header blocks (Author, Date, Purpose, Change Log) matching the standard used in `vGP_nc.sql` and `vRevenueD.sql`.
