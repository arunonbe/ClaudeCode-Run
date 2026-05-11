# DevOps and Operations Report: DS_DB_ATL_atlys_rv_nus_r

## Build System

| Attribute | Detail |
|---|---|
| Project type | SQL Server Data Tools (SSDT) `.sqlproj` (MSBuild) |
| Project file | `atlys_rv_nus_r.sqlproj` |
| Solution file | `atlys_rv_nus_r.sln` |
| Target SQL Server | SQL Server 2016 (`Sql130DatabaseSchemaProvider`) |
| Target framework | .NET 4.5 |
| Build configurations | Debug, Release (AnyCPU) |
| Output | `bin/Release/atlys_rv_nus_r.sql` DACPAC deployment script |
| SSDT version | VS 11.0+ |

---

## CI/CD Pipelines

**No CI/CD pipeline files exist in this repository.** The same gap observed in `atlys_rv_nca_r` applies here. No Jenkinsfile, GitLab CI, or Azure DevOps pipeline files are present.

The git branch is `development` (single tracked branch, same as NCA rollback). The shallow clone pattern (`.git/shallow` present) is repeated.

---

## Deployment Approach

Same SSDT DACPAC publish pattern as the NCA rollback:
1. Build with `msbuild atlys_rv_nus_r.sqlproj /p:Configuration=Release`
2. Deploy with `SqlPackage.exe /Action:Publish`
3. Target: production SQL Server instance hosting the US Atlys databases

Since this project contains only views (plus `tblGLLinks` as an external dependency), deployments are low-risk schema operations.

**Special deployment consideration**: `tblGLLinks` is referenced by other databases (NCA rollback and primary databases) via cross-database joins. Any changes to this table's schema (columns, data types) require coordinated deployment with the NCA databases that depend on it. This creates a cross-repo deployment dependency that is not documented in any pipeline file.

---

## Environments

Same environment structure assumed as NCA rollback: Production, UAT, Dev. No environment configs are tracked in this repository.

---

## Operational Risks

### Risk 1: Cross-Repo Schema Dependency on tblGLLinks
`tblGLLinks` in this database is a shared configuration table used by multiple databases. If this database is dropped, renamed, or its schema modified without coordinating with NCA databases, the NCA reporting layer will break. This dependency is not documented in any deployment checklist or pipeline.

### Risk 2: No CI/CD Pipeline
Same risk as NCA rollback — manual deployments without governance documentation.

### Risk 3: Single Branch Development
Only `development` branch exists. No separation of production-deployed code from in-progress work.

### Risk 4: Monthly Date Normalization Logic
The `DATEADD(m, DATEDIFF(m, 30, date), 30)` formula in `vIssuance` and `vRevenue` normalizes dates to the 30th of each month. While correct for most months, this formula can produce unexpected results for February (since February has fewer than 30 days, the arithmetic may cross month boundaries). This is a potential data quality risk for financial period-end reporting in February.

**Example**: `DATEADD(m, DATEDIFF(m, 30, '2024-02-15'), 30)` — the behavior should be validated against actual SQL Server execution to confirm the expected period assignment for February dates.

### Risk 5: tblGLLinks Change Management
As the authoritative GL mapping table for the US and NCA Atlys reporting ecosystem, changes to `tblGLLinks` data (not schema) could affect revenue line classifications in financial reports. There is no documented change management process for this configuration table. Recommend treating `tblGLLinks` updates as financially significant changes subject to finance team approval.

### Risk 6: ECAN_R Linked Server Dependency (via vRevenueT_Partner)
Same linked server dependency on Great Plains as the NCA rollback. Unavailability of the GP linked server will fail the partner revenue view.

### Risk 7: Shallow Git Clone
Audit trail is limited. Full git history is not available for change management review.
