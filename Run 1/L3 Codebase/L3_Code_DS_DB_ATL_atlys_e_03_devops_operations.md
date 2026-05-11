# DevOps / Operations Analysis — DS_DB_ATL_atlys_e (atlys_e)

## Build Technology

The repository is a **SQL Server Data Tools (SSDT) database project** (`.sqlproj`), targeting project version 4.1 with `ToolsVersion="4.0"` (MSBuild). The SSDT provider is `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider`, corresponding to SQL Server 2008 R2. Despite this provider setting, the database compatibility level is set to 90 (SQL Server 2005) in `<CompatibilityMode>90</CompatibilityMode>` within `atlys_e.sqlproj` (line 63).

**Build outputs:** SSDT produces a `.dacpac` (Data-Tier Application Package) when compiled. The project defines two configurations:
- **Debug** — `bin\Debug\atlys_e.sql`, debug symbols enabled, no optimisation.
- **Release** — `bin\Release\atlys_e.sql`, optimised, pdb-only symbols.

The compiled build script (`atlys_e.sql`) can be used as a deployment artifact. `<DeployToDatabase>True</DeployToDatabase>` indicates the project was configured for direct deployment from Visual Studio or MSBuild.

---

## CI/CD Pipeline

**No CI/CD configuration files are present in this repository.** There are no pipeline YAML files (Azure DevOps, GitHub Actions, Jenkins), no `Makefile`, no PowerShell deployment scripts, and no DACPAC publish profiles (`.publish.xml`) committed to source control. The `.gitignore` file is present but its contents were not examined.

**Implication:** Deployments are most likely performed manually by a DBA using Visual Studio SSDT "Publish" or `SqlPackage.exe` command-line tool directly against the target SQL Server instance. This is a significant operational risk in a PCI-regulated environment — it means there is no automated, auditable, repeatable deployment record.

---

## Environments

Evidence of multiple environments is visible in the Security directory:

| Security file | Implied environment |
|---|---|
| `NAM_PROD.sql` / `NAM_PROD_1.sql` | Production |
| `NAM_PROD_CPP.sql` | Production — CPP variant |
| `NAM_PROD_CPP_APAC.sql` | Production — APAC CPP variant |
| `NAM_PROD_ITOPS.sql` / `NAM_PROD_ITOPS_1.sql` | Production — IT Operations |
| `NAM_UAT.sql` / `NAM_UAT_1.sql` | User Acceptance Testing |
| `NAM_PPA_PRD_ATLYS.sql` / `NAM_PPA_PRD_ATLYS_1.sql` | PPA (Pre-Production Acceptance?) Production Atlys |
| `NAM_ppa_prd_ABAT.sql` / `NAM_ppa_prd_ABAT_1.sql` | PPA Production ABAT |

These files contain `EXECUTE sp_addrolemember` and `GRANT` statements. They are environment-specific login mappings that are included in the SSDT project build (`<Build Include="Security\*.sql" />`), meaning environment-specific permissions are compiled into a single deployable artifact rather than being managed separately. This creates **deployment risk**: applying the project to any environment will attempt to configure all login mappings from all environments, which may fail or silently skip inapplicable logins.

---

## Deployment and Migration Approach

SSDT uses a **state-based deployment model**: the project defines the desired end-state of the schema, and `SqlPackage.exe` generates a diff-script at deploy time. There are no explicit migration scripts (no `V001__`, `V002__` Flyway/Liquibase style files). Rollback therefore requires either:
1. A previously compiled dacpac with the prior schema state, or
2. A database backup restored from before deployment.

The `<Recovery>BULK_LOGGED</Recovery>` recovery model setting is notable: bulk-logged mode allows minimal logging for bulk operations (improving performance) but **restricts point-in-time recovery** — only full or differential backups can be used for restore between log backups. For a regulated financial database, full recovery model is strongly recommended.

---

## Operational Risks

### Risk 1 — Deprecated recovery model
The `BULK_LOGGED` recovery model prevents point-in-time restore. A data-corrupting transaction followed by a bulk operation before the next full backup would result in data loss. **Recommendation:** Move to `FULL` recovery model and implement regular transaction log backups.

### Risk 2 — No TDE
Transparent Data Encryption is disabled (`<IsEncryptionOn>False</IsEncryptionOn>`). Backup files are therefore unencrypted. In a PCI environment, backup media must be protected. **Recommendation:** Enable TDE and ensure backup encryption is in place.

### Risk 3 — Compatibility level 90
SQL Server 2005 compatibility mode is active. This restricts the query optimiser to older cardinality estimation and prevents use of modern T-SQL syntax. More critically, SQL Server 2005 has been end-of-life since 2016, meaning no further security patches. Even if the actual server instance is a newer version of SQL Server, running at compat level 90 means stored procedures cannot benefit from newer execution plan improvements. **Recommendation:** Test and upgrade compatibility level to at least 130 (SQL Server 2016).

### Risk 4 — Environment-specific logins in SSDT project
All environment logins (PROD, UAT, PPA, APAC) are compiled into the same SSDT project. Deploying the project from the wrong environment branch will apply incorrect permission grants. **Recommendation:** Externalise environment-specific security scripts from the SSDT project into a separate, environment-gated pipeline step.

### Risk 5 — No CI/CD
Manual deployments to production are not auditable by default. PCI DSS v4.0.1 Requirement 6.3 mandates that all changes to system components are managed through a defined change-control process including testing and approval records. Without pipeline automation, compliance evidence must come entirely from manual ticket/ITSM records. **Recommendation:** Implement an Azure DevOps or equivalent pipeline using `SqlPackage.exe publish` with approval gates.

### Risk 6 — Trigger-based business logic during schema changes
The `trgUsers` trigger cascades changes to three other tables (`tblSalesReps`, `tblRelMgrs`, `tblAcctMgrs`). Schema changes to any of these tables must be tested for trigger side effects. The trigger also performs `PWDENCRYPT` re-hashing on any UPDATE to `pwd`, meaning a bulk data migration touching the `pwd` column will trigger a hash operation on every row.

### Risk 7 — CHECK constraint on database existence
`tblCompanies` has a CHECK constraint that calls `DB_ID()` to validate that the referenced fee and reward databases exist. This constraint will fail during disaster recovery scenarios where those databases have not yet been restored, blocking the `tblCompanies` insert/update and potentially preventing application startup. **Recommendation:** Move this validation to application-level code or a scheduled validation job.

---

## Monitoring Considerations

- No SQL Server Agent jobs are defined in this repository.
- No alerting or monitoring configuration is present.
- FortiDB role (`FortiDBRptRole.sql` in Security/) indicates a database activity monitoring (DAM) agent is deployed — this is a positive security control.
- `NAM_GTS_gpatmon.sql` and `NAM_GTS_MSSQL_DBA_RO.sql` suggest monitoring logins for GTS (Global Technology Services) read-only DBA access.
