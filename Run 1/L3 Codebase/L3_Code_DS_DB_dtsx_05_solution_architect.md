# DS_DB_dtsx — Solution Architect View

## Technical Debt Summary

This repository contains significant accumulated technical debt spanning security, operational, and architectural dimensions. The packages are built on SQL Server 2012 SSIS (end-of-life), use legacy file-based deployment, have no automated testing, and embed or externally store credentials in plaintext.

---

## All Objects — Names and Purpose

### PROD Packages

| Object Name | Type | Purpose |
|---|---|---|
| `AMLMantasETLNAM.dtsx` | SSIS Package | Extracts account, transaction, address, and customer data from EcountCore/Great Plains for AML Mantas feed. Contains 9,917+ lines of XML. Multi-container package with RunDailyProcess/Extract/Extract Data sub-containers. |
| `Daily_Reconciliation_Files.dtsx` | SSIS Package | Generates daily reconciliation files for Sunrise bank partner |
| `Daily_Reconciliation_Files_QA.dtsx` | SSIS Package | QA version of above |
| `BinBankETL.dtsx` | SSIS Package | Loads BIN-to-bank mapping reference data |
| `BinBankETL-old.dtsx` | SSIS Package | Legacy version — should be deleted |
| `FDR_Import_DD031.dtsx` | SSIS Package | Imports FDR DD031 settlement file into staging |
| `IVR_CallLogs.dtsx` | SSIS Package | Imports IVR call log data |
| `CITI_INV_HJRCPTS_File_Processor.dtsx` | SSIS Package | Citi hardware/inventory HJ receipts processor |
| `CITI_INV_HJVLM_File_Processor.dtsx` | SSIS Package | Citi HJ volume processor |
| `CITI_INV_PLASTDUD_File_Processor.dtsx` | SSIS Package | Citi plastic dud/defect file processor |
| `CITI_INV_PLASTICS_File_Processor.dtsx` | SSIS Package | Citi plastics inventory processor |
| `CITI_INV_PLASTPOS_File_Processor.dtsx` | SSIS Package | Citi POS plastics processor |
| `NAOT_Card_Ship_File_Processor.dtsx` | SSIS Package | Citi NAOT card shipping status file processor |
| `Fiserv_Card_Ship_File_Processor.dtsx` | SSIS Package | Fiserv card shipping status file processor |
| `Returned_Checks.dtsx` | SSIS Package | Extracts returned-check data from EcountCore to CSV. Connects to `p-db02.nam.wirecard.sys\db02.Ecountcore` and `.Ecountcore.report` using Integrated Security (SSPI) |

### QA-Only Packages

| Object Name | Purpose |
|---|---|
| `AMLMantasETL.dtsx` | QA baseline AML Mantas ETL |
| `AMLMantasETLNAMPAT.dtsx` | PAT environment AML ETL |
| `AMLMantasETLNAMUAT.dtsx` | UAT environment AML ETL |
| `BinBankETL_old.dtsx` | Legacy BinBank ETL (QA) |

### Configuration Files

| Object Name | Purpose |
|---|---|
| `Mantas_NAM_UAT.dtsConfig` | External config for UAT AMLMantasETLNAM — contains **plaintext credentials** |
| `Mantas_NAM_UAT_backup.dtsConfig` | Backup copy — also contains **plaintext credentials** |

---

## Security Vulnerabilities — Detailed

### CRITICAL: Plaintext Password in Git Repository

**File**: `QA/q-na-bat03/c-base/runtime/ndmroot/SSIS/Mantas_NAM_UAT.dtsConfig`
**Location**: XML element `<ConfiguredValue>` for `DomesticReporting`, `DYNAMICS`, `GPCompanies`, `Reporting` connections
**Credential exposed**: Username `report`, Password `[REDACTED — rotate immediately]`
**Servers exposed**:
- `ppamwdcPDsql4A1\ppamwdcPDsql4A1` → `Ecountcore_Process_SS`
- `ppamwdcPIsql3A1\ppamwdcPIsql3A1` → `DYNAMICS`, `ecnt`
- `PPAMWDCUDSQL1C1\PPAMWDCUDSQL1C1` → `cf_report`

**Impact**: Anyone with repository access (any GitLab user in the `northlane/development/data-services/databases` group) can authenticate to these SQL Server instances with the `report` credentials. The `report` login connects to `Ecountcore_Process_SS` which is a CDE database.

**Remediation**: Immediately rotate the `report` SQL login password on all affected servers. Remove the `.dtsConfig` files from Git history (BFG Repo Cleaner). Migrate credential storage to Windows Credential Manager or Azure Key Vault.

**PCI DSS Mapping**: Requirement 8.3.6 (passwords/passphrases must not be stored in scripts, batch files, or configuration files in cleartext).

---

### CRITICAL: CVV Stored in Database Table

**File**: `E:\OnbeEast363\repos\DS_DB_ecountcore_process\dbo\Tables\fdr_process_dd031_data.sql` — column `[cvv] VARCHAR(3)`
**Context**: The `FDR_Import_DD031.dtsx` package ingests FDR settlement files containing a CVV field, which is then written to the `fdr_process_dd031_data` table.
**PCI DSS Mapping**: Requirement 3.3.1 — Sensitive Authentication Data (SAD) must not be stored after authorisation. CVV is explicitly listed as SAD. Storage after authorisation is prohibited even if encrypted.
**Remediation**: The CVV column must be removed from `fdr_process_dd031_data`. The SSIS import procedure should null/blank this field before INSERT.

---

### HIGH: Hardcoded Development File Paths

**Location**: All `.dtsx` packages, flat file connection managers
**Example**: `DTS:ConnectionString="C:\Project\Development\SSIS\Mantas\output\TestData\Account_20130710_EMEAPPDLY_1.dat"` (`AMLMantasETLNAM.dtsx`, line 37)
**Impact**: If the `.dtsConfig` file fails to load or is absent, the package would attempt to read/write developer workstation paths that do not exist on the batch server. Silent data quality failures.
**Remediation**: Use SSIS environment variables or project parameters. Remove hardcoded dev paths.

---

### HIGH: SMTP Without SSL

**Location**: `Returned_Checks.dtsx`, connection manager `mail.Wirecard.com`
**Value**: `SmtpServer=smtp.nam.wirecard.sys;UseWindowsAuthentication=True;EnableSsl=False`
**Impact**: Alert email content transmitted in cleartext on network. Email may contain financial or operational data.
**Remediation**: Enable SSL/TLS (`EnableSsl=True`).

---

### HIGH: Stale Domain References

**All packages** reference `*.wirecard.sys` and `*.nam.wirecard.sys` domains. Server aliases include `p-db02`, `p-db06`, `p-db08`, `q-db02`, `ppamwdcPDsql4A1`, `ppamwdcPIsql3A1`. These are Wirecard-era hostnames. A DNS inventory audit is required to confirm these are still valid or have been aliased.

---

### MEDIUM: "Primary Customer Account Password" in AML Feed

**Location**: `AMLMantasETLNAM.dtsx`, column mapping in AccountFileExtract component (lines 765, 7382–9920)
**Issue**: A column named `Primary Customer Account Password` is mapped from the source stored procedure (`uspAMLAccountExtract`) to the Mantas output file. This field name suggests customer authentication credentials may be flowing to the AML flat file.
**Remediation**: Audit what data this field actually contains. If it is a customer PIN or online password, this is a critical PCI/security violation requiring immediate remediation.

---

### MEDIUM: No Parameterisation — SQL Injection Not Applicable (ETL Context)

SSIS OLE DB Sources use stored procedure calls and direct SQL — no user-supplied dynamic SQL is constructed in the packages themselves. SQL injection is not a vector here, but the stored procedures called (e.g., `uspAMLAccountExtract`) should be audited separately in the `Ecountcore_Process_SS` database.

---

## Remediation Priority Matrix

| Priority | Finding | Action |
|---|---|---|
| P0 — Immediate | Plaintext password `[REDACTED — rotate immediately]` in `.dtsConfig` committed to Git | Rotate credential; remove from Git history; deploy secrets manager |
| P0 — Immediate | CVV column in `fdr_process_dd031_data` (written by FDR_Import_DD031.dtsx) | Remove CVV column from table; null field in SSIS before write |
| P1 — Within 30 days | `Primary Customer Account Password` field in AML Mantas feed | Audit field content; mask or remove if sensitive |
| P1 — Within 30 days | SMTP without SSL in Returned_Checks.dtsx | Enable TLS |
| P2 — Within 90 days | SSIS 2012 (end of life) | Plan migration to SSIS 2019 or Azure Data Factory |
| P2 — Within 90 days | Manual deployment process | Implement GitLab CI/CD pipeline with deployment stages |
| P3 — Within 180 days | Hardcoded dev paths in connection managers | Parameterise all file paths via SSIS environment variables |
| P3 — Within 180 days | Stale Wirecard domain references | Validate/update all server names and DNS aliases |
| P3 — Within 180 days | Shared `report` login across all packages | Create per-package service accounts with least-privilege permissions |
