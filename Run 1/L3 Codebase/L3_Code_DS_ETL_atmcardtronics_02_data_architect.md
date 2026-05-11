# Data Architect Report — DS_ETL_atmcardtronics

## Repository Identity

**Repository:** DS_ETL_atmcardtronics  
**SSIS Version:** 11.0.7001.0 (SQL Server 2012 SP4 CU equivalent)  
**Protection Level:** `EncryptSensitiveWithUserKey` (project-level)  
**Destination Database:** `cf_report` on `q-db03.nam.wirecard.sys\db03,2232`

---

## Connection Manager Inventory

### Project-Level Connection Manager

| Name | Type | Connection String | Authentication |
|---|---|---|---|
| `CF_Report` | OLE DB (OLEDB) | `Data Source=q-db03.nam.wirecard.sys\db03,2232;Initial Catalog=cf_report;Provider=SQLNCLI11.1;Integrated Security=SSPI;Auto Translate=False;` | Windows Integrated (`SSPI`) — no embedded password |

**Source:** `ATMCardtronics/CF_Report.conmgr`, line 9; `ATMCardtronics.dtproj` lines 52–65

The server name `q-db03.nam.wirecard.sys` uses the legacy `wirecard.sys` DNS suffix, indicating this connection points to the QA/production environment that retains the Wirecard-era naming. Port `2232` is a non-default SQL Server port (default is 1433), suggesting the named instance uses a custom port.

### Package-Level Connection Managers

Each package defines its own local connection managers for source flat files. Examples from `ATMCardtronics_DailyDispense.dtsx`:

| Connection Name | Type | Connection String (Design-Time) | Notes |
|---|---|---|---|
| `CSV Source` | FLATFILE | `C:\ETL\In\WirecardDispenseDetail2019092009171031.csv` | Runtime path overridden by `@[User::source_full_name]` |

From `ATMCardtronics_TACTDIST_Import.dtsx`:

| Connection Name | Type | Connection String (Design-Time) | Notes |
|---|---|---|---|
| `Activity Excel File` | EXCEL (ACE.OLEDB.12.0) | `C:\ETL\In\Cardtronics\WirecardATM_FISSettlementBalancing2018_11_14_100303.xlsx` | Runtime path: `@[User::dest_full_name]` |
| `TACTDIST File` | FLATFILE | `C:\ETL\In\D181114.CCSXIFSA11151022.TACTDIST` | Runtime path: `@[User::source_full_name]` |
| `SMTP Connection Manager` | SMTP | `SmtpServer=nl-smtp-01.nam.wirecard.sys;UseWindowsAuthentication=False;EnableSsl=False;` | No TLS |

---

## SSIS Package Inventory and Data Flow Mappings

### ATMCardtronics_DailyDispense.dtsx
- **Source:** CSV flat file from Cardtronics (`WirecardDispenseDetail*.csv`)
- **Destination:** `cf_report` database (specific table not captured in header)
- **Key columns processed:** TID, Currency, sod_balance, disp_before_replen, END_Residual, load_amt, disp_after_replen, EOD_balance, total_20, total_50, total_100, total_disp
- **Format:** Comma-delimited, text-qualified, UTF-8/1252 code page, header row present

### ATMCardtronics_DispenseDetail.dtsx (349 KB — largest package)
- **Source:** Detailed dispense records CSV
- **Destination:** `cf_report` (likely a detail dispense table with transaction-level records)
- **Notes:** Largest package suggests complex transformation logic or wide column set

### ATMCardtronics_TACTDIST_Import.dtsx (393 KB — second largest)
- **Source:** TACTDIST flat file (`D*.CCSXIFSA*.TACTDIST` format) + FIS Settlement Excel file
- **Destination:** `cf_report` (settlement/reconciliation tables)
- **Notes:** Uses Microsoft ACE OLEDB 12.0 for Excel source — requires 32-bit ACE driver or 64-bit ACE driver installed on the SSIS server

### ATMCardtronics_Replenishment.dtsx
- **Source:** Replenishment data CSV
- **Destination:** `cf_report` (ATM replenishment event table)

### ATMCardtronics_Interchange.dtsx (87 KB — smallest processing package)
- **Source:** Interchange fee settlement file
- **Destination:** `cf_report` (interchange fee table)

### ATMCardtronics_Surcharge.dtsx
- **Source:** Surcharge data
- **Destination:** `cf_report` (surcharge fee table)

### ATMCardtronics_ElectronicJournal.dtsx
- **Source:** ATM electronic journal records
- **Destination:** `cf_report` (electronic journal/audit table)
- **Regulatory note:** This data is required for Reg E dispute investigations

### ATMCardtronics_SwitchBalance.dtsx
- **Source:** Switch balance data
- **Destination:** `cf_report` (switch balance table)

### ATMCardtronics_DailyRpt.dtsx
- **Source:** Daily report file
- **Destination:** `cf_report` (daily summary table)

### ATMCardtronics_DevicePerformance.dtsx
- **Source:** Device performance metrics
- **Destination:** `cf_report` (device performance table)

### ATMCardtronics_PartnerMonthlyAcctStat.dtsx
- **Source:** Monthly account statement from partner
- **Destination:** `cf_report` (monthly statement table)

### ATMCardtronics_AdjustmentEmail.dtsx (99 KB)
- **Source:** `cf_report` database (reads adjustment data)
- **Destination:** Email via SMTP
- **Flow direction:** INVERSE — this package reads from the database and sends email notifications

---

## Project Parameters

| Parameter | Value | Sensitive | Purpose |
|---|---|---|---|
| `SourcePath` | `C:\ETL\In\` | No | Flat file source directory |
| `DestinationPath` | `C:\ETL\In\Cardtronics\` | No | Processed file staging |
| `EmailTo` | `van.nguyen2@northlane.com` | No | Adjustment email recipient |
| `SMTPServer` | `nl-smtp-01.nam.wirecard.sys` | No | SMTP relay server |
| `EmailCC` | `van.nguyen2@northlane.com` | No | Email CC |
| `ArchiveFolder` | `C:\ETL\In\CardtronicsArchive\` | No | Processed file archive |
| `EmailFrom` | `noreply@northlane.com` | No | Email sender address |

**Source:** `ATMCardtronics/Project.params`, lines 1–150

---

## Protection Level — CRITICAL FLAG

```xml
<SSIS:Project SSIS:ProtectionLevel="EncryptSensitiveWithUserKey">
```
**Source:** `ATMCardtronics.dtproj`, line 15

`EncryptSensitiveWithUserKey` is the default SSIS protection level and is **not suitable for server deployment**. This protection level encrypts sensitive values using the Windows DPAPI key of the user who saved the package. When deployed to a SQL Server Agent or SSIS Catalog on a server, the decryption key is unavailable and the package will:
- Fail to load sensitive connection string values
- Execute with NULL/blank values for sensitive parameters
- Produce cryptic errors at runtime that do not clearly identify the root cause

**However:** The CF_Report connection manager uses `Integrated Security=SSPI` (Windows Authentication), so no password is stored as sensitive in that connection. The `PasswordVerifier` property in the project file (`ATMCardtronics.dtproj`, line 29) stores a DPAPI-encrypted value — this is the project-level password verifier used internally by SSIS and does not represent a functional secret exposure.

**The net risk:** `EncryptSensitiveWithUserKey` creates deployment complexity but the actual sensitive data exposure is low because no SQL passwords are embedded in these connections. The risk increases if any package-level SQL connections with passwords were added in the future without changing the protection level.

---

## Sensitive Data Assessment

| Data Element | Source File | PCI/Regulatory Flag |
|---|---|---|
| Terminal ID (TID) | All dispense/ATM packages | Card-network terminal identifier — maps to cardholder access points. Not a PAN. |
| Settlement amounts (interchange, surcharge) | Interchange.dtsx, Surcharge.dtsx | Financial settlement data — GLBA |
| Electronic journal records | ElectronicJournal.dtsx | ATM transaction audit trail — Reg E relevant |
| TACTDIST settlement data | TACTDIST_Import.dtsx | Card network settlement — PCI DSS scope adjacent |
| Email addresses (admin) | Project.params | Personal data (GDPR/CCPA) — staff email addresses in configuration |

**No PAN (Primary Account Number), CVV, or PIN data is identifiable in the flat file column definitions reviewed.** The dispense data contains terminal-level aggregates, not cardholder-level transaction data. However, the full column mappings for all 13 packages were not fully read — a complete PAN/SAD audit of all package data flows is recommended.
