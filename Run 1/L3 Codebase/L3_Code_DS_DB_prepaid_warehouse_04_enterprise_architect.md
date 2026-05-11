# DS_DB_prepaid_warehouse — Enterprise Architect Assessment

## 1. Platform Generation

The Prepaid Warehouse is a **second-generation on-premises analytical database** built on classic SSDT/SQL Server patterns. It targets SQL Server 2016 (DSP Sql130) and uses .NET Framework 4.6.1 build tooling. The architecture is a conventional star-schema data warehouse with partition-based OLAP support. This is representative of a platform generation from approximately 2010–2018.

No cloud-native analytics patterns (Azure Synapse, Databricks, Redshift) are used. No streaming ingestion (Kafka, Event Hub) is present. The warehouse depends on SQL Server-linked servers for cross-database queries against operational sources.

---

## 2. Role in the Onbe Architecture

The Prepaid Warehouse occupies the **reporting and analytics layer** for the US prepaid business:

```
Operational Layer          ETL/CDC Layer           Analytics Layer
─────────────────          ─────────────           ───────────────
EcountCore (OLTP)    -->   stagingdata.*  -->   dim.* + fact.*
FDR Processor        -->   dbo work tables -->  Reporting SPs
JobService           -->                        OLAP Cube (external)
```

Downstream consumers include:
- Crystal Reports (referenced via `DS_RPT_crystal-invoice-templates-us` repo)
- OLAP cubes fed via `_OLAPInc` tables
- External data feeds (TTS, Citi — via `rpt_TTS_data_feed_Citi`)
- Internal reporting users (via `NAM_GTS_ECNT_DAT_PPDW_NA_RptgUsers` group)
- Enterprise Risk group (Rpt_Risk_* procedures)
- Client services team (standard issuance and spending reports)

---

## 3. System Dependencies

### 3.1 Upstream (Data Sources)
| Source System | Access Method | Data Pulled |
|---|---|---|
| EcountCore (`ecountcore_SS`) | Linked server `[REPORTINGDBSERVER]` | FDR card/DDA account tables, member data, balance data |
| EcountCore Process (`Ecountcore_Process_ss`) | Linked server | Auth/CHD DCAF data |
| FDR Processor | Via ecountcore tables | Card account detail, DDA accounts |
| JobService | CDC | Job service action events |
| Citi systems | Via NACHA file processing | Nacha/deposit data |

### 3.2 Downstream (Consumers)
| Consumer | Access Pattern |
|---|---|
| Crystal Reports | Direct SQL query via reporting role |
| OLAP Cube | Polling `_OLAPInc` tables |
| Client analytics portals | Stored procedure calls |
| TTS / Citi partners | Stored procedure output (data feed) |
| Enterprise Risk | Stored procedure calls + direct queries |
| Ad-hoc DBA/analyst | Direct table access via reporting role |

### 3.3 Cross-Database References
The warehouse references `[REPORTINGDBSERVER]` (linked server) in stored procedures. This is a hardcoded server name that couples the warehouse to its operational database server. Any migration, failover, or rename of the reporting server requires updating all affected stored procedures.

---

## 4. Migration Complexity Assessment

### 4.1 Schema Migration
The warehouse schema is large but structurally conventional. A migration to a cloud analytics platform (Azure Synapse Analytics or Azure SQL Data Warehouse) would require:
- Porting approximately 120 stored procedures — many use SQL Server-specific syntax (partition functions, `OPTION (LOOP JOIN)`, `@@IDENTITY`, linked server queries)
- Re-implementing partition schemes as Synapse distribution/partition strategies
- Converting columnstore indexes to Synapse columnstore tables
- Replacing linked server references with external data sources or ADF pipelines

Estimated migration complexity: **High** (6–12 month effort for full migration with parity testing)

### 4.2 ETL Migration
The ETL pipeline is currently implemented as SQL stored procedures running as SQL Agent jobs (inferred). Migration to a modern ETL framework (Azure Data Factory, dbt, Apache Spark) would require re-engineering the entire ETL layer, not just the schema.

### 4.3 OLAP Migration
The `_OLAPInc` pattern feeds an external OLAP cube product (likely SQL Server Analysis Services, SSAS). Migration to Power BI Premium or Azure Analysis Services requires cube model re-authoring.

---

## 5. Integration Patterns

### 5.1 Linked Server Queries
Multiple stored procedures reference `[REPORTINGDBSERVER].Ecountcore_SS.dbo.*` and `[REPORTINGDBSERVER].Ecountcore_Process_SS.dbo.*`. This distributed query pattern:
- Creates tight coupling to the operational server
- Can cause performance degradation if the linked server connection is slow
- Cannot be easily tested in isolation without the linked server connection

### 5.2 Cross-Database Views
The `_vw` views in `dim/` and `fact/` schemas provide a consistent query interface for reporting consumers, decoupling the physical table structure from report queries.

---

## 6. Technical Debt Inventory

| Debt Item | Location | Risk Level |
|---|---|---|
| Date-stamped procedure variants | `dbo/Stored Procedures/rpt_Inventory_Management_Report_card_reissue_*` | Low — dead code accumulation |
| Hardcoded `[REPORTINGDBSERVER]` linked server name | Multiple stored procedures | Medium — operational brittleness |
| No CI/CD pipeline | Repo root | High — unvalidated deployments |
| `DimTransactionTypeOLD` retained in production schema | `dim/Tables/` | Low — suggests incomplete migration |
| Work table proliferation (~60 tables) | `dim/`, `fact/`, `dbo/` | Medium — maintenance overhead |
| `SqlServerVerification = False` in sqlproj | `Prepaid_Warehouse.sqlproj` line 22 | Medium — build-time SQL errors not caught |
| No data retention policy in schema | All tables | High — CCPA/privacy compliance risk |

---

## 7. Architectural Risks

1. **Single reporting server dependency** — all ETL and reporting depends on `[REPORTINGDBSERVER]`. There is no evidence of read replica or HA/DR failover for the reporting server.
2. **No column-level encryption or dynamic data masking** — PII in `DimAccountHolder` is fully accessible to any role with `db_datareader` membership.
3. **Incremental OLAP consistency** — the `_OLAPInc` tables are populated separately from the main fact tables. If an ETL run populates the main fact but fails before populating `_OLAPInc`, the OLAP cube will be out of sync with the warehouse, producing incorrect analytics without visible error.
4. **No event-driven architecture** — the warehouse is entirely batch-driven. Near-real-time reporting needs (e.g., same-day risk monitoring) cannot be served by this architecture.
