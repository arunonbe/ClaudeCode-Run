# DS_ETL_sykes — DevOps and Operations Perspective

## Repository Structure and Build Artefacts

The repository is a Visual Studio SSIS solution with the following deployable artefacts:

| File | Type | Purpose |
|---|---|---|
| `Sykes.sln` | VS Solution | Top-level solution; references the `Sykes` project |
| `Sykes\Sykes.dtproj` | SSIS Project | Project manifest; 136 KB — lists all 8 packages |
| `Sykes\cf_report.conmgr` | Connection Manager | Shared target DB connection |
| `Sykes\Project.params` | Project Parameters | Empty — no project-level parameters defined |
| `Sykes\Sykes.database` | SSAS Database stub | Unprocessed; not operationally deployed |
| `Sykes\sykes_*.dtsx` | SSIS Packages (8) | Individual ETL workflows |

There is no CI/CD pipeline definition (no `.gitlab-ci.yml`, no Dockerfile, no deployment script). Deployment is manual, via Visual Studio SSIS project publish or `ispac` deployment to the SSIS Catalog.

## SSIS Protection Level — Security Finding

The `Sykes.dtproj` manifest declares:

```xml
SSIS:ProtectionLevel="EncryptSensitiveWithUserKey"
```

**This is a critical deployment risk.** `EncryptSensitiveWithUserKey` encrypts sensitive properties (connection string passwords, parameter values marked `Sensitive=1`) using the Windows DPAPI key of the user who last saved the project. When the project is deployed by a different user or on a different machine (e.g., a CI agent or a different DBA), all sensitive values are lost — they appear as empty strings or cause decryption errors at runtime.

Evidence: `Sykes.dtproj` line 29 contains a `PasswordVerifier` property with a DPAPI-encrypted blob (`AQAAANCMnd8B...`). The project also defines `CM.cf_report.Password` as a sensitive parameter (line 77). These values will be inaccessible after any re-deployment by a different Windows identity.

**Recommendation**: Change the protection level to `DontSaveSensitive` and supply sensitive values through SSIS Catalog environment variable references or Azure Key Vault-backed configurations at deploy time.

## Deployment Target

The connection manager targets `d-na-db01.nam.wirecard.sys,2232` (`cf_report.conmgr` line 8). The `d-` prefix indicates a **development** environment. Operational packages executing against development databases suggest either:
1. The packages have not been promoted to a production SSIS Catalog with environment-overridden connection strings, or
2. The `cf_report` reporting database lives in a shared dev/reporting tier rather than a dedicated production server.

This should be validated against the current server landscape to confirm whether these packages actually execute against a production database in the `d-na` naming tier.

## Package Versioning and Authorship

| Package | Creator | Date | Computer |
|---|---|---|---|
| `sykes_call_summary.dtsx` | `WIRECARD\van.nguyen2` | 2020-06-29 | PF0VELTW |
| `sykes_DPR.dtsx` | `WIRECARD\van.nguyen2` | 2020-07-09 | PF0VELTW |
| `sykes_monthly_invoice.dtsx` | `WIRECARD\colin.treat` | 2020-10-16 | PF0VFP1H |
| `sykes_weekly_grifols.dtsx` | `WIRECARD\van.nguyen2` | 2020-06-29 | PF0VELTW |
| `sykes_weekly_TXU.dtsx` | `WIRECARD\van.nguyen2` | 2020-06-29 | PF0VELTW |
| `sykes_weekly_verizon.dtsx` | `WIRECARD\van.nguyen2` | 2020-06-29 | PF0VELTW |

All packages use `DTS:LastModifiedProductVersion="11.0.7001.0"` (SSIS 2012 SP4 CU), confirming the development toolchain is SQL Server Data Tools 2012. This version is end-of-life and has no Microsoft support.

## Operational File Handling

### Input Drop Zone
```
C:\ETL\In\SykesReports\         <- scan folder (folder_path)
C:\ETL\In\SykesReports\temp\    <- working copy (temp_folder_path)
C:\ETL\In\SykesReports\archive\ <- post-process archive (archive_folder)
```

The `sykes_monthly_invoice.dtsx` developer tested from a local Documents path (`C:\Users\colin.treat\Documents\projects\wdnamcbts-1033\`). This path is baked into the package parameter defaults (line 41) and will cause the package to fail on any host that does not have that directory structure.

### File Delivery Mechanism
No SFTP or automated file delivery component is present in this repository. Sykes presumably delivers files to the `C:\ETL\In\SykesReports\` UNC path via a file-transfer process external to this project. The absence of an inbound file-transfer package is an operational dependency gap — if the transfer fails, the ETL will silently process zero files.

## Scheduling and Orchestration

No SQL Agent job definitions or SSIS Catalog schedule configurations are present in the repository. Scheduling is managed externally (SQL Server Agent jobs, presumably) and is not version-controlled in this repo. This represents a documentation and change-management gap.

## Error Handling and Alerting

Unlike `DS_ETL_warehouse`, the Sykes project has **no email notification parameters** — `Project.params` is empty. There is no `SuccessEmailTo`, `FailEmailTo`, or `EmailFrom` configuration in any package. If a package fails, operations will only discover the failure by checking SQL Server Agent job history or SSIS Catalog execution reports.

**Recommendation**: Add a project-level failure-notification parameter and configure `Send Mail Task` objects on package `OnError` event handlers, or integrate with a centralised alerting platform.

## .gitignore Analysis

The `.gitignore` (6,384 bytes) is a standard Visual Studio `.gitignore` template and includes the comment (line 179): `# but database connection strings (with potential passwords) will be unencrypted`. This advisory note acknowledges that SSIS connection strings with embedded passwords would be committed in plaintext. In this project, all connections use Windows Integrated Security (`SSPI`), so no plaintext passwords are present in connection strings. However, the `Sensitive=1` DPAPI-encrypted blob in `Sykes.dtproj` line 29 IS committed to version control — while it is encrypted, it is encrypted per-user and therefore non-portable.

## Operational Risks Summary

| Risk | Severity | Recommendation |
|---|---|---|
| `EncryptSensitiveWithUserKey` protection level | High | Change to `DontSaveSensitive` + Catalog environments |
| No CI/CD pipeline | Medium | Implement GitLab CI with `ispac` deployment stage |
| Developer local paths in package defaults | Medium | Replace with UNC share paths; promote to project parameters |
| SQLNCLI11.1 provider (EOL) | Medium | Migrate to `MSOLEDBSQL` |
| No alerting on failure | Medium | Add `Send Mail Task` on OnError events |
| SSIS 2012 toolchain | Low-Medium | Plan upgrade path to SSIS 2019 |
| No schedule in version control | Low | Document or export SQL Agent job XML to repo |
