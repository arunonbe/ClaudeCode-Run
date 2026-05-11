# Data Architect View — DS_ETL_finance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance`
**SSIS Project format:** Project Deployment Model
**Protection level:** `EncryptSensitiveWithUserKey` (Finance.dtproj line 15)

---

## Source Databases / Systems

| Connection Manager | Database | Server | Provider | Auth | Used By |
|---|---|---|---|---|---|
| `Atlys_FcCR` | `ATLYS_FcCR` | `d-na-db02.nam.wirecard.sys\db02,2232` | OLEDB (`SQLNCLI11.1`) | Windows SSPI | Atlys_RfCks, Atlys_recalc |
| `Atlys_RvCR` | `ATLYS_RvCR` | `d-na-db02.nam.wirecard.sys\db02,2232` | OLEDB (`SQLNCLI11.1`) | Windows SSPI | Atlys_RfCks, Cambridge_Recon |
| `ATLYS_RvCR_DotNet` | `ATLYS_RvCR` | `d-na-db02.nam.wirecard.sys\db02,2232` | ADO.NET (SqlClient) | Windows Integrated | Salesforce_Update |
| `cf_report` | `cf_report` | `q-db03.nam.wirecard.sys\db03,2232` | OLEDB (`SQLNCLI11.1`) | Windows SSPI | MonthEnd_*, NegativeBalance, Export_GP |

**Key observation:** Two separate connection managers point to `ATLYS_RvCR` — one OLEDB (`Atlys_RvCR.conmgr`) and one ADO.NET (`ATLYS_RvCR_DotNet.conmgr`). This is a common SSIS pattern when different tasks need different provider semantics (e.g., OLEDB for Data Flow Sources, ADO.NET for Execute SQL Tasks using SqlCommand).

---

## Target Systems

| Target | Type | Format | Location |
|---|---|---|---|
| `\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\` | UNC File Share | Pipe-delimited CSV | MonthEnd balance output files |
| Great Plains ERP | Downstream (via Export_GP_CCP_PBR) | TBD — likely staged table or file | Export_GP_CCP_PBR.dtsx |
| Salesforce CRM | REST API / HTTP | JSON or proprietary | Salesforce_Update_Atlys_Forecast.dtsx |

---

## SSIS Package Inventory

### Package: `MonthEnd_NegativeBalance.dtsx` (307,872 bytes)

**Largest package in the project.** Contains the full month-end negative balance extraction pipeline.

**Connection Managers:**
- `cf_report` (OLEDB) — source of balance data
- Flat file connection — target CSV on `\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\`

**Data Flow Columns (from MonthEnd_NonZeroBalance.dtsx as proxy):**

| Column | Type | Width | Sensitive Flag |
|---|---|---|---|
| `Account Number` | String | 30 chars | **FLAG — potential PAN/account identifier** |
| `Balance` | Decimal | 18,2 | Financial amount |
| `Balance EffectiveDate` | DateTime | — | Date |

**Business rule:** Separate executions per `Bank` parameter (Sunrise, Peoples, MB Financial) and per `Product` (US=4, Canada=6).

---

### Package: `MonthEnd_NonZeroBalance.dtsx` (26,661 bytes)

**Connection Managers:**
- `Monthend_NonZero` — FLATFILE target, path expression: `@[User::DestinationFolder] + @[User::FileName] + ".csv"` (dtsx line 25)
- Default path: `\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\MonthlyBalance_20210128.csv`

**Parameters:** `Bank`, `MonthEndStoredProcedure`, `Product` (US/Canada)

---

### Package: `MonthEnd_PositiveBalance.dtsx` (24,353 bytes)

Structural twin of `MonthEnd_NonZeroBalance` for positive-balance accounts. Same file schema, same parameter set.

---

### Package: `NegativeBalance_Snaphot.dtsx` (3,682 bytes)

**Simple Execute SQL Task package.**

**Connection Manager used:** `cf_report` (resolved via `{716D5232-23D2-449D-97DB-36B5B98EA5EF}` — cf_report.conmgr DTSID, dtsx line 44)

**SQL called:**
```sql
EXEC [dbo].[usp_rpt_negative_balance_monthly_snapshot] @MonthsToKeep = ?
```
(dtsx line 45)

**Parameter binding:** `$Package::MonthsToKeep` → `@MonthsToKeep` (Int32, Input)

---

### Package: `Cambridge_ReconFile.dtsx` (113,008 bytes)

Cambridge is a banking partner for cross-border payments and ACH services. This package generates the reconciliation file comparing Onbe transaction records against Cambridge's settlement records.

**Likely data flow:**
- Source: `cf_report` or `ATLYS_RvCR` database (transaction records)
- Transform: Format to Cambridge-expected layout; flag discrepancies
- Target: Flat file sent to Cambridge via SFTP (SFTP task likely present in full package body not yet inspected)

---

### Package: `Atlys_RfCks.dtsx` (122,947 bytes)

**Atlys Reverse/Refund Fee Checks.** Second-largest package.

**Connection Managers:** `Atlys_FcCR` (OLEDB) and `Atlys_RvCR` (OLEDB) — both Atlys programme databases.

This package likely reads fee charge records from `ATLYS_FcCR` and revenue reconciliation records from `ATLYS_RvCR`, computes reversals or verifications, and writes results back or exports them.

---

### Package: `Export_GP_CCP_PBR.dtsx` (71,947 bytes)

Extracts pre-billing reconciliation data and exports it to Great Plains format or staging for GP import.

**Source:** `cf_report` database
**Target:** Likely a file on `\\d-na-stk01.nam.wirecard.sys\GP_Files\` (shared GP file drop location, seen in finance-gp repo)

---

### Package: `Salesforce_Update_Atlys_Forecast.dtsx` (73,425 bytes)

**CRM integration package.** Reads Atlys forecast data from `ATLYS_RvCR` via the ADO.NET connection manager (`ATLYS_RvCR_DotNet`) and pushes it to Salesforce.

**Connection Manager:** `ATLYS_RvCR_DotNet` — ADO.NET, `d-na-db02.nam.wirecard.sys\db02,2232`, Windows Integrated Security.

**Salesforce connectivity:** Likely via an SSIS custom component (Salesforce connector) or a Script Task using the Salesforce REST API or Bulk API. Salesforce credentials are likely stored as package parameters (not visible in the .dtproj connection manager section — may be embedded in the package Script Task body).

---

### Package: `Atlys_recalc_forecast.dtsx` (5,041 bytes)

Small package — likely a single Execute SQL Task calling a stored procedure to recalculate forecast figures on the `ATLYS_FcCR` or `ATLYS_RvCR` database.

---

### Package: `Monthly_Account_Balance.dtsx` (672 bytes — STUB)

Empty package. No data flow or control flow tasks defined. Created 2021-01-21. Likely a placeholder for future development.

---

## Project-Level Parameters (`Project.params`)

| Parameter | Value | Purpose |
|---|---|---|
| `DBServer` | `Q-DB03.NAM.WIRECARD.SYS\DB03,2232` | Primary database server |
| `DBServer_ECNT` | `Q-DB04.NAM.WIRECARD.SYS\DB03,2232` | Secondary server (ECNT databases) |
| `DestinationFolder` | `\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\` | File output share |
| `SMTPServer` | `nl-smtp-01.nam.wirecard.sys` | Email notification server |

---

## Sensitive Data Assessment

| Data Element | Package | Column/Field | PCI/Regulatory Concern |
|---|---|---|---|
| `Account Number` | MonthEnd_NonZeroBalance, MonthEnd_NegativeBalance, MonthEnd_PositiveBalance | Flat file column 1 | **HIGH — if PAN or truncated PAN: PCI DSS Req 3, 4** |
| `Balance` (decimal) | All MonthEnd packages | Flat file column 2 | Financial amount — GLBA, SOX |
| `Balance EffectiveDate` | All MonthEnd packages | Flat file column 3 | Date data |
| Salesforce API credentials | Salesforce_Update_Atlys_Forecast | (in Script Task or parameters) | Credentials in package — review for plaintext storage |

---

## Encryption in Transit

- All SQL Server connections use `Integrated Security=SSPI` (Windows auth) — no SQL passwords
- Connection strings do **not** include `Encrypt=True` — network-level TLS not enforced
- Flat files written to a UNC share — no file-level encryption visible in the packages
- SMTP server `nl-smtp-01.nam.wirecard.sys` — no TLS configuration visible for email notifications

**Risk:** Unencrypted flat files containing Account Numbers and Balances on a UNC network share. If the share is accessible from workstations or insufficiently ACL'd, this could constitute a PCI DSS violation (Requirement 3.4 — render PAN unreadable wherever stored; Requirement 4.2 — protect data in transit).

---

## Database Schema Notes

- `ATLYS_FcCR` = Atlys Fee Charge Reconciliation
- `ATLYS_RvCR` = Atlys Revenue Reconciliation
- `cf_report` = Client/Finance reporting database (cross-cutting reporting store)
- All databases reside on `d-na-db02` (ATLYS) or `q-db03` (cf_report) — two separate SQL Server instances within the `NAM.WIRECARD.SYS` domain
