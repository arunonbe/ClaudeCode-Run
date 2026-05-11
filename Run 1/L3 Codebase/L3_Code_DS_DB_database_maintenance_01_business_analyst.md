# Business Analyst View — DS_DB_database_maintenance

## Business Purpose
This repository contains SQL Server maintenance automation scripts for the Wirecard/Onbe Data Services SQL Server estate. It is entirely infrastructure-facing with no direct business transaction logic. Its purpose is to ensure database availability, performance, and integrity — capabilities that underpin every customer-facing payment and disbursement system.

## Capabilities
- **Index reorganization and rebuild**: Time-aware, fragmentation-driven index maintenance across all user databases, using Ola Hallengren's `IndexOptimize` framework as the execution engine.
- **Statistics refresh**: Incremental statistics update on all user databases, run as a second SQL Agent job step after index work.
- **Database integrity check**: Weekly `DBCC CHECKDB` (physical-only) across all databases, with a 9-hour time cap, for early detection of storage corruption.
- **Job scheduling**: Two SQL Agent jobs (`DBMP User Databases -- Index and stats reorg (custom)` and `DBMP User Databases -- Integrity Check (custom)`) are scripted in full, including schedules, categories, email notification operators, and failure handling.

## Key Entities
| Entity | Description |
|---|---|
| `CommandLog` (master) | Ola Hallengren audit table logging every index/stats command executed, start/end time, errors |
| SQL Agent Job: Index reorg | Daily midnight run; adaptive time limits by hour-of-day |
| SQL Agent Job: Integrity Check | Weekly (Saturday 21:00), 9-hour time limit |
| `IndexOptimize_AgentWrapper` SP | Custom wrapper controlling fragmentation thresholds and time windows |

## Business Rules
1. Index maintenance is disabled on servers whose name starts with `C` (`@enabled = CASE WHEN LEFT(@@SERVERNAME,1) = 'C' THEN 0 ELSE 1 END`) — interpreted as a convention for non-production/CI servers.
2. Nightly window (00:00–05:00): up to 150-minute runtime; only indexes ≤ 50 GB pages processed.
3. Morning window (05:00–07:00): run must complete by 07:00.
4. Business hours (07:00+): only 15 minutes of index work allowed.
5. Medium fragmentation triggers `INDEX_REORGANIZE`; high fragmentation triggers `INDEX_REBUILD_ONLINE` first, then `INDEX_REORGANIZE`.
6. Statistics update uses `@OnlyModifiedStatistics = 'Y'` — only statistics changed since last update are refreshed.
7. Integrity check uses `@PhysicalOnly = 'Y'` (fast CHECKSUM scan); logical check is not configured.

## Process Flows
1. **Nightly index maintenance**: SQL Agent fires at 00:30 → `IndexOptimize_AgentWrapper` → computes time budget → calls `master.dbo.IndexOptimize` → step 2 stats update → complete. On failure: job fails (no retry).
2. **Weekly integrity check**: Saturday 21:00 → `DatabaseIntegrityCheck @Databases='ALL_DATABASES'` → `@PhysicalOnly='Y'` → runs up to 9 hours → logs to `CommandLog`.

## Compliance Concerns
- PCI DSS Req 10 (audit logs): `CommandLog` provides a maintenance audit trail; however it lives in `master` and its retention is not managed by this repo.
- PCI DSS Req 12.3.4 / availability: Scheduled maintenance protects database performance and integrity — directly supports system availability obligations.
- The integrity check is physical-only; a full logical `DBCC CHECKDB` would provide stronger corruption detection under PCI DSS data-integrity expectations.

## Risks
- **Single-owner SA account**: Both jobs are owned by `sa` — a shared, highly-privileged login. Violates PCI DSS Req 7/8 (least privilege, individual accountability).
- **No backup job** in this repo despite README claiming backup coverage. Backup scripts are absent from the codebase.
- **Email hardcoded to `DataServicesGroup-Operator`**: Failure notifications depend on this operator existing at deployment time; no validation.
- **Physical-only integrity check**: Logical corruption (e.g., torn page, allocation errors) may not be caught until data loss occurs.
- **No CI/CD pipeline**: Scripts are manually deployed with no automated testing or validation gate.
