# DevOps & Operations Report — DS_ETL_atmcardtronics

## Repository Identity

**Repository:** DS_ETL_atmcardtronics  
**Deployment Model:** SSIS Project Deployment Model (`.ispac`) to SSIS Catalog or legacy SQL Server Agent  
**CI/CD Pipeline:** None detected  
**Build System:** Visual Studio SSIS (SSDT — SQL Server Data Tools)

---

## Build and Deployment Model

### Solution and Project Structure
```
ATMCardtronics.sln          ← Visual Studio solution file
ATMCardtronics/
  ATMCardtronics.dtproj     ← SSIS project file (192 KB)
  ATMCardtronics.database   ← SSAS database definition (stub)
  Project.params            ← Project-level parameters
  CF_Report.conmgr          ← Shared connection manager
  *.dtsx (13 packages)      ← SSIS packages
```

### Deployment Steps (Manual)
1. Open `ATMCardtronics.sln` in Visual Studio SSDT
2. Build the project to generate an `.ispac` deployment package
3. Deploy `.ispac` to SSIS Catalog on the target SQL Server
4. Configure environment variables in SSIS Catalog to override project parameters (SourcePath, DestinationPath, SMTP, email addresses)
5. Create SQL Server Agent jobs to schedule each package

**No automated build pipeline exists.** There is no Jenkins file, Azure DevOps YAML, or PowerShell deployment script in the repository.

---

## SSIS Package Execution Requirements

### Runtime Dependencies
- **ACE OLEDB 12.0 driver** — Required by `ATMCardtronics_TACTDIST_Import.dtsx` for Excel source reading. If executing in 64-bit SSIS runtime, the 64-bit ACE driver must be installed. Many environments require the SSIS package to run in 32-bit mode for Excel connectivity.
- **SQL Server OLEDB Native Client 11** (SQLNCLI11.1) — Required by CF_Report connection manager
- **SMTP relay access** — Packages that send email require access to `nl-smtp-01.nam.wirecard.sys`
- **File system access** — Read access to `C:\ETL\In\Cardtronics\` and write access to `C:\ETL\In\CardtronicsArchive\`

### EncryptSensitiveWithUserKey — Deployment Risk
The project protection level `EncryptSensitiveWithUserKey` means:
- Packages can only be loaded by the Windows user account that saved them (the developer's account)
- On a server, if a service account different from the developer's account executes the package, sensitive values may be lost
- **Mitigation:** The CF_Report connection uses Windows authentication (SSPI), so no password is encrypted. Functional impact may be low, but this should be changed to `DontSaveSensitive` with SSIS Catalog environment parameters before production deployment.

---

## Scheduling and Cadence

No SQL Server Agent job scripts are present in this repository. Scheduling is managed externally. Based on package names, inferred cadence:

| Package | Expected Frequency |
|---|---|
| ATMCardtronics_DailyDispense | Daily |
| ATMCardtronics_DispenseDetail | Daily |
| ATMCardtronics_DailyRpt | Daily |
| ATMCardtronics_ElectronicJournal | Daily |
| ATMCardtronics_Surcharge | Daily |
| ATMCardtronics_Interchange | Daily |
| ATMCardtronics_SwitchBalance | Daily |
| ATMCardtronics_Replenishment | Daily or as-needed |
| ATMCardtronics_DevicePerformance | Daily or weekly |
| ATMCardtronics_TACTDIST_Import | Daily (settlement cycle) |
| ATMCardtronics_PartnerMonthlyAcctStat | Monthly |
| ATMCardtronics_AdjustmentEmail | Event-driven or daily |
| ATMCardtronics_Dispensed | Daily |

---

## File Delivery Mechanism

Cardtronics delivers data files to `C:\ETL\In\` on the SSIS host server. The delivery mechanism (FTP, SFTP, batch file drop, API) is not documented in this repository. File naming patterns visible from hardcoded design-time paths:
- CSV files: `WirecardDispenseDetail<timestamp>.csv`
- TACTDIST files: `D<YYMMDD>.CCSXIFSA<timestamp>.TACTDIST`
- Excel files: `WirecardATM_FISSettlementBalancing<timestamp>.xlsx`

The file naming still uses `Wirecard` prefix as of the design-time path captured at package creation (2018). If the actual Cardtronics-delivered file names have been updated to reflect the Onbe/North Lane rebrand, SSIS dynamic path expressions must have been updated to match. The package uses variable expressions (`@[User::source_full_name]`) to override the design-time path at runtime, which provides flexibility.

---

## SMTP Configuration and Email Operations

- **SMTP Server (design-time):** `nl-smtp-01.nam.wirecard.sys`
- **Parameter override:** `$Project::SMTPServer` — can be overridden via SSIS Catalog environment
- **UseWindowsAuthentication:** False
- **EnableSsl:** False — **SMTP is unencrypted**
- **EmailFrom (design-time):** `noreply@northlane.com`
- **EmailTo/CC:** `van.nguyen2@northlane.com`

The SMTP connection does not use TLS/SSL. Emails sent by SSIS packages (adjustment notifications) traverse the internal network without encryption. If the SMTP relay is on an internal network only, the risk is limited to internal actors. However, PCI DSS Req 4.2.1 (encrypt transmission of cardholder data over open, public networks) and Onbe security standards may require encrypted SMTP.

---

## Operational Risk Assessment

| Risk | Severity | Description |
|---|---|---|
| EncryptSensitiveWithUserKey protection level | MEDIUM | May fail on server deployment; should be changed before production use |
| 32-bit ACE driver dependency for Excel | MEDIUM | ACE driver version management on server; may conflict with 64-bit SSIS |
| SMTP without TLS | MEDIUM | Adjustment email content may include financial adjustment data |
| Legacy `wirecard.sys` DNS in connection string | LOW | DNS must still resolve; will fail after DNS decommission |
| No CI/CD pipeline | MEDIUM | Manual build and deploy; no quality gate |
| Hardcoded design-time paths in packages | LOW | Runtime overridden by variables; but creates confusion in debugging |
| Single email recipient (van.nguyen2@northlane.com) | LOW | If individual leaves, email notifications stop |
