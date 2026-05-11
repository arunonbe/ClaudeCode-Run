# Solution Architect Report — DS_ETL_atmcardtronics

## Repository Identity

**Repository:** DS_ETL_atmcardtronics  
**Risk Profile:** MEDIUM-HIGH — external partner integration with unencrypted SMTP, legacy SSIS version, and protection level mismatch

---

## Complete Object Inventory

| Object | Type | Purpose |
|---|---|---|
| `ATMCardtronics_DailyDispense.dtsx` | SSIS Package | Daily ATM cash dispense summary ingestion |
| `ATMCardtronics_DispenseDetail.dtsx` | SSIS Package | Granular dispense transaction detail ingestion |
| `ATMCardtronics_Interchange.dtsx` | SSIS Package | Interchange fee settlement ingestion |
| `ATMCardtronics_Surcharge.dtsx` | SSIS Package | Surcharge fee ingestion |
| `ATMCardtronics_SwitchBalance.dtsx` | SSIS Package | Switch balance reconciliation ingestion |
| `ATMCardtronics_Replenishment.dtsx` | SSIS Package | ATM cash replenishment event ingestion |
| `ATMCardtronics_ElectronicJournal.dtsx` | SSIS Package | ATM electronic journal (transaction audit) ingestion |
| `ATMCardtronics_DailyRpt.dtsx` | SSIS Package | Daily consolidated operational report ingestion |
| `ATMCardtronics_DevicePerformance.dtsx` | SSIS Package | ATM device uptime/performance metrics ingestion |
| `ATMCardtronics_TACTDIST_Import.dtsx` | SSIS Package | TACT settlement distribution file import (CSV + Excel) |
| `ATMCardtronics_PartnerMonthlyAcctStat.dtsx` | SSIS Package | Monthly partner account statement reconciliation |
| `ATMCardtronics_AdjustmentEmail.dtsx` | SSIS Package | Reads adjustments from cf_report; sends email alerts |
| `ATMCardtronics_Dispensed.dtsx` | SSIS Package | Total dispensed amounts summary |
| `CF_Report.conmgr` | Connection Manager | OLE DB connection to cf_report database |
| `Project.params` | Parameter File | SourcePath, DestinationPath, EmailTo, EmailCC, EmailFrom, SMTPServer, ArchiveFolder |
| `ATMCardtronics.dtproj` | Project File | SSIS project definition; ProtectionLevel=EncryptSensitiveWithUserKey |
| `ATMCardtronics.database` | Database Definition | SSAS stub (minimal content) |
| `ATMCardtronics.sln` | Solution File | Visual Studio solution |

---

## Security Vulnerabilities

### HIGH

**1. EncryptSensitiveWithUserKey — Server Deployment Failure Risk**  
File: `ATMCardtronics.dtproj`, line 15  
```xml
<SSIS:Project SSIS:ProtectionLevel="EncryptSensitiveWithUserKey">
```
This protection level is unsuitable for server deployment. Any sensitive values (even if currently none) will be unreadable when executed by a service account. The correct setting for catalog deployment is `DontSaveSensitive` (with environment parameters in SSIS Catalog) or `EncryptAllWithPassword`. The `PasswordVerifier` encrypted blob at line 29 further confirms user-key encryption is active.

**2. SMTP Without TLS — Email Content Exposure**  
File: `ATMCardtronics_TACTDIST_Import.dtsx`, line 42  
```xml
SmtpConnectionManager ConnectionString="SmtpServer=nl-smtp-01.nam.wirecard.sys;UseWindowsAuthentication=False;EnableSsl=False;"
```
Email sent by `ATMCardtronics_AdjustmentEmail.dtsx` regarding ATM adjustment records is transmitted without SSL/TLS. Adjustment details may include financial data (amounts, terminal IDs, dates). On an internal network the risk is limited to internal threat actors, but this violates the principle of encrypting financial data in transit.

**3. Stale DNS — Legacy `wirecard.sys` Domain**  
File: `CF_Report.conmgr`, line 9  
```
Data Source=q-db03.nam.wirecard.sys\db03,2232
```
The `wirecard.sys` DNS domain is the legacy internal domain from the Wirecard era. If this DNS zone has been decommissioned or the server `q-db03.nam.wirecard.sys` has been renamed/replaced, this connection will fail silently until the next package execution. There is no fallback or alternative connection string.

**4. Single Named Individual as Email Recipient**  
File: `Project.params`, lines 61, 103  
```
van.nguyen2@northlane.com
```
A single named individual is the recipient for all ATM adjustment email notifications. If this person leaves the organisation, email notifications will be undelivered and the business will have no alerting for ATM adjustments. This is an operational continuity risk.

### MEDIUM

**5. Hardcoded Local File System Paths**  
File: `Project.params`, lines 19, 40, 124  
```
C:\ETL\In\
C:\ETL\In\Cardtronics\
C:\ETL\In\CardtronicsArchive\
```
All paths are local to the SSIS execution server (`C:\ETL\`). This creates tight coupling between the ETL package and the specific server on which it runs. If the package is moved to a different server or deployed to Azure, all paths must be updated. Modern ETL architectures use UNC paths, cloud storage (Azure Blob), or configuration-driven path injection.

**6. SQL Server 2012 SSIS Tooling — EOL**  
Package metadata: `DTS:LastModifiedProductVersion="11.0.7001.0"` (all packages)  
SQL Server 2012 SSIS extended support ended July 2022. While the packages may run on newer SSIS versions, they have not been tested or validated against them (no evidence of upgrade in the metadata).

**7. Microsoft ACE OLEDB 12.0 Driver for Excel**  
File: `ATMCardtronics_TACTDIST_Import.dtsx`, line 29  
```
Provider=Microsoft.ACE.OLEDB.12.0
```
The ACE OLEDB driver is not pre-installed on server SKUs and has known 32-bit/64-bit compatibility issues in SSIS. This package likely requires the SSIS runtime to be set to 32-bit mode, which disables 64-bit optimisations for all other packages executed in the same agent job step.

---

## Technical Debt Inventory

| Item | Debt Type | Priority |
|---|---|---|
| EncryptSensitiveWithUserKey protection level | Security/Operations | P1 |
| SMTP without TLS (EnableSsl=False) | Security | P1 |
| Legacy wirecard.sys DNS dependency | Operations | P2 |
| Single named individual as email recipient | Operations | P2 |
| Hardcoded local C:\ETL paths | Architecture | P2 |
| SQL Server 2012 SSIS tooling (EOL July 2022) | Lifecycle | P2 |
| ACE OLEDB 12.0 Excel driver dependency | Operations | P2 |
| No CI/CD pipeline | Process | P2 |
| No error handling / retry logic visible in packages | Architecture | P3 |
| Wirecard branding in file name patterns | Housekeeping | P3 |

---

## Remediation Priorities

### Immediate (P1)
1. Change SSIS project protection level to `DontSaveSensitive` and configure SSIS Catalog environment variables for all sensitive parameters. Redeploy to production.
2. Enable TLS/SSL on the SMTP connection manager (`EnableSsl=True`). Confirm the SMTP relay supports TLS.

### Short-Term (P2)
3. Update the `EmailTo`/`EmailCC` parameters from individual named addresses to a distribution group or email alias (e.g., `atm-ops@onbe.com`).
4. Update the CF_Report connection string to use a current DNS name (non-wirecard.sys). Coordinate with the network/infrastructure team for DNS migration.
5. Migrate `C:\ETL\In\` paths to a UNC share or Azure Blob Storage path that is not tied to a specific server.
6. Upgrade the SSIS project in SSDT to SQL Server 2019 format; validate all packages execute correctly.
7. Evaluate replacing ACE OLEDB with a Flat File parser for the TACTDIST Excel file, or request Cardtronics to deliver in CSV format.

### Longer-Term (P3)
8. Evaluate migrating the 13 SSIS packages to Azure Data Factory (ADF) pipelines. ADF provides built-in monitoring, retry policies, and cloud-native storage integration.
9. Implement a schema validation step in each package to detect Cardtronics format changes before they cause data load failures.
10. Add package-level error handling (OnError event handler) with logging to a structured error table in cf_report.
