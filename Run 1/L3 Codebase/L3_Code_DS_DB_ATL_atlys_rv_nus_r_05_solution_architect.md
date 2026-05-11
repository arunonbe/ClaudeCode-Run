# Solution Architect Report: DS_DB_ATL_atlys_rv_nus_r

## Technical Debt Summary

| Debt Item | Severity | File/Location |
|---|---|---|
| No CI/CD pipeline | High | Root — no pipeline file |
| `tblGLLinks` in rollback database creates reverse dependency | High | `vRevenue.sql` line 15 |
| Monthly date formula potentially incorrect for February | Medium | `vIssuance.sql` line 3, `vRevenue.sql` line 12 |
| No permissions tracked in source control | Medium | No Security/ folder |
| Shared `tblGLLinks` has no change management process | High | Data governance gap |
| SSDT target version SQL 2016 potentially stale | Low | `atlys_rv_nus_r.sqlproj` |
| Single `development` branch | Medium | `.git/packed-refs` |

---

## Security Vulnerability Assessment

### SQL Injection
**Risk: LOW.** View-only project with no parameterized queries.

### Hardcoded Credentials
**None found.** No connection strings or secrets in any SQL file.

### Excessive Permissions
No permissions file present in this project. Same gap as NCA rollback.

### `tblGLLinks` Data Integrity Risk
The GL mapping table determines revenue categorization. Unauthorized or unreviewed changes to `tblGLLinks` data could cause material misstatements in financial reports. No row-level security, audit trigger, or data change log is evident from this project's files.

**Recommendation**: Add a DML audit trigger or temporal table to `tblGLLinks` to record all INSERT/UPDATE/DELETE operations with user identity and timestamp. This is a SOX-relevant control.

---

## Complete Object Inventory with Purpose

### Views

| Object | File | Purpose | Notes |
|---|---|---|---|
| `dbo.vCosts` | `dbo/Views/vCosts.sql` | UNPIVOTs FDR and GP operational costs into row-per-metric format | No sensitive data |
| `dbo.vCSCallTypes` | `dbo/Views/vCSCallTypes.sql` | CS call volume by type for cost allocation | No sensitive data |
| `dbo.vGP_nc` | `dbo/Views/vGP_nc.sql` | Master GP analysis (no commissions); UNPIVOT of all financial line items | Key analytical view |
| `dbo.vIssuance` | `dbo/Views/vIssuance.sql` | Monthly-aggregated issuance; date normalized to 30th of month | Date formula risk |
| `dbo.vPlastics` | `dbo/Views/vPlastics.sql` | Physical card production quantities | No sensitive data |
| `dbo.vPrograms` | `dbo/Views/vPrograms.sql` | Program master from GP with deduplication | Cross-DB to GP |
| `dbo.vRevenue` | `dbo/Views/vRevenue.sql` | Monthly revenue by program and GL line code; uses LOCAL tblGLLinks | Key config dependency |
| `dbo.vRevenueSum` | `dbo/Views/vRevenueSum.sql` | Total revenue sum by program and month | No sensitive data |
| `dbo.vRevenueT0` | `dbo/Views/vRevenueT0.sql` | Union of standard, FVD, and partner revenue | No sensitive data |
| `dbo.vRevenueT_FVD` | `dbo/Views/vRevenueT_FVD.sql` | FVD revenue from tblFVD_Revenue; filtered to 2007+ | No sensitive data |
| `dbo.vRevenueT_Partner` | `dbo/Views/vRevenueT_Partner.sql` | Partner revenue from GP SOP tables; GL '5%' filter | Cross-DB to GP |
| `dbo.vSpend` | `dbo/Views/vSpend.sql` | Spend by type, monthly aggregated | No sensitive data |

### Tables (Referenced but not defined here)
| Table | Significance |
|---|---|
| `dbo.tblGLLinks` | CRITICAL — authoritative GL mapping config; must be protected |

---

## Remediation Priority List

### Priority 1 — High (Immediate Action)

1. **Relocate tblGLLinks to a shared reference database**: Create a dedicated `atlys_gl_config` or `atlys_shared` database to host `tblGLLinks`. Update all NCA and US databases to reference the new location. This eliminates the architectural anti-pattern of a rollback database being a production dependency.

2. **Add audit trigger or temporal table on tblGLLinks**: Since this table controls revenue classification, all changes must be logged with user identity and timestamp for SOX and financial audit purposes. Implement as a DDL or DML trigger, or convert to a SQL Server temporal table.

3. **Add CI/CD pipeline**: As with the NCA rollback, a deployment pipeline is required for governance compliance.

### Priority 2 — Medium (Next Sprint)

4. **Validate February date normalization**: Test the `DATEADD(m, DATEDIFF(m, 30, date), 30)` formula against February dates on the target SQL Server version to confirm correct period assignment. If incorrect, update to a period-table approach similar to the NCA schema.

5. **Add permissions tracking**: Create `Security/Permissions.sql` to track all grants on this database's objects.

6. **Document tblGLLinks change process**: Establish a change management procedure requiring finance team sign-off for any modifications to `tblGLLinks` data.

### Priority 3 — Low (Backlog)

7. **Standardize date aggregation approach**: Align the US and NCA schemas to use the same date period approach (either both use `vPeriods` join, or both use the inline formula). This simplifies maintenance and cross-regional reporting.

8. **Update SSDT target version** to match production SQL Server version.

9. **Unshallow git clone** for complete audit history.
