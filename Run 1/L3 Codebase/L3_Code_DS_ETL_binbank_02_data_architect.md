# Data Architect Report — DS_ETL_binbank

## Repository Identity

**Repository:** DS_ETL_binbank  
**SSIS Version:** 11.0.7001.0 (SQL Server 2012)  
**Protection Level:** `EncryptSensitiveWithUserKey` (project-level)  
**Source/Destination Database:** `cf_report` on `qc-az-db03.nam.wirecard.sys\qi_db03`

---

## Connection Manager Inventory

### Project-Level Connection Manager

| Name | Type | Connection String | Authentication |
|---|---|---|---|
| `cf_report` | OLE DB (OLEDB) | `Data Source=qc-az-db03.nam.wirecard.sys\qi_db03;Initial Catalog=cf_report;Provider=SQLNCLI11.1;Integrated Security=SSPI;Auto Translate=False;` | Windows Integrated (SSPI) |

**Source:** `cf_report.conmgr`, line 9; `BINBANK.dtproj` lines 55–56

Note: The server is `qc-az-db03` (QC prefix — this is a QC/staging environment reference, not production). The production equivalent would likely be `pc-az-db03` or similar. However, this design-time path may be overridden by SSIS Catalog environment parameters at deployment. Named instance: `qi_db03`.

**CRITICAL FLAG — Password Parameter Present:**  
In `BINBANK.dtproj` line 74, a `CM.cf_report.Password` project parameter exists. This suggests the `cf_report` connection has a password-bearing configuration option in the project, even though the design-time connection uses Windows Authentication. This may indicate a mixed-authentication deployment in some environments, or may be a residual parameter. The value itself is not visible (it would be encrypted under `EncryptSensitiveWithUserKey`).

---

## NACHA File Structure — Data Architecture

NACHA files are 94-character fixed-width records. The pipeline generates files with this structure:

### NACHA File Connection (from `nacha_print_file.dtsx`)

**NACHA File:**  
Path: `C:\ETL\Out\FifthThird\temp\53-ach-daily-recon<timestamp>.txt`  
Format: Single column "Column", row-delimited — each row is one 94-character NACHA record

**EFA (Early Funding Arrangement) File:**  
Path: `C:\ETL\Out\FifthThird\temp\EFA53-ach-daily-recon<timestamp>.txt`  
Format: Same single-column flat file structure

### NACHA Record Content (Field-Level)

A standard NACHA file contains the following sensitive record types:
| Record Type | Code | Contains |
|---|---|---|
| File Header | 1 | Immediate Destination (bank routing), Immediate Origin, file creation date/time |
| Batch Header | 5 | Company name, Company ID, Service Class Code, Originator (routing number) |
| Entry Detail | 6 | **Routing number (9 digits)**, **Account number (up to 17 digits)**, Transaction Code, Amount, Individual Name |
| Entry Addenda | 7 | Additional payment information |
| Batch Control | 8 | Entry count, total debit/credit amounts |
| File Control | 9 | Block count, batch count, total amounts |

**The Entry Detail records (Type 6) contain routing and account numbers, which are sensitive financial data.** Under NACHA Operating Rules and GLBA, this data must be:
- Transmitted securely to the bank (encrypted SFTP or direct connectivity)
- Stored securely (access-controlled, potentially encrypted)
- Retained per regulatory schedule
- Purged when no longer required

---

## Source Database — cf_report Objects (Inferred)

Based on package variables and the NACHA processing logic, the following `cf_report` objects are used by the BINBANK pipeline:

| Object (Inferred) | Type | Purpose |
|---|---|---|
| NACHA configuration table | Table | `nacha_configurations` variable — stores bank-specific NACHA parameters (routing numbers, batch configs) |
| NACHA file queue table | Table | `queued_files` variable — staging table for files pending processing |
| `status_id` tracking table | Table | Processing status tracking for NACHA file generation |
| `file_id` reference | Integer key | Identifies the specific NACHA file being processed |
| Program balance tables | Tables | Used by `program_balance_by_bank.dtsx` |
| Transaction code tables | Tables | Used by `sunrise_transaction_code_export.dtsx` |

The full schema of `cf_report` is not defined in this repository (it is defined in `DS_DB_cf_report` or equivalent). The BINBANK packages consume existing `cf_report` tables.

---

## SSIS Variable Architecture (nacha_file_process.dtsx)

The NACHA processing package uses several complex variables:

| Variable | Data Type | Sensitivity | Purpose |
|---|---|---|---|
| `file_id` | Integer (3) | No | Current NACHA file identifier |
| `missing_config_count` | Integer (3) | No | Count of missing bank configurations |
| `nacha_configurations` | ManagedSerializable (13) | **Yes** | Serialised list of bank configs — may contain routing numbers and account numbers |
| `queued_files` | ManagedSerializable (13) | **Yes** | List of files queued for processing — may contain file metadata with financial identifiers |
| `source_load_count` | Integer (3) | No | Source record count |
| `status_id` | Integer | No | Processing status |

**The `nacha_configurations` variable uses SOAP-serialised ManagedSerializable objects** (DataType 13), meaning it stores .NET objects serialised to XML inside the SSIS package. These objects likely contain bank routing numbers, company IDs, and ACH network identifiers. This data would be encrypted under `EncryptSensitiveWithUserKey` if marked sensitive, but the sensitivity flag in the variable definition is not explicitly set (defaults to 6789 = IncludeInDebugDump for some variables). A full sensitivity audit of the variable declarations is required.

---

## Sensitive Data Identification

### CRITICAL — ACH Financial Data

| Data Element | Location | PCI/Regulatory Flag |
|---|---|---|
| Bank routing numbers (ABA) | NACHA output files; `nacha_configurations` variable | NACHA Operating Rules; GLBA |
| Bank account numbers | NACHA Entry Detail records (Type 6) | NACHA Operating Rules; GLBA; potentially PCI DSS Req 3 if linked to card accounts |
| Transaction amounts | NACHA Entry Detail records | GLBA |
| Individual/company names | NACHA Entry Detail records | GLBA; potentially GDPR/CCPA for individual names |
| Company ID / Tax ID | NACHA Batch Header | GLBA |

### MEDIUM — Program Balance Data

| Data Element | Location | Flag |
|---|---|---|
| Program balance by bank | `program_balance_by_bank.dtsx` output | Commercially sensitive; GLBA |
| Sunrise transaction codes | `sunrise_transaction_code_export.dtsx` output | Commercially sensitive |

---

## Encryption Assessment

### In Transit
- **Database connection:** Windows Integrated Security (SSPI) — encrypted if SQL Server is configured to force encryption. Non-default; must be verified.
- **NACHA files to bank:** No SFTP/transmission configuration in this repository. File transmission to banking partners must use encrypted SFTP (NACHA requires secure transmission). This is a gap in the observable architecture.
- **Output files stored locally:** `C:\ETL\Out\FifthThird\temp\` — local disk, unencrypted file system.

### At Rest
Output NACHA and EFA files are written as plaintext to `C:\ETL\Out\FifthThird\temp\`. These files contain routing numbers and account numbers. They should be:
1. Encrypted at rest (BitLocker, TDE equivalent for files)
2. Purged immediately after successful transmission to the bank
3. Access-controlled to only the ETL service account and authorised staff

No evidence of any of these controls is present in the repository.
