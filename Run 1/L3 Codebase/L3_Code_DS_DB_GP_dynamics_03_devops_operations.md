# DS_DB_GP_dynamics — DevOps / Operations View

## 1. Build System

| Attribute | Detail |
|-----------|--------|
| Project file | `dynamics.sqlproj` (322 KB) |
| SSDT schema provider | `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008 R2 compatibility) |
| MSBuild version | 4.0 |
| Output type | Database (DACPAC) |
| `DeployToDatabase` | True |
| `SqlServerVerification` | Not observed in the first 30 lines — check full project for override |
| Project size | Very large — 300+ tables, 80+ SPs, views, defaults, triggers |

The `dynamics.sqlproj` file is 322 KB, indicating a very large SSDT project with hundreds of SQL objects. Building this project will produce a large DACPAC that encompasses the entire GP DYNAMICS database schema.

---

## 2. CI/CD Pipeline

**No CI/CD pipeline files are present in this repository.** No `.gitlab-ci.yml`, `Jenkinsfile`, or Azure Pipelines YAML was found. Deployment is presumed to be manual DACPAC application via SSDT publish or a centralised pipeline in a separate configuration repository (`CONFIG_jenkins-file`).

**Impact**: Changes to the GP DYNAMICS schema (e.g. new GP hotfixes, security role changes, user additions) are deployed without automated testing or approval gates. For a system that controls access to financial records (SOX), this is a control gap.

---

## 3. Database Change Management

**State-based model (SSDT DACPAC)**: Object definitions in `.sql` files represent the desired end state. `SqlPackage.exe` generates and applies an incremental migration script at deploy time.

**Risks specific to GP**:
- Microsoft Dynamics GP releases its own update scripts through the GP upgrade process. These updates may conflict with or be overwritten by a DACPAC deployment if the DACPAC is not kept in sync with GP's current schema version.
- The `DBVERSION`, `DB_Upgrade`, and `SYUPDATE` tables track the GP version. Any DACPAC deployment must not inadvertently modify these tables or drop GP-standard objects that the GP application depends on at runtime.
- Custom objects (Banker SVC procedures, audit triggers, `zAuditGPUserSec`) must be maintained alongside GP standard objects.

**No rollback scripts**: DACPAC deployments are destructive (drop+create or ALTER). Rollback requires a point-in-time restore or a previous DACPAC baseline.

---

## 4. User Provisioning Process

Based on the Security folder contents, the user provisioning process for GP DYNAMICS is:
1. A new SQL login is created (`CREATE LOGIN [userid] WITH PASSWORD = N'...'` in individual security `.sql` files — see Section 5 for critical finding).
2. The user is added to `DYNGRP` role membership via `EXECUTE sp_addrolemember`.
3. The `DYNGRP.sql` file shows ~90 named user accounts in the role as of the last commit.

This process requires committing plaintext passwords to source control for SQL Authentication logins — a **critical security finding** (see 05_solution_architect.md).

---

## 5. Environments

Security files include:
| Login Pattern | Environment |
|---------------|-------------|
| `NAM_UAT` | UAT |
| `NAM_PROD` | Production |
| `NAM_PROD_CPP`, `NAM_PROD_CPP_APAC` | Production (CPP team) |
| `NAM_PROD_ITOPS` | Production (IT Operations) |
| `NAM_UAT` | UAT |
| Named individual accounts (e.g. `VL47548`, `Patricia.Pace`) | Production user accounts |

The presence of **Windows Authentication logins** (`FROM WINDOWS WITH DEFAULT_LANGUAGE`) for service accounts (e.g. `NAM_PPA_PRD_CLU`, `NAM\PPA_PRD_CLU`) alongside **SQL Authentication logins with plaintext passwords** for individual users represents a mixed-mode authentication configuration.

---

## 6. GP Version and Patching

- Schema provider `Sql100` targets SQL Server 2008 R2 schema compatibility. If the production SQL Server is a newer version (2016, 2019, or 2022), the schema provider setting may be stale and should be updated.
- GP version is tracked in `DBVERSION` and `DB_Upgrade` tables. The presence of `ME240443`, `ME240444`, `ME276001`, `ME27602`... etc. (tables prefixed `ME`) suggests specific GP hotfix/service-pack additions have been applied.
- The `taErrorCode` table and `GP-RSM-Customization` reference (separate repo) indicate third-party ISV customisations (RSM) are present, which must be managed independently of standard GP patches.

---

## 7. Operational Risks

| Risk | Severity | Detail |
|------|----------|--------|
| Plaintext passwords in Security `.sql` files | Critical | `gplain.sql`, `crystal.sql`, `ISAUser.sql`, `report.sql` contain `CREATE LOGIN ... WITH PASSWORD = N'...'` — credentials committed to version control. Immediate rotation and removal from repo required. |
| GP standard schema + custom objects in same DACPAC | High | DACPAC deployment could inadvertently drop or modify GP-standard tables needed by the GP runtime application. |
| `amAutoGrant` dynamic SQL | High | `CREATE PROCEDURE amAutoGrant @tablename ... EXEC (@command)` — table name is passed as a parameter and concatenated into a SQL string. An injection of a crafted table name could execute arbitrary SQL. |
| No CI/CD pipeline | High | Manual deployments to production ERP without automated regression or rollback capability. |
| `SearchAllTables` procedure | Medium | Full-scan across all GP tables; can cause blocking and performance issues if executed in production. |
| SQL Server 2008 R2 schema provider | Low | Stale target; should be updated to match actual SQL Server version. |
