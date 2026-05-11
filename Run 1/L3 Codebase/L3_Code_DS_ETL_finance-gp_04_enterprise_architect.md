# Enterprise Architect View — DS_ETL_finance-gp

## Positioning in the Onbe Data Platform

`DS_ETL_finance-gp` is the **ERP integration hub** of the Onbe financial data platform. It occupies the layer between Onbe's proprietary card programme databases and the Microsoft Dynamics GP general ledger. This is the most complex and financially consequential of the six repositories.

Architecturally, it sits at the intersection of:
- **Operational data** (ecountcore transactions, ATLYS programme records)
- **Financial reporting** (cf_report aggregations)
- **Banking infrastructure** (CitiDirect ACH and drawdown)
- **ERP general ledger** (Great Plains journal entries)

---

## Platform Generation

| Attribute | Value |
|---|---|
| Earliest package creation | `SOFeeAggregation.dtsx` — 2011-04-07 (creator: `CB_OFFICE\MButola`) |
| Most recent package modification | 2020–2021 era (based on version builds) |
| Oldest domain (creator) | `CB_OFFICE\` — Crossroads/eCount era (pre-Wirecard) |
| SSIS deployment model | **Package Deployment Model** (older, with config tables) — mixed with Project Deployment Model elements |
| SSIS version | SQL Server 2012 (v11.0.7001.0) |

This is a **first-generation to second-generation** component. `SOFeeAggregation.dtsx` with VersionBuild 1464 was created in 2011 and has been continuously evolved. This is one of the oldest actively maintained packages in the platform — a 13+ year old SSIS package with over 1,400 build increments.

---

## Role in Data Architecture

```
Card Transaction Processing (ecountcore)
  → Fee Calculation (Banker/Ecountcore)
    → SOFeeAggregation (aggregate fees)
      → SOFeeInvoicing (generate GP invoices)
        → Great Plains GL (journal entries)
          → Financial Statements (SOX)

Card Settlement (FDR files)
  → SSIS_FDR (reconcile FDR settlement)
    → cf_report (reconciliation records)
      → SSIS_GLBatchE (GL batch)
        → Great Plains GL

ACH Fund Movement (Citibank)
  → CitiDirectACH / CitidirectDrawdown
    → GP payment tables (AP)
      → Bank ledger reconciliation
```

---

## Dependencies

### Upstream Dependencies

| Dependency | Type | Criticality |
|---|---|---|
| `ecountcore` database (transaction records) | SQL Server | Critical — missing transactions = incorrect invoicing |
| `ATLYS_E` database (Atlys programme) | SQL Server | Critical — Atlys-specific revenue calculation |
| `cf_report` database | SQL Server | High — reporting aggregations as input |
| `Banker.dbo.SSISJobConfigurations` | SQL Server table | Critical — drives CPPLoopProcess orchestration |
| FDR settlement files | Flat file / SFTP | High — daily FDR file required for SSIS_FDR |
| CitiDirect banking platform | External banking API | Critical — ACH submission window |
| Great Plains installation | SQL Server (GP schema) | Critical — GL posting target |

### Downstream Dependencies

| Dependent System | What It Receives |
|---|---|
| Great Plains GL | Journal entries, AP invoices, customer payments |
| Banking partners | ACH NACHA files via CitiDirect |
| DS_ETL_great-plains | GP-format files consumed from `\\stk01\GP_Files\` |
| DS_ETL_finance | Shares cf_report and ATLYS databases; parallel consumption |
| Finance team (SOX) | GL batch exports feed period-end closes |
| Revenue Share partners | RSCheck outputs |

---

## Migration Complexity Assessment

**Modernisation difficulty: VERY HIGH**

This is the most difficult ETL set to modernise in the six repositories for multiple reasons:

1. **Age and complexity:** The oldest packages date to 2011. `SOFeeAggregation` has version build 1464 — indicating 1,464 incremental saves over 13 years. The full complexity of fee calculation logic is embedded across multiple 300+ KB packages.

2. **Banking partner integration:** CitiDirect ACH integration requires specific NACHA file formats negotiated with Citibank. Any change requires Citibank testing and approval cycles (typically 60–90 days).

3. **Great Plains coupling:** GP has a fixed, undocumented (from Microsoft's perspective) table schema. Writing directly to GP tables bypasses GP's API layer. Changes to GP version (e.g., upgrade from GP 2016 to GP 18.x) risk breaking all GL batch and payment packages.

4. **SOX-in-scope:** The GL batch export process (`SSIS_GLBatchE.dtsx`) is SOX-audited. Replacing it requires a parallel-run period and SOX auditor sign-off on the replacement.

5. **Configuration table dependency:** `Banker.dbo.SSISJobConfigurations` is undocumented and outside version control. The full schema and all job type values must be reverse-engineered before migration.

6. **Package size:** The largest package (`SSIS_FDR.dtsx` at 720 KB) represents months of development effort. Rewriting it in ADF or a modern framework is a major project.

**Estimated re-implementation effort:** 12–18 months for full migration to Azure Data Factory + Logic Apps + NACHA service, with parallel SOX validation.

**Modern replacement options:**
- Azure Data Factory for SQL-to-SQL and SQL-to-file pipelines
- Azure Functions for CitiDirect API integration
- GP REST API or eConnect for GP integration (replacing direct table writes)
- NACHA file generation microservice (replace hardcoded file formatting in SSIS)

---

## Cross-Repo Relationships

| Repo | Relationship |
|---|---|
| DS_ETL_great-plains | Heavily overlapping packages — DS_ETL_great-plains appears to be an older version or sub-project of this repo (same package names: CitiDirectACH, Onus, SOFeeInvoicing, etc.) |
| DS_ETL_finance | Shares ATLYS_E, cf_report databases; parallel financial processing |
| DS_ETL_generic-etl | Some packages (FDR_Import, IVR) are reusable variants also appearing in generic-etl |
| DS_DB_GP_EAST, DS_DB_GP_ECNT, DS_DB_GP_ECAN | Database schema repos for the GP target databases |
| DS_DB_ecountcore | Source database schema repo |

---

## Strategic Concern: Overlap with DS_ETL_great-plains

The `DS_ETL_great-plains` repo contains packages with **identical or near-identical names** to packages in this repo:
- `CitiDirectACH.dtsx`, `CitidirectDrawdown.dtsx`, `ClientRefund.dtsx`, `CPPLoopProcess.dtsx`, `FeeInvoicingACH.dtsx`, `FeeInvoicingDrawdown.dtsx`, `Onus.dtsx`, `PRD_CustomerBalance.dtsx`, `RSCheck.dtsx`, `SOFeeAggregation.dtsx`, `SOFeeInvoicing.dtsx`, `SOJobsvc.dtsx`, `SOOrdersvc.dtsx`, `SOVoid.dtsx`

This strongly suggests that `DS_ETL_great-plains` is an **older, branched or archived copy** of this repository, or a separate entity-specific variant (e.g., North vs East entities). This duplication represents a significant **maintenance risk** — changes made in one repo may not be reflected in the other, leading to logic divergence between entities.
