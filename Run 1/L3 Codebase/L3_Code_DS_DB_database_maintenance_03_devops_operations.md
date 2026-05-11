# DevOps / Operations View — DS_DB_database_maintenance

## Build and Packaging
- No SSDT `.sqlproj` or `.sln` file is present. This is a collection of raw T-SQL scripts, not a compiled database project.
- No build system (MSBuild, Maven, Gradle) is referenced.
- Artifacts: 4 `.sql` files that must be manually executed in order.

## Deployment
Deployment is entirely manual:
1. Execute `MaintenanceSolution_20191201213232.sql` on `master` — installs Ola Hallengren framework objects (`CommandLog`, `CommandExecute`, `DatabaseBackup`, `DatabaseIntegrityCheck`, `IndexOptimize`).
2. Execute `IndexOptimize_AgentWrapper.sql` on `master` — creates the custom wrapper stored procedure.
3. Execute `DBMP User Databases -- Index and stats reorg (custom).sql` on `msdb` — registers the daily SQL Agent job.
4. Execute `DBMP User Databases -- Integrity Check (custom).sql` on `msdb` — registers the weekly SQL Agent job.

There is no idempotency guard on the agent wrapper SP (no `IF EXISTS` / `DROP` pattern at the file level — the framework install uses `IF NOT EXISTS`).

## Configuration Management
- Server naming convention (`LEFT(@@SERVERNAME,1) = 'C'`) is the only environment-detection mechanism. No environment variables, configuration tables, or deployment parameters are used.
- `@BackupDirectory`, `@CleanupTime`, `@OutputFileDirectory` are all set to `NULL` in `MaintenanceSolution` — using SQL Server defaults.
- `@LogToTable = 'Y'` is the only non-default configuration set at install time.
- Time window thresholds (150 min, 07:00 cutoff, 15 min for business hours) are hardcoded in `IndexOptimize_AgentWrapper.sql`.

## Observability
| Signal | Source | Notes |
|---|---|---|
| Job success/failure | SQL Agent email | `@notify_level_email=2` (on failure) for Index job; `@notify_level_email=0` (never) for Integrity job |
| Command-level audit | `master.dbo.CommandLog` | Every command with start/end time and error |
| SQL Agent history | `msdb.dbo.sysjobhistory` | Standard SQL Agent retention |

Alerting gaps:
- The Integrity Check job has `@notify_level_email=0` — DBA team receives NO email alert if the weekly integrity check fails.
- No Prometheus/Grafana/Datadog integration. Observability is SQL Agent-native only.

## Infrastructure Dependencies
| Dependency | Notes |
|---|---|
| SQL Server Agent | Must be running; job ownership by `sa` |
| `DataServicesGroup-Operator` | SQL Agent operator must be pre-created on target instance |
| `master.dbo.IndexOptimize` | Ola Hallengren framework object must be installed first |
| `master.dbo.DatabaseIntegrityCheck` | Ola Hallengren framework object must be installed first |
| `sqlcmd.exe` | Index reorg step runs via `CmdExec` subsystem; `sqlcmd` must be on PATH |
| Windows Authentication | `sqlcmd -E` uses the SQL Agent service account |

## Operational Risks
1. **No alert on integrity check failure**: Silent failures — data corruption could go undetected.
2. **`sa` job ownership**: If `sa` is disabled (PCI best practice), jobs will not run.
3. **CmdExec subsystem dependency**: Index reorg step uses `CmdExec` rather than T-SQL; if xp_cmdshell/CmdExec is restricted, the job silently breaks.
4. **`@MaxNumberOfPages = 50 GB`**: Indexes larger than 50 GB are never rebuilt. Very large tables in high-write environments (e.g., `ecountcore`) may remain fragmented indefinitely.
5. **No retry**: Both jobs have `@retry_attempts=0`. A transient storage blip causes an immediate failure with no self-healing.

## CI/CD
- No CI/CD pipeline exists for this repository.
- No `.gitlab-ci.yml`, Jenkinsfile, or equivalent is present.
- No automated SQL syntax validation, unit tests, or deployment gating.
- Recommendation: Integrate `sqlcmd` syntax check or SSDT build into a pipeline; add smoke-test step to verify framework objects exist post-deploy.
