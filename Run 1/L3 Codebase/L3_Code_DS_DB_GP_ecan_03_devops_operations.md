# DS_DB_GP_ecan — DevOps / Operations View

## 1. Build System

| Attribute | Detail |
|-----------|--------|
| Project file | `ecan.sqlproj` |
| Solution file | `ecan.sln` |
| MSBuild tool version | 4.0 |
| Schema provider | `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008 R2 compatibility) |
| Output type | Database (DACPAC) |
| `DeployToDatabase` | True |
| `SqlServerVerification` | False — compile-time validation disabled |
| `IncludeCompositeObjects` | True — cross-database references included in model |
| `QueryStoreCaptureMode` | Auto |
| `QueryStoreDesiredState` | ReadWrite |
| Target DB schema version | SQL Server 2008 R2 (`Sql100`) — should be updated to match production SQL Server version |
| `ModelCollation` | `1033,CI` (Latin1_General_CI_AS — case-insensitive English) |

**Note**: `ModelCollation 1033,CI` is English (US) collation. For a Canadian operations database (ECAN), consideration should be given to whether French-Canadian content (if any) requires a different collation setting.

---

## 2. CI/CD Pipeline

**No CI/CD pipeline files are present in this repository.** No `.gitlab-ci.yml`, `Jenkinsfile`, or Azure Pipelines YAML was found.

Based on the broader Onbe platform context, deployment is likely performed manually or through a centralised pipeline in `CONFIG_jenkins-file`. Without pipeline evidence in this repo, it is impossible to verify deployment gates or testing requirements.

---

## 3. Database Change Management

**State-based DACPAC model**: Changes are made to `.sql` files in the SSDT project, DACPAC is built, and `SqlPackage.exe` applies differential changes to the target database.

**Stored procedure organisation**: SPs are split across `Procs1` through `Procs18` subfolders, indicating the project grew over time and was periodically reorganised into new batches to manage SSDT build performance. This is a common pattern for large GP SSDT projects.

**Report folder**: Contains `rpt_check_issuance.sql` — a report procedure in a separate folder, suggesting some report-layer objects are managed separately from application layer objects.

**Risk for GP schema**: The same risks as identified for DYNAMICS apply — GP upgrade scripts may conflict with DACPAC deployments if the SSDT project is not kept in sync with the GP application version.

---

## 4. Security File Pattern

The `Security/` folder contains ~220 SQL files. The pattern observed:
- `{loginid}.sql` — `CREATE LOGIN [...] WITH PASSWORD = N'...'` or `FROM WINDOWS WITH DEFAULT_LANGUAGE`
- `{loginid}_1.sql` — `CREATE USER [{loginid}] FOR LOGIN [{loginid}]` or `CREATE USER [{loginid}] WITHOUT LOGIN`

This paired naming convention means each principal has two files: one for the server-level login, one for the database-level user. The `_1.sql` files create the database user; the `.sql` files create the login.

**Security observations**:
- `DYNSA.sql` — `CREATE USER [DYNSA] WITHOUT LOGIN` — DYNSA is a GP-internal user without a login, used for GP system operations.
- `crystal.sql` — `CREATE LOGIN [crystal] WITH PASSWORD = N'Wkokvfts{usvf!fg{#{etxtemsFT7_&#$!~<&e;Q{crxmasf'` — **plaintext credential, different password from the dynamics repo** — indicating per-database unique passwords, but still plaintext in source control.
- `Banker_execute` role — `EXEC sp_addrolemember ... 'NAM\PROD'` — the production domain account has Banker execute permission.
- `NAM_PAAPRDDFINSPVC.sql`, `NAM_PPA_PRD_FinSVC.sql` — Finance Service Windows Authentication login.
- `ordersvc.sql`, `raf.sql` — Order Service and Refer-a-Friend service logins.
- `ACCTGWF_APP_GRP.sql` — Accounting workflow application group.
- `NAM_GTSDBSVC84.sql` — A database service account, likely for monitoring or backup.

---

## 5. Environments

| Login Pattern | Environment |
|---------------|-------------|
| `NAM_UAT` | UAT |
| `NAM_PROD` | Production |
| `NAM_PROD_ITOPS` | Production IT Operations |
| Individual named logins | Production GP users |
| `NAM_PPA_PRD_*` service accounts | Production application services |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|------|----------|--------|
| Plaintext SQL Auth passwords in Security scripts | Critical | `crystal.sql`, `report.sql`, `report_full.sql` contain plaintext passwords. Different from dynamics passwords (per-database unique) but still plaintext in Git. |
| `amAutoGrant` dynamic SQL | High | Present in Procs1 folder (replicated from DYNAMICS pattern); same injection risk. |
| No CI/CD pipeline | High | Manual deployments without automated testing or approval gates. |
| `Permissions.sql` is 118 KB | Medium | A single 118 KB permissions file is unmaintainable; individual permission changes cannot be reviewed in isolation. Should be split by role/login. |
| GP version mismatch risk | High | `Sql100` schema provider may be stale; deploying a DACPAC against a newer SQL Server GP instance risks dropping/altering tables the GP application depends on. |
| Cross-database reference in views | Medium | `BankerAllSOView` and others reference `rsm_customer_rollup` which may be defined in the same or a different database — if drift occurs the view breaks silently. |
| `QueryStore` enabled | Low | `QueryStoreCaptureMode = Auto` and `QueryStoreDesiredState = ReadWrite` — positive for performance monitoring; ensure query store max size is configured to prevent storage bloat. |
