# DS_DB_GP_emxn — DevOps & Operations Report

## 1. Project Build Configuration

| Attribute | Value | Source |
|-----------|-------|--------|
| Project type | SQL Server Database Project (SSDT) | `emxn.sqlproj` line 1–10 |
| MSBuild schema provider | `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` | `emxn.sqlproj` line 11 |
| Target SQL Server version | SQL Server 2008 (compatibility 100) | `emxn.sqlproj` lines 11, 63 |
| Target framework | .NET 4.5 | `emxn.sqlproj` line 20 |
| Output type | Database (DACPAC) | `emxn.sqlproj` line 12 |
| Deploy to database | True | `emxn.sqlproj` line 19 |
| Include composite objects | True | `emxn.sqlproj` line 24 |

The SSDT project produces a DACPAC (Data-Tier Application Package) which is the deployable artifact. The project uses MSBuild and can be compiled via Visual Studio or `SqlPackage.exe`.

## 2. Build Artifacts

- **DACPAC**: Output to `bin/Debug/emxn.dacpac` or `bin/Release/emxn.dacpac` depending on build configuration.
- **Publish script**: Generated via `SqlPackage.exe /a:Script` for review before deployment.
- No `publish.xml` profile files were found in the repository — deployment targets (server, database name, credentials) are not committed. This is good practice from a secrets perspective but means deployment instructions exist only in undocumented operational runbooks.

## 3. CI/CD Pipeline

**No CI/CD configuration files were found in the repository** (no `.gitlab-ci.yml`, no Jenkinsfile, no Azure DevOps pipeline YAML). Based on Onbe's wider platform patterns (the repo `CONFIG_jenkins-file` and `DS_ETL_*` use Jenkins), the expected CI/CD approach is:

1. Developer commits to GitLab.
2. Jenkins pipeline (defined in `CONFIG_jenkins-file` repo) triggers SSDT build via MSBuild.
3. DACPAC is compared against target database using `SqlPackage.exe /a:DeployReport`.
4. Change script reviewed by DBA (manual gate).
5. Deployment executed to UAT, then promoted to PROD.

This pattern is inference based on platform standards; no pipeline config was committed to this repo.

## 4. Change Management

The repository does **not** contain a `DeltaSql/` folder (unlike `DS_DB_notificationsvc` which does). This means:
- Incremental schema changes are managed exclusively through the DACPAC diff-and-deploy mechanism.
- No individual migration scripts are maintained per-ticket/per-sprint.
- **Risk**: DACPAC deployment on a 16,594-procedure, 1,078-table schema can generate extremely long deployment scripts with potential for unintended drops if schema comparison is misconfigured.

### Change Management Risks
1. **GP Schema Ownership**: Most of the 16,594 stored procedures are Dynamics GP vendor-owned. Any GP upgrade or patch that changes procedure signatures would create deployment conflicts.
2. **No rollback scripts**: DACPAC deployments are forward-only unless a backup is restored. The absence of `DeltaSql/rollback/` scripts means rollback requires a full database restore.
3. **Named user logins in Security folder**: The `Security/` directory contains ~200 individual SQL login scripts (e.g., `Amber.Lukacko.sql`, `Sharon.Sywulak.sql`). These must be maintained in sync with Active Directory/HR offboarding processes.

## 5. Environment Management

The `Security/` folder reveals environment-level roles:
- `NAM_GTSDBSVC84.sql` — Service account for GTS (GP Technical Support) DBA service
- `ACCTGWF_APP_GRP.sql` — Accounting Workflow application group
- `DYNGRP.sql`, `DYNWORKFLOWGRP.sql` — Standard Dynamics GP groups
- `RAPIDGRP.sql` — Rapid deployment group

No separate environment-specific publish profiles were committed. Deployment targets are presumed managed via Jenkins parameters or manual SSMS deployments.

## 6. Database Configuration (from sqlproj)

| Setting | Value | Risk Note |
|---------|-------|-----------|
| `IsEncryptionOn` | False | TDE not enabled — data at rest unencrypted |
| `AllowSnapshotIsolation` | False | No MVCC; read operations take shared locks |
| `ReadCommittedSnapshot` | False | Reader-writer contention possible |
| `PageVerify` | CHECKSUM | Good — corruption detection enabled |
| `AutoShrink` | False | Correct — AutoShrink disabled |
| `CompatibilityMode` | 100 (SQL 2008) | **HIGH RISK** — 16-year-old compat level |
| `DelayedDurability` | DISABLED | Appropriate for financial system |
| `IsChangeTrackingOn` | False | No CDC; no audit trail at DB level |
| `ServiceBrokerOption` | DisableBroker | Broker disabled — no async messaging |
| `Trustworthy` | False | Correct security posture |
| `VardecimalStorageFormatOn` | True | Legacy feature, no longer recommended |

## 7. Security Model

### SQL Login Grants (Security folder patterns)
Each user in `Security/` has paired files:
- `Username.sql` — Creates the login/user and assigns to roles
- `Username_1.sql` — Grants specific permissions (SELECT, EXECUTE, etc.)

Roles observed:
- `DYNGRP` — Standard GP users (full GP application access)
- `DYNWORKFLOWGRP` — Workflow-enabled GP users
- `RAPIDGRP` — Rapid deployment / integration accounts
- `rpt_*` — Reporting roles (e.g., `rpt_accounting manager`, `rpt_payroll`, `rpt_power user`)

### Governance Concern
Individual named logins (`Amber.Lukacko`, `Sharon.Sywulak`, `Patricia.Pace`, `mstaudenmayer`) represent personal Windows or SQL accounts. This creates user lifecycle management risk — departed employees may retain access until their SQL login is manually revoked. This is inconsistent with PCI DSS Requirement 7 (need-to-know) and Requirement 8 (individual user accounts).

## 8. Operational Risks

| Risk | Severity | Description |
|------|----------|-------------|
| SQL 2008 compatibility level | **CRITICAL** | Compat 100 is end-of-life; missing performance features (batch mode, adaptive joins, inline index create) |
| TDE not enabled | **HIGH** | Data at rest is not encrypted; physical media exposure would expose employee PII and financial data |
| No CI/CD pipeline committed | **HIGH** | Deployments are manual or undocumented; change traceability gap |
| Named individual SQL logins | **HIGH** | User lifecycle risk; PCI DSS Req 8 non-compliance risk |
| No DeltaSql migration folder | **MEDIUM** | No per-change rollback capability |
| ReadCommittedSnapshot disabled | **MEDIUM** | Shared lock contention on 1,078 tables during heavy GP batch operations |
| 16,594 stored procedures in source control | **MEDIUM** | Extremely large DACPAC diff operations; deployment time risk |
| VardecimalStorageFormatOn | **LOW** | Deprecated feature; should be replaced with row/page compression |

## 9. Backup and Recovery

No backup scripts or maintenance jobs are committed to this repository. Onbe's `DS_DB_database_maintenance` repository likely contains the maintenance plan. For a GP financial database with employee SSNs and vendor tax IDs, recovery time objective (RTO) and recovery point objective (RPO) must be formally documented. Recommended:
- RPO: ≤ 1 hour (log shipping or Always On AG)
- RTO: ≤ 4 hours
- Full backup: Daily
- Transaction log backup: Every 15 minutes

## 10. Monitoring

No monitoring configuration is committed. Standard Onbe tooling (observed in security roles) includes:
- `NAM_GTS_gpatmon` — GP monitoring account
- `NAM_ppa_prd_mon` — Production monitoring service account
- FortiDB (`FortiDBRptRole`) — Database activity monitoring (DAM) — present in security roles across GP databases, indicating FortiDB is used for audit trail generation.
