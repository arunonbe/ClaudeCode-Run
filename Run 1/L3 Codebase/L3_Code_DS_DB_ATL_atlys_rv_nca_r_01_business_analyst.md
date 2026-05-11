# Business Analyst Report: DS_DB_ATL_atlys_rv_nca_r

## Repository Identity

| Field | Value |
|---|---|
| Repository name | DS_DB_ATL_atlys_rv_nca_r |
| Full meaning | Atlys Reward Value NCA Rollback/Reversal |
| Database project type | SQL Server Data Tools (SSDT) `.sqlproj` |
| Target SQL Server | SQL Server 2016 (DSP: `Sql130DatabaseSchemaProvider`) |
| Solution file | `atlys_rv_nca_r.sln` |
| Source files | 13 view definitions, no tables or stored procedures |

---

## Business Purpose

This database is a **rollback/reversal variant** of the Atlys Reward Value NCA (Non-Canada Americas) financial reporting database. It exists as a **read-only reporting layer** that sits on top of operational data from the eCount core platform and the Great Plains (GP) ERP system. The `_r` suffix in the database name consistently indicates a rollback or reversal companion to the primary database (`atlys_rv_nca`), meaning this schema holds replicated reporting views that can be swapped in when the primary database must be rolled back during a deployment.

The primary role is to **support the Atlys financial reporting and analytics web application** (part of the `atlys_WAPP` service) with pre-built views that aggregate program-level financial data across:

- Card issuance volumes and dollar amounts
- Revenue recognition by type and GL account
- Transaction spend by category
- Physical card (plastics) production quantities
- Cost allocation (FDR transaction costs, stock, CS, IVR, Telecom, royalties)
- Gross Profit (GP) calculation by program

---

## Business Processes Supported

### 1. Revenue Reporting
Views `vRevenueT0`, `vRevenueD`, `vRevenueDSum`, `vRevenueT_FVD`, and `vRevenueT_Partner` together provide a unified revenue fact layer. Revenue sources include:
- Standard program revenue from the `revenue` table (local)
- Face Value Discount (FVD) revenue from `tblFVD_Revenue`
- Partner/affiliate revenue sourced directly from Great Plains (`ECAN_R.dbo.SOP10102`, `SOP30200`, `GL00100`) via cross-database linked server joins

The partner revenue view (`vRevenueT_Partner`, line 3–8) extracts posted, non-voided sales entries from GP with GL accounts beginning with '5' (revenue accounts). This represents actual client billing postings in Great Plains.

### 2. Gross Profit Analysis
`vGP_nc` (vGP Non-Commission) is the master analytical view used by stored procedure `sys_gp_details_cross_tab` in the primary `atlys_rvcr` database. It UNPIVOTs dozens of financial metrics (issuance, plastics, revenue, costs, spend, virtual cards, emboss adjustments) into a long-format dataset allowing the Atlys UI to render cross-tab GP reports per program per period.

### 3. Issuance and Load Tracking
`vIssuanceD` (line 1–7) aggregates `tblIssuance` by program and date, then joins to `vPeriods` to assign each issuance record to a reporting period. This supports load volume monitoring.

### 4. Plastic Card Tracking
`vPlasticsD` aggregates `tblPlastics` card production records. This supports tracking of embossed card quantities ordered for each program.

### 5. Spend Analysis
`vSpendD` pivots `tblSpend` (spend by type, program, date) against the period calendar. Spend types include purchase, ATM, and other transaction categories.

### 6. Cost Allocation
`vCosts` UNPIVOTs `tblfdrcosts` and `tblgprecords` into a row-per-cost-type format, covering transaction processing costs (FDR), stock, ATM, ACH, merchant, product, CS, telecom, and IVR.

---

## Data Stored and Processed

This repo defines **no tables or stored procedures** — it is purely a view layer. All views select from:

| External database | Purpose |
|---|---|
| `dbo.tblIssuance` | Local load issuance amounts and counts |
| `dbo.tblPlastics` | Local physical card production |
| `dbo.tblSpend` | Local spend transaction summaries |
| `dbo.tblfdrcosts` | Local FDR (First Data Resources) cost data |
| `dbo.tblgprecords` | Local GP cost summary records |
| `dbo.tblFVD_Revenue` | Face Value Discount revenue adjustments |
| `dbo.revenue` | Core revenue ledger records |
| `dbo.tblGLLinks` (via `ATLYS_Rv_NUS_R`) | GL account to line code mapping — cross-database |
| `ECAN_R.dbo.RM00101`, `RM00303` | Great Plains receivables master — cross-database |
| `ECAN_R.dbo.SOP10102`, `SOP30200` | GP sales order details — cross-database |
| `ECAN_R.dbo.GL00100` | GP general ledger account codes — cross-database |
| `dbo.tblCoreVirtual` | Virtual card counts by program |
| `dbo.tblCoreEmboss`, `tblCoreEmbossAdjust` | Physical emboss production with vendor |
| `dbo.tblCostsAllocMethodExtVendorRates` | Vendor-based cost allocation rates |

The cross-database reference to `ATLYS_Rv_NUS_R.dbo.tblGLLinks` (seen in `vRevenueD.sql` line 15 and `vGP_nc.sql` line 127) indicates this NCA rollback database shares GL mapping definitions with the US rollback sibling, implying a common GL structure across geographic variants.

---

## Business Rules Expressed in SQL

1. **Period assignment**: All aggregated metrics join to `vPeriods` using `BETWEEN p.date1 AND p.date2`, binding each transaction to a monthly/weekly reporting period.
2. **Partner revenue filter**: Only posted (`POSTED = 1`), non-voided (`VOIDSTTS = 0`) GP transactions with GL accounts starting with '5' (revenue type) are included (`vRevenueT_Partner.sql`, lines 5–7).
3. **FVD revenue inclusion**: Revenue from FVD is included only for dates from `1/1/2007` onward, and only when the net FVD amount after adjustments is non-zero (`vRevenueT_FVD.sql`, lines 5–8).
4. **Deduplication of GP programs**: `vPrograms` filters out duplicate program records from GP's `RM00101` by retaining only the highest `DEX_ROW_ID` per program, removing hyphenated sub-records.
5. **Zero suppression**: `vCosts` and `vGP_nc` suppress rows where amount = 0 to reduce result set size.
6. **CS call type tracking**: `vCSCallTypes` tracks customer service call volume by type, contributing to the CS cost and volume analysis in the GP view.

---

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | This database handles **no cardholder data** (no PANs, CVV, track data). It is a financial analytics layer only. Not in PCI DSS CDE scope. |
| **NACHA / Reg E** | References ACH cost metrics (`ach_qty`, `ach_cst` in `vCosts`/`vGP_nc`), indicating that ACH withdrawal volumes and costs flow through this reporting layer. |
| **SOX / Financial reporting** | Revenue recognition data sourced from GP ERP is subject to financial close controls. Cross-database GP joins must align with GP posting dates for accurate period reporting. |
| **GLBA** | No PII or financial account data specific to cardholders is present. |

---

## Data Flows

```
eCount Core (tblIssuance, tblPlastics, tblSpend, tblfdrcosts, tblgprecords, revenue)
        |
        v
atlys_rv_nca_r views (vIssuanceD, vPlasticsD, vSpendD, vCosts, vRevenueT0)
        |
        +-- ATLYS_Rv_NUS_R.dbo.tblGLLinks (GL mapping)
        +-- ECAN_R (GP ERP: SOP10102, GL00100, RM00101)
        |
        v
vGP_nc, vRevenueD, vRevenueDSum
        |
        v
Atlys web application (atlys_WAPP) -> Finance reporting users
```

---

## Integration with Services

- **ATLYS_E** (Atlys Engine): The primary `atlys_rvcr` stored procedures reference `ATLYS_E.dbo.sys_chkuser` for access control, indicating this rollback database participates in the same security framework.
- **ECAN_R**: Linked server to Great Plains ERP (NCA region). Cross-database joins in `vPrograms` and `vRevenueT_Partner` pull live GP data.
- **ATLYS_Rv_NUS_R**: The US rollback sibling database provides the `tblGLLinks` table, suggesting shared GL mapping infrastructure.
- **Atlys reporting web application**: The Atlys WAPP queries these views (mediated through stored procedures in the active rvcr/nca databases) to render financial dashboards.
