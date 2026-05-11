# DevOps & Operations Report — DS_CCP_wired-output

## Build System

DS_CCP_wired-output uses **Visual Studio SSIS (Integration Services)** tooling, Product Version 14.0 (SSDT for Visual Studio 2017). Project file: `wired-output.dtproj`. Solution file: `wired-output.sln`. Project Deployment Model with `DontSaveSensitive` protection level.

The project builds to a `.ispac` archive that is deployed to SSISDB via the Deployment Wizard.

## CI/CD Pipeline

**No CI/CD pipeline configuration exists.** No `.gitlab-ci.yml`, Jenkinsfile, Azure DevOps YAML, or automated deployment scripts are present. This is consistent across all 6 DS_CCP repos.

## Deployment Mechanism

1. Build in Visual Studio → `wired-output.ispac`
2. Deploy via `ISDeploymentWizard.exe /S /ST:File /SP:wired-output.ispac /DS:<server> /DP:\SSISDB\wdnam-ccp-etl\wired-output`
3. Configure SSISDB environment variables: WEP SFTP credentials, client SFTP credentials, SMTP server, file paths
4. SQL Agent job `wired_report_output` (defined in DS_CCP_db09) triggers the master package

## Execution Flow

```
SQL Agent Job: wired_report_output
    └─► SSISDB: wdnam-ccp-etl\wired-output\wired_master_output.dtsx
        ├─► Data Flow: Read due subscriptions from WIRED.report_requests
        └─► Foreach Loop: For each due subscription
            └─► Execute: call_report_packages.dtsx
                ├─► Execute: rpt_Program_Balance_Report.dtsx / rpt_*
                │   └─► Generate output file → C:\ETL\Out\WEP\{filename}
                ├─► Execute: send_wep.dtsx (if DeliveryMethod = 'WEP')
                │   └─► Upload to sftp.amer1.wirecard.com
                ├─► Execute: send_client_sftp.dtsx (if DeliveryMethod = 'SFTP')
                │   └─► Upload to client SFTP server
                └─► SMTP send mail (if DeliveryMethod = 'Email')
                    └─► Send to DeliverySpecification email list
        └─► INSERT into report_requests_log (success/failure per subscription)
```

## Environments

| Environment | WIRED DB Connection | WEP SFTP |
|---|---|---|
| Development | `d-phl-db01.wirecard.lan` (hardcoded in `wired_db.conmgr`) | Dev/test SFTP |
| Production | SSISDB environment override of `wired_db` connection | `sftp.amer1.wirecard.com` (default in Project.params) |

The `wired_db.conmgr` `.wirecard.lan` DNS suffix indicates this connection manager was last updated while on the Wirecard internal network. Post-acquisition, the development server reference may need updating.

## Schedule

`wired_report_output` SQL Agent job runs on a schedule defined in DS_CCP_db09. Based on the timing of cache refresh (`cache_refresh` runs at 03:45 AM), the report output job likely runs after 04:00 AM to ensure fresh cache data is available. The exact schedule is in the `wired_report_output.sql` Agent job script (not read in full — referenced only by the disable script).

## Monitoring and Alerting

### What is Monitored
- SQL Agent job failure → email to DBA operator
- `report_requests_log`: Every subscription execution is logged with `Success` bit, `StatusComment`, and timestamp

### What is NOT Monitored
- **No client-facing delivery confirmation**: If `send_wep.dtsx` uploads successfully but the file is never retrieved by the client from WEP, no alert is triggered
- **No delivery SLA alerting**: No check that all due subscriptions were processed within the expected time window
- **No report content validation**: No check that generated report files are non-empty or contain the expected data
- **No email delivery confirmation**: SMTP send mail tasks fire-and-forget — no delivery receipt or bounce handling
- **No retry logic for failed deliveries**: If `send_wep.dtsx` fails due to a transient SFTP error, the subscription is logged as failed and not retried until the next scheduled run (which could be 24 hours later)
- **No notification to data services when a subscription fails**: Only the DBA group receives SQL Agent failure emails; the data services team may not know a client's report was not delivered

## Backup and Recovery

Not defined in this repository. Package recovery:
- `.ispac` redeployable from Git
- SSISDB credentials must be reconfigured after a fresh deployment
- Report files in `C:\ETL\Out\WEP\` are transient — not backed up (nor should they be; they can be regenerated)
- `report_requests_log` provides historical delivery status — should be backed up with the WIRED database

## Operational Risks

1. **Cache dependency timing**: `wired_master_output.dtsx` executes report packages using cache data populated by `wired_cache_refresh`. If cache refresh is slow or fails silently (empty cache — per wired-caching analysis), reports will be generated from stale or empty data and delivered to clients without warning. This is the most significant operational risk.

2. **`wired_db.conmgr` `.wirecard.lan` DNS**: Development connection manager references `d-phl-db01.wirecard.lan`. This hostname may not resolve post-acquisition. If a developer tries to test locally without SSISDB env override, connection will fail with DNS resolution error rather than a meaningful error message.

3. **`call_report_packages.dtsx` at 59,952 bytes is the largest package**: Large SSIS packages are harder to debug, test, and maintain. Control flow complexity is high. A failure mid-execution in this package may be difficult to diagnose from SSISDB execution logs alone.

4. **WEP SFTP endpoint Wirecard-branded**: `sftp.amer1.wirecard.com` — if this endpoint has been migrated to Onbe infrastructure under a new DNS name, and the SSISDB environment override is not current, report deliveries to the WEP portal will fail.

5. **Client SFTP credentials in `report_requests.DeliverySpecification`**: If client SFTP credentials are stored in the `DeliverySpecification` column, they are used by `send_client_sftp.dtsx` at runtime. Any SQL injection into the WIRED DB (e.g., via the vulnerable `usp_Wired_SubscriptionStatus_RPT` procedure) could potentially manipulate delivery targets.

6. **Email delivery to personal email addresses in seed data**: If the seed data email addresses (`patricia.zysk@wirecard.com`, `pattizysk@outlook.com`) are still active in production `report_requests`, programme financial reports may be delivered to personal/former email addresses. This is a data leakage risk.

7. **`rpt_Program_Balance_Report_Plus Fee.dtsx`**: Space in filename is non-standard — could cause issues in certain deployment scripts or command-line tooling that doesn't quote paths.
