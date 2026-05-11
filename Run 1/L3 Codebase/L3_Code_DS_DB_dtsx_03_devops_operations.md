# DS_DB_dtsx — DevOps and Operations View

## Build System

There is **no build system** for this repository. The `.dtsx` files are pre-compiled SSIS packages in XML format. There is no Visual Studio solution file (`.sln`), no SSIS project file (`.dtsproj`), and no MSBuild configuration. The repository is purely a file-system snapshot used as a version-control safety net rather than a true CI/CD source.

The packages were created using SQL Server Data Tools (SSDT) for Visual Studio — the creator computer name `GTSECNTW555103` is embedded in `AMLMantasETLNAM.dtsx` (line 7, `DTS:CreatorComputerName`), and package modification timestamps reference SQL Server Integration Services version `11.0.5058.0` (SQL Server 2012) and `11.0.7001.0` (SQL Server 2012 SP4).

---

## CI/CD Pipeline

**There is no CI/CD pipeline in this repository.** The GitLab README is a default template with no populated content. No `.gitlab-ci.yml` file is present. No Jenkins file, no GitHub Actions workflow, no Azure DevOps pipeline definition exists.

---

## Deployment Approach

Deployment is entirely **manual and file-copy based**:

1. A developer or DBA modifies the `.dtsx` package in SSDT on their workstation.
2. The updated `.dtsx` file is copied manually (likely via RDP or file share) to the target directory on the batch server (`p-na-bat03` for PROD, `q-na-bat03` for QA).
3. The previous version is renamed or moved to a backup subfolder (evidenced by backup directories: `backup`, `Backup_19sept`, `kuldip_backup`, `original_backup`, `Backup_Kuldip`, `Backup_21Nov17`).
4. The Git repository is updated as an afterthought (backup copies are also committed, indicating no branch strategy was followed).

The use of developer initials in backup folder names (`kuldip_backup`) indicates individual-level ad-hoc change management rather than a team process.

---

## Package Scheduling / Execution

Packages are executed via **SQL Server Agent jobs** on the batch server. No SQL Server Agent job definitions are stored in this repository. The scheduling configuration exists only on the target server and is not source-controlled. Observed execution contexts:

- **AMLMantasETLNAM.dtsx** — Scheduled as a nightly/daily batch for AML data feed to Oracle Mantas. Runs against PROD on `p-na-bat03` using the `report` SQL login.
- **BinBankETL.dtsx** — Periodic (likely weekly or on-demand) BIN/bank reference data load.
- **FDR_Import_DD031.dtsx** — Daily post-settlement FDR file ingestion. FDR delivers DD031 files via NDM (Network Data Mover), placed in directories on the batch server, then SSIS picks them up.
- **Citi/Fiserv Card Ship File Processors** — Daily, triggered after NDM file download from Citi/Fiserv. NDM (Connect:Direct) places files in the `ndmroot` or `personix` directory trees.
- **Returned_Checks.dtsx** — Triggered on receipt of returned-check data, likely daily.
- **Daily_Reconciliation_Files.dtsx** — Daily, for Sunrise bank partner.

---

## Monitoring

No monitoring configuration is present in the repository. SSIS package execution results are logged by SQL Server Agent to the SQL Server Agent job history. There is no evidence of:
- SSIS catalog (SSISDB) deployment — packages run from the filesystem (package deployment model, not project deployment model)
- Custom logging to a monitoring table
- Email alerting within packages (except `Returned_Checks.dtsx` which has an SMTP connection manager to `smtp.nam.wirecard.sys` — Windows auth, no SSL, which is a cleartext transmission risk)

---

## Environments

| Environment | Server | Domain | Notes |
|---|---|---|---|
| PROD | `p-na-bat03` | `NAM` (Wirecard NAM) | Active production server; packages in `PROD/` folder |
| QA/Stage | `q-na-bat03` | `NAM` | QA/UAT packages with separate dtsConfig files |

Both environments reference internal domain `*.nam.wirecard.sys` and `*.wirecard.sys`, which indicates the legacy Wirecard infrastructure. These DNS names and server aliases must be updated if still in use post-acquisition.

---

## Backup and Recovery

Package "backup" is the manual file-copy process described above. Key observations:

- Multiple backup folders exist side-by-side with no clear naming convention for dates or ticket numbers.
- `Backup/06172018/JIRA 15/Returned_Checks.dtsx` — the only backup that references a JIRA ticket number, suggesting a mid-2018 change management improvement attempt that was not sustained.
- No automated backup of the batch server filesystem is configured via this repository.
- Recovery in case of corruption: restore from the Git repository.

**Recovery Gap**: If SQL Server Agent job definitions are lost (they are not in this repo), the schedule and execution parameters would need to be rebuilt from memory or documentation.

---

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| No CI/CD — fully manual deployment | High | Any deployment error directly impacts production. No rollback automation. |
| Plaintext passwords in `.dtsConfig` files committed to Git | Critical | Password `r3p0rt1ng` for `report` SQL login is visible in `Mantas_NAM_UAT.dtsConfig`. Any person with repository access has production credentials. |
| Package ProtectionLevel=2 on PROD | High | If packages are re-saved under a different Windows user account, all sensitive properties become blank, breaking production runs silently. |
| No SSIS catalog / project deployment model | Medium | No centralised package management, version history, or parameter management. |
| NDM file directories not source-controlled | Medium | File input paths hardcoded in packages; if NDM routing changes, packages silently read no data. |
| Stale Wirecard domain references | High | All server names reference `*.wirecard.sys` — may require urgent DNS or hosts-file patching in current infrastructure. |
| No file cleanup for Mantas output | Medium | Output flat files accumulate on filesystem, representing uncontrolled cardholder data at rest. |
| SQL Server 2012 SSIS version | High | SQL Server 2012 is end-of-life (July 2022). Packages built for SSIS 2012 may need migration. |
| SMTP without SSL (`Returned_Checks.dtsx`) | Medium | Cleartext email transmission. Email alerting should use TLS. |
| CVV stored in `fdr_process_dd031_data` | Critical | Post-authorisation CVV storage is a direct PCI DSS Requirement 3.3.1 violation. |
