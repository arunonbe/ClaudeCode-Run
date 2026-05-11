# DS_WH_ecount-warehouse — Enterprise Architect Report

## Platform Generation and Architectural Positioning

`DS_WH_ecount-warehouse` is a **Generation 1 (Gen-1) analytical platform** component. Evidence:
- The SSAS project `Prepaid_DW_OLAP/Domestic_OLAP.database` was created in 2012 (DSV created timestamp `2012-08-20`)
- It uses the **SQL Server 2008-era SSAS Multidimensional** model (as opposed to the more modern SSAS Tabular model introduced in SQL Server 2012)
- The reporting layer uses **SSRS 2008/2012-era `.rdl` format** with `.rptproj` Visual Studio project files
- The semantic model files use `.smdl` format, which is a legacy **Report Model** format deprecated by Microsoft in SQL Server 2016+
- The solution structure references `xOne`, `xProcess`, and `xContent` naming conventions consistent with the earliest generation of the Onbe East (eCount) architecture

This positions the warehouse as the **oldest active analytical system** in the Onbe East platform, predating the current microservices architecture by approximately a decade.

---

## Role in the Enterprise Architecture

### Layer: Analytical / Reporting
The warehouse sits at the **top of the data pyramid** — it is a consumer of operational data, not a producer. It has no write-back capability to operational systems.

```
┌─────────────────────────────────────────────────────┐
│  Business Intelligence / Reporting Layer            │
│  DS_WH_ecount-warehouse (SSAS + SSRS)               │
└────────────────────────┬────────────────────────────┘
                         │ reads from
┌────────────────────────▼────────────────────────────┐
│  Data Warehouse Layer                                │
│  prepaid_warehouse DB (SQL Server)                   │
│  DS_DB_prepaid_warehouse (separate repo)             │
└────────────────────────┬────────────────────────────┘
                         │ populated by
┌────────────────────────▼────────────────────────────┐
│  ETL Layer                                           │
│  DS_ETL_warehouse (separate repo)                   │
└────────────────────────┬────────────────────────────┘
                         │ reads from
┌────────────────────────▼────────────────────────────┐
│  Operational Data Layer                              │
│  ecountcore, cbaseapp, prepaid_warehouse (OLTP)     │
│  DS_DB_ecountcore, DS_DB_cbaseapp (separate repos)  │
└─────────────────────────────────────────────────────┘
```

### Dependency Map

**Systems that depend on DS_WH_ecount-warehouse:**
- **Client Services team** — uses `MasterCAM.rdl`, `multiCAM.rdl`, `Program Information Extract.rdl` for program management
- **Finance / Accounting** — uses settlement and billing reports (T-Mobile Weekly Billing, Pricing reports)
- **Risk team** — uses `MonthEnd_Analysis.rdl`, snapshot reports
- **Operations** — uses `JobSvc Actions.smdl` cube for batch job monitoring
- **Product / Business Development** — uses trend graphs and spending reports for client presentations

**Systems DS_WH_ecount-warehouse depends on:**
- `DS_DB_prepaid_warehouse` — the underlying SQL Server DW database
- `DS_ETL_warehouse` — the ETL process that populates the DW
- `DS_DB_ecountcore` — ultimate source of truth for transaction data
- `DS_DB_cbaseapp` — source of cardholder, account holder, and payment data

---

## Technology Stack Assessment

| Component | Technology | Generation | Support Status |
|---|---|---|---|
| OLAP Engine | SSAS Multidimensional (SQL Server 2008+) | Gen-1 | Still supported but deprecated path |
| Reporting | SSRS 2008/2012 | Gen-1 | Active support but legacy format |
| Semantic Models | `.smdl` Report Models | Gen-1 | **Deprecated by Microsoft** in SQL Server 2016 |
| Development Tool | Visual Studio SSDT | Current | Still supported |
| Data Format | Star schema SQL views | Gen-1 | Standard |

The `.smdl` files (`AccountHolder Detail.smdl`, `All Transaction Detail.smdl`, etc.) use a **Microsoft-deprecated format**. Report models (`.smdl`) were removed from SQL Server Reporting Services 2017+. This means:
- These semantic model files cannot be deployed to SSRS 2017 or later
- If SSRS is upgraded beyond 2016, all report model-based reports will break
- Migration to SSAS Tabular + Power BI or SSRS Report Builder native datasets is required

---

## Integration Points with Other Repositories

| Repository | Integration Type | Direction |
|---|---|---|
| `DS_DB_prepaid_warehouse` | Database schema | DS_WH reads from prepaid_warehouse DB |
| `DS_ETL_warehouse` | ETL population | ETL writes to prepaid_warehouse DB which DS_WH reads |
| `DS_DB_ecountcore` | Source data | Via ETL pipeline |
| `DS_DB_cbaseapp` | Source data | Via ETL pipeline (account holder data) |
| `DS_DB_cf_report` | Direct report data source | `cf_report 4A1.rds` connection |
| `DS_DB_jobsvc` | JobSvc action source | Feeds JobSvc Actions cube |
| `DS_DB_nexpay_claimable` | Claimable payment data | Feeds claimable payment reports |

---

## Migration Complexity Assessment

### Complexity: HIGH

Migrating this repository to a modern analytical architecture (e.g., Azure Synapse Analytics, Databricks, or SSAS Tabular + Power BI) would require:

1. **Schema re-engineering** — All 25+ dimension views must be re-expressed in the target platform's data model format
2. **Cube-to-tabular conversion** — SSAS Multidimensional to SSAS Tabular is not a direct migration; MDX queries must be rewritten as DAX
3. **SSRS to Power BI / Fabric** — All 60+ `.rdl` reports must be rebuilt or migrated using Power BI Report Builder (which has an import path for `.rdl`)
4. **Semantic model deprecation** — The `.smdl` Report Models have no migration path to modern platforms; each must be rebuilt as a Power BI dataset or SSRS shared dataset
5. **Report consumer re-training** — Client Services, Finance, and Risk teams are likely accustomed to the current SSRS report parameters and navigation

A conservative estimate for full migration is 6–12 months of dedicated BI development effort.

---

## Enterprise Architecture Patterns

### Current Anti-Patterns
1. **Schema drift risk** — No synchronization mechanism between the SSAS DSV and the evolving `prepaid_warehouse` schema. Last DSV update was 2017; any changes to `prepaid_warehouse` since then are not reflected.
2. **No data lineage documentation** — No catalog or lineage tool (e.g., Apache Atlas, Microsoft Purview) tracks how data flows from operational tables to warehouse views to cube measures to report columns.
3. **Monolithic report projects** — Reports are organized by consumer team folder, not by data domain. The `multiCAM.rdl` at 897 KB is a single report covering multiple data domains — this is an anti-pattern that creates maintenance complexity.
4. **Single role security** — The `CubeReader.role` approach does not support the multi-tenant program model where different clients should see only their own data.

### Recommended Target Architecture
For an Onbe East modernization roadmap:
1. **Near-term**: Implement SSAS member filters on `DimProgram_vw` and `DimAccessLevel_vw` to enforce data segregation
2. **Medium-term**: Migrate SSAS Multidimensional to SSAS Tabular (SQL Server 2022) to extend supportability
3. **Long-term**: Move to Azure Synapse Analytics + Power BI Premium for cloud-native BI with row-level security at the dataset level
