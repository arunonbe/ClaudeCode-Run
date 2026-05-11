# DevOps & Operations Report — DS_CCP_wired-caching

## Build System

DS_CCP_wired-caching uses **Visual Studio SSIS (Integration Services)** tooling, Product Version 14.0.3002.113 (SSDT for Visual Studio 2017). The project file is `wired-caching.dtproj` using the Project Deployment Model. Solution file: `wired-caching.sln`.

Protection level: `DontSaveSensitive` — sensitive values (SFTP passwords, passphrases, Oracle password) are stripped from package files and must be configured via SSISDB environments.

## CI/CD Pipeline

**No CI/CD pipeline configuration exists.** No `.gitlab-ci.yml`, Jenkinsfile, Azure DevOps YAML, or similar pipeline definitions are present.

## Deployment Mechanism

Manual SSIS Project Deployment:
1. Build project in Visual Studio → produces `wired-caching.ispac`
2. Deploy `.ispac` via SSIS Deployment Wizard or command: `ISDeploymentWizard.exe /S /ST:File /SP:wired-caching.ispac /DS:<server> /DP:\SSISDB\wdnam-ccp-etl\wired-caching`
3. Configure SSISDB environment variables for Oracle DWH password and SFTP credentials
4. Set parameter values for `SourceFolder`, `GP_SFTP_HostName`, etc. per environment
5. Create SQL Agent jobs (from DS_CCP_db09 `wired_cache_refresh.sql` and `wired_cache_GP.sql` scripts)

No automated deployment scripts exist. All steps are manual.

## SSIS Execution Orchestration

```
SQL Agent Job: wired_cache_refresh (Daily 03:45 AM)
    └─► SSISDB: wdnam-ccp-etl\wired-caching\cache_refresh.dtsx
        └─► Executes all individual cache packages:
            ├─► cache_pbr.dtsx
            ├─► cache_agg_spend.dtsx
            ├─► cache_card_ship_date.dtsx
            └─► cache_rapid_undeliverable_cards.dtsx

SQL Agent Job: wired_cache_GP (Daily 5:30 PM + 2nd/3rd of month 10 AM)
    └─► SSISDB: wdnam-ccp-etl\wired-caching\import_cache_pbr_GP.dtsx
        ├─► Files_sftp.dtsx / Receive_SFTP.dtsx (GP file retrieval)
        └─► Import to cache_pbr_GP
```

## Environments

| Environment | Server | WIRED DB Connection |
|---|---|---|
| Development | `d-phl-db01` (hardcoded in `wired_db.conmgr`) | Wirecard dev LAN |
| Production | p-db09 (SSISDB host); WIRED DB via SSISDB env override | Wirecard/Northlane production |

The `wired_db.conmgr` file hardcodes the development server name `d-phl-db01`. In SSISDB Project Deployment, this connection string is overridden by the SSISDB environment's `wired_db` connection manager configuration. However, if a package is run outside of SSISDB (e.g., directly from file), it will attempt to connect to the dev server.

## Monitoring and Alerting

- **SQL Agent failure emails**: `wired_cache_refresh` and `wired_cache_GP` jobs send email to `DBA` operator on failure.
- **SSISDB execution logs**: All package executions are logged to `SSISDB.catalog.executions` with error messages.
- **Email notification parameter**: `NotifyEmailAddress` project parameter enables package-level email notifications (e.g., on SFTP file receipt or failure).

### Gaps
- **No cache freshness validation**: No post-load check that the cache tables contain expected row counts or recent dates. An empty cache (e.g., Oracle DWH connection failure) would load zero rows to staging and swap to an empty production cache, silently producing blank reports.
- **No Oracle DWH health check**: No pre-execution test of `DWH_AWS_SSH` reachability before attempting cache load.
- **No alert on cache-to-report timing**: No check that `cache_refresh` completes before `wired_report_output` begins. If `cache_refresh` is slow and overlaps with report generation, reports could use stale cache data.
- **SSH tunnel monitoring**: The Oracle DWH connection relies on the `DWH_AWS_SSH` DSN being active. If the SSH tunnel drops, the Oracle connection fails. No external monitoring of SSH tunnel health is visible.

## Backup and Recovery

Not defined in this repository. Cache data recovery:
- Cache tables can be repopulated by re-running the SSIS packages — no backup of cache data is needed
- SSIS package recovery: re-deploy `.ispac` from Git and reconfigure SSISDB credentials
- Recovery of GP SFTP files: depends on whether GP files are retained on the SFTP server after download

## Operational Risks

1. **Oracle DWH decommission**: The CCP Oracle DWH was shut down in July 2020 (per DS_CCP_db09 analysis). If the `DWH_AWS_SSH` DSN / SSH tunnel is no longer active, all Oracle-sourced cache packages (`cache_pbr.dtsx`, `cache_agg_spend.dtsx`, `cache_card_ship_date.dtsx`, `cache_rapid_undeliverable_cards.dtsx`) will fail. Cache data may be stale since CCP shutdown. **This is likely the current state.**

2. **Default QA SFTP hostname**: `GP_SFTP_HostName` defaults to `sftp-qa.nam.wirecard.com`. Misconfiguration would send GP file requests to the Wirecard QA SFTP server, potentially retrieving QA data or failing silently if the QA server is decommissioned.

3. **`wired_db.conmgr` development server hardcode**: `Data Source=d-phl-db01` in the connection manager file. If deployed without SSISDB environment override, packages write cache data to the development server, not production.

4. **Oracle username `RM_BI_USER` in source control**: Committed in `ccp_dwh.conmgr`. Any developer with repo access knows the Oracle service account username. Combined with the DSN name `DWH_AWS_SSH`, an attacker with internal access could attempt brute-force or credential stuffing against this Oracle account.

5. **PackagePart reuse dependency**: `PackagePart1.dtsxp` is a shared package part (692 bytes). If this part is modified in isolation without re-building dependent packages, those packages may use the old compiled version from SSISDB. Package parts require rebuilding all dependent packages on change.

6. **No GP file archival visibility**: `Receive_SFTP.dtsx` archives received GP files to `ArchivedFolder`. If the archive directory fills up or becomes unavailable, the SFTP package will fail. No disk space monitoring is evident.
