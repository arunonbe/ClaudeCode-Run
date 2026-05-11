# Business Analyst View — DS_ETL_database-maintenance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_database-maintenance`
**Solution file:** `Database-Maintenance.sln` (Visual Studio 2010 format)
**README summary:** "Contains packages used to maintain databases."

This repository contains a single SSIS project (`database-maintenance.dtproj`) with one deployed package (`IndexReorganize-Large.dtsx`). Its sole business purpose is automated database index maintenance across all platform databases, ensuring query performance does not degrade due to index fragmentation.

---

## Business Purpose

Database index fragmentation is an operational risk in high-transaction payment platforms. As Onbe processes millions of card transactions, disbursements, settlement records, and fee calculations daily, the underlying SQL Server tables accumulate fragmented B-tree indexes. Without periodic reorganisation, query execution plans degrade, response times increase, and downstream ETL pipelines (finance reconciliation, GL batch exports, settlement) run slower or time out.

This package automates the invocation of Ola Hallengren's **`IndexOptimize`** stored procedure — an industry-standard, open-source SQL Server maintenance solution — on all user databases on the target server. The procedure is well-regarded in the SQL Server DBA community and is referenced explicitly in the package's C# script task (`ScriptMain.cs`, line 503: `SqlCommand cmd = new SqlCommand("dbo.IndexOptimize", conn)`).

---

## Processes Automated

| Process | Description |
|---|---|
| Index Reorganisation (large indexes) | Calls `dbo.IndexOptimize` with `@FragmentationMedium = INDEX_REORGANIZE` and `@FragmentationHigh = INDEX_REORGANIZE` on all user databases |
| Fragmentation threshold filtering | Only indexes with fragmentation above `fragmentation_limit` (default 10%) are processed |
| Size-banded targeting | Only indexes with at least `min_number_of_pages` pages (default 6,553,600 pages ≈ large tables) are targeted, protecting small tables from unnecessary maintenance overhead |
| Execution time budgeting | Package enforces a total wall-clock time limit (`time_limit`, default 28,800 seconds = 8 hours) and a per-execution-cycle limit (`exec_time_limit`, default 3,600 seconds = 1 hour) |
| Timeout-graceful looping | On SQL timeout, the package waits `exec_delay` seconds (default 60) then retries rather than failing hard. This pattern prevents transaction log explosions during business hours |
| Logging to table | `@LogToTable = 'Y'` is passed to `IndexOptimize`, which writes completion records to the `CommandLog` table in the `master` database, providing an audit trail |

---

## Data Flows

This is a **control-flow-only** ETL package; there is no Data Flow Task. The flow is purely procedural:

1. **Get Start Time** (Expression Task) — captures `GETDATE()` into `User::start_time`
2. **Exec Loop Container** (For Loop) — iterates while `exec_done == false` AND `elapsed_time < time_limit`
   - **Execute Index Reorganize** (Script Task) — acquires the `Index Server` ADO.NET connection to `d-phl-db01.wirecard.lan` (master database) and calls `dbo.IndexOptimize` as a stored procedure with parameterised inputs
   - **Calculate Elapsed Time** (Expression Task) — recomputes seconds elapsed since start; triggers if `exec_done == false` (precedence constraint at line 964)

---

## Schedule / Frequency

No SQL Agent job definition is stored in this repository. The package is designed to run as a **long-running overnight maintenance job** (8-hour maximum window). Based on the time limit parameters and industry practice, this would typically be scheduled after business hours — likely 10 PM to 6 AM — via SQL Agent or Windows Task Scheduler on the production batch server. The per-cycle limit (1 hour) and inter-cycle delay (60 seconds) suggest the intent is to run continuously until completion or until the 8-hour window expires.

---

## Business Rules Encoded in ETL Transforms

| Rule | Location | Value |
|---|---|---|
| Minimum index size threshold | `Project.params`, parameter `min_number_of_pages` | 6,553,600 pages (only large indexes) |
| Maximum index size (optional) | `Project.params`, parameter `max_number_of_pages` | 0 (infinity — not capped) |
| Fragmentation threshold | `Project.params`, parameter `fragmentation_limit` | 10% |
| Retry on timeout | `ScriptMain.cs`, line 528–539 | Waits `exec_delay` seconds then continues loop |
| Hard error propagation | `ScriptMain.cs`, line 533–535 | Non-timeout exceptions fire SSIS error event and bubble up |
| Total time budget | `Project.params`, parameter `time_limit` | 28,800 seconds (8 hours) |
| Execution window per cycle | `Project.params`, parameter `exec_time_limit` | 3,600 seconds (1 hour) |

---

## Regulatory Relevance

**PCI DSS v4.0.1 — Requirement 6.3 (Security Vulnerabilities) / 12.3 (Risk Management):** Database performance directly impacts the availability of card transaction processing. Degraded indexes cause query timeouts in the cardholder data environment (CDE), potentially causing failed transactions. Automated maintenance is a standard operational control.

**SOX relevance:** While this package does not touch financial data directly, it underpins the availability and accuracy of all financial ETL pipelines in this repository set. Indexes on reconciliation tables, GL batch tables, and settlement tables that are reorganised by this job affect the integrity of SOX financial reporting controls downstream.

**No card data (PANs, CVVs, track data) flows through this package.** The package exclusively invokes a maintenance stored procedure and reads no business data.

---

## Creators / History

- Original package created: **2020-02-21** by `WIRECARD\van.nguyen2` on machine `PF0VELTW`
- SSIS version: SQL Server 2012 Integration Services (version 11.0.7001.0)
- The domain prefix `WIRECARD\` indicates this was built during the Wirecard-era platform, prior to the Onbe rebrand
