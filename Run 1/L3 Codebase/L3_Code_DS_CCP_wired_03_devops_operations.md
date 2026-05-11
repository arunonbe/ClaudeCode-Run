# DevOps & Operations Report — DS_CCP_wired

## Build System

DS_CCP_wired uses **Visual Studio SSDT** with `wired.sqlproj` targeting `Microsoft.Data.Tools.Schema.Sql.Sql130DatabaseSchemaProvider` (SQL Server 2016). Solution file: `wired.sln`.

Key project settings:
- `DeployToDatabase=True`
- `IncludeCompositeObjects=True`
- No SqlServerVerification setting explicitly set (defaults to False based on schema version)

The SSDT project produces a `.dacpac` artifact on build, which can be deployed via SqlPackage.exe or SSDT Publish.

## CI/CD Pipeline

**No CI/CD pipeline configuration exists.** No `.gitlab-ci.yml`, Jenkinsfile, Azure DevOps pipeline YAML, or deployment automation scripts are present. Deployment is manual.

## Deployment Mechanism

1. **Schema deployment**: Manual SSDT dacpac publish to target SQL Server `WIRED` database.
2. **Post-deployment data**: Three post-deployment scripts are committed:
   - `post_deployment\insert_report_parameter_lookup.sql` — seeds the 30 parameter lookup entries
   - `post_deployment\insert_report_requests.sql` — seeds initial report subscriptions (includes personal email addresses)
   - `post_deployment\insert_report_schedule_timeslot.sql` — seeds schedule codes and time slots

Post-deployment scripts run as part of the SSDT publish process. If subscriptions are already present, the `SET IDENTITY_INSERT ON` / `IF EXISTS (SELECT 1 FROM table) BEGIN TRUNCATE ...` pattern in `insert_report_parameter_lookup.sql` will overwrite existing lookup data — but `insert_report_requests.sql` uses `SET IDENTITY_INSERT ON` without existence checks, meaning it will fail if records already exist. This is a **deployment fragility**.

## SQL Agent Jobs (from `SQL Agent Scripts\`)

Three SQL Agent job scripts are stored in the `SQL Agent Scripts\` subfolder (not a post-deployment script — these must be applied manually to msdb):

| File | Job Name | Schedule | Description |
|---|---|---|---|
| `wired_cache_refresh.sql` | `wired_cache_refresh` | Daily at 03:45 AM | Executes `cache_refresh.dtsx` from wired-caching project |
| `wired_cache_GP.sql` | `wired_cache_GP` | Daily at 5:30 PM + 2nd/3rd of month at 10 AM | Imports GP data to `cache_pbr_GP` |
| `wired_report_output.sql` | `wired_report_output` | (not read in full — referenced in disable script) | Triggers report output pipeline |

All jobs reference production SSIS server `p-db09.nam.wirecard.sys\db09` and SSISDB environment references by hardcoded integer (ENVREFERENCE 4). Jobs owned by `sa`.

## Environments

SSDT project has no environment-specific publish profiles. The `wired_db.conmgr` files in DS_CCP_wired-caching and DS_CCP_wired-output point to:
- Development: `d-phl-db01` / `d-phl-db01.wirecard.lan` — Wirecard development server
- No production connection manager visible in this repo (production uses SSISDB environment override)

## Monitoring and Alerting

### Database-Level Monitoring
- `usp_Wired_SubscriptionStatus_RPT` provides a manual health dashboard for Data Services staff
- `report_requests_log` provides execution history with `Success` bit and `StatusComment` columns
- No automated alerts on report delivery failure beyond SQL Agent job-level email notification

### Alerting Gaps
- **No proactive delivery failure alert**: If a report fails to generate or deliver, the only notification is the SQL Agent job failure email (sent to DBA operator, not the report requester or client)
- **No SLA monitoring**: No mechanism to detect that a report was scheduled for delivery but was not attempted
- **No client-facing notification**: Clients do not receive notification when their subscribed report fails to deliver — they would only notice when the expected report is absent
- **No duplicate delivery prevention**: If `wired_cache_refresh` is run twice in a day, could reports be delivered twice?

## Backup and Recovery

Not defined in this repository. The WIRED database schema is in Git. Data recovery considerations:
- `report_requests`: Contains active subscription config — critical to restore
- `cache_*`: Refreshed daily from source — can be rebuilt by re-running cache jobs after recovery
- `report_requests_log`: Historical data — restoration priority is lower
- `report_schedule`/`report_timeslot`/`report_parameter_lookup`: Static reference data — restorable from post-deployment scripts

Recovery approach: Restore database from backup; re-run post-deployment scripts for reference data; verify subscription records from backup.

## Operational Risks

1. **`report_requests.ID` SMALLINT overflow**: If the system processes thousands of subscriptions and log entries annually, the SMALLINT PK (max 32,767) could overflow. Overflow would halt all new subscription creation silently or with a constraint violation error.

2. **`insert_report_requests.sql` deployment fragility**: The post-deployment seed script uses `SET IDENTITY_INSERT ON` without idempotency guards. If the target DB already has records, the script will fail with duplicate key errors on the first record. This prevents clean redeployment without manual data cleanup.

3. **Wirecard AD groups**: Security roles (`WIRECARD\GL_WDNAM-DEVQA`, `WIRECARD\GL_WDNAM-DS_Admin`) reference Wirecard Active Directory groups. Post-Northlane/Onbe acquisition, these AD group names likely no longer resolve. Access may have been migrated ad-hoc without updating the SSDT project. The repo would deploy broken security objects if applied to a new Onbe environment.

4. **SSISDB ENVREFERENCE integers**: SQL Agent job commands in `SQL Agent Scripts\` use hardcoded `/ENVREFERENCE 4`. If the SSISDB environment is rebuilt, the reference ID will change and the job command strings must be manually updated.

5. **Personal email addresses in seed data**: `insert_report_requests.sql` contains personal email addresses committed to version control. Under GDPR, these must be identified, redacted from history, and data subjects notified if the repository is accessed by unauthorised parties.

6. **`vw_param_Frequencies` view**: The view (3,577 bytes) is large for a simple parameter view — without reading the full content, it may contain embedded business logic that could be a maintenance burden.
