# DevOps / Operations Report — DS_DB_ecountcore_rollback

## 1. Build System

| Property | Value |
|---|---|
| Project type | SSDT SQL Server Database Project (`Ecountcore_rollback.sqlproj`) |
| Build tool | MSBuild with SSDT targets |
| Output | DACPAC (`Ecountcore_rollback.dacpac`) |
| Target DSP | `Microsoft.Data.Tools.Schema.Sql.Sql130DatabaseSchemaProvider` — SQL Server 2016 |
| Build configurations | `Debug` and `Release` (standard SSDT configurations) |
| Project GUID | `{2a61d93c-51af-4b7a-b926-e1e6016e4966}` |

**Significant build consideration**: The project contains 200+ tables, many of which are historical rollback snapshots with date-stamped names (e.g., `ach_transaction_journal_jwu_20030326`). Every table in the SSDT project is compiled into the DACPAC and deployed to the target database. This means **all historical archive tables are deployed as live database objects**, not just retained as data. This is an unusual architecture that creates ongoing maintenance and PCI scope concerns.

---

## 2. Deployment

There is **no CI/CD pipeline configuration** visible in this repository. No `Jenkinsfile`, Azure DevOps YAML, or deployment scripts are present. Deployment follows the standard SSDT DACPAC pattern.

**Deployment risk specific to this project**: The DACPAC includes `allfreedomcard` (plaintext PAN table) and `user_validation_information` (plaintext credential table) as build-included objects. Any DACPAC publish will deploy these tables to the target instance. This is a **PCI DSS deployment risk** — the DACPAC should not be published to a PCI-scoped environment without first removing these table definitions.

**`[archive_data]` filegroup dependency**: The `archive_ctrl` table is created `ON [archive_data]` (`archive_ctrl.sql:11`). The SSDT project includes `Storage/archive_data.sql` which adds this filegroup. If deploying to a SQL Server instance where this filegroup does not exist, the `ALTER DATABASE ... ADD FILEGROUP [archive_data]` statement in the Storage script must be applied before the main DACPAC publish.

**Archive management deployment prerequisite**: The `archive_fdaj_commit_this` procedure disables and re-enables triggers on `ecountcore.dbo.fdr_dda_account_journal` (`archive_fdaj_commit_this.sql:88, 150`). This procedure requires the executing service account to have `ALTER TABLE` privilege on `ecountcore` — a significant cross-database permission that must be verified during deployment.

---

## 3. Configuration Management

The `dbo.controls` table serves as the primary application configuration store. The `archive_ctrl_batch_size` table configures batch sizes for each archived table type:

```
dbo.archive_ctrl_batch_size (table_name, queued_batch_size)
```

The `archive_fdaj_commit_this` procedure reads batch size at runtime:
```sql
DECLARE @batch_size INT = ISNULL(( 
    SELECT queued_batch_size 
    FROM dbo.archive_ctrl_batch_size 
    WHERE table_name = 'archive_ctrl_fdaj'), 250);
```
Default batch size is 250 records if not configured.

No external configuration files (`.config`, `appsettings.json`) are present — all configuration is table-driven.

---

## 4. Observability

| Capability | Status |
|---|---|
| `AuditJob` table | Present — SQL Agent job step execution audit trail |
| `archive_ctrl_table_stats` | Present — tracks archive operation statistics (records processed, timing) |
| `archive_fdaj_commit_this` error handling | TRY/CATCH block with `RAISERROR` — errors are surfaced (`archive_fdaj_commit_this.sql:152-173`) |
| Monitor stored procedures (active) | `monitor_autoach_failure`, `monitor_CoreCardCreation`, `monitor_FinancialProcess_DuplicateCard`, `monitor_ach_settlement_check`, `monitor_job_pending_tx_check` — operational health monitoring SPs present |
| `monitor_autoach_failure_autoFix` | Automated remediation procedure — auto-fixes known ACH failure patterns |
| FortiDB DAM | `FortiDBRptRole` security role present — database activity monitoring configured |
| Query Store | Not configured in project file — must verify on production instance |

The monitoring stored procedures (`monitor_*`) are called from SQL Agent jobs on a scheduled basis to detect operational anomalies. The presence of `monitor_autoach_failure_autoFix` indicates the database has automated remediation capability for specific ACH failure scenarios.

---

## 5. Service Account Access Matrix

Security scripts define the following access:

| Login/Role | Access Type |
|---|---|
| `NAM_PPA_PRD_APISVC` | API Service — application access |
| `NAM_PPA_PRD_BMCSVC` | BMC Service — operational tooling |
| `NAM_PPA_PRD_CSASVC` | CSA Service — customer service app |
| `NAM_PPA_PRD_CSWSVC` | Customer web service |
| `NAM_PPA_PRD_CZSVC` | ClientZone service |
| `NAM_PPA_PRD_ECAPSVC` | ECAP service |
| `NAM_PPA_PRD_ECORESVC` | ECORE service |
| `NAM_PPA_PRD_IVRWSVC` | IVR web service |
| `NAM_PPA_PRD_NROLLSVC` | Enrollment service |
| `NAM_PPA_PRD_OPSVC` | Operations service |
| `NAM_PPA_PRD_ORDERSVC` | Order service |
| `NAM_PPA_PRD_SCHSVC` | Scheduler service |
| `NAM_PPA_PRD_SQL` | SQL service account |
| `brigantine` | Brigantine application |
| `cccapp` | CCC application |
| `csa` | CSA application |
| `workbench` | Workbench application |
| `notification_svc` | Notification service |
| `emer_*` (20+ logins) | Emergency access logins (individual named users) |
| `B2C` | B2C application |
| `GENTRAN` | Gentran EDI service |
| `ecountcore_rollback_Delete/Select/Update/execute` | Permission roles |
| `FortiDBRptRole` | DAM role |

**Notable**: 20+ individual named emergency access logins (`emer_ag60132`, `emer_ec45727`, etc.) are defined in the Security scripts. These are individual DBA/engineer emergency access accounts — their presence in source control confirms they are deployed to production. Each individual login represents a named person with direct database access, which should be managed via PAM (Privileged Access Management) and reviewed periodically.

---

## 6. Operational Risks

| Risk | Severity | Description |
|---|---|---|
| `allfreedomcard` PAN table deployed via DACPAC | **CRITICAL** | DACPAC publish deploys a plaintext PAN table to every environment — PCI DSS Req 3.3 violation |
| `archive_fdaj_commit_this` disables ecountcore trigger | **HIGH** | Archive procedure has DDL control over `ecountcore`'s `fdr_dda_account_journal` trigger; if trigger disable fails to re-enable, account balance updates stop working in production |
| 20+ individual emergency access logins | **HIGH** | Named individual emergency logins without visible PAM controls; access may persist beyond employment or incident |
| No CI/CD pipeline | HIGH | Manual deployment risks; no automated regression testing |
| Historical PCI data (2002-2008) with no purge | HIGH | 20+ years of ACH/NACHA data in scope for PCI DSS and CCPA right-to-erasure |
| `user_validation_information` plaintext passwords deployed | HIGH | Authentication credentials deployed to production |
| Cross-database ALTER TABLE permissions required | MEDIUM | Service account must have `ALTER TABLE` on `ecountcore` — escalated privileges |

---

## 7. CI/CD Assessment

**Current state**: No CI/CD pipeline. Manual DACPAC deployment via SSDT/SqlPackage.exe is assumed.

**Recommended remediations before any deployment pipeline is established:**

1. Remove `allfreedomcard` and `user_validation_information` tables from the SSDT project (or convert to empty-schema-only definitions with data purged from production)
2. Remove or externalize individual `emer_*` emergency access logins from the project — manage via PAM tooling (CyberArk, BeyondTrust)
3. Add a deployment gate that validates the DACPAC does not introduce PCI-violating objects (check for plaintext PAN/CVV columns)
4. Add `[archive_data]` filegroup pre-flight check to deployment scripts
5. Establish a change management approval gate for any modification to archive procedures that interact with `ecountcore` triggers
