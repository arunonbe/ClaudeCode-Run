# DS_DB_cf_report — DevOps and Operations View

## 1. Build System

`DS_DB_cf_report` is **not an SSDT project**. No `.sqlproj`, `.sln`, or `.dacpac` file is present in the repository. The repository contains raw SQL scripts organized in a schema/object-type directory hierarchy:

```
cf-report/
  BINBANK/
    Functions/         3 functions
    Stored Procedures/ 30+ procedures
    Tables/            25 tables (including config inserts)
  dbo/
    Functions/         80+ functions
    Stored Procedures/Procs1/  100+ procedures
    Tables/            90+ tables
    Views/             70+ views
  mantas/
    Stored Procedures/ 10 procedures
    Tables/            14 tables
    Views/             9 views
  ECNT_AB/             1 SP, 2 tables
  ISA/                 1 table
  NAOT/                7 tables
  NA_ATLYS/            16 views
  CB_OFFICE_*/         4 personal workspace schemas
DeltaSql/
  2026-03-01/STBR-4812/  7 forward + 7 rollback
  2026-04-12/STBR/STBR-5652/  6 forward + 6 rollback
```

Deployment is entirely script-based. There is no automated schema-diffing, no DACPAC differential deploy, and no idempotency guarantee on the base scripts (most use `CREATE OR ALTER PROCEDURE` which is SQL Server 2016+ syntax, confirming the target is not SQL Server 2012 despite the linked databases using older tooling).

---

## 2. CI/CD Assessment

**No CI/CD pipeline exists in this repository.** No `.github/`, `azure-pipelines.yml`, `.gitlab-ci.yml`, or any workflow files were found.

This means:
- Schema and stored procedure changes are deployed manually by running delta scripts against the target database (or by a DBA running `CREATE OR ALTER PROCEDURE` scripts directly).
- There is no automated linting, syntax validation, or integration testing for new procedures or table changes.
- No deployment gates exist — a developer with database access can push a change without peer review at the database level.
- No environment promotion workflow (dev → staging → production) is enforced by the repository.

**Gap**: For a database that generates NACHA ACH files (subject to NACHA Operating Rules) and produces regulatory outputs (NAUPA escheatment, FinCEN/BSA, OFAC screening support), the absence of CI/CD means compliance-critical logic can be altered without automated regression detection.

---

## 3. Change Management — DeltaSql Pattern

cf_report has an active and well-structured delta-SQL change management pattern:

### Pattern Description
Each change set lives in a dated folder with Jira ticket reference:
```
DeltaSql/{YYYY-MM-DD}/{TICKET}/
  {N}__{TICKET}_{description}.sql   (forward scripts)
  rollback/
    {N}__rollback_{TICKET}_{description}.sql   (rollback scripts)
```

Scripts are numbered for sequential execution. Rollback scripts exist for every forward script — this is a mature pattern that supports controlled rollback if a deployment must be reversed.

### Active Change Sets

| Ticket | Date | Scripts | Scope |
|---|---|---|---|
| STBR-4812 | 2026-03-01 | 7 forward, 7 rollback | Bank Integration transaction file; Tcode_Lookup_Addenda table creation |
| STBR-5652 | 2026-04-12 | 6 forward, 6 rollback | Further tcode lookup addenda changes; app_BI_Transaction_File revision |

The most recent activity is `6__STBR-5652_app_BI_Transaction_File.sql` dated April 12, 2026 — confirming cf_report is under active development as of April 2026, the most recently modified database in this analysis batch.

### Contrast with Base Scripts
The base `cf-report/` directory scripts use `CREATE OR ALTER PROCEDURE` — they are idempotent for procedures. However, `CREATE TABLE` statements in the base scripts are not idempotent; running them against an existing database would fail. The DeltaSql scripts use `CREATE TABLE` only for new tables introduced in a specific ticket. This creates a split deployment model:
- **Initial provisioning**: Run all base scripts (manual; no tooling)
- **Change deployment**: Run numbered DeltaSql scripts in order

There is no Flyway, Liquibase, or similar migration tracking table — executed delta scripts must be tracked manually (e.g., by a runbook or spreadsheet).

---

## 4. Environment Configuration

No environment-specific configuration files, connection strings, or environment variables are present in the repository. Server names are hard-coded in procedure logic:

**`app_BI_Transaction_File.sql` (line 107)**: `FROM [ECountcore_ss].[dbo].[fdr_dda_account_journal]`

The `_ss` suffix naming convention (`ECountcore_ss`, `Ecountcore_Process_SS`) suggests these are linked server names configured on the cf_report SQL Server instance. Linked server names are not in source control — they must be configured on each environment's SQL Server instance separately.

This creates an environment-configuration gap: a new environment (e.g., disaster recovery or dev) must have the same linked server names configured, or all cross-database procedures will fail at runtime.

---

## 5. Operational Procedures

### Bank Integration File Generation
The `BINBANK.app_BI_Transaction_File` procedure (and its `_Account_Balance_File`, `_Card_Status_File`, `_TransactionInternational_File` counterparts) are the primary operational outputs. Based on procedure code:

1. The procedure checks `BINBANK.ProcessStatus` for prior runs — idempotent guard prevents double-runs for the same date range.
2. Truncates the `BINBANK.Transaction` staging table.
3. Queries `ecountcore_ss..fdr_dda_account_journal` via linked server.
4. Populates `BINBANK.Transaction` with the extracted data.
5. Updates card numbers (iterative batch UPDATE, 10,000 rows at a time) — a potential performance concern for large cardholder populations.
6. Updates `BINBANK.ProcessStatus` with completion timestamp.

**Operational Risk**: No error handling (`BEGIN TRY/CATCH`) is visible in `app_BI_Transaction_File.sql`. If the linked server query fails mid-run, the `BINBANK.Transaction` table will be left truncated without new data. Downstream consumers (FI file generation) would receive an empty or partial dataset without any error signal.

### NACHA File Generation
The `usp_nacha_queue_file` procedure uses `BEGIN TRY/CATCH` with `BEGIN TRAN` / `COMMIT TRAN` (lines 26-60). It queues a file record in `nacha_file_status` and calls `usp_nacha_queue_file_sources` within the same transaction. This is a transactionally safe pattern.

The `usp_nacha_print_section_*` procedures generate the fixed-format NACHA file sections. These are called in sequence to build the output file. NACHA file integrity (correct padding to 10-record blocking factor, matching control totals) depends on all sections being called in the correct order — there is no orchestration procedure visible in this repository that enforces the calling sequence.

---

## 6. Monitoring

No dedicated monitoring or alerting stored procedures are present in cf_report itself.

The `BINBANK.ProcessLog` and `BINBANK.ProcessStatus` tables provide post-hoc visibility into file generation runs. However:
- `BINBANK.ProcessStatus` records completion but does not contain error codes or exception messages.
- No SiteScope integration, SNMP trap, or alerting procedure was found.
- Operational teams must query `BINBANK.ProcessStatus` manually or via an external monitoring tool to detect missed runs or processing failures.

**Gap**: A missed Bank Integration file run would not be detected automatically until the FI reports a missing file or a downstream reconciliation discrepancy is noticed. For a daily production operation governed by the FI service agreement, this represents an operational risk.

---

## 7. Dead Code and Hygiene Issues

The repository contains significant quantities of non-production artifacts:

### Multiple Versions of Procedures
Several procedures exist in triplicate (`_old`, current, `_New`), indicating incomplete decommissioning of prior versions:
- `fdr_process_nacha_post`, `fdr_process_nacha_post_old`, `fdr_process_nacha_post_test`, `fdr_process_nacha_post_test3`, `fdr_process_nacha_post_test_cursor` (5 versions)
- `app_func_card_expiration_is_reissue`, `_New`, `_old` (3 versions)
- `app_func_service_card_expiration_get_status`, `_New`, `_old` (3 versions)
- `rpt_func_card_expiration_count`, `rpt_func_card_expiration_count_committed`
- `rpt_func_card_expiration_get_count`, `_debug`, `_jwu`

### Personal Workspace Objects in Production Schema
The `CB_OFFICE_*` schemas contain production database objects that are individual analyst workspaces. These objects:
- Are not subject to normal change management controls
- May contain PII data from ad-hoc queries that was never purged (e.g., `CB_OFFICE_HNaylor._hwnivRsData`)
- Create compliance exposure if they persist cardholder data outside the defined data flow

### Test Procedure Names
Procedures named `billtest2`, `fdr_process_nacha_post_test`, `fdr_process_nacha_post_test3`, and `dmp_ecountjournalfact` suggest development artifacts left in the production schema.

---

## 8. Backup and Recovery

No backup configuration is present in the repository. Backup is handled by `DS_DB_database_maintenance`.

cf_report does not use trigger-based archiving (unlike CCP). There is no `_ARCHIVE` table pattern. Recovery of accidentally deleted or overwritten records depends entirely on database-level backup/restore. Given the operational nature of `BINBANK.Transaction` (truncated and repopulated nightly), point-in-time recovery of that table must be coordinated with the nightly job schedule.

---

## 9. Operational Risks Summary

| Risk | Severity | Description |
|---|---|---|
| No error handling in BI file generation procedures | HIGH | `app_BI_Transaction_File` truncates the target table before populating it; a linked-server failure would leave the table empty with no error signal |
| No CI/CD pipeline | HIGH | All deployments are manual; no automated regression testing for compliance-critical logic (NACHA, escheatment) |
| Multiple procedure versions in production | MEDIUM | Dead code (e.g., 5 versions of `fdr_process_nacha_post`) creates confusion about which version is active; increases maintenance burden |
| Linked server hard-coded names | MEDIUM | `ECountcore_ss` and `Ecountcore_Process_SS` are not in source control; environment configuration is implicit |
| Personal workspace schemas in production | MEDIUM | `CB_OFFICE_*` schemas bypass normal data governance; may contain unaudited PII data |
| No migration execution tracking | MEDIUM | DeltaSql scripts have no tracking table; there is no way to confirm which scripts have been applied to a given environment |
| No NACHA orchestration procedure | MEDIUM | The print-section procedures must be called in sequence; no single orchestration procedure enforces correct NACHA file assembly |
