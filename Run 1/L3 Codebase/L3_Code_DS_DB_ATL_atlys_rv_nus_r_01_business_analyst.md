# Business Analyst Report: DS_DB_ATL_atlys_rv_nus_r

## Repository Identity

| Field | Value |
|---|---|
| Repository name | DS_DB_ATL_atlys_rv_nus_r |
| Full meaning | Atlys Reward Value US Rollback/Reversal |
| Database project type | SQL Server Data Tools (SSDT) `.sqlproj` |
| Target SQL Server | SQL Server 2016 (DSP: `Sql130DatabaseSchemaProvider`) |
| Project GUID | `{2ad56ad6-450b-4e4f-8fc6-11888596fa5b}` |
| Source files | 12 view definitions, no tables or stored procedures |

---

## Business Purpose

This database is the **US-region rollback/reversal companion** to the primary `atlys_rv_nus` database. Like its NCA counterpart (`atlys_rv_nca_r`), this is a view-only schema that provides the Atlys financial reporting application with a stable read endpoint during deployments or rollbacks of the primary US database.

The US variant (`nus` = North America United States) is the primary revenue-reporting database for the US prepaid card programs managed through the eCount platform. The rollback variant (`_r`) contains replicated views that mirror the primary database's view structure.

**Critical distinction from the NCA rollback**: The `atlys_rv_nus_r` database is the GL configuration **source** for both itself and the NCA rollback database — the `tblGLLinks` table referenced in `atlys_rv_nca_r.vRevenueD` (`ATLYS_Rv_NUS_R.dbo.tblGLLinks`) resides **in this database**. This means the US rollback database serves dual duty: as a rollback view layer for US reporting AND as the shared GL configuration repository for the NCA reporting databases.

---

## Business Processes Supported

### 1. US Program Revenue Reporting
`vRevenue` (line 10–16) aggregates program revenue from `vRevenueT0` by program, month (normalized to the 30th of each month via `DATEADD(m, DATEDIFF(m, 30, revenue.rev_date), 30)`), and GL line code. The monthly normalization to the 30th is a business rule for consistent period-end reporting.

### 2. Gross Profit Analysis (No-Commission View)
`vGP_nc` mirrors the NCA variant's structure but for US programs. It aggregates issuance, plastics, revenue, spend, costs, virtual cards, and emboss data into a unified UNPIVOT format for cross-tab reporting.

### 3. Issuance Volume Tracking
`vIssuance` aggregates `tblissuance` by program and month (also normalized to the 30th). The monthly aggregation — rather than daily — differs from the NCA `vIssuanceD` which retains daily granularity with period join. This is a key architectural difference between the US and NCA reporting schemas.

### 4. Partner Revenue Integration
`vRevenueT_Partner` pulls partner billing data from Great Plains (US GP company, presumably `ECNT_R` or similar US company code based on context).

### 5. Face Value Discount Revenue
`vRevenueT_FVD` incorporates FVD revenue adjustments from `tblFVD_Revenue`.

### 6. GL Configuration Host
`tblGLLinks` (present in this database based on `vRevenue.sql` line 15 using a local `dbo.tblGLLinks` reference, unlike NCA which cross-references this DB) maps GL account numbers to reporting line codes used across multiple Atlys regional databases.

---

## Data Stored and Processed

This repo defines no tables or stored procedures. All views reference:

| Source | Purpose |
|---|---|
| `dbo.tblissuance` | Program load issuance |
| `dbo.revenue` | Revenue ledger |
| `dbo.tblGLLinks` | **LOCAL** — GL account to line code mapping (US + NCA shared) |
| `dbo.tblFVD_Revenue` | FVD revenue |
| `dbo.vRevenueT_Partner` | Partner GP revenue |
| `dbo.tblPlastics` (via `vPlastics`) | Physical card production |
| `dbo.tblSpend` (via `vSpend`) | Spend transactions |
| `dbo.tblfdrcosts` (via `vCosts`) | FDR processing costs |

The local `tblGLLinks` reference (line 15 of `vRevenue.sql`) distinguishes this database from the NCA variant and confirms the US rollback database hosts the authoritative GL mapping table.

---

## Business Rules in SQL

1. **Monthly date normalization**: Both `vIssuance` and `vRevenue` normalize dates to the 30th of each month using `DATEADD(m, DATEDIFF(m, 30, date), 30)`. This differs from the NCA rollback which uses explicit period table joins (`vPeriods`). The US schema uses a simpler monthly alignment formula.

2. **GL-based revenue line coding**: Revenue is grouped by GL account number mapped to named line codes via `tblGLLinks`. This mapping controls how revenue appears in financial reports (e.g., mapping GL 5800-900 to "RAF100" for refer-a-friend revenue).

3. **FVD revenue inclusion**: Same rule as NCA — FVD included from 2007 onward, non-zero net amounts only.

4. **Partner revenue GL filter**: Only GL accounts starting with '5' (revenue classification) from posted, non-voided GP sales orders are included.

---

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | No cardholder data present. Not in CDE scope. |
| **NACHA / Reg E** | ACH cost metrics flow through `vCosts`; US jurisdiction ACH rules apply to upstream data. |
| **SOX** | Revenue recognition from GP is subject to financial control; GL mapping in `tblGLLinks` is a financially significant configuration table. |

---

## Integration with Services

- **NCA databases** (`atlys_rv_nca_r`, `atlys_rv_nca`): Read `tblGLLinks` from this database via cross-database reference
- **Great Plains ERP (US)**: `vRevenueT_Partner` reads US GP sales order data
- **Atlys web application**: Consumes these views via `atlys_rvcr` stored procedures
- **FDR processor**: `tblfdrcosts` data originates from FDR settlement files loaded into the operational database
