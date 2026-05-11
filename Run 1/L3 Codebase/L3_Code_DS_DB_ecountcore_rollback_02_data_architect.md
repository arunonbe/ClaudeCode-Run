# Data Architect Report — DS_DB_ecountcore_rollback

## 1. Repository Structure and Build System

`DS_DB_ecountcore_rollback` is an **SSDT SQL Server Database Project** (`Ecountcore_rollback.sqlproj`).

**Key project properties:**
- **Project GUID**: `{2a61d93c-51af-4b7a-b926-e1e6016e4966}`
- **DSP**: `Microsoft.Data.Tools.Schema.Sql.Sql130DatabaseSchemaProvider` — SQL Server 2016 target (Sql130)
- **Active branch**: none specified in shallow clone; project name is `Ecountcore_rollback`
- **Collation**: `SQL_Latin1_General_CP1_CI_AS`
- **Recovery**: Full recovery inferred from operational archive procedures (not declared in project file — defaults apply)
- **Storage**: Custom `[archive_data]` filegroup defined in `Storage/archive_data.sql`

The project targets SQL Server 2016 (`Sql130`), which is the most modern of all repos analysed in this batch and consistent with the active operational nature of the archive management layer.

---

## 2. Schema Composition

Single schema: `dbo` plus a separate `GENTRAN` schema.

| Schema | Object Type | Count | Purpose |
|---|---|---|---|
| `dbo` | Tables | 200+ | Historical rollback snapshots + active archive control tables |
| `dbo` | Stored Procedures | 80+ | Archive management, monitoring, reporting, escheatment |
| `dbo` | Functions | 5 | Escheatment logic, card expiration counting, string parsing |
| `GENTRAN` | Stored Procedures | 1 | EDI/card activation extract |

---

## 3. Table Inventory

### 3.1 Active Operational Tables

| Table | Purpose | Sensitivity |
|---|---|---|
| `dbo.archive_ctrl` | Archive control master: `archive_ctrl_id SMALLINT IDENTITY`, `archive_type`, `archive_status`, `create_date`, `create_user`, `update_date`, `update_user`; PK on `[archive_data]` filegroup | LOW |
| `dbo.archive_ctrl_fdaj` | FDAJ archival control records: DDA-level archival tracking with `archived BIT` flag | MEDIUM — DDA numbers |
| `dbo.archive_ctrl_batch_size` | Configures batch size per archived table type | LOW |
| `dbo.archive_ctrl_dda` | DDA-level archive control | MEDIUM |
| `dbo.archive_ctrl_fdaja` | FDAJA (FDAJ adjusted) archive control | MEDIUM |
| `dbo.archive_ctrl_fdajea` | FDAJ escrow adjustment archive control | MEDIUM |
| `dbo.archive_ctrl_fdajeas` | FDAJ escrow adjustment staging | MEDIUM |
| `dbo.archive_ctrl_fdajp` | FDAJ payment archive control | MEDIUM |
| `dbo.archive_ctrl_fdajr` | FDAJ reversal archive control | MEDIUM |
| `dbo.archive_ctrl_table_stats` | Archive operation statistics | LOW |
| `dbo.archive_status_xref` | Archive status code lookup | LOW |
| `dbo.archive_type_xref` | Archive type code lookup | LOW |
| `dbo.archive_queue_csa_comments` | CSA comments archival queue | LOW |
| `dbo.AuditJob` | SQL Agent job execution audit: job step tracking | LOW |
| `dbo.controls` | Application control parameters | LOW |
| `dbo.Inquiry_types` | Inquiry type reference | LOW |

### 3.2 Critical Security / PCI Violations

| Table | Columns | Severity | Note |
|---|---|---|---|
| `dbo.allfreedomcard` | `FirstName NVARCHAR(255)`, `LastName NVARCHAR(255)`, `CardNumber NVARCHAR(16)` | **CRITICAL** | **Plaintext full card number.** `allfreedomcard.sql:1-5`. Full PAN stored without encryption or masking. PCI DSS Req 3.3 violation |
| `dbo.user_validation_information` | `password VARCHAR(100)`, `secret_answer VARCHAR(50)` (inferred from Business Analyst report) | **HIGH** | Plaintext credentials stored in a table — authentication data without hashing |

### 3.3 Historical Rollback Archive Tables

Hundreds of point-in-time snapshot tables following naming conventions:
- `ach_transaction_journal_jwu_YYYYMMDD` — ACH journal snapshots (JWu DBA)
- `fdr_process_nacha_file_jwu_YYYYMMDD` — NACHA file records
- `mellon_process_check_file_rollback_YYYYMMDD` — Mellon check processing rollbacks
- `ach_transaction_journal_backup_MMDDYYYY` — periodic journal backups

Date range: **2002 to 2013**. Examples:
- `ach_transaction_journal_jwu_20030326` (March 2003)
- `affiliate_2201_balance_off_jwu_20020830` (August 2002 — one of the earliest records)
- `ach_transaction_journal_backup_12262008` (December 2008)
- `app_profile_user_papercheck_20130814` (August 2013)

These tables contain historical ACH transaction data, NACHA file records, cardholder balance adjustments, and promotion configuration snapshots. They were created manually by DBA staff during incident responses and data corrections.

### 3.4 Other Notable Tables

| Table | Purpose | Sensitivity |
|---|---|---|
| `dbo.APP_PROFILE_ESCHEATMENT_RULES_20081019` | Escheatment rule snapshot from October 2008 | LOW (reference data) |
| `dbo.app_process_escheatment_queue_20101012` | Escheatment queue snapshot from 2010 | MEDIUM — DDA-level data |
| `dbo.Maricopa_ATM_fee_reversals_20100909` | ATM fee reversals snapshot from 2010 | MEDIUM |
| `dbo.core_creditcard_20061218` | Credit card snapshot from December 2006 | **HIGH** — likely contains historical card data |
| `dbo.FDRSYNC_CREATE` / `FDRSYNC_MISSING_IN_ECOUNTCORE` | FDR sync reconciliation tables | MEDIUM |
| `dbo.Sweep_fdr_dda_account_journal` | FDAJ sweep data snapshot | HIGH — transaction data |

---

## 4. Functions

| Function | Purpose | Key Logic |
|---|---|---|
| `dbo.app_func_escheatment_is_account_escheatable(@dda_number, @ref_dt, @balance, @rule_set_id, @state)` | Returns BIT: whether account meets escheatment criteria | Cross-DB call to `ecountcore.dbo.app_func_dda_get_balance_by_date`, `app_func_escheatment_get_rule_set`, `app_func_escheatment_dda_get_address_state`; evaluates dormancy period and balance thresholds |
| `dbo.app_func_escheatment_get_expiration_date(@dda_number, @ref_dt, @rule_set_id, @state)` | Returns DATETIME: escheatment expiration date | State-specific dormancy rules |
| `dbo.app_func_escheatment_is_maintenance_fee_allowed(@dda_number, @ref_dt, @rule_set_id, @state)` | Returns BIT: whether maintenance fee is permissible | State fee rules |
| `dbo.parseStringToTable(@string, @delimiter)` | String split utility function | Returns table of parsed values |
| `dbo.rpt_func_card_expiration_get_count(@program_id, @date)` | Returns count of expiring cards for program/date | Reporting utility |

---

## 5. Sensitive Data Assessment

| Field | Table | Classification | Regulatory |
|---|---|---|---|
| `CardNumber NVARCHAR(16)` | `dbo.allfreedomcard` | **PLAINTEXT PAN — CRITICAL** | **PCI DSS Req 3.3 violation** |
| `password VARCHAR(100)` | `dbo.user_validation_information` | Plaintext credential | PCI DSS Req 8; GLBA |
| `secret_answer VARCHAR(50)` | `dbo.user_validation_information` | Plaintext secret | PCI DSS Req 8 |
| `dda_number CHAR(16)` | Multiple archive tables | DDA/account identifier | GLBA NPPI |
| Historical ACH transaction amounts | `ach_transaction_journal_*` tables | Financial transaction data | NACHA; Reg E |
| Historical NACHA file content | `fdr_process_nacha_file_jwu_*` | NACHA file records | NACHA; PCI DSS |
| `@cv_code varchar(32)` parameter | `fdr_card_account_create` (encrypted procedure) | CVV/CVC | **PCI DSS SAD — not to be stored** |

---

## 6. Cross-Database References

The escheatment functions in this database make **direct cross-database calls** to `ecountcore`:

```sql
-- app_func_escheatment_is_account_escheatable.sql:47
set @balance = ecountcore.dbo.app_func_dda_get_balance_by_date(@dda_number, @ref_dt)

-- app_func_escheatment_is_account_escheatable.sql:50
set @rule_set_id = ecountcore.dbo.app_func_escheatment_get_rule_set(left(@dda_number, 8))
```

The archive management procedure `archive_fdaj_commit_this` cross-references `ecountcore.dbo.fdr_dda_account_journal` directly:

```sql
-- archive_fdaj_commit_this.sql:88
ALTER TABLE ecountcore.dbo.fdr_dda_account_journal 
    DISABLE TRIGGER fdr_dda_account_journal_historical_adjustment_blocking_trigger;
```

This means `Ecountcore_rollback` has **DDL control over a trigger in the ecountcore database** — a very tight coupling and an operational risk.

---

## 7. Encryption and Storage

| Control | Status |
|---|---|
| TDE | Not configured in project file; must verify on production instance |
| Column-level encryption | `util_update_cvcode` procedure uses `WITH ENCRYPTION` on the procedure body, not on the column |
| `[archive_data]` filegroup | Dedicated filegroup for archive tables (`Storage/archive_data.sql`); archive control tables created `ON [archive_data]` |

---

## 8. Data Quality and Retention

| Issue | Description |
|---|---|
| Historical data spanning 2002-2013 | Data from 2002 is over 20 years old; well beyond NACHA 2-year minimum and any reasonable PCI retention period |
| No automated purge procedures found | Historical rollback tables have no defined lifecycle or purge mechanism |
| `archive_ctrl_batch_size` controls | The archive batch process has configurable batch sizes (`archive_ctrl_batch_size.sql`), providing operational control |
| `archive_ctrl_table_stats` | Statistics table tracks archive operation progress — provides operational visibility |

---

## 9. Compliance Gaps

| Gap | Description | Regulation |
|---|---|---|
| `allfreedomcard.CardNumber` plaintext PAN | Unmasked, unencrypted 16-digit card number in production SSDT project | **PCI DSS Req 3.3 — CRITICAL** |
| `user_validation_information` plaintext credentials | Hashing not confirmed | PCI DSS Req 8.3 |
| Historical data beyond retention limits | 20+ years of ACH/NACHA transaction data | PCI DSS; NACHA; CCPA (right to erasure) |
| CVV parameter stored in `fdr_card_account_detail` | `fdr_card_account_create` inserts `@cv_code` | **PCI DSS Req 3.3 — SAD must not be stored** |
| Cross-DB DDL execution | `archive_fdaj_commit_this` disables trigger in ecountcore | SOX change management; PCI DSS Req 6 |
