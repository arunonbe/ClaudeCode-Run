# Solution Architect View — DS_ETL_finance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance`
**Package count:** 9 (8 active, 1 stub)
**Connection managers (project-level):** 4
**Protection level:** `EncryptSensitiveWithUserKey`

---

## Complete Object / Package Inventory

### SSIS Packages

| Package | Size (bytes) | Purpose | Key Connections |
|---|---|---|---|
| `MonthEnd_NegativeBalance.dtsx` | 307,872 | Month-end negative balance extraction per bank/product | `cf_report` → CSV flat file |
| `MonthEnd_NonZeroBalance.dtsx` | 26,661 | Month-end non-zero balances extraction | `cf_report` → CSV flat file |
| `MonthEnd_PositiveBalance.dtsx` | 24,353 | Month-end positive balances extraction | `cf_report` → CSV flat file |
| `NegativeBalance_Snaphot.dtsx` | 3,682 | Rolling 12-month negative balance snapshot | `cf_report` (Execute SQL) |
| `Cambridge_ReconFile.dtsx` | 113,008 | Cambridge bank reconciliation file generation | `cf_report`/ATLYS → file |
| `Atlys_RfCks.dtsx` | 122,947 | Atlys reverse/refund fee checks | `ATLYS_FcCR`, `ATLYS_RvCR` |
| `Export_GP_CCP_PBR.dtsx` | 71,947 | GP/CCP pre-billing reconciliation export | `cf_report` → GP files |
| `Atlys_recalc_forecast.dtsx` | 5,041 | Atlys forecast recalculation trigger | `ATLYS_FcCR` or `ATLYS_RvCR` |
| `Salesforce_Update_Atlys_Forecast.dtsx` | 73,425 | Push Atlys forecasts to Salesforce CRM | `ATLYS_RvCR_DotNet` → Salesforce |
| `Monthly_Account_Balance.dtsx` | 672 | **STUB — empty package** | None |

---

## Connection Manager Inventory

### Project-Level Connection Managers

| File | Object Name | DTSID | Type | Server | Database | Auth | Sensitive |
|---|---|---|---|---|---|---|---|
| `Atlys_FcCR.conmgr` | `Atlys_FcCR` | `{27C6B569-72E2-4CDD-A809-D2E4DA58B389}` | OLEDB (SQLNCLI11.1) | `d-na-db02.nam.wirecard.sys\db02,2232` | `ATLYS_FcCR` | Windows SSPI | No |
| `Atlys_RvCR.conmgr` | `Atlys_RvCR` | (inferred) | OLEDB (SQLNCLI11.1) | `d-na-db02.nam.wirecard.sys\db02,2232` | `ATLYS_RvCR` | Windows SSPI | No |
| `ATLYS_RvCR_DotNet.conmgr` | `ATLYS_RvCR_DotNet` | `{8B0B0F19-2E34-4602-9A23-660DC8F406A5}` | ADO.NET SqlClient | `d-na-db02.nam.wirecard.sys\db02,2232` | `ATLYS_RvCR` | Windows Integrated | No |
| `cf_report.conmgr` | `cf_report` | `{716D5232-23D2-449D-97DB-36B5B98EA5EF}` | OLEDB (SQLNCLI11.1) | `q-db03.nam.wirecard.sys\db03,2232` | `cf_report` | Windows SSPI | No |

---

## Security Vulnerabilities

### 1. Unencrypted Account Number Data in Flat Files

**File:** `MonthEnd_NonZeroBalance.dtsx`, line 44 — `Account Number` column
**File:** `MonthEnd_NegativeBalance.dtsx` (same schema inferred)
**Output location:** `\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\`

**Severity: HIGH**
The `Account Number` field is written to unencrypted pipe-delimited CSV files on a UNC network share. If these account numbers represent cardholder account numbers, full or partial PANs, or ACH account numbers, this violates:
- **PCI DSS Requirement 3.4** — render PAN unreadable wherever stored
- **PCI DSS Requirement 4.2** — protect data during transmission over open/public networks
- **GLBA Safeguarding Rules** — protect non-public personal financial information

**Remediation:** Verify whether `Account Number` is a PAN or truncated PAN. If so, apply AES-256 encryption to the output file, or replace with masked values (first 6/last 4). Implement access controls on the UNC share.

### 2. `EncryptSensitiveWithUserKey` Protection Level

**File:** `Finance.dtproj`, line 15
**PasswordVerifier blob:** `Finance.dtproj` line 29

Same DPAPI issue as in DS_ETL_database-maintenance. The `CM.Atlys_FcCR.Password` parameter (Finance.dtproj line 81, `Sensitive=1`) is DPAPI-protected to the developer's key.

**Severity: Medium**
**Remediation:** Switch to SSIS catalog–managed sensitive parameters.

### 3. Hardcoded Development/QA Server Hostnames

**Files:** `Atlys_FcCR.conmgr` (line 8), `ATLYS_RvCR_DotNet.conmgr` (line 8), `cf_report.conmgr` (line 8)

Connection strings embed `d-na-db02.nam.wirecard.sys` (dev) and `q-db03.nam.wirecard.sys` (QA) server names, committed to git.

**Severity: Low-Medium**
These hostnames are internal and not publicly exposed, but committing environment-specific server names to source control makes environment isolation harder and leaks infrastructure naming conventions.

**Remediation:** Use SSIS catalog environment variable bindings for all connection string parameters.

### 4. No TLS Enforcement on SQL Connections

All connection strings use `Integrated Security=SSPI` without `Encrypt=True`.

**Severity: Medium** (especially for connections that carry financial amounts and account numbers)

### 5. Potential Salesforce API Credential Exposure

**File:** `Salesforce_Update_Atlys_Forecast.dtsx`

Salesforce connections require OAuth tokens or username/password/security token. If these are stored in Script Task source code or hardcoded in package variables, they would constitute a credentials-in-code violation. The full Script Task body of this 73 KB package requires inspection.

**Severity: HIGH (pending full inspection)**
**Remediation:** Store Salesforce credentials in SSIS catalog sensitive parameters, Azure Key Vault, or Windows Credential Manager — not in the package body.

---

## Technical Debt

| Item | Severity | Notes |
|---|---|---|
| Empty stub package committed (`Monthly_Account_Balance`) | Medium | Dead code in production repo; confusing for operators and engineers |
| Visual Studio 2010 solution format | Medium | Upgrade to VS 2019/2022 SSDT required |
| Mixed SSIS versions (2012 + 2017 packages in same project) | Medium | Consistency risk; 2017-format package may behave differently in 2012 catalog |
| No CI/CD | High | Manual deployments, no regression testing |
| Unencrypted financial flat file output | High | PCI/GLBA risk if Account Numbers are cardholder identifiers |
| Duplicate connection managers for ATLYS_RvCR | Low | `Atlys_RvCR.conmgr` (OLEDB) and `ATLYS_RvCR_DotNet.conmgr` (ADO.NET) — acceptable SSIS pattern but adds maintenance overhead |
| No file cleanup/archival in packages | Medium | CSV files accumulate on the UNC share indefinitely |

---

## Remediation Priority

| Priority | Action |
|---|---|
| 1 (Critical) | Audit `Account Number` field: confirm PAN/non-PAN status; apply encryption or masking if PAN |
| 2 (Critical) | Inspect Salesforce_Update_Atlys_Forecast.dtsx Script Task body for embedded credentials |
| 3 (High) | Implement CI/CD pipeline with automated `.ispac` build and environment-parameterised deployment |
| 4 (High) | Add file encryption for flat file outputs containing financial data |
| 5 (Medium) | Replace `EncryptSensitiveWithUserKey` with SSIS catalog environment variable sensitivity |
| 6 (Medium) | Remove or promote the `Monthly_Account_Balance.dtsx` stub to avoid operational confusion |
| 7 (Medium) | Add `Encrypt=True` to all connection strings |
| 8 (Low) | Upgrade solution to VS 2019/2022 SSDT |
