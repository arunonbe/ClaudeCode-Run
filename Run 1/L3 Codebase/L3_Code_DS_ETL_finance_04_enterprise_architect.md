# Enterprise Architect View — DS_ETL_finance

## Positioning in the Onbe Data Platform

`DS_ETL_finance` occupies the **financial reporting and client reconciliation layer** of the Onbe data platform. It sits between the operational transaction databases (`ATLYS_FcCR`, `ATLYS_RvCR`, `cf_report`) and three downstream consumers: banking partners (via flat files), the Great Plains ERP (via `Export_GP_CCP_PBR`), and the Salesforce CRM (via the forecast update package).

This is the **primary finance-facing ETL** in the platform. All other DS_ETL repos either feed into it (DS_ETL_generic-etl provides reusable patterns), receive data from it (DS_ETL_finance-gp consumes GP-ready exports), or are parallel processes (DS_ETL_great-plains handles direct GP journal entries).

---

## Platform Generation

| Attribute | Value |
|---|---|
| Solution format | Visual Studio 2010 (`Format Version 11.00`) |
| SSIS version | SQL Server 2012 (v11.0.7001.0) — confirmed across multiple packages |
| Newest package version seen | SQL Server 2017 (v14.0.3002.113) — `Monthly_Account_Balance.dtsx` creator `INT\david.tran` |
| Creator domains | `INT\david.tran`, `INT\julia.ginzburg` — Integrated/Northlane era (post-Wirecard) |
| Oldest package | `SSIS_GLBatchE.dtsx` in DS_ETL_great-plains (2008); this repo's oldest is 2019 |

This is a **third-generation** component — created during the Northlane/Onbe era (2019–2021), using SSIS 2012 tooling maintained on what appear to be SQL Server 2017 production servers.

---

## Role in Data Architecture

```
[Onbe Transaction Databases]
  ATLYS_FcCR (Fee Charge Reconciliation)
  ATLYS_RvCR (Revenue Reconciliation)
  cf_report (Financial Reporting DB)
        |
        v
[DS_ETL_finance SSIS packages]
   MonthEnd balance extraction
   Cambridge reconciliation
   GP billing export
   Salesforce forecast sync
        |
   +----|----+-------+----------+
   v         v       v          v
[CSV files] [GP ERP] [Salesforce] [Banking partners]
```

---

## Dependencies

### Upstream (what DS_ETL_finance depends on)

| Dependency | System | Risk |
|---|---|---|
| `ATLYS_FcCR` database populated | DS transaction engine | If fee charge records not written, reconciliation produces incorrect output |
| `ATLYS_RvCR` database populated | DS transaction engine | Missing revenue records cause reconciliation gaps |
| `cf_report` database populated | Reporting store (ETL from operational DBs) | Stale or incomplete cf_report data produces incorrect month-end reports |
| Banking partner schema (Cambridge) | External banking partner | Schema changes at Cambridge break `Cambridge_ReconFile.dtsx` |
| Salesforce API availability | Salesforce SaaS | Salesforce downtime breaks forecast sync |
| `\\q-na-bat03` file share | Infrastructure | Share unavailability fails all flat file output packages |
| SQL Server Agent on execution host | Infrastructure | All package scheduling depends on SQL Agent |

### Downstream (what depends on DS_ETL_finance)

| Dependent System | What It Consumes |
|---|---|
| Banking partners (Sunrise, Peoples, MB) | Month-end balance CSV files |
| Cambridge | Reconciliation file for settlement matching |
| DS_ETL_finance-gp | GP-ready billing export files (from `Export_GP_CCP_PBR`) |
| Salesforce (account managers) | Atlys forecast updates |
| Finance team / SOX reporting | Month-end balance reports |

---

## Migration Complexity Assessment

**Modernisation difficulty: HIGH**

This is the most business-critical ETL set in the six repositories. Several factors increase migration complexity:

1. **Banking partner file formats** — `Cambridge_ReconFile.dtsx` and the MonthEnd balance files have specific formats negotiated with external partners. Any format change requires partner coordination and testing cycles.

2. **SOX controls** — The month-end balance packages feed financial reporting processes. Any modernisation must include audited parallel-run testing to demonstrate output equivalence.

3. **Salesforce integration** — The `Salesforce_Update_Atlys_Forecast.dtsx` package integrates two distinct systems. Replacing this requires Salesforce API credentials management, rate limit handling, and regression testing.

4. **Multiple banking partner variants** — The parameterised `Bank` parameter (Sunrise/Peoples/MB) means there are effectively three execution profiles per MonthEnd package. Migration must preserve per-bank logic fidelity.

5. **Package size** — `MonthEnd_NegativeBalance.dtsx` at 307 KB likely contains substantial transformation logic. Full analysis requires opening in SSDT.

**Modern replacement options:**
- Azure Data Factory (ADF) pipelines for SQL-to-file and SQL-to-API patterns
- Azure Functions or Logic Apps for the Salesforce integration
- dbt (data build tool) for SQL-level transformations + Azure Blob Storage for file output

**Estimated re-implementation effort:** 6–10 weeks per major package (Cambridge, MonthEnd_NegativeBalance, Salesforce), with extensive UAT against banking partners.

---

## Cross-Repo Relationships

| Repo | Relationship |
|---|---|
| DS_ETL_finance-gp | Downstream consumer of `Export_GP_CCP_PBR.dtsx` output; shares connection to GP databases |
| DS_ETL_great-plains | Parallel GL batch export process; both repos share the `cf_report` database as a data source |
| DS_ETL_generic-etl | Provides reusable SSIS patterns; `cf_report.conmgr` appears in both repos with identical connection strings |
| DS_DB_ATL_atlys_fc_nca, DS_DB_ATL_atlys_rv_nca | Sibling repos managing the ATLYS_FcCR and ATLYS_RvCR database schema DDL |

---

## Financial Data Lineage (Key Flows)

```
Onbe card transactions
  → ecountcore (transaction processing DB)
    → cf_report (reporting DB — populated by separate ETL)
      → MonthEnd_NegativeBalance.dtsx
        → Balance CSV files → Banking partners
          → Month-end settlement reconciliation

  → ATLYS_FcCR (fee charges)
  → ATLYS_RvCR (revenue)
    → Atlys_RfCks.dtsx → Fee verification/reversal processing
    → Cambridge_ReconFile.dtsx → Cambridge reconciliation
    → Salesforce_Update_Atlys_Forecast.dtsx → Salesforce CRM
```
