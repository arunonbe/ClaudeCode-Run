# DevOps and Operations Report: DS_DB_ATL_atlys_rvcr

## Build System

| Attribute | Detail |
|---|---|
| Project type | SQL Server Data Tools (SSDT) `.sqlproj` (MSBuild) |
| Project file | `atlys_rvcr.sqlproj` |
| Target SQL Server | SQL Server 2016 (`Sql130DatabaseSchemaProvider`) |
| Target framework | .NET 4.5 |
| Object count | ~20 tables, ~35 views, ~45 stored procedures, ~20 functions |
| Build output | DACPAC + deployment script |

The project is substantially smaller than the primary `atlys_rv_nus` database (which has 270+ views and 120+ functions), consistent with its role as a router/dispatcher rather than a data-holding database. The SSDT build resolves cross-database references to `ATLYS_E` via dacpac references or by marking those objects as external references.

---

## CI/CD Pipelines

**No CI/CD pipeline files exist in this repository.** No Jenkinsfile, Azure DevOps pipeline YAML, or GitLab CI configuration is present in the repository root or any subdirectory.

- No automated DACPAC build stage
- No automated deployment to UAT or Production environments
- No schema change validation or drift detection
- No automated rollback mechanism for failed deployments

Given that `atlys_rvcr` is the **entry-point database** for the entire Atlys financial reporting application — every user request passes through here before being routed to company-specific databases — the absence of a CI/CD pipeline represents a significant operational and compliance gap. Any schema change deployed incorrectly could disrupt financial reporting for all companies and regions simultaneously.

---

## Deployment Approach

Based on the SSDT project structure, the inferred manual deployment process is:

1. `msbuild atlys_rvcr.sqlproj /p:Configuration=Release` → produces `atlys_rvcr.dacpac`
2. `SqlPackage.exe /Action:Publish /SourceFile:atlys_rvcr.dacpac /TargetConnectionString:"..."` → generates differential deployment script
3. DBA reviews and executes script against target SQL Server instance

**Critical deployment considerations specific to atlys_rvcr:**

- **Cross-database dependency on ATLYS_E**: All stored procedures call `ATLYS_E.dbo.sys_chkuser`, `sys_chkuserrights`, `sys_cinfo`, and `sys_regioncinfo`. Any deployment that touches these cross-database objects requires coordination with the ATLYS_E team.
- **Dynamic stored procedure execution in `tblJobs`**: The `exec_proc` column in `tblJobs` stores procedure names executed dynamically via `EXEC @p`. Any stored procedure rename or removal must be coordinated with `tblJobs` data updates.
- **`dbo` user bypass**: The access control pattern `IF USER_NAME() <> 'dbo'` means that deployments run under the `dbo` account bypass all authentication checks. This is by design but must be controlled via deployment account management.
- **Session-scoped staging tables**: The `tblEC_*` tables use `spid` in their clustered index. Structural changes to these tables must account for active sessions; a deployment during active import operations could corrupt in-flight data.
- **Security folder — 30+ files**: The Security folder contains login and permission definitions for multiple AD groups, service accounts, and roles. These must be applied in correct order (logins before role memberships before grants).

---

## Environments

The Security folder defines access for multiple environments and access tiers:

| File / Group | Environment | Access Level |
|---|---|---|
| `NAM_PROD.sql`, `NAM_PROD_1.sql` | Production | Standard production access |
| `NAM_UAT.sql`, `NAM_UAT_1.sql` | UAT | Test environment access |
| `NAM_PPA_PRD_ATLYS.sql` | Production | Application service account (Windows Auth) |
| `NAM_PPA_PRD_ABAT.sql` | Production | Automated batch service account |
| `Prod_Support_execute.sql` | Production | EXECUTE on all stored procedures |
| `Prod_Support_Update.sql` | Production | INSERT + UPDATE on all tables |
| `FortiDBRptRole.sql` | Production | FortiDB DAM reporting |
| `ifs_infosec.sql`, `ifs_gidadb.sql` | All | Information security monitoring |
| `NAM_GTS_gpatmon.sql`, `NAM_GTS_MSSQL_DBA_RO.sql` | All | DBA monitoring (read-only) |
| `NAM_ICG_DBA_Default.sql` | All | ICG DBA standard access |
| `NAM_PROD_CPP.sql`, `NAM_PROD_CPP_APAC.sql` | Production | CPP/APAC production access |
| `NAM_PROD_ITOPS.sql` | Production | IT Operations access |
| `gers_read.sql`, `gers_role.sql` | All | GERS reporting access |
| `report.sql`, `report_full.sql` | All | Report-level access tiers |
| `scpardb.sql`, `raf.sql` | All | Additional service accounts |

The breadth of the security file list — 30+ distinct principals — indicates that this database is widely accessed across multiple teams, departments, and automated systems.

---

## Backup and Recovery

No backup scripts are present in this repository. Key recovery considerations:

- **Schema recovery**: SSDT project enables schema rebuild from source in minutes
- **Data recovery**: `tblSettle`, `tblSettleDtl`, and FDR staging tables contain financially critical settlement data with no defined recovery point objective (RPO) in the codebase
- **Session-scoped staging tables**: Orphaned `tblEC_*` rows from crashed sessions cannot be recovered from backup without identifying the original session context
- **`tblJobs` data**: Job schedule definitions are configuration data. Loss of this table's data would disable all automated GL batch and balance reconciliation jobs. This data should be version-controlled separately from the schema

---

## Operational Risks

### Risk 1: No CI/CD Pipeline — CRITICAL
For a PCI DSS Level 1 financial entry-point database, the absence of an automated deployment pipeline means all schema changes are ad-hoc and undocumented. Any deployment error could disable financial reporting for all companies routed through this database. This is the single highest-severity operational gap.

### Risk 2: Dynamic Procedure Execution via tblJobs
`sys_jobrun` dynamically executes the procedure name stored in `tblJobs.exec_proc` using `EXEC @p`. While the `tblJobs` table has a CHECK constraint (`exec_proc IS NULL OR object_id([exec_proc], 'P') IS NOT NULL`) to ensure the procedure exists at the time of constraint evaluation, there is no runtime privilege check. If a procedure in `tblJobs` is dropped or renamed, the CHECK constraint will fail on INSERT/UPDATE but existing rows referencing the old procedure name will continue to exist and will fail at runtime with a non-descriptive error.

### Risk 3: `dbo` User Bypasses All Access Controls
The pattern `IF USER_NAME() <> 'dbo' BEGIN ... ATLYS_E.dbo.sys_chkuser ... END` is replicated across every stored procedure. The `dbo` database user has unlimited access to all stored procedures with no authorization checking. In a PCI DSS environment, the `dbo` account must be restricted to automated deployment processes only, and all human access must be via named accounts subject to authorization checks.

### Risk 4: Session-Scoped Tables as Permanent Tables
The `tblEC_*` staging tables accumulate orphaned rows from crashed or timed-out sessions because they are permanent SQL Server tables, not temporary tables. There is no cleanup job to remove orphaned session data. Over time, this can cause storage growth and data confusion during concurrent import operations. Identifying orphaned rows requires correlating `spid` values against `sys.sysprocesses`, which may not be reliable across SQL Server restarts.

### Risk 5: Prod_Support_Update Permissions
`Prod_Support_Update.sql` grants INSERT and UPDATE on all base tables to the `Prod_Support_Update` role. In a PCI DSS Level 1 environment, this permission grants the ability to modify settlement data, FDR staging data, and job schedules without any programmatic controls or audit trail beyond the FortiDB DAM. The FortiDB policy must be confirmed as actively monitoring and alerting on these accounts.

### Risk 6: No Data Retention for Settlement Data
`tblSettle`, `tblSettleDtl`, and `tblFDR_*` tables have no purge procedures. Settlement data accumulates indefinitely. For a PCI DSS in-scope database, a defined data retention schedule with automated purge procedures is a compliance requirement. The current state creates unbounded data growth and extends the window of exposure for any BIN-adjacent data.

### Risk 7: Cross-Database Join Availability
Every stored procedure depends on `ATLYS_E.dbo.sys_chkuser` and related functions. If the `ATLYS_E` database is unavailable (maintenance, failure, upgrade), all stored procedures in `atlys_rvcr` will fail. There is no fallback or circuit breaker pattern. This is a single point of failure for the entire Atlys reporting application.

### Risk 8: FortiDB Integration
`FortiDBRptRole.sql` confirms FortiDB database activity monitoring is deployed. This is a positive security control. Monitoring policies must be kept current and alerting must be confirmed active for the high-risk accounts (`Prod_Support_Update`, `dbo`, all service accounts).
