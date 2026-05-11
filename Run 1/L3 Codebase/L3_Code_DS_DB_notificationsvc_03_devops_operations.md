# DS_DB_notificationsvc — DevOps and Operations Report

## 1. Build System

| Attribute | Value |
|-----------|-------|
| Project type | SSDT SQL Database Project (Visual Studio / SQL Server Data Tools) |
| Project file | `NotificationSvc.sqlproj` |
| Solution file | `NotificationSvc.sln` |
| SSDT DSP | `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` (SQL Server 2012) |
| Target framework | .NET Framework 4.6.1 (SSDT build host) |
| Build output | DACPAC (`NotificationSvc.dacpac`) — binary schema deployment package |
| CI/CD pipeline | **None found** — no `.gitlab-ci.yml`, no Jenkins pipeline, no GitHub Actions |

The SSDT project compiles all `*.sql` files listed in `NotificationSvc.sqlproj` into a DACPAC. The DACPAC is then deployed to SQL Server using SSDT's publish mechanism (`SqlPackage.exe /Action:Publish`).

---

## 2. Deployment Mechanism

**Current (inferred):** Manual DACPAC deployment or DeltaSql script execution by a DBA.

**DeltaSql pattern** (`DeltaSql/<date>/<ticket>/`):
- Forward migration scripts in `DeltaSql/2026-04-26/BZGD-0000/`
- Rollback scripts in `DeltaSql/2026-04-26/BZGD-0000/rollback/`
- Scripts must be run in order: `notificationssvc_consent_tables.sql` → `notificationssvc_alter_tables.sql` → `notificationssvc_consent_migration.sql` → `notificationssvc_events.sql` → `notificaiton-service-type.sql`

There is no automated deployment pipeline present in this repository. Deployment relies on:
1. A DBA manually running DeltaSql scripts against the target SQL Server instance
2. DACPAC publish for baseline schema deployment

**Risk**: Without pipeline automation, there is no enforcement of environment promotion order (dev → QA → UAT → prod), no mandatory pre-deployment validation, and no automated rollback trigger on failure.

---

## 3. Configuration Management

- No environment-specific configuration files (`.env`, application properties) exist in this repo — it is a pure database project.
- Database connection strings and credentials are managed by the application services that connect to `NotificationSvc` (e.g., `notification-framework_SVC`).
- **Exception**: `Security/notificationsvc.sql` contains the `notificationsvc` login with plaintext password — this is a security configuration artefact that must not be run against production systems from source control.
- Security SQL files (`Security/*.sql`) define logins, roles, and role memberships. These are **environment-specific** and should not be in version control in their current form (they contain AD group names and login passwords).

---

## 4. Observability

- **Application logging**: Not applicable (database project only).
- **SQL Server auditing**: No `AUDIT` or `EXTENDED EVENTS` session definitions are present in the schema.
- **Operational reporting**: `rpt_Failed_Email_Notifications` stored procedure provides a failure report query.
- **Debug view**: `notification_message_debug_vw` (view) joins notification tables for operational debugging.
- **Mailgun tracking**: `mailgun_events_queue` table + `mailgun_events_queue_process` SP provide webhook-driven delivery event tracking.
- **Job tracking**: `email_reader_job_status` and `mailgun_jobrun_tracker` track email reader job runs.
- **No alerting**: No SQL Agent job alerts or notification triggers are defined in this repository.

---

## 5. Infrastructure Dependencies

| Dependency | Type | Details |
|-----------|------|---------|
| SQL Server 2012+ | Database engine | DSP targets SQL 2012 (`Sql110`); actual production server version unknown |
| `notification-framework_SVC` | Primary writer | Java service that inserts notification events and reads queue |
| `notification-service-client_SVC` | API consumer | Reads notification configuration |
| Mailgun API | External email delivery | Webhook callbacks write to `mailgun_events_queue` |
| SMS provider | External SMS delivery | Writes to `sms_opt_out`, `ch_consent` |
| Quartz scheduler | In-application | `QRTZ_*` tables managed by Java Quartz scheduler within notification service |
| `ordersvc`, `jobsvc`, `ecountcore` | Upstream event sources | Write `notification_event` records |
| SSDT / Visual Studio | Build tooling | Required for DACPAC build |
| `SqlPackage.exe` | Deployment tooling | Required for DACPAC publish |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|------|---------|--------|
| No CI/CD pipeline | HIGH | Manual deployment increases change error risk; no automated testing or validation |
| Plaintext login password in source control | CRITICAL | `Security/notificationsvc.sql` contains cleartext password; anyone with repo access has DB credentials |
| Emergency accounts with write access | HIGH | `emer_*` accounts have `db_datawriter`; no evidence of usage audit or session recording |
| DeltaSql manual execution order dependency | MEDIUM | The 5-script migration sequence for BZGD-0000 must be run in exact order; no tooling enforces this |
| Missing data retention/purge jobs | MEDIUM | `email_details`, `mailgun_events_queue`, `notification_event_archive` grow unbounded without purge |
| `QRTZ_*` table contention | MEDIUM | Quartz scheduler tables under concurrent load can become a performance bottleneck; no index review present |
| No DACPAC baseline version | MEDIUM | No versioning tag or baseline DACPAC stored; reconstruction requires rebuilding from all SQL files |
| Temp tables in permanent schema | LOW | `temp_notification_config_program_template_map` and `_map1` committed as permanent objects |

---

## 7. CI/CD Assessment

**Current state**: No CI/CD. The repository has no pipeline configuration.

**Recommended pipeline stages** for a production-grade database project:
1. `validate` — SSDT build (MSBuild with SqlTasks.targets); check for syntax errors.
2. `dacpac-diff` — Generate a schema diff between current DACPAC and previous baseline; fail if breaking changes detected.
3. `deploy-dev` — Deploy DACPAC to development SQL Server instance.
4. `deploy-qa` — Deploy DACPAC to QA instance after QA sign-off.
5. `deltasql-validate` — Lint DeltaSql scripts; verify rollback scripts exist for each forward migration.
6. `deploy-uat` — Apply DeltaSql migrations to UAT.
7. `deploy-prod` — Gated production deployment with DBA approval.

**Missing artefacts**:
- `.gitlab-ci.yml` or equivalent pipeline definition
- `Makefile` or deployment script
- Environment-specific SSDT publish profiles (`*.publish.xml`)
- Test data generation scripts for post-deployment validation
