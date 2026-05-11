# Solution Architect View — DS_ETL_generic-etl

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_generic-etl`
**Package count:** 9
**Connection manager files:** 7

---

## Complete Object / Package Inventory

| Package | Size (bytes) | Purpose | Key Connections |
|---|---|---|---|
| `FDR_Import_DD031.dtsx` | 556,916 | FDR First Data settlement file import | File share → Ecountcore_Process |
| `IVR_CallLogs.dtsx` | 227,720 | IVR call log data import | IVR source → cf_report |
| `RC_Contact_Log.dtsx` | 156,968 | Contact log from Azure SQL to on-premise | Azure SQL (`dw_api`) → cf_report/cbaseapp |
| `Add_CSA_Archive_Comment.dtsx` | 72,145 | CSA record archiving comments | cbaseapp or ecountcore_process |
| `StarSf.dtsx` | 61,136 | STAR network Excel to Salesforce | Excel file → Salesforce (Script Task) |
| `CSL_Activity.dtsx` | 49,896 | CSL activity extraction | cbaseapp → cf_report |
| `Folder_File_CleanUp.dtsx` | 41,544 | File system housekeeping | File system |
| `Export_Network_Settlement_Sunrise.dtsx` | 34,571 | Sunrise bank settlement export | cf_report → flat file |
| `IVR_card_activation_update.dtsx` | 31,247 | Card activation status update from IVR | IVR data → ecountcore or cbaseapp |

---

## Connection Manager Inventory (Full)

| File | Object Name | Server | Catalog | Type | Auth | CRITICAL FLAGS |
|---|---|---|---|---|---|---|
| `alchemy-srv-dev.conmgr` | `alchemy-srv-dev` | `alchemy-srv-dev.database.windows.net` | `dw_api` | OLEDB SQLNCLI11.1 | SQL Auth (`rc_contact_log_user`) | **CRITICAL: DPAPI password blob in git** |
| `cbaseapp.conmgr` | `cbaseapp` | `d-na-db01.nam.wirecard.sys\db01,2232` | `cbaseapp` | OLEDB SQLNCLI11.1 | Windows SSPI | Dev server in git |
| `cf_report.conmgr` | `cf_report` | `q-db03.nam.wirecard.sys,2232` | `cf_report` | OLEDB SQLNCLI11.1 | Windows SSPI | QA server in git |
| `Ecountcore_Process.conmgr` | `Ecountcore_Process` | `d-na-db01.nam.wirecard.sys\db01` | `Ecountcore_Process` | OLEDB SQLNCLI11.1 | Windows SSPI | Dev server in git |
| `ecountcore_rollback.conmgr` | `ecountcore_rollback` | `d-na-db01` | `ecountcore_rollback` | OLEDB | SSPI | Dev server in git |
| `Vendor.conmgr` | `Vendor` | `d-na-db01.nam.wirecard.sys\db01` | `Vendor` | OLEDB SQLNCLI11.1 | Windows SSPI | Dev server in git |

---

## CRITICAL Security Vulnerabilities

### VULNERABILITY 1: SQL Authentication Password Blob in Git

**File:** `E:\OnbeEast363\repos\DS_ETL_generic-etl\ETL\alchemy-srv-dev.conmgr`
**Lines 7–11**

```xml
DTS:ConnectionString="...User ID=rc_contact_log_user;...Persist Security Info=True;..."
<DTS:Password DTS:Name="Password" Sensitive="1">
  AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAb3R5mOGu8UyAeV1m5LuXwAAAAAACAAAAAAADZgAAwAAAABAAAABz9MozpBG1nX...
</DTS:Password>
```

**Severity: CRITICAL**

Analysis:
- `User ID=rc_contact_log_user` — SQL login name is in plaintext in the connection string
- `Persist Security Info=True` — password is persisted in the connection manager
- The `<DTS:Password>` element contains a DPAPI-encrypted blob beginning with `AQAAANCMnd8BFdERjHoAwE/Cl+sB` — the standard Windows DPAPI header
- This blob is committed to git and is therefore visible to anyone with repository access
- The DPAPI encryption is keyed to the Windows user account that last saved the file (`WIRECARD\david.tran` on the project creator's machine)

**Immediate actions required:**
1. Rotate the `rc_contact_log_user` password on `alchemy-srv-dev.database.windows.net` immediately
2. Remove the credential from the `.conmgr` file and replace with a placeholder
3. Store the credential in the SSIS catalog as a sensitive environment variable, or migrate to Azure AD Managed Identity
4. Scan git history to ensure the credential has not been exposed in earlier commits (use `git log --all -p -- ETL/alchemy-srv-dev.conmgr`)
5. Report to the Security team per PCI DSS Requirement 6.3.3 incident response procedures

**PCI DSS violation:** This constitutes a violation of:
- **PCI DSS Req 2.2.7** — All non-console administrative access must be encrypted
- **PCI DSS Req 6.3.3** — All software components are protected from known vulnerabilities; credentials must not be in code
- **PCI DSS Req 8.3** — Strong cryptography for all non-console access credentials

---

### VULNERABILITY 2: Hardcoded File Path with Month/Year Timestamp

**File:** `StarSf.dtsx`, line 29
```
C:\ETL\In\STARsf\STARSf_10_2020.XLSX
```

**Severity: Medium**
Requires manual update each month. Operator error risk — package may silently process stale data.

---

### VULNERABILITY 3: Unencrypted SMTP with `Persist Security Info=True`

**File:** `StarSf.dtsx` (SMTP connection manager, line 41–43)
```
SmtpServer=smtp.nam.wirecard.sys;UseWindowsAuthentication=False;EnableSsl=False;
```

**Severity: Medium**
Email notifications sent without encryption or authentication. The connection string `Persist Security Info=True` on the Azure SQL connection means credentials could be extracted from connection objects at runtime.

---

### VULNERABILITY 4: Azure SQL via SQLNCLI11 — Deprecated Driver

**File:** `alchemy-srv-dev.conmgr`, line 8
```
Provider=SQLNCLI11.1;
```

SQLNCLI11 is deprecated by Microsoft for Azure SQL Database connections. It does not support all modern Azure SQL features and may not receive security patches. The recommended driver is ODBC Driver 18 for SQL Server.

**Severity: Medium**

---

### VULNERABILITY 5: `Persist Security Info=True` on Azure SQL Connection

**File:** `alchemy-srv-dev.conmgr`, line 8

Setting `Persist Security Info=True` allows the connection object to expose the password after the connection is established. Combined with a committed DPAPI blob, this increases the effective exposure of the credential.

**Severity: Medium** (compounding factor with Vulnerability 1)

---

## Technical Debt

| Item | Severity |
|---|---|
| SQL auth password in git (Azure SQL) | Critical |
| 556 KB FDR import package — unreviewed for PCI compliance | High |
| Hardcoded file path with month/year | High |
| Stale Northlane email addresses in package parameters | Medium |
| SQLNCLI11 for Azure SQL (deprecated) | Medium |
| No CI/CD | High |
| Unencrypted SMTP | Medium |
| No TLS on any SQL connections | High |
| Manual monthly file update required for StarSf | High (operational) |

---

## Remediation Priority

| Priority | Action |
|---|---|
| 1 (Critical) | Immediately rotate `rc_contact_log_user` password on Azure SQL; remove credential from git |
| 2 (Critical) | Audit `FDR_Import_DD031.dtsx` for PAN data handling and PCI DSS compliance |
| 3 (High) | Replace hardcoded `STARSf_10_2020.XLSX` path with dynamic date expression |
| 4 (High) | Update Northlane email addresses (`@northlane.com`) to current Onbe addresses |
| 5 (High) | Migrate Azure SQL connection from SQLNCLI11 + SQL Auth to ODBC Driver 18 + Azure AD Managed Identity |
| 6 (High) | Add `Encrypt=True;TrustServerCertificate=False;` to all on-premise SQL connections |
| 7 (Medium) | Enable SMTP TLS (`EnableSsl=True`) for email notifications |
| 8 (Medium) | Implement CI/CD pipeline |
| 9 (Low) | Remove `Persist Security Info=True` from Azure SQL connection string |
