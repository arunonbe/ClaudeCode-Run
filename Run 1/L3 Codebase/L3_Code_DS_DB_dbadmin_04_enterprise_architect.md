# Enterprise Architect View — DS_DB_dbadmin

## Platform Generation
**Gen-2** — SSDT project with Visual Studio solution, SQL Server 2016 schema provider (Sql130), and structured security principal management. Represents a step up from the raw-script Gen-1 maintenance repo but predates modern CI/CD, IaC, and cloud-native observability approaches.

## Business Domain
Infrastructure / DBA Operations. Cross-cutting concern touching every database on the SQL Server estate. Contains domain-aware logic (`app_func_in_same_fdr_cycle`) that encodes business cycle timing from the FDR card processing world — an unusual coupling between DBA tooling and payment business rules.

## Role in the Platform
- **Observability hub** for the SQL Server estate: blocking, deadlocks, job health, drive space, index state, replication, error logs.
- **Security audit support**: orphaned users, SA password state, non-DBO objects, security role reporting — feeds into PCI DSS compliance evidence.
- **Integration point** for external monitoring tools: SiteScope (`usp_GetJobStatus_SiteScope`), FortiDB (database activity monitoring), vulnerability scanner (`vascan`), InfoSec tools (`ifs_infosec`).
- **FDR processing awareness**: `app_func_in_same_fdr_cycle` is reused across multiple systems; its presence here suggests DBAdmin is a shared library for business-logic functions used in DBA procedures.

## Dependencies

### Upstream (DBAdmin depends on)
| Component | Reason |
|---|---|
| All SQL Server databases on instance | Cross-database DMV queries, indexstats collection |
| `msdb` | SQL Agent job monitoring |
| `master` | System extended procedures, server-level DMVs |
| FortiDB agent | Pre-existing deployment of FortiDB for DBAdmin to serve report role |
| SiteScope | External monitoring that calls `usp_GetJobStatus_SiteScope` |

### Downstream (depends on DBAdmin)
| Component | Reason |
|---|---|
| DBA team monitoring workflows | All DBA diagnostics run against this database |
| SiteScope / monitoring platform | Calls `usp_GetJobStatus*` procedures |
| DS_DB_database_maintenance | Shares job monitoring pattern; `sp_job_monitor` references `dbadmin.dbo.job_monitor` |
| `DS_DB_ordersvc`, `ecountcore`, etc. | `Collect_Index_Information` cross-database dynamic SQL |
| FortiDB | Granted `FortiDBRptRole` with read access |

## Integration Patterns
- **Polling**: External tools (SiteScope, FortiDB) poll DBAdmin via SQL queries.
- **Push email**: `sp_job_monitor` and `utl_dba_drive_space_alert` push email notifications.
- **Cross-database dynamic SQL**: `Collect_Index_Information` and `Defragment_DB` use dynamic SQL to query and operate on other databases by name.
- **Shared function library**: `app_func_in_same_fdr_cycle` function is a shared utility; its placement in DBAdmin creates an implicit dependency for any procedure that calls it cross-database.

## Strategic Status
**Retain and modernise (medium priority).** DBAdmin is actively used infrastructure — its monitoring and security-audit procedures are referenced by external tools. However:

1. **Legacy email domains** must be updated immediately (operational risk).
2. **CDO mail** should be replaced with `sp_send_dbmail`.
3. **Service account over-provisioning** should be remediated (PCI DSS).
4. **Encrypted procedures** should be decrypted and placed under proper source control.
5. Long-term: evaluate migration of observability to modern platforms (Datadog, Azure Monitor, Grafana) and retain DBAdmin only for SQL-specific diagnostic procedures.

## Migration Blockers
- If migrating from SQL Server to Azure SQL MI: most procedures work as-is; `xp_fixeddrives`, `xp_sqlagent_enum_jobs`, and CDO mail will need replacement.
- If migrating to Azure SQL Database: significant rework needed; Agent jobs, cross-database queries, and many extended procedures are unsupported.
- `app_func_in_same_fdr_cycle` must be migrated alongside any application that calls it cross-database.
