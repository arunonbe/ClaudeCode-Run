# DevOps / Operations View — DS_DB_GP_emeam

## Build and Packaging
- **SSDT Project**: `emeam.sqlproj`, SQL Server 2008 schema provider (`Sql100`), no associated `.sln` file in the root (standalone project).
- Target framework: .NET 4.5.
- Collation: `SQL_Latin1_General_CP1_CI_AS` (Latin1, case-insensitive — standard for Dynamics GP).
- Build produces a `.dacpac` artifact.
- `SqlServerVerification=False` — expected for GP; many GP objects reference other GP databases or system objects not visible to the build.
- `IncludeCompositeObjects=True`.

**Key SSDT project settings** (from `emeam.sqlproj`):
- `CompatibilityMode=100` (SQL Server 2008)
- `IsEncryptionOn=False`
- `AnsiNulls=False`, `AnsiWarnings=False`, `AnsiPadding=False`, `QuotedIdentifier=False`
- `ServiceBrokerOption=EnableBroker` — Service Broker is enabled
- `QueryStoreCaptureMode=Auto`, `QueryStoreDesiredState=ReadWrite` — Query Store is configured (requires SQL Server 2016+, inconsistent with CompatibilityLevel 100)
- `PageVerify=CHECKSUM`
- `VardecimalStorageFormatOn=True` — legacy vardecimal feature (deprecated in SQL Server 2012+)
- `IsNestedTriggersOn=True` — GP uses nested triggers
- `RecursiveTriggersEnabled=False`

## Deployment
- Entirely manual — no CI/CD pipeline is present.
- SSDT dacpac deployment via `SqlPackage.exe` would apply schema changes.
- **Critical operational constraint**: Dynamics GP database schemas must be managed through the GP upgrade installer, not arbitrary SSDT deployments. Deploying a dacpac against a live GP database without GP installer validation risks breaking GP application compatibility.
- Likely actual deployment pattern: GP upgrades run by Dynamics GP Administrator; SSDT project is maintained as a schema documentation/source-control artifact rather than the primary deployment mechanism.

The `Security\` folder contains principal creation and role membership scripts that must be deployed separately from the main dacpac (logins must be created at the instance level first).

## Configuration Management
- No environment-specific configuration files in the repository.
- No SQLCMD variable substitution (no `$(DatabaseName)` placeholders in table DDL — unlike ordersvc which uses filegroup references).
- All configuration is embedded in the GP application layer, not in database SQL.
- Branch: `development` (active branch per `.git/HEAD`) — suggests the repo is used for ongoing development, not just archival.

## Observability
| Signal | Source | Notes |
|---|---|---|
| GP application logs | Dynamics GP client/server | Application-layer; not in this repo |
| SQL Agent jobs | GP-managed maintenance jobs | Not in this repo |
| DBAdmin monitoring | DS_DB_dbadmin | Index stats, blocking, drive space for this instance |
| `SE000401` staging table | Populated by `SE_Get_*` procs | Session-scoped reporting data; not persistent monitoring |

No dedicated observability is implemented in this repository. Relies entirely on instance-level DBAdmin monitoring.

## Infrastructure Dependencies
| Dependency | Notes |
|---|---|
| Dynamics GP Application Server | GP app tier must connect to this database |
| SQL Server 2016+ | Query Store settings require 2016+; CompatibilityLevel 100 can coexist |
| Service Broker | `ServiceBrokerOption=EnableBroker` — GP workflow may use Service Broker |
| `sp_bindefault` system procedure | `BindDynamicsDefaults` uses deprecated `sp_bindefault` / `sp_unbindefault` |
| `dbo.syscolumns` / `dbo.sysobjects` (legacy catalog views) | `BindDynamicsDefaults` queries legacy compatibility views |
| Management Reporter / FRx | Consumes `SE_Get_*` stored procedures |
| GP Report Writer | Uses `rpt_*` roles for access |

## Operational Risks
1. **Deprecated `sp_bindefault`**: `BindDynamicsDefaults` uses `sp_bindefault` and legacy catalog views (`syscolumns`, `sysobjects`). These are removed in future SQL Server versions. If migrated to SQL Server 2022 or later, `BindDynamicsDefaults` will fail.
2. **`SET ROWCOUNT` in `BindDynamicsDefaults`**: Uses `set rowcount 1` / `set rowcount 0` — deprecated in SQL Server 2022. The procedure will fail post-migration.
3. **Session-scoped staging (`SE000401`)**: `SE_Get_Acc_Detail_Hist` deletes then repopulates `SE000401` by USERID — concurrent sessions for the same USERID will produce race conditions and incorrect report results.
4. **Non-ANSI settings**: Any T-SQL that relies on ANSI behaviour (e.g., `'' = NULL` comparisons) will produce different results if ANSI settings are changed — migration risk.
5. **Named individual SQL logins**: 25+ named individual logins must be manually maintained. No evidence of automated synchronisation with HR/LDAP.
6. **`tdhruv`, `sdmello`, `tlal` logins**: Informal naming (not employee ID format) — lifecycle management harder to track.
7. **No backup configuration in SSDT**: Backup strategy for EMEAM financials not governed by source control.

## CI/CD
- No CI/CD pipeline is present in this repository.
- No `.gitlab-ci.yml`, Jenkinsfile, or equivalent.
- Active `development` branch suggests ongoing changes, making the absence of a pipeline a deployment quality risk.
- Recommendation: Source-control the GP schema for documentation purposes only; use GP upgrade installer for actual deployments. Add a dacpac build step for schema drift detection.
