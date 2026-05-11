# DS_ETL_great-plains — DevOps and Operations Report

## 1. Build System

| Attribute | Value |
|-----------|-------|
| Project type | SSIS Package Deployment Model (pre-2012) |
| Project file | `Great-Plains.dtproj` — legacy `.dtproj` format |
| Solution file | `Great-Plains.sln` |
| SSIS format version | SQL Server 2008 R2 (`ProductVersion 10.50.1600.1`) |
| Packages | 34 `.dtsx` files in root directory (flat structure — no subdirectories) |
| Build output | No `.ispac` — Package Deployment Model does not produce ISPAC |
| CI/CD pipeline | **None** — no `.gitlab-ci.yml`, no Jenkins pipeline, no GitHub Actions |

Unlike the `DS_ETL_ccp-import-to-legacy` repo (which uses the 2012 Project Deployment Model with SSISDB), this repository uses the **older Package Deployment Model**. This means:
- Packages are deployed individually to the file system or MSDB (not to SSISDB catalog).
- Environment-specific configuration is in `.dtsConfig` XML files (not in SSISDB environments).
- The `Great-Plains.dtproj` file is an Analysis Services project structure repurposed for SSIS — the Source Control state is base64-encoded `<Enabled>false</Enabled>` indicating source control integration was never configured.

---

## 2. Deployment Mechanism

**Inferred (no pipeline present):** Manual deployment via SSIS Package Deployment Wizard or `dtutil.exe`.

Package Deployment Model deployment steps:
1. Build the project in Visual Studio (BIDS 2008 or SSDT 2012 in compatibility mode).
2. Deploy individual packages to the target SSIS server using:
   - `dtutil.exe /COPY SQL;<packagename> /SourceFile <package.dtsx>` (deploy to MSDB)
   - Or direct file copy to SSIS package store directory
3. Configure environment-specific connection strings via `.dtsConfig` files or SSIS Package Configurations.
4. Execute packages via SQL Server Agent jobs or `dtexec.exe`.

No deployment scripts, pipeline, or automation artefacts are present in the repository.

---

## 3. Configuration Management

**Package Deployment Model configuration** (inferred from project format — no `.dtsConfig` files are in the repository):
- Connection strings are likely embedded within `.dtsx` packages in encrypted form (SSIS EncryptSensitiveWithUserKey or EncryptAllWithUserKey protection levels).
- Environment-specific overrides are managed at runtime via SQL Server Agent job steps or `dtexec` configuration file parameters.
- **Concern**: Without `.dtsConfig` files in the repository, there is no version-controlled configuration. Connection strings (including server names and potentially credentials) may be only in the deployed package binaries.

**Source Control integration**: The `Great-Plains.dtproj` State field decodes to `<Enabled>false</Enabled>` — source control integration was never configured. Developers committed packages directly without source control hooks.

---

## 4. Observability

- **SQL Server Agent logging**: Packages are executed via SQL Server Agent; MSDB job history provides execution status.
- **SSIS log providers**: Each `.dtsx` package may have SSIS log providers configured internally (SQL Server, text file, Windows Event Log) — not visible without parsing package XML.
- **No centralised monitoring**: No SCOM alerts, SQL Server Agent alert framework, or APM integration.
- **SOJobsvc version ambiguity**: Three versions of `SOJobsvc` (`SOJobsvc.dtsx`, `SOJobsvc_Orig.dtsx`, `SOJobsvc_recompile.dtsx`) — operators must manually verify which version is deployed to production.
- **`CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx`**: Presence of a one-time migration package creates operational risk — if accidentally scheduled, it would re-run a data warehouse migration.

---

## 5. Infrastructure Dependencies

| Dependency | Type | Assessment |
|-----------|------|------------|
| SSIS 2008 R2 runtime | Compute | EOL July 2019 — no security patches for 6+ years |
| Microsoft Dynamics GP SQL Server | Database | GP ERP database server (all invoicing/GL packages) |
| `ecountcore` / `cbaseapp` | Database | Source for transaction and billing data |
| `prepaid_warehouse` SQL Server | Database | Source for cube reconciliation and GL data |
| FDR flat file share | File system | First Data settlement files — PCI DSS scope |
| Visa VSS file share | File system | Visa settlement files — PCI DSS scope |
| CitiDirect bank | External | ACH file delivery (US and Canada) |
| SQL Server Agent | Scheduler | Package execution scheduler |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|------|---------|--------|
| SSIS 2008 R2 — EOL since July 2019 | CRITICAL | Over 6 years without security patches; critical infrastructure running on unsupported software |
| SOJobsvc 3-version ambiguity | CRITICAL | Three versions of the same package in one project; unclear which is deployed to production. Incorrect package execution would post wrong Sales Orders to GP, causing SOX-reportable financial errors |
| `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` in active project | HIGH | One-time migration package; if scheduled or executed by mistake, runs a production server data migration |
| No CI/CD | HIGH | Manual deployment; no environment promotion control |
| PCI DSS data in EOL infrastructure (`SSIS_VSS`, `SSIS_FDR`) | HIGH | Visa and FDR settlement data processed by SSIS 2008 R2 |
| No `.dtsConfig` in source control | MEDIUM | Connection strings and environment config are not version controlled |
| No rollback mechanism | MEDIUM | GL batch postings to GP are difficult to reverse; no rollback SP or undo package present |
| Source control integration disabled | MEDIUM | `<Enabled>false</Enabled>` in project — no source control hooks or file locking |

---

## 7. CI/CD Assessment

**Current state**: No CI/CD. Package Deployment Model projects cannot be built to `.ispac` — they require a different deployment automation approach.

**Legacy Package Deployment automation**:
```powershell
# Example deployment script for Package Deployment Model
$packages = Get-ChildItem -Path ".\*.dtsx" -Exclude "SOJobsvc_Orig.dtsx","SOJobsvc_recompile.dtsx","CDW_*.dtsx"
foreach ($pkg in $packages) {
    & dtutil.exe /FILE "$($pkg.FullName)" /COPY SQL;"GreatPlains\$($pkg.BaseName)" /QUIET
}
```

**Recommended actions**:
1. Migrate project to SSIS 2012+ Project Deployment Model (SSISDB catalog).
2. Delete `SOJobsvc_Orig.dtsx` and `SOJobsvc_recompile.dtsx` from the project; use git history for version recovery.
3. Remove `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` from the deployable package set.
4. Implement environment-specific SSISDB environment references for all connection strings.
5. Add package execution to a CI/CD pipeline for automated testing in dev environment.
