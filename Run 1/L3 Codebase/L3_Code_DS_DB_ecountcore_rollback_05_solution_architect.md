# Solution Architect Report — DS_DB_ecountcore_rollback

## 1. Technical Architecture

`DS_DB_ecountcore_rollback` is an **SSDT SQL Server Database Project** (`Ecountcore_rollback.sqlproj`) targeting **SQL Server 2016** (`Sql130DatabaseSchemaProvider`) — the most modern target DSP in this analysis batch.

**Project identity:**
- Project GUID: `{2a61d93c-51af-4b7a-b926-e1e6016e4966}`
- Target DSP: `Sql130` (SQL Server 2016)
- Collation: `SQL_Latin1_General_CP1_CI_AS`
- Custom filegroup: `[archive_data]` (`Storage/archive_data.sql`)
- Active security roles: 40+ logins/roles including 20+ individual emergency access logins

**Functional subsystems within one database:**

| Subsystem | Objects | Description |
|---|---|---|
| FDAJ Archive Management | `archive_fdaj_*` tables, `archive_fdaj_commit_this`, `archive_fdaj_commit_wrapper`, `archive_fdaj_prepare_*`, `archival_fdaj_dda` | Live archive of `ecountcore.fdr_dda_account_journal` |
| Escheatment Compliance | 3 functions + 5+ procedures + data snapshot tables | State unclaimed property eligibility determination |
| Operations Monitoring | `monitor_*` procedures (6+) | ACH, card creation, settlement, pending transaction monitoring |
| Historical Rollback Archive | 200+ date-stamped tables | 2002-2013 incident response snapshots |
| GENTRAN EDI | `GENTRAN.app_process_activation_extract` | Card activation export for IBM Sterling Gentran |

---

## 2. API Surface

### 2.1 Archive Management API

**Primary procedure: `archive_fdaj_commit_this(@archive_ctrl_id SMALLINT, @DDA_Table AS ArchiveDDATableType READONLY)`**

Key implementation details (`archive_fdaj_commit_this.sql`):
- Reads batch size from `dbo.archive_ctrl_batch_size` (default 250) at line 35
- Creates temp table `#delete_base` with batch assignments (line 37-52)
- Processes batches in a WHILE loop (lines 54-146)
- **Disables** `ecountcore.dbo.fdr_dda_account_journal_historical_adjustment_blocking_trigger` at line 88
- Deletes from `ecountcore.dbo.fdr_dda_account_journal` with OUTPUT clause (lines 103-114)
- Inserts deleted records into `dbo.fdr_dda_account_journal_archive` (lines 116-122)
- Commits after each batch (line 128) — avoids table-level locks
- **Re-enables** trigger at line 150 (also in CATCH block at line 169)
- Full TRY/CATCH with ROLLBACK and RAISERROR (lines 152-173)

### 2.2 Escheatment Functions API

```sql
-- Primary escheateability check
dbo.app_func_escheatment_is_account_escheatable(
    @dda_number CHAR(16),    -- DDA account number
    @ref_dt DATETIME,         -- reference date
    @balance INT = null,      -- optional pre-fetched balance
    @rule_set_id TINYINT = null,  -- optional pre-fetched rule set
    @state CHAR(2) = null    -- optional pre-fetched state
) RETURNS BIT
```

Decision logic: (1) check if state allows maintenance fee → if no, escheatable; (2) check if state allows escheatment at all; (3) check if dormancy period has expired; (4) check balance threshold. All cross-DB calls to `ecountcore.dbo.*`.

### 2.3 Monitoring API

| Procedure | Monitors |
|---|---|
| `monitor_autoach_failure` | Auto-ACH failures (authored JWu 2004, updated 2006) |
| `monitor_autoach_failure_autoFix` | Automated remediation for known ACH failure patterns |
| `monitor_CoreCardCreation` | Card creation pipeline health |
| `monitor_FinancialProcess_DuplicateCard` | Duplicate card issuance detection |
| `monitor_ach_settlement_check` | ACH settlement completeness verification |
| `monitor_job_pending_tx_check` | Stuck pending transaction detection |

### 2.4 GENTRAN EDI API

`GENTRAN.app_process_activation_extract` — extracts card activation data for IBM Sterling Gentran EDI interchange. No further details visible without reading the procedure body; the `GENTRAN` schema login is defined in `Security/GENTRAN.sql`.

---

## 3. Security Posture

| Control | Status | Finding |
|---|---|---|
| `allfreedomcard.CardNumber` | Plaintext NVARCHAR(16) | **CRITICAL PCI DSS Req 3.3 violation** — full PAN stored unencrypted (`allfreedomcard.sql:4`) |
| `user_validation_information.password` | Plaintext VARCHAR(100) | **HIGH** — authentication credential stored in cleartext |
| CVV parameter in `fdr_card_account_create` | `@cv_code varchar(32)` inserted to `fdr_card_account_detail` | **PCI DSS SAD — not to be stored post-auth** |
| `util_update_cvcode` | Procedure body `WITH ENCRYPTION` | Procedure text is obfuscated but the underlying CVV update operation still stores SAD |
| Cross-DB DDL permissions | `archive_fdaj_commit_this` requires ALTER TABLE on ecountcore | Service account needs DDL privilege on the core payments database — violates least privilege |
| 20+ individual emergency logins | `emer_*` in Security scripts | Named individual accounts with direct DB access; should be governed via PAM |
| FortiDB DAM | `FortiDBRptRole` role defined | Database activity monitoring configured |
| TDE | Not configured in project | Cannot confirm from SSDT alone |

---

## 4. Technical Debt

| Item | File:Line | Impact |
|---|---|---|
| `allfreedomcard` plaintext PAN deployed via DACPAC | `dbo/Tables/allfreedomcard.sql:4` | Critical PCI DSS violation deployed to every environment; must be remediated before next DACPAC publish |
| CVV storage | `fdr_card_account_create` (implied), `util_update_cvcode` | SAD (CVV) stored post-authorisation; PCI DSS Req 3.2 violation |
| 200+ historical tables in production SSDT project | `dbo/Tables/` directory | All historical snapshots are live deployed database objects; not archived as data files |
| `monitor_autoach_failure` authored 2004 | `monitor_autoach_failure.sql:29` | 20+ year old monitoring procedure; logic may reference obsolete conditions |
| Cross-DB trigger DDL | `archive_fdaj_commit_this.sql:88` | `ALTER TABLE ecountcore.dbo.fdr_dda_account_journal DISABLE TRIGGER` — architectural anti-pattern |
| 20+ individual emergency logins in source | `Security/emer_*.sql` | Named individual logins committed to source control; rotation and offboarding not visible |
| Historical data 2002-2013 without disposition | 200+ snapshot tables | No documented retention policy or purge mechanism |
| SQL 2005 compat-level escheatment functions | Function headers (JWu 2006) | Functions authored under SQL 2005-era practices; compatibility with SQL 2016+ features should be verified |
| `parseStringToTable` utility function | `dbo/Functions/parseStringToTable.sql` | String split utility predates `STRING_SPLIT()` (SQL 2016+); can be replaced with native function |

---

## 5. Gen-3 Migration Requirements

| Requirement | Description |
|---|---|
| Remediate PCI violations first | `allfreedomcard` PAN data must be purged and table removed; CVV in `fdr_card_account_detail` must be assessed and purged before any Gen-3 migration |
| Design FDAJ archival in Gen-3 | Replace the cross-database trigger-disabling archive pattern with a purpose-built data lifecycle service; Gen-3 approach: Azure Data Factory archival pipeline or SQL Server Stretch Database / columnar archival |
| Migrate escheatment service | Escheatment functions must be ported to a dedicated Unclaimed Property Compliance Service with state-rule engine; timing is constrained by annual state filing calendar |
| Decommission GENTRAN EDI | IBM Sterling Gentran is end-of-life legacy; migrate card activation export to a modern EDI platform or direct API |
| Disposition historical data | Legal/Compliance sign-off required on whether 2002-2013 data must be retained for regulatory purposes or can be purged; CCPA right-to-erasure obligations for any cardholder-identifiable records |
| Replace `parseStringToTable` | Use native `STRING_SPLIT()` available in SQL Server 2016+ |
| Retire individual emergency logins | Replace `emer_*` logins with PAM-controlled just-in-time access |
| Decouple archive from ecountcore DDL | Remove the requirement for `ALTER TABLE` privilege on ecountcore triggers |

---

## 6. Code-Level Risks

| Risk | File:Line | Notes |
|---|---|---|
| `allfreedomcard.CardNumber NVARCHAR(16)` | `dbo/Tables/allfreedomcard.sql:4` | Plaintext PAN in production table — DACPAC publishes this to every environment |
| Trigger disable without guaranteed re-enable | `archive_fdaj_commit_this.sql:88, 150, 169` | If the CATCH block's re-enable (`line:169`) fails (e.g., permission error during error handling), the trigger remains disabled indefinitely; account balance updates in ecountcore stop working |
| `archive_fdaj_commit_this` commits within loop | `archive_fdaj_commit_this.sql:128` | Mid-loop COMMIT means a failure after COMMIT but before the `archived=1` update (line 131-139) could leave records deleted from ecountcore but not marked as archived — data inconsistency risk |
| Escheatment function cross-DB calls with no error handling | `app_func_escheatment_is_account_escheatable.sql:47-53` | No TRY/CATCH — if `ecountcore` is unavailable, the escheatment function fails with an unhandled cross-DB error |
| `parseStringToTable` custom function vs native | `dbo/Functions/parseStringToTable.sql` | Custom string-split function; SQL Server 2016+ has `STRING_SPLIT()`; the custom version may have different behaviour for edge cases (empty strings, multi-char delimiters) |
| Historical 1099 tables from 2004 | `dbo/Tables/1099_04018347_Samsun_2004.sql` etc. | Tax data tables (IRS 1099) from 2004 deployed as live SQL tables; 20+ year old tax data in scope for CCPA, SOX record-keeping, and IRS data retention |
