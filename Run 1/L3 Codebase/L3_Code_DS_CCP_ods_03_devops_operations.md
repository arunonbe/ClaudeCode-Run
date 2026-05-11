# DevOps & Operations Report — DS_CCP_ods

## Build System

DS_CCP_ods uses **Visual Studio SQL Server Data Tools (SSDT)** with a `.sqlproj` project file targeting `Microsoft.Data.Tools.Schema.Sql.Sql130DatabaseSchemaProvider` (SQL Server 2016). The solution file is `ods.sln`.

Key project settings from `ods.sqlproj`:
- `DeployToDatabase=True`
- `SqlServerVerification=False` — no static analysis/verification on build
- `IncludeCompositeObjects=True` — composite object references included
- Target Framework: v4.5
- `TreatWarningsAsErrors=False` in both Debug and Release configurations

Build produces a `.dacpac` artifact which can be deployed via SSDT Publish or SqlPackage.exe.

## CI/CD Pipeline

**No CI/CD pipeline configuration exists in this repository.** There is no `.gitlab-ci.yml`, Jenkinsfile, Azure DevOps YAML, or any other pipeline definition. The SSDT project is suitable for CI/CD integration (dacpac publish), but none has been implemented. Deployment is manual.

## Deployment Mechanism

Manual dacpac deployment via SSDT or SqlPackage.exe. No evidence of automated deployment scripts. The `DeployToDatabase=True` flag enables incremental schema-compare-and-publish via SSDT's publish profile, but no `.publish.xml` file is present in the repository.

## Database Change Management

The ODS schema uses **SSDT project-based schema management** — schema objects are defined as CREATE statements, and SSDT generates incremental ALTER scripts on publish. This is a step above raw manual scripts but still lacks formal versioning:

- **No migration framework**: No Flyway or Liquibase. Schema changes are tracked at the object level in Git, not as ordered migration steps.
- **No version table**: No `SchemaVersion` or `__EFMigrationsHistory` equivalent.
- **Potential drift**: If any DBA applies an ad-hoc ALTER to the production ODS database outside of SSDT, the schema will drift from the source-controlled definition.

## Environments

Based on analysis of DS_CCP_db09 job scripts, the following environments are inferred:
- **Development** (D-* servers)
- **Test/QA** (T-* or Q-* servers)
- **COB** (C-* servers — continuity-of-business)
- **Production** (P-* servers — specifically `p-db09.nam.wirecard.sys\db09`)

The SSDT project does not have environment-specific publish profiles, so deployment to different environments requires manual server connection changes.

## Monitoring and Alerting

### In-Database Monitoring
1. `usp_SQLAgentFail_Notification`: Polls `msdb.dbo.sysjobactivity` every 5 minutes for jobs that failed in the past 5 minutes. Sends HTML email via Database Mail (`SQLMail` profile) to `DBA` operator. Called by a SQL Agent job on p-db09.

2. `spVerifyImport`: Called by SSIS packages before executing settlement reports. Validates:
   - Mastercard files present (expected count: 1 post-CCP-shutdown, 6 originally)
   - FIS settlement file present (`.STL` format)
   - FIS daily fee file present (`.IXS.csv` format, if applicable)
   - Sends email alert if any expected files are missing for any date in the reporting period

3. `FileIOLog` + `FileIOLogActivity` trigger: Every file processed by SSIS is logged. The trigger provides an immutable change audit trail.

### Gaps
- **No row-count validation**: Import procedures do not fail or alert if staging tables are empty before the staging-to-production transform. A file could arrive empty and pass silently.
- **No performance monitoring**: No query duration thresholds, no DMV-based monitoring, no wait-stat alerting.
- **No data quality checks**: No validation that PAN format matches expected patterns, no duplicate detection, no referential checks on incoming settlement data.
- **No alerting for PAN access**: The DDM bypass (UNMASK) is not audited. No SQL Server Audit specification is visible in the schema.

## Backup and Recovery

Not defined in this repository. Backup is an instance-level concern for p-db09. Given the CDE status of this database, PCI DSS Requirement 12.3.4 requires that backup media is physically secured and encrypted. The absence of backup configuration in the repo means this cannot be verified from source.

## Operational Risks

1. **PAN data in staging tables has no time-bound cleanup**: `FISRptCardHolderActivityStaging` accumulates PAN data between the load and the transform procedures. If SSIS fails between load and transform, PANs may sit in the staging table indefinitely with no cleanup mechanism.

2. **Archive tables have no retention policy**: `FISRptCardholderActivityArchive` grows unboundedly. As a table containing PANs, it should be subject to the same retention/purge controls as the production table.

3. **`spVerifyImport` email recipient depends on msdb `sysoperators`**: The recipient list is fetched at runtime from `msdb.dbo.sysoperators WHERE name = 'DBA'`. If the DBA operator's email changes or is removed, alerts silently stop without error (the `IF ISNULL(@Recipients, '') <> ''` guard swallows the failure).

4. **`util_get_date_range` duplicate `mtd` case**: Lines 82 and 101 both handle `@frequency = 'mtd'`. The second case (different calculation using `datediff(month,0,@refdate)`) is dead code — it can never execute. If the second calculation is the intended one for month-to-date, the procedure returns incorrect dates.

5. **Staging tables cleared by SSIS**: Staging tables appear to be truncated before each load by SSIS packages. If SSIS fails mid-truncate, downstream procedures will process empty datasets without warning.

6. **`spVerifyImport` uses MAXRECURSION 0**: The CTE in this procedure uses `OPTION (MAXRECURSION 0)` — unlimited recursion for a date-range loop. This is acceptable for bounded date ranges but could cause resource issues for very wide date ranges.

## SSDT Project Structure

```
ods.sln
ods.sqlproj (targets SQL Server 2016 / Sql130)
├── dbo\
│   ├── Tables\ (26 table definitions)
│   └── Stored Procedures\ (20 procedure definitions)
└── Security\
    ├── NAM_PROD.sql (login creation)
    ├── NAM_PROD_1.sql (role membership)
    ├── report.sql (login creation)
    ├── report_1.sql (role membership)
    ├── ODS_Execute.sql (role definition)
    ├── ODS_Unmask.sql (role definition + member assignment)
    ├── RoleMemberships.sql (role assignments)
    └── Permissions.sql (GRANT statements)
```
