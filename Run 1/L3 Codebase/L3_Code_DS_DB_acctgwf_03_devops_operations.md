# DS_DB_acctgwf — DevOps & Operations Report

## 1. Build System

The project uses a **Visual Studio SQL Server Database Project (SSDT)** format, defined in `acctgwf.sqlproj` (21.5 KB). Key project properties:

- **Project format**: MSBuild `ToolsVersion="4.0"`, `.NET Framework 4.5` target
- **Schema provider**: `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008 compatibility)
- **Output type**: `Database` — generates a `.dacpac` artifact
- **Project GUID**: `{eeadb636-f458-4a0b-8960-c2d595d760a2}`
- **Collation**: `1033,CI` (English, case-insensitive)
- **Composite objects**: `IncludeCompositeObjects = True` (cross-database references are resolved)

The build produces a **DACPAC** (Data-tier Application Package) that can be deployed using `SqlPackage.exe` or Visual Studio's Publish mechanism.

## 2. CI/CD Pipeline Assessment

**No CI/CD pipeline configuration files were found** in this repository. Specifically:
- No `.github/workflows/` directory
- No Azure Pipelines YAML (`azure-pipelines.yml`)
- No Jenkins `Jenkinsfile`
- No `.gitlab-ci.yml`

The repository contains only a `.gitignore` (6.4 KB, standard VS SSDT template) and source SQL files. This strongly indicates that **deployments are performed manually** by a DBA using Visual Studio's Publish wizard or command-line `SqlPackage.exe`.

**Operational Risk — HIGH**: Manual deployment processes introduce risk of environment drift, missed change tracking, and inability to roll back deterministically.

## 3. Database Change Management

SSDT source control is the change management mechanism. All schema objects are tracked as individual `.sql` files in `git`. Changes are accumulated in source and deployed as a differential DACPAC publish.

**Observations**:
- No migration scripts (incremental `V001__`, `V002__` style) are present — this is a state-based (declarative) approach, not a migration-based approach.
- The `combine_dtl` and `combine_log` tables appear to be remnants of a combine/merge operation — no stored procedure in the repo manages them, suggesting they were created outside of the standard SDLC.
- `tblAW_Docs_old` exists as dead schema, indicating that schema cleanup is not routinely performed after deprecations.

## 4. Environments

Based on the Security role files, the following SQL Server login patterns suggest at least three environments:

| Login Pattern | Environment |
|---|---|
| `NAM\PROD` | Production |
| `NAM\UAT` | User Acceptance Testing |
| `NAM\PROD_CPP`, `NAM\PROD_CPP_APAC` | Production CPP/APAC variants |
| `NAM\PROD_ITOPS` | Production IT Operations access |
| `ifs_gidadb`, `ifs_infosec` | Security/compliance monitoring accounts |
| `scpardb` | SCPar database service account |
| `gers_read`, `gers_role` | GERS (reporting?) read access |
| `NAM_GTS_gpatmon` | GTS GPat monitoring |
| `FortiDBRptRole` | FortiDB database activity monitoring |
| `ACCTGWF_APP_GRP` | Application group (primary app account) |
| `Prod_Support_*` | Break-glass production support roles |

**No development environment logins are present in the Security directory**, suggesting this security script reflects production-only access.

## 5. Security Role Configuration

From `Security/RoleMemberships.sql`:
- `ifs_gidadb`, `NAM\ISA_SQL_SECADMIN`, `scpardb`, `ifs_infosec` are members of **`db_accessadmin`** and **`db_securityadmin`** AND **`db_denydatawriter`** — these are audit/security scanner accounts with elevated schema permissions but write-denied.
- `NAM\PROD_CPP`, `NAM\PROD_CPP_APAC`, `NAM\PROD`, `NAM\UAT`, `NAM\PROD_ITOPS` are members of **`db_datareader`** — broad read access.
- `ACCTGWF_APP_GRP` is the application role — granted `EXECUTE` on stored procedures, `SELECT` on views.

**Operational Risk — MEDIUM**: `NAM\PROD` and `NAM\UAT` both have `db_datareader`, meaning the UAT application service account has the same data-level access as production. If the UAT environment connects to a production database replica, this broadens the attack surface.

From `Security/Prod_Support_Select.sql`, `Prod_Support_execute.sql`, `Prod_Support_Schema_View.sql`, `Prod_Support_Update.sql`: A granular break-glass set of roles exists for production support operations, with separate SELECT, EXECUTE, SCHEMA VIEW, and limited UPDATE capabilities.

## 6. Backup and Recovery

No backup or recovery scripts are present in this repository. Database backup is assumed to be managed at the infrastructure level (SQL Server Agent jobs or Azure Backup). 

**Gap**: Recovery Time Objective (RTO) and Recovery Point Objective (RPO) are not codified in this repository. The database does not use Change Tracking (`IsChangeTrackingOn = False`, per `acctgwf.sqlproj` line 46), so CDC-based replication to a hot standby is not configured at the schema level.

## 7. Query Store Configuration

Per `acctgwf.sqlproj`:
- `QueryStoreCaptureMode = Auto`
- `QueryStoreDesiredState = ReadWrite`
- `QueryStoreFlushInterval = 900` seconds
- `QueryStoreMaxStorageSize = 100` MB
- `QueryStoreStaleQueryThreshold = 30` days

Query Store is enabled, providing performance diagnostics. The 100 MB cap is conservative for a database with complex recursive CTEs and dynamic SQL patterns.

## 8. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| No CI/CD pipeline | HIGH | Manual deployments only; no automated testing or promotion controls |
| TDE disabled | HIGH | At-rest encryption absent (`IsEncryptionOn = False` in `.sqlproj`) |
| SHA-1 password hashing | HIGH | `tblAWUsers` trigger uses SHA-1 (HASHBYTES), deprecated since NIST SP 800-131A (2015) |
| Unlimited recursion | MEDIUM | `OPTION (MAXRECURSION 0)` in `sys_tasks.sql` and `sys_schedules.sql` — runaway query risk with wide date ranges |
| Dead schema | LOW | `tblAW_Docs_old`, `combine_dtl`, `combine_log` are inactive tables consuming space and adding confusion |
| No data retention | MEDIUM | Task history, workpaper comments, and open item notes accumulate indefinitely |
| Broad `db_datareader` grants | MEDIUM | Multiple service accounts have full read access to all tables including user credentials table |
| Linked server dependency | MEDIUM | GL queries depend on dynamic cross-database SQL targeting `GlDbName` — if that DB is offline, GL account features fail entirely |

## 9. Monitoring Gaps

- **No SQL Agent job definitions** in this repo — monitoring and alerting for failed tasks are external.
- **FortiDBRptRole** is present (`Security/FortiDBRptRole.sql`, 74 bytes), indicating that **Fortinet FortiDB** (database activity monitoring) is deployed. This is a positive compliance control.
- No query alerts or extended events configuration is present in the SSDT project.
- The `tblAW_TaskHistory` table records task completion status, but there is no automated alerting stored procedure for overdue tasks — this would need to be implemented via a SQL Agent job or application-layer scheduler.
