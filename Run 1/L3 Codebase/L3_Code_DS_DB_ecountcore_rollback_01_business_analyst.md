# DS_DB_ecountcore_rollback — Business Analyst View

## Repository Overview

`DS_DB_ecountcore_rollback` is a Git repository containing an SSDT SQL Server Database Project (`Ecountcore_rollback.sqlproj`) targeting SQL Server 2016 (`Sql130DatabaseSchemaProvider`). Unlike the active processing repositories, this database serves a dual role: it is both a **historical rollback and research workspace** containing dated point-in-time data snapshots from 2002 to 2013, and a **live operational component** containing active archive management, escheatment processing, monitoring, and reporting stored procedures that are still in use.

The database name `Ecountcore_Rollback` and the naming conventions of its tables (suffixed with `_jwu_YYYYMMDD`, `_rollback_YYYYMMDD`, `_backup_MMDDYYYY`) confirm that many tables represent manual data snapshots created by DBAs during incident responses, data corrections, and platform migrations going back to the earliest days of the EcountCore platform.

---

## Business Purpose

The database serves multiple concurrent business functions:

### 1. Historical Rollback Archive

Hundreds of point-in-time table snapshots capture the state of ACH transactions, NACHA files, card distributions, and member data at specific dates during platform incidents, data corrections, and vendor transitions. Examples:

- `ach_transaction_journal_jwu_20030326` — ACH journal snapshot from March 2003
- `fdr_process_nacha_file_jwu_20020419` — NACHA file records from April 2002 (one of the earliest records in the estate)
- `mellon_process_check_file_rollback_20041201` — Rollback data from a December 2004 Mellon check processing incident
- `ach_transaction_journal_backup_12262008` — ACH journal backup from December 2008

These snapshots enabled DBA teams to restore individual transactions or sets of records after data errors without performing a full database restore.

### 2. Live FDAJ (FDR DDA Account Journal) Archive Management

A complete, actively-maintained archive framework for `fdr_dda_account_journal` (FDAJ) data exists in this database. Stored procedures `archive_fdaj_commit_this`, `archive_fdaj_commit_wrapper`, `archive_fdaj_prepare_dda`, `archive_fdaj_prepare_records`, and related procedures implement a batched, DDA-level archival workflow with:
- Trigger-aware batch deletion (references `fdr_dda_account_journal_historical_adjustment_blocking_trigger` and `fdr_dda_account_journal_update_trigger`)
- Control tables (`archive_ctrl`, `archive_ctrl_fdaj`, `archive_ctrl_batch_size`) tracking archive state
- Dedicated `[archive_data]` filegroup for archived data

This is a live operational component — not just historical artefacts.

### 3. Escheatment Processing

Five stored procedures and multiple associated data snapshot tables implement the state unclaimed property (escheatment) workflow:
- `app_func_escheatment_get_expiration_date` — calculates the expiration date for escheatment eligibility
- `app_func_escheatment_is_account_escheatable` — determines if an account qualifies for escheatment
- `app_func_escheatment_is_maintenance_fee_allowed` — fee calculation logic for dormant accounts

Escheatment data is directly subject to state unclaimed property laws, which vary by state but typically require reporting and remittance after 3-5 years of account inactivity. These procedures are part of Onbe's regulatory compliance obligations across multiple US states.

### 4. Monitoring and Operational Health

Active monitoring stored procedures provide operational visibility for payment processing:
- `monitor_autoach_failure` — detects and reports auto-ACH failures
- `monitor_autoach_failure_autoFix` — automated remediation for known ACH failure patterns
- `monitor_CoreCardCreation` — monitors card creation pipeline health
- `monitor_FinancialProcess_DuplicateCard` — detects duplicate card issuance
- `monitor_ach_settlement_check` — verifies ACH settlement completeness
- `monitor_job_pending_tx_check` — checks for stuck pending transactions

### 5. Reporting

Over 30 reporting stored procedures support finance, operations, and compliance:
- `rpt_ACH_Batch_Reconciliation` — ACH batch reconciliation report (cross-references `ecountcore` tables)
- `rpt_mellon_origination` / `rpt_mellon_origination_return` — Mellon ACH origination and return reports
- `rpt_daily_dd` — daily direct deposit report
- `rpt_ach_withdrawal_review`, `rpt_ach_withdrawal_review_CANADA` — withdrawal review for domestic and Canadian ACH
- `rpt_program_card_expiration_summary` — card expiration summary by programme

### 6. GENTRAN/EDI Integration

A separate `GENTRAN` schema contains `app_process_activation_extract` — a stored procedure for extracting card activation data for IBM Sterling Gentran EDI processing. This component supports card activation file generation for EDI interchange.

---

## Regulatory Relevance

### PCI DSS

The `allfreedomcard` table contains `CardNumber NVARCHAR(16) NULL` — a plaintext, unencrypted Primary Account Number column. This table stores first name, last name, and full card number without any encryption or masking. This is a critical PCI DSS violation.

The `fdr_card_account_create` stored procedure accepts `@card_number char(16)` and `@cv_code varchar(32)` as parameters and inserts the `cv_code` directly into `fdr_card_account_detail`. The `util_update_cvcode` procedure updates the `cv_code` field (procedure body is encrypted with `WITH ENCRYPTION`). Both constitute confirmed CVV storage in the rollback database.

### NACHA / Reg E

Historical NACHA file data snapshots dating back to 2002 are present. These exceed NACHA's 2-year minimum retention requirement but represent potential PCI and CCPA scope for historical cardholder data.

### Escheatment / State Unclaimed Property Law

The active escheatment processing procedures and data tables make this database a compliance-relevant component for state unclaimed property reporting. Any disruption to escheatment processing could expose Onbe to state regulatory penalties.

### SOC 1

The monitoring and archival procedures support financial reporting controls. The FDAJ archive framework directly manages the lifecycle of DDA (Demand Deposit Account) transaction journal records used in financial reconciliation.

---

## Key Observations

1. The database straddles two eras: it contains both ancient (2002-2008) historical snapshots from the early EcountCore deployment and actively maintained (2020+) archive management procedures (`archive_fdaj_commit_this` authored by Van Nguyen, 2020-02-11).

2. The `allfreedomcard` table containing plaintext card numbers appears to be a historical migration artefact from an early programme called "AllFreedomCard" — but it remains in the SSDT project and would be deployed as a live table if this DACPAC were published.

3. The `user_validation_information` table stores plaintext `password VARCHAR(100)` and `secret_answer VARCHAR(50)` — authentication credentials without hashing evidence.

4. The Galileo-prefixed views (`galileo_account_dob`, `galileo_dda_account`, `galileo_user_enrollment`, etc.) indicate a historical integration with Galileo Financial Technologies, potentially representing a migration path from an earlier card processing platform to FDR/First Data.
