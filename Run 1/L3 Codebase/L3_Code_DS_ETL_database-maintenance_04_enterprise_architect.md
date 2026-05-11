# Enterprise Architect View — DS_ETL_database-maintenance

## Positioning in the Onbe Data Platform

This repository occupies the **infrastructure maintenance layer** of the Onbe data platform. It is not a business-process ETL in the traditional sense — it does not move data between systems — but it is a critical enabler of all ETL pipelines in the adjacent repositories (DS_ETL_finance, DS_ETL_finance-gp, DS_ETL_great-plains, etc.). Without healthy index structures, the stored procedures called by financial and GP ETL packages will degrade in performance or fail on timeout.

**Platform generation:** This package was created in 2020 using SSIS 2012 (SQL Server Integration Services, version 11.0.7001.0). The SSIS Package Format Version is 6, which corresponds to SQL Server 2012–2014. The solution file format is Visual Studio 2010. This is a **second-generation** component — post the original Wirecard on-premise SQL Server estate, but pre-cloud migration.

---

## Role in Data Architecture

| Concern | Role |
|---|---|
| Query performance | Prevents fragmentation-induced slow queries across all databases (ecountcore, ATLYS_E, cf_report, GP databases, etc.) |
| ETL reliability | Reduces risk of timeout failures in adjacent ETL packages during their SQL stored procedure calls |
| Capacity management | By logging to `master.dbo.CommandLog`, provides a historical record of index growth (pages processed) that can inform future capacity planning |
| Operational database health | Acts as a synthetic SLA: if `IndexOptimize` cannot complete within 8 hours, fragmentation is accumulating faster than the maintenance window allows |

---

## Dependencies

### Upstream (what this package depends on)

| Dependency | Type | Risk if unavailable |
|---|---|---|
| Ola Hallengren `dbo.IndexOptimize` in `master` | SQL Server stored procedure | Package fails immediately on startup |
| `master.dbo.CommandLog` table | SQL Server table (Hallengren) | `@LogToTable = 'Y'` will cause execution failure if table absent |
| Windows domain `WIRECARD.LAN` / `INT` or `NAM` | Active Directory (for Integrated Security) | Authentication failure if domain trust is broken |
| `d-phl-db01.wirecard.lan` server availability | SQL Server instance | Package cannot connect to target |

### Downstream (what depends on this package)

| Dependent System | Dependency |
|---|---|
| DS_ETL_finance packages | Performance of stored procedures on `cf_report`, `ATLYS_FcCR`, `ATLYS_RvCR` databases |
| DS_ETL_finance-gp packages | Performance on `Ecountcore`, `Banker`, `ATLYS_E`, `ECAN`, `ECNT` databases |
| DS_ETL_great-plains packages | Performance on GP company databases (`ECNT`, `ECAN`, `EMEAM`, `EMXN`, `TWO`) |
| DS_ETL_generic-etl packages | Performance on `cbaseapp`, `Ecountcore_Process`, `Vendor` databases |
| All Onbe application services | General SQL Server query performance for transactional workloads |

---

## Migration Complexity Assessment

**Modernisation difficulty: LOW**

This package is unusual in the ETL set because it is a simple infrastructure automation tool rather than a complex data pipeline. Migration options:

1. **Replace with Azure SQL Database Advisor / Automatic Tuning** (if migrating to Azure SQL): Azure SQL Managed Instance and Azure SQL Database both have built-in automatic index management. This package becomes entirely redundant on Azure SQL managed offerings.

2. **Replace with Ola Hallengren SQL Agent jobs directly**: The `IndexOptimize` stored procedure can be called directly from a SQL Agent job without any SSIS wrapper. The SSIS layer here adds minimal value beyond the For Loop retry logic — which itself could be replaced by a T-SQL WHILE loop.

3. **Replace with dbatools PowerShell** (`Invoke-DbaQuery` calling `IndexOptimize`): Modern DevOps-friendly approach that integrates with PowerShell DSC and configuration management pipelines.

4. **Keep as-is**: The package is functional and low-risk. If the Onbe platform remains on SQL Server 2019/2022 on-premise or in IaaS (SQL Server on Azure VMs), this package can continue to operate unchanged — it just needs its connection string parameter updated to point to the correct server.

**Estimated re-implementation effort:** 1–2 engineer-days to replace with a SQL Agent job calling `IndexOptimize` directly.

---

## Technical Age / Platform Generation

| Attribute | Value | Implication |
|---|---|---|
| SSIS version | SQL Server 2012 (v11.0.7001.0) | Can deploy to any SSIS 2012+ catalog; backward compatible |
| .NET target | .NET Framework 4.0 | No modern async/await patterns; `System.Data.SqlClient` (legacy) |
| Creator domain | `WIRECARD\van.nguyen2` | Pre-Onbe acquisition; Wirecard-era tooling |
| VS Solution format | Visual Studio 2010 | Needs upgrade for VS 2019/2022 SSDT |
| Script task language | C# | Positive: C# script tasks are more maintainable than VB.NET equivalents found in older packages |

---

## Relationship to Other Repos in This Set

This repo is the only pure infrastructure/maintenance repo among the six. The other five all handle financial data. The naming convention `DS_ETL_*` groups all of them in the Onbe data services (DS) namespace, suggesting they are managed by the same data services team and share operational responsibility.

---

## Strategic Recommendations

1. **Decommission SSIS wrapper** and replace with a SQL Agent job T-SQL step calling `IndexOptimize` directly — simpler, easier to monitor, no SSDT dependency
2. **Add monitoring** — integrate with Onbe's platform monitoring (e.g., Datadog SQL Agent integration) to alert on failures and track fragmentation trends over time
3. **Expand scope** — if this package only handles one server, similar jobs should exist (or be created) for every production SQL Server instance (`d-na-db01`, `d-na-db02`, `q-db03`, `q-db04`, etc.) referenced across the other five ETL repos
4. **Automate deployment** — add a simple PowerShell deployment script to the repo to enable repeatable promotion across environments
