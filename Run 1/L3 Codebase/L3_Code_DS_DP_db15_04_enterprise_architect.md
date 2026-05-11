# Enterprise Architect Report — DS_DP_db15

## Repository Identity

**Repository:** DS_DP_db15  
**Platform Generation:** Legacy SQL Server data platform (Generation 1) — Analytics/Risk sub-tier  
**Role in Architecture:** ATM fleet management, risk analytics, and contract configuration for prepaid card programs

---

## Architectural Role

DB15 (`RiskDB`) occupies a specialised **analytical and risk management layer** within Onbe's data platform, distinct from the OLTP transaction-processing shards (db01–db08). Its function falls into three areas:

```
[Card Processors / ATM Network (Cardtronics)]
           ↓ ETL pipelines
[ECountcore_ss] ← FDR/PSX inventory and card accounts
[cf_report]     ← Plastic/forms volume data
[reportingdbserver2008] ← Legacy ATM data warehouse
           ↓ Linked server queries / direct joins
[RiskDB — Shard 15]
    ├── ATM Cash Forecast Detail (qryReports)
    ├── Stock/Emboss Reconciliation Reports
    ├── FVD Contract Configuration (EUC_DMT_ContractSummary_FIELDS)
    ├── SPAMAP Program-Account Mappings (EUC_DMT_SPAMAP_DATA)
    └── DMT Global Configuration (EUC_DMT_GLOBAL_DATA)
           ↓ Reporting application reads
[ATM Management / Risk Dashboard / Finance Reporting]
```

---

## DMT (Data Management Tool) Architecture

The `EUC_DMT_*` table family is the most architecturally significant pattern in DB15. DMT appears to be a proprietary data management framework with:

- **Change tracking:** Each data change is assigned an integer `change#` (monotonically increasing via `MAX(change#) + 1`)
- **Cache pattern:** Each entity has a `_DATA` table (all changes) and a `_DATACACHE` table (current state)
- **Updaterelated procedure:** `EUC_DMT_updaterelated @keyname, @changeid` cascades changes through the DMT entity graph
- **Multi-entity coverage:** ATM terminals, contracts, SPAMAP, global config, separations

This is a **custom audit/versioning framework** built entirely in T-SQL. It predates modern event-sourcing patterns but achieves similar goals. The architecture has the following enterprise implications:

1. **Schema coupling:** All DMT entities share the same key-value store pattern, making schema evolution difficult without touching multiple tables
2. **Performance risk:** The `MAX(change#) + 1` pattern for generating sequence IDs is vulnerable to race conditions under concurrent write load (though DMT appears to be batch-loaded, reducing this risk)
3. **Cache consistency:** The `_DATACACHE` tables must be kept in sync with `_DATA` tables via `EUC_DMT_updaterelated`; if this procedure fails silently, cache and source data diverge

---

## Legacy Infrastructure Dependency

The most significant enterprise architecture concern in DB15 is the **dependency on `reportingdbserver2008`**:

- This linked server points to a server named after SQL Server 2008, suggesting it was provisioned in the SQL Server 2008 era (pre-2010)
- The server may still be running SQL Server 2008 R2 (end of extended support: July 2019) or may have been upgraded but retained its legacy name
- The ATM cash forecast report (`OnbeATM_CashForecastDetail`) is **architecturally coupled to this legacy server** via `OPENQUERY` calls
- This represents a modernisation blocker: the ATM forecast capability cannot be migrated until this dependency is resolved

---

## Cross-Shard Data Dependencies

DB15 (RiskDB) creates read dependencies on:

| Source | Integration Type | Coupling |
|---|---|---|
| `ECountcore_ss` | Same-instance cross-database query | Tight — direct table joins |
| `cf_report` | Same-instance cross-database query | Tight — direct table joins |
| `reportingdbserver2008` | Linked server OPENQUERY | Loose but risky — network/availability dependency |

This multi-shard read pattern means RiskDB query performance is affected by the load and availability of three other databases/servers. There is no query isolation layer (views, staging tables, or APIs) between RiskDB and its data sources.

---

## Client Program Configuration Scope

The presence of TXU Energy-specific program ID updates (`US-567963`) indicates that DB15 participates in **client program lifecycle management**. Program configuration changes made here affect:
- Card issuance rules
- Account assignment
- Potentially fee and balance calculations

Changes to program IDs are high-risk: an incorrect program ID mapping could cause cards to be processed under the wrong program, affecting cardholder balances and client billing.

---

## Migration Complexity Assessment

| Migration Concern | Complexity | Notes |
|---|---|---|
| Decommissioning `reportingdbserver2008` linked server | HIGH | ATM forecast report must be rewritten without OPENQUERY |
| Migrating DMT framework to modern change-data-capture | VERY HIGH | Custom multi-table versioning system; no off-the-shelf replacement |
| Extracting RiskDB to independent analytics platform | HIGH | Deep cross-database dependencies on ECountcore_ss and cf_report |
| Migrating `qryReports` to a proper BI tool (Power BI, Tableau) | MEDIUM | Query text can be ported; execution framework needs replacing |
| Modernising FVD tier management | MEDIUM | Currently hard-coded in DMT tables; candidate for product configuration API |
