# Data Architect View — DS_DB_database_maintenance

## Data Stores
| Store | Location | Purpose |
|---|---|---|
| `master.dbo.CommandLog` | SQL Server `master` database | Audit log of every maintenance command (index rebuild, stats update, integrity check) |
| `msdb.dbo.sysjobs` / SQL Agent catalog | `msdb` | Job definitions, schedules, history |
| Target user databases (all) | Each database instance | Databases being maintained |

## Schema and Tables
### `CommandLog` (created by MaintenanceSolution install)
| Column | Type | Notes |
|---|---|---|
| ID | int IDENTITY PK | Row identifier |
| DatabaseName | sysname | Target database |
| SchemaName | sysname | Target schema |
| ObjectName | sysname | Target object (index/table) |
| ObjectType | char(2) | U = user table, IX = index |
| IndexName | sysname | Index name |
| IndexType | tinyint | 1=clustered, 2=nonclustered |
| StatisticsName | sysname | Statistics name if stat update |
| PartitionNumber | int | Partition number |
| ExtendedInfo | xml | Additional XML metadata |
| Command | nvarchar(max) | Exact T-SQL command executed |
| CommandType | nvarchar(60) | e.g., ALTER_INDEX, UPDATE_STATISTICS |
| StartTime | datetime | Execution start |
| EndTime | datetime | Execution end (null if running/failed) |
| ErrorNumber | int | SQL error number if failure |
| ErrorMessage | nvarchar(max) | SQL error text if failure |

No other tables are created or owned by this repository.

## Sensitive Data Handling
- No PII, payment card data, or financial data is stored or processed by this repo.
- `CommandLog.Command` contains T-SQL DDL strings (index names, table names) — no row-level data is captured.
- `CommandLog.ErrorMessage` may contain schema hints from error text, but not sensitive data.

## Encryption and Protection
- No encryption is applied to `CommandLog` or SQL Agent job definitions.
- No TDE (Transparent Data Encryption) settings are configured by this repository.
- SQL Agent job steps use Windows-authenticated `sqlcmd -E` — no embedded SQL credentials in scripts.

## Data Flow
```
SQL Agent Scheduler
  -> IndexOptimize_AgentWrapper (master)
       -> master.dbo.IndexOptimize (Ola Hallengren framework)
            -> Issues ALTER INDEX / UPDATE STATISTICS on target databases
            -> Writes to master.dbo.CommandLog

SQL Agent Scheduler (weekly)
  -> master.dbo.DatabaseIntegrityCheck
       -> Issues DBCC CHECKDB (PhysicalOnly) on all databases
       -> Writes to master.dbo.CommandLog
```

## Data Quality and Retention
- `CommandLog` has no retention policy defined in this repository. Over time this table grows without bound.
- The Ola Hallengren framework recommends a scheduled cleanup job for `CommandLog`; it is not present in this repo.
- No data quality rules apply (this is a DBA operations repo, not an application data repo).

## Compliance Gaps
1. **Backup configuration absent**: README describes backup as in-scope; no backup scripts or schedules exist in the repo. This is a gap against PCI DSS Req 12.3 (protect system components) and business continuity obligations.
2. **CommandLog retention not managed**: Unbounded log growth in `master` risks performance degradation and disk exhaustion on primary instances.
3. **No TDE verification**: This repo does not verify or enforce TDE on any databases in scope. Encryption state of databases is not tracked here.
4. **Physical-only integrity check**: CHECKDB with `@PhysicalOnly = 'Y'` does not perform allocation checks or logical consistency checks. Full logical integrity checks are not scheduled.
