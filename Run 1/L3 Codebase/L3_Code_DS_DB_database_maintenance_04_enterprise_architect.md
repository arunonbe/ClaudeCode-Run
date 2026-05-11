# Enterprise Architect View — DS_DB_database_maintenance

## Platform Generation
**Gen-1** — Pre-SSDT, script-only maintenance tooling. No project model, no declarative schema, no pipeline integration. Represents the original Wirecard Data Services DBA practices inherited at acquisition.

## Business Domain
Infrastructure / Platform Engineering. Zero overlap with business domains (payments, disbursements, cardholder management). This is a cross-cutting operational concern touching every database on the SQL Server estate.

## Role in the Platform
- Foundational: all SQL Server databases that drive transactional workloads (ordersvc, ecountcore, banker, strongbox, etc.) depend on this maintenance regime for sustained query performance and data integrity.
- Supports Availability SLA obligations by preventing index fragmentation degradation under high-write prepaid card workloads.
- Supports PCI DSS Req 12.3 operational procedures by providing scheduled, logged maintenance.

## Dependencies
### Upstream (this repo depends on)
| Component | Reason |
|---|---|
| Ola Hallengren SQL Server Maintenance Solution v2019-12-01 | All execution is delegated to framework objects in `master` |
| SQL Server Agent | Job scheduling and execution |
| Windows Authentication (NTLM/Kerberos) | `sqlcmd -E` uses service account identity |

### Downstream (depends on this repo)
| Component | Reason |
|---|---|
| All SQL Server databases on instance | Index health, statistics freshness, integrity validation |
| Monitoring systems (SiteScope, etc.) | May query job status or CommandLog |

## Integration Patterns
- **Push-only**: SQL Agent jobs fire on schedule; no external trigger or API surface.
- **Local-only**: `@server_name = N'(local)'` — jobs are always local to the instance where scripts are deployed. Multi-instance estate requires separate deployment per host.
- **Polling log**: `CommandLog` can be polled externally (monitoring tools, SiteScope via DBAdmin `usp_GetJobStatus_SiteScope`) for operational status.

## Strategic Status
**Retain with hardening.** The Ola Hallengren solution is a widely-adopted industry standard and remains appropriate for Gen-1/Gen-2 SQL Server instances. It is not a migration target itself; it supports the SQL Server estate regardless of generation.

Key gaps to address before strategic review:
1. Promote to SSDT project for proper versioning and pipeline integration.
2. Add CommandLog retention cleanup job.
3. Replace `sa` job ownership with a dedicated service account.
4. Add backup job scripts (currently absent despite README claim).

## Migration Blockers
- None that block migration of other components. This repo is infrastructure-only.
- If the SQL Server estate is migrated to Azure SQL Managed Instance or Azure SQL Database, the Ola Hallengren solution is partially supported (Azure SQL DB does not support `IndexOptimize` across all features). This would require migration to Azure Automation or elastic jobs.
