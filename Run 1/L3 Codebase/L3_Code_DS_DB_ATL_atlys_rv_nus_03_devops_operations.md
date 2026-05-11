# DevOps and Operations Report: DS_DB_ATL_atlys_rv_nus

## Build System

| Attribute | Detail |
|---|---|
| Project type | SQL Server Data Tools (SSDT) `.sqlproj` (MSBuild) |
| Project file | `atlys_rv_nus.sqlproj` (102 KB) |
| Solution file | `ATLYS_Rv_NUS.sln` |
| Target SQL Server | SQL Server 2016 (`Sql130DatabaseSchemaProvider`) |
| Target framework | .NET 4.5 |
| Object count | ~95 tables, ~270 views, ~80 stored procedures, ~120 functions |
| Build output | DACPAC + deployment script |

The large `.sqlproj` file (102 KB vs. ~4 KB for the rollback variants) reflects the comprehensive schema. Building this project requires all cross-database objects to be resolvable or marked as external references.

---

## CI/CD Pipelines

**No CI/CD pipeline files exist in this repository.** Despite being the most critical database in the Atlys family, no Jenkinsfile, Azure DevOps pipeline, or GitLab CI configuration is present.

- Branch: `development` (single tracked branch)
- Shallow clone: `.git/shallow` present
- Remote: `origin/HEAD` → `development`

**This is the highest-severity gap in the entire Atlys database family.** This primary US financial database has no automated deployment pipeline, no automated testing, and no documented deployment procedure tracked in version control.

---

## Deployment Approach

Based on the SSDT project structure:
1. `msbuild ATLYS_Rv_NUS.sln /p:Configuration=Release` → produces `atlys_rv_nus.dacpac`
2. `SqlPackage.exe /Action:Publish /SourceFile:atlys_rv_nus.dacpac /TargetConnectionString:"..."` → generates differential deployment script
3. DBA reviews and executes script against target instance

**Critical deployment considerations:**
- `revenue.sql` contains a trigger (`trg_revenue`) that fires on INSERT/UPDATE. Table recreation or trigger modification requires careful sequencing.
- ~270 views and 120+ functions create a complex dependency graph. SSDT handles this via topological sort during deployment generation, but manual deployments could get the order wrong.
- The `NOT FOR REPLICATION` flag on identity columns in `tblAuditLog`, `revenue`, and `tblAuditDetails` indicates this database is part of a SQL Server replication topology. Schema changes that affect replicated tables require coordination with the replication publisher/subscriber setup.
- `tblGLLinks` is read by NCA databases via cross-database join. Changes to this table require coordinated deployment with NCA databases.
- The `ATLYS_APP_GRP` role binds to a Windows AD account (`NAM\PPA_PRD_ATLYS`). Role membership must be re-applied if the database is rebuilt from scratch.

---

## Environments

The Security folder contains files for multiple environments/access tiers:
- `NAM_PROD.sql`, `NAM_PROD_1.sql` — Production environment logins
- `NAM_UAT.sql`, `NAM_UAT_1.sql` — UAT environment logins
- `NAM_PPA_PRD_ATLYS.sql` — Application service account (production)
- `NAM_PPA_PRD_ABAT.sql` — ABAT (automated batch) service account
- `Prod_Support_*.sql` — Production support role with SELECT, EXECUTE, VIEW DEFINITION, and limited UPDATE access
- `FortiDBRptRole.sql` — FortiDB database activity monitoring reporting role
- `ifs_infosec.sql`, `ifs_gidadb.sql` — Information security monitoring accounts
- `NAM_GTS_gpatmon.sql`, `NAM_GTS_MSSQL_DBA_RO.sql` — DBA monitoring accounts
- `NAM_ICG_DBA_Default.sql` — ICG DBA default access
- `scpardb.sql`, `raf.sql`, `report.sql`, `report_full.sql` — Report access roles

---

## Backup and Recovery

No backup scripts in this repository. Key recovery considerations:
- **Schema recovery**: SSDT project enables rebuild from source (minutes to deploy views/SPs)
- **Data recovery**: All tables contain financial data; data loss would be financially significant. RTO/RPO must be defined by the infrastructure team.
- **Replication recovery**: `NOT FOR REPLICATION` columns indicate a replicated database. Recovery must account for replication topology (re-initializing subscriptions).

---

## Operational Risks

### Risk 1: No CI/CD Pipeline — CRITICAL
For a primary financial database in a PCI DSS Level 1 environment, the absence of a documented, automated deployment pipeline is a significant control gap. All deployments are ad-hoc, undocumented, and not subject to automated testing or approval gates.

### Risk 2: Replication Dependency
The `NOT FOR REPLICATION` flags indicate this database participates in SQL Server replication. Schema changes to replicated tables (`revenue`, `tblAuditLog`, `tblAuditDetails`) require coordinating with the replication topology. Failure to do so can break replication and cause data inconsistencies across replicas.

### Risk 3: Trigger Logic for Revenue Classification
The `trg_revenue` trigger auto-classifies revenue entries using LEFT OUTER JOINs to `vAffiliates`, `vProducts`, and `tblProgramsBank`. If any of these dependent views or tables have stale data or are temporarily unavailable, the trigger could silently misclassify revenue. There is no error handling in the trigger.

### Risk 4: Dynamic SQL in sys_execsqlviewtext
The `sys_execsqlviewtext` procedure (127 lines) constructs and executes dynamic SQL via `sp_executesql`. While input validation via `ATLYS_E.dbo.sys_chkstr` is applied to most parameters, the `@ViewName` parameter references `OBJECT_ID(@ViewName)` directly without the same validation, creating a potential SQL injection vector if the calling code does not adequately sanitize this parameter. See `sys_execsqlviewtext.sql` lines 23–30, 41.

### Risk 5: Cross-DB Dependency on tblGLLinks
Changes to `tblGLLinks` will affect NCA reporting databases immediately. No deployment coordination mechanism exists.

### Risk 6: 270+ Views — Deployment Complexity
Deploying schema changes to a database with 270+ views creates complex dependency resolution. SSDT handles this automatically, but manual DBA scripts frequently get view order wrong, causing deployment failures.

### Risk 7: tblGLMap_new, tblGLMap_old, tblGLMap_new_new, tblGLMap_old_old
Multiple versioned copies of the GL map table (`tblGLMap_new`, `tblGLMap_old`, `tblGLMap_new_new`, `tblGLMap_old_old`) suggest a history of ad-hoc schema changes without proper version control practices. These orphaned tables represent technical debt and potential confusion.

### Risk 8: FortiDB Integration
`FortiDBRptRole.sql` indicates FortiDB database activity monitoring is deployed. This is a positive security control. Ensure FortiDB policies are current and alerting is active.
