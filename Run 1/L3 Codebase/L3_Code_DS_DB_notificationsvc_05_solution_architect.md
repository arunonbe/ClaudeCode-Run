# DS_DB_notificationsvc — Solution Architect Report

## 1. Technical Architecture

| Attribute | Value |
|-----------|-------|
| Database engine | Microsoft SQL Server 2012 (DSP: `Sql110DatabaseSchemaProvider`) |
| Project format | SSDT SQL Database Project (MSBuild 4.0 / .NET FX 4.6.1 build host) |
| Schema collation | `1033, CI` (SQL_Latin1_General_CP1_CI_AS for most new tables) |
| Artefact type | DACPAC + DeltaSql migration scripts |
| Object count | 75+ tables, 41 stored procedures, 2 scalar functions, 1 view |
| Schema structure | Single `dbo` schema throughout |
| Scheduler | Quartz (Java) — QRTZ tables in SQL Server 2012 format (legacy Quartz 1.x schema including deprecated `QRTZ_JOB_LISTENERS` and `QRTZ_TRIGGER_LISTENERS` tables) |
| Migration tooling | DeltaSql (folder-based manual scripts) |

---

## 2. API Surface

This is a database-only repository. There is no HTTP API surface. All interactions are through:

1. **Stored procedures** (41 total) — the primary interface for the notification service Java application.
2. **Views** — `notification_message_debug_vw` for operational queries.
3. **Direct table access** — `db_datareader`/`db_datawriter` roles allow direct table reads/writes by some principals.

### Key Stored Procedure Groups

| Group | Procedures | Pattern |
|-------|-----------|---------|
| `notification_get_*` | 9 procedures | Read configuration data for notification engine |
| `notification_update_*` | 2 procedures | Update queue/message status |
| `notification_exists_*` | 2 procedures | Existence checks |
| `notification_select/update_batch_*` | 2 procedures | Batch notification queue management |
| `wizard_notification_*` | ~15 procedures | Client-facing notification setup wizard (email) |
| `wizard_notification_sms_*` | ~12 procedures | Client-facing notification setup wizard (SMS) |
| `mailgun_events_queue_process` | 1 procedure | Multi-action SP: insert/update/select Mailgun events |
| `update_wizard_*` | 3 procedures | Update wizard event selection helpers |
| `rpt_Failed_Email_Notifications` | 1 procedure | Reporting SP for failed notifications |
| `util_get_date_range` | 1 procedure | Date range utility |
| `notification_message_debug` | 1 procedure | Debug query SP |

**Design note**: `mailgun_events_queue_process` implements an `@action` parameter dispatch pattern (insert/update/select) — a Gen-1 anti-pattern where a single stored procedure handles multiple operations. This creates implicit API coupling and makes unit testing impossible without calling the full SP.

---

## 3. Security Posture

### 3.1 Authentication

- **SQL logins** (`notificationsvc`, `b2c`, `report`, `report_full`) use SQL Server authentication with hardcoded passwords in Security SQL files.
- **Windows AD logins** (`NAM\PROD`, `NAM\UAT`, `NAM\PROD_ITOPS`, `NAM\PROD_CPP`, `NAM\PROD_CPP_APAC`) use Integrated Security — appropriate for Windows domain environments.
- **Emergency logins** (`emer_sk14163`, `emer_rb27292`, `emer_sp10000`, `emer_sr14161`) — four personnel-linked emergency accounts with both read and write access. No session recording or usage audit mechanism visible.

### 3.2 Authorisation

- Role-based access via SQL Server database roles (`db_datareader`, `db_datawriter`, `db_accessadmin`, `db_securityadmin`, `db_denydatawriter`).
- Custom roles: `notificationsvc_Select`, `notificationsvc_Execute`, `notificationsvc_Delete`, `notificationsvc_Update` — granular per-operation grants for the service account.
- `ifs_infosec`, `NAM\ISA_SQL_SECADMIN`, `ifs_gidadb` have `db_denydatawriter` — security team has read-only access with explicit write denial.
- `FortiDBRptRole` — FortiDB database monitoring agent role (database activity monitoring).
- `gers_role`, `gers_read` — likely GERS (governance/risk reporting system) integration roles.

### 3.3 Secrets / Credentials

**CRITICAL FINDING**: `Security/notificationsvc.sql` contains:
```
CREATE LOGIN [notificationsvc]
    WITH PASSWORD = N'Es}rjJemnve:khlbm_xno9 PmsFT7_&#$!~<wRmaiau{uV{r';
```
This is a SQL Server login password stored in plaintext in a git repository. This violates:
- **PCI DSS Requirement 8.3.1**: Passwords must not be stored in cleartext.
- **GLBA Safeguards Rule**: Customer information system credentials must be protected.

**Immediate action required**: Rotate the `notificationsvc` login password and remove it from version control. Use a secrets vault (HashiCorp Vault, Azure Key Vault, AWS Secrets Manager) to manage database credentials.

Similar findings apply to all other `Security/*.sql` files that contain `CREATE LOGIN ... WITH PASSWORD` statements.

### 3.4 Encryption

- No Always Encrypted, Transparent Column Encryption, or `ENCRYPTBYKEY` patterns are used.
- PII fields (`to_address`, `identifier`, phone numbers) are stored as plaintext `VARCHAR`/`NVARCHAR`.
- Reliance on Transparent Data Encryption (TDE) at the server level is assumed but not confirmed in schema artefacts.
- The April 2026 consent migration stores phone numbers in `ch_consent.identifier VARCHAR(255)` — plaintext.

---

## 4. Technical Debt

| Issue | Location | Severity | Detail |
|-------|----------|---------|--------|
| SQL Server 2012 DSP target | `NotificationSvc.sqlproj` | HIGH | SQL Server 2012 is end-of-life (EOL July 2022). Database likely runs on a newer engine but targets the 2012 compatibility level |
| Quartz 1.x deprecated tables | `QRTZ_JOB_LISTENERS`, `QRTZ_TRIGGER_LISTENERS` | MEDIUM | These tables were removed in Quartz 2.x. Their presence indicates the Quartz version in use is very old |
| `mailgun_events_queue_process` action dispatch | `dbo\Stored Procedures\` | MEDIUM | Single multi-action SP is an anti-pattern; difficult to test and maintain |
| Hardcoded passwords in `Security/*.sql` | `Security/` | CRITICAL | Multiple login creation scripts with plaintext passwords in source control |
| Cross-database reference tables (`CbaseApp_*`, `EcountCore_*`, `JobSvc_*`) | `dbo\Tables\` | MEDIUM | Shadow copies of external system tables create data consistency risk |
| Temp tables as permanent schema objects | `temp_notification_config_*` | LOW | Migration artifacts left as permanent table definitions |
| `QUOTED_IDENTIFIER OFF` on two SPs | `rpt_Failed_Email_Notifications`, `util_get_date_range` | LOW | Non-standard SQL mode; can cause issues with certain XML/string operations |
| No automated tests | Repository-wide | HIGH | No unit tests, integration tests, or data validation scripts |
| DeltaSql manual execution | `DeltaSql/` | MEDIUM | No tooling enforces execution order or tracks applied migrations |

---

## 5. Gen-3 Migration Assessment

**Migration effort**: HIGH

### What must change
1. **Schema migration**: Replace DACPAC + DeltaSql with Liquibase (as used by Gen-3 services like `exemplar-cross-border-transfer-service`).
2. **Stored procedure replacement**: All 41 stored procedures must be re-implemented as Spring Data JPA repositories or JDBC templates in a Java service layer.
3. **Secrets management**: All hardcoded credentials must be replaced with Spring Cloud Config + Vault integration.
4. **Encryption**: Column-level encryption (or Always Encrypted) required for PII fields to meet Gen-3 security standards.
5. **Quartz migration**: Move from SQL Server–backed Quartz to a cloud-native scheduler (e.g., Spring Cloud Task + AWS EventBridge Scheduler or Kubernetes CronJobs).
6. **Data retention policy**: Implement automated purge jobs for `email_details`, `mailgun_events_queue`, and `notification_event_archive`.

### What can be preserved
- The logical data model (event → message → queue → delivery) is sound and should be preserved in the Gen-3 schema.
- The consent management schema (`ch_consent`, `ch_consent_history`, `ch_quiet_hours`) introduced in April 2026 was designed with Onbe naming conventions (`ch_` prefix, `DATETIME2(3)`, `SYSUTCDATETIME()`) suggesting it was already designed with a Gen-3 migration in mind.
- The TCPA quiet hours enforcement model is compliant and should be ported as-is.

---

## 6. Code-Level Risks

| Risk | File | Detail |
|------|------|--------|
| Password in source control | `Security/notificationsvc.sql` | Production credential committed to git |
| Null `to_address` possible | `notification_queue.to_address VARCHAR(100) NULL` | Email can be dispatched with null recipient; no NOT NULL constraint |
| Unbounded `NVARCHAR(MAX)` | `notification_template.template_value`, `ch_consent_history.provider_message` | No size limit; large payloads can cause table bloat |
| `GOTO` patterns in SP | `mailgun_events_queue_process` | Structured error flow uses `GOTO` labels — unstructured control flow in T-SQL; error handling fragile |
| Missing `TRY/CATCH` | Multiple SPs | `@@ERROR <> 0 GOTO` pattern predates structured exception handling; may miss errors in multi-statement transactions |
| No FK on `notification_event.program_id` | `notification_event` | `program_id VARCHAR(16)` has no foreign key constraint; invalid program codes can be inserted silently |
| Cross-DB table staleness | `CbaseApp_email_templates`, `EcountCore_*`, `JobSvc_*` | No synchronisation mechanism defined in this repo; these may be permanently out of sync with source systems |
