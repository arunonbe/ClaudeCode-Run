# DevOps and Operations Report: DS_DB_ATL_atlys_rv_nca_r

## Build System

| Attribute | Detail |
|---|---|
| Project type | SQL Server Data Tools (SSDT) `.sqlproj` (MSBuild) |
| Solution file | `atlys_rv_nca_r.sln` |
| Project file | `atlys_rv_nca_r.sqlproj` |
| Target framework | .NET 4.5 (`TargetFrameworkVersion v4.5`) |
| Target SQL Server version | SQL Server 2016 (`Sql130DatabaseSchemaProvider`) |
| Build configurations | Debug, Release (AnyCPU) |
| Output artifacts | `bin/Release/atlys_rv_nca_r.sql` (DACPAC/deployment script) |
| SSDT version | Visual Studio 11.0+ (v11.0 targets path fallback in project file) |

The project uses the standard SSDT MSBuild pipeline. Running `msbuild atlys_rv_nca_r.sqlproj /p:Configuration=Release` produces a compiled DACPAC and deployment SQL script. The `DeployToDatabase=True` flag means a publish profile can directly push schema changes to a target SQL Server instance.

---

## CI/CD Pipelines

**No CI/CD pipeline files were found in this repository.** There are no:
- Jenkins `Jenkinsfile` or pipeline scripts
- GitLab CI `.gitlab-ci.yml`
- Azure DevOps `azure-pipelines.yml`
- GitHub Actions workflows
- PowerShell or batch deployment scripts

The repository contains only SQL source files and the SSDT project definition. Based on patterns observed across the Onbe DS_DB repository set, deployment is likely coordinated via a shared CI template repository (`CONFIG_ci-templates` or `CONFIG_jenkins-file`), but no direct reference is present here.

**Gap**: The absence of a pipeline definition in the repository means deployment automation is externally governed and may be ad-hoc or manual for this repo. This is an operational risk.

---

## Deployment and Migration Approach

SSDT projects deploy schema changes using `SqlPackage.exe` with DACPAC publish. The typical approach:
1. Build produces `atlys_rv_nca_r.dacpac`
2. `SqlPackage /Action:Publish` compares target database schema to DACPAC and generates a differential deployment script
3. DBA or CI agent executes the script against the target instance

Since this project contains **only views** (no tables), deployments are low risk — `CREATE OR ALTER VIEW` operations are generally non-destructive. However:
- The `_r` suffix naming convention implies this is a **rollback target**: when the primary `atlys_rv_nca` database is being updated, this database can serve as the active view layer until the primary is ready
- Cross-database dependencies (`ATLYS_Rv_NUS_R`, `ECAN_R`) must be available on the target server for deployment validation to succeed; `IncludeCompositeObjects=True` in the project file tells SSDT to validate these external references during build

---

## Environments

No environment-specific configuration files or connection strings are present in this repository. Based on the naming conventions observed across the codebase:

| Environment | Likely database name |
|---|---|
| Production | `atlys_rv_nca_r` on NAM production SQL cluster |
| UAT | Separate instance, naming TBD |
| Development | Developer-local or shared dev SQL instance |

The `git` branch tracked is `development` (`refs/heads/development`), with the remote `origin/HEAD` also pointing to `development`. There is no `main` or `master` branch in the packed-refs. This suggests a single active development line without evidence of environment-branching strategy.

---

## Backup and Recovery

No backup scripts, maintenance plans, or recovery procedures are defined in this repository. Backup responsibility falls to the SQL Server DBA team managing the host instance. Given this is a view-only database with no persistent data of its own, the recovery objective is primarily:
- Schema recovery: rebuild from SSDT project source (fast)
- Data recovery: not applicable (all data is in upstream operational databases)

**Gap**: No documented RTO/RPO for this database exists in the repository. Recommend documenting that schema recovery time = SSDT deploy time (minutes).

---

## Operational Risks

### Risk 1: Cross-Database Dependency Fragility
The views depend on three external databases: the local `atlys_rv_nca` tables, `ATLYS_Rv_NUS_R.dbo.tblGLLinks`, and multiple `ECAN_R` (Great Plains) tables. If any linked server connection or database availability changes, all views that reference those objects will fail silently (returning empty results or runtime errors). No error handling or fallback logic exists within the views themselves.

### Risk 2: No Deployment Pipeline
Without a tracked CI/CD pipeline in this repository, deployments may be performed manually by DBAs. Manual deployments increase the risk of environment drift, missed deployments, or production incidents from untested changes.

### Risk 3: SSDT Target Version Mismatch
The project targets SQL Server 2016 (`Sql130`). If the hosting instance is upgraded to SQL Server 2019 or 2022, the SSDT project should be re-targeted to avoid deployment warnings or schema generation differences.

### Risk 4: No Schema Version Tracking
There are no flyway, liquibase, or custom migration tracking tables. Schema version history is only traceable via git commit history.

### Risk 5: Single Branch Development
Only a `development` branch exists. No evidence of a `release` or `hotfix` branch structure. Changes go directly from development to production, which is a deployment governance risk for a regulated payments environment.

### Risk 6: Shallow Clone
The git repository uses a shallow clone (`shallow` file present). This limits the ability to trace full commit history for audit purposes, which may be relevant for SOX or PCI DSS change management audit trails.
