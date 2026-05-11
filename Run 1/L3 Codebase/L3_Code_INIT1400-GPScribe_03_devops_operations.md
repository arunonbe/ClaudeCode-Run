# DevOps & Operations — INIT1400-GPScribe

## CI/CD Pipeline

The `INIT1400-GPScribe` repository has **no CI/CD pipeline configuration**. There are no GitHub Actions workflows, no GitLab CI/CD files, no Azure DevOps pipelines, and no test automation. All deployment is manual: a DBA or developer executes the SQL scripts directly against the target SQL Server instance `P-AZ-GPSQL-VM01`.

This is consistent with how many SQL Server integration jobs at Onbe are managed — as DBA-owned scripts rather than application code — but it introduces significant operational and compliance risk.

## Deployment Model

### Script Execution Order

The five SQL files must be deployed in dependency order:

| Order | Script | Target DB | Purpose |
|-------|--------|-----------|---------|
| 1 | `seeStringToTable.sql` | SWIFT | Creates the `seeStringToTable` table-valued function used by INTI1400_UpdateProcessedFlag |
| 2 | `INTI1400_UpdateProcessedFlag.sql` | Dev_Swiftgift_CRM (10.10.150.7) | Creates the flag-update SP on the CRM server |
| 3 | `DYNO_Scribe_West_DataImport.sql` | SWIFT | Creates Step 1 stored procedure |
| 4 | `DYNO_Scribe_West_InvoiceImport.sql` | SWIFT | Creates/alters Step 2 stored procedure |
| 5 | `INIT1400-SQLJob.sql` | msdb | Creates the SQL Agent job definition |

Note that `INTI1400_UpdateProcessedFlag.sql` must be deployed to the **remote server** at `10.10.150.7`, not to the GP server. This requires DBA access to both servers. There is no automation enforcing this deployment sequence.

`DYNO_Scribe_West_InvoiceImport.sql` uses `ALTER PROCEDURE`, meaning the procedure must already exist before running the script. If deploying to a fresh server, a `CREATE PROCEDURE` stub must be executed first or the script modified.

### No Environment Separation

There is a single set of scripts with no environment-specific configuration. The linked server IP (`10.10.150.7`) and database names (`SWIFT`, `Dev_Swiftgift_CRM`, `DYNAMICS`) are hardcoded in the stored procedures. There are no development or QA counterparts visible in the repository.

The comment history in `DYNO_Scribe_West_InvoiceImport.sql` includes testing notes (e.g., `--AND x.DOCUMENT_DATE = '6/18/2024' -- Used for Testing Purpose` on the decoded line 226) suggesting that testing was performed by temporarily modifying the production stored procedure rather than running a separate test environment. This is an anti-pattern that risks leaving test code in production.

## Runtime Configuration

| Parameter | Value | Location |
|-----------|-------|----------|
| GP Server | `P-AZ-GPSQL-VM01` | README.md line 1 |
| Source CRM IP | `10.10.150.7` | DYNO_Scribe_West_DataImport.sql line 33 |
| Source DB | `Dev_Swiftgift_CRM` | DYNO_Scribe_West_DataImport.sql line 33 |
| Target DB | `SWIFT` | INIT1400-SQLJob.sql lines 41, 55 |
| Job Owner | `NAM\David.Laumonier` | INIT1400-SQLJob.sql line 26 |
| Schedule | Mon–Sat at 10:30 AM | INIT1400-SQLJob.sql lines 61–73 |
| Location Code | `SWIFT` (hardcoded) | DYNO_Scribe_West_InvoiceImport.sql decoded line 139 |
| User2Ent field | `'ScribeWest'` | DYNO_Scribe_West_InvoiceImport.sql decoded line 463 |

## Error Handling and Recovery

The `DYNO_Scribe_West_InvoiceImport.sql` stored procedure includes a documented manual recovery procedure (in the header comment block, decoded from wide-char encoding):

**Case 1 — Batches Failed to Import or Missed (server disconnect, Scribe hung)**:
1. Log into GP and delete all batches related to the failed import.
2. Comment/uncomment specific `AND BATCH_ID IN (...)` clauses in the procedure body to target specific batches.
3. Execute the view so changes take effect.
4. Re-run the procedure.

This recovery process **requires manual modification of production stored procedure code**. There is no parameterized re-run mechanism (e.g., a `@specific_batch_id` parameter). Each recovery event is a manual code change, increasing risk of error and reducing auditability.

**Automatic partial-failure cleanup**: When an invoice partially fails eConnect import, the procedure deletes the partial GP records from SOP tables (SOP10100, SOP10200, SOP10202, SOP10106, SOP10107, SOP10101, SOP10102) using `@tblResultErrSum` to identify failed SOPNUMBEs. This is a compensating transaction pattern — the GP state is restored to pre-import for failed documents.

## Monitoring and Alerting

- **Error log table**: `CA_tblScribeInvoice_ErrorLog` captures eConnect errors with `SOPNUMBE`, `BATCHID`, `ITEMNMBR`, `ErrCode`, `ErrMsg`. This must be queried manually to detect failures; there is no automated alerting.
- **Database Mail**: Code for `msdb.dbo.sp_send_dbmail` to `david.laumonier@onbe.com` with an HTML failure report is **commented out** in `DYNO_Scribe_West_InvoiceImport.sql` (decoded lines 597–603, comment: `/* Need DBMAIL turned on */`). This means email alerting is **not operational**. A job failure or eConnect error will only be detected if someone manually queries the error log table.
- **SQL Agent job notification**: `@notify_level_eventlog=2` (log on failure) is set in `INIT1400-SQLJob.sql` line 19, meaning job-level failures appear in the Windows Event Log. However, eConnect errors that return non-zero error codes but do not cause the stored procedure to RAISERROR or fail will not trigger this notification.
- **No health check endpoint**: There is no external monitoring integration (no Azure Monitor alert, no SCOM alert, no Datadog check).

## Operational Risks

| Risk | Description | Impact |
|------|-------------|--------|
| Silent partial import failures | eConnect errors are logged to a table but no active alert fires | Revenue recognition gap; GL/CRM reconciliation issue |
| Manual recovery requires code modification | Recovery from batch failures requires editing production SP | Risk of introducing bugs during incident response |
| No idempotency guarantee | Re-running Step 1 could re-stage already-staged records if `INTI1400_UpdateProcessedFlag` call failed | Duplicate records in staging table |
| `DYNO_Scribe_West_InvoiceImport.sql` uses `ALTER PROCEDURE` | Deployment fails on fresh server; requires pre-existing procedure | Deployment failure on DR/new server |
| No DR/failover configuration | Single job on single server; no standby or failover procedure documented | Single point of failure for daily revenue import |
| Job owner is a named individual | `@owner_login_name=N'NAM\David.Laumonier'` — personal AD account as job owner | If account is disabled/deleted, job stops running |
| Source DB named `Dev_Swiftgift_CRM` | Possible mislabeled production database | Data quality and governance ambiguity |

## Recommendations

| Priority | Action | Effort |
|----------|--------|--------|
| Critical | Enable DB Mail notification — uncomment and configure `sp_send_dbmail` | 0.5 day |
| Critical | Change job owner from personal AD account to a service account | 0.5 day |
| High | Add `@specific_batch_id` parameter to InvoiceImport SP for clean re-run without code modification | 1 day |
| High | Confirm whether `Dev_Swiftgift_CRM` is production; rename if so | 0.5 day (assessment + rename) |
| High | Implement source control deploy pipeline (SSDT project or Flyway) to track and automate script deployment | 3–5 days |
| Medium | Add staging table archival/purge job to prevent unbounded growth | 1 day |
| Medium | Implement Azure Monitor or SCOM alert on GP SQL Agent job failures | 1 day |
| Medium | Add idempotency guard to Step 1 to prevent duplicate staging on re-run | 1 day |
| Low | Document a formal recovery runbook replacing the inline SQL comments | 0.5 day |
