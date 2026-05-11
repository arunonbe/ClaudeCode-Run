# Data Architect Report: DS_DB_ATL_atlys_rv_nus_r

## Overview

SSDT database project targeting SQL Server 2016, containing **12 SQL view definitions** and **no other database objects** (no tables, stored procedures, functions, triggers, or indexes defined in this project). The project GUID is `{2ad56ad6-450b-4e4f-8fc6-11888596fa5b}`.

A critical architectural distinction: this database hosts a **local** `dbo.tblGLLinks` table (referenced without a database qualifier in `vRevenue.sql` line 15), making it the authoritative source for GL account-to-line-code mappings used by both this US database and the NCA sibling databases that cross-reference `ATLYS_Rv_NUS_R.dbo.tblGLLinks`.

---

## Complete Database Object Inventory

### Views (12 total)

| View Name | Source File | Purpose |
|---|---|---|
| `dbo.vCosts` | `dbo/Views/vCosts.sql` | UNPIVOTs FDR and GP cost columns into row-per-metric format |
| `dbo.vCSCallTypes` | `dbo/Views/vCSCallTypes.sql` | Customer service call counts by type |
| `dbo.vGP_nc` | `dbo/Views/vGP_nc.sql` | Master GP analysis view (no commissions); UNPIVOT structure for all financial metrics |
| `dbo.vIssuance` | `dbo/Views/vIssuance.sql` | Monthly-aggregated card issuance by program (normalized to 30th of month) |
| `dbo.vPlastics` | `dbo/Views/vPlastics.sql` | Physical card production quantities by program |
| `dbo.vPrograms` | `dbo/Views/vPrograms.sql` | Program master from Great Plains |
| `dbo.vRevenue` | `dbo/Views/vRevenue.sql` | Monthly-aggregated revenue by program and GL line code |
| `dbo.vRevenueSum` | `dbo/Views/vRevenueSum.sql` | Summarized revenue totals by program |
| `dbo.vRevenueT0` | `dbo/Views/vRevenueT0.sql` | Union of standard, FVD, and partner revenue sources |
| `dbo.vRevenueT_FVD` | `dbo/Views/vRevenueT_FVD.sql` | FVD revenue from `tblFVD_Revenue` |
| `dbo.vRevenueT_Partner` | `dbo/Views/vRevenueT_Partner.sql` | Partner revenue from Great Plains SOP tables |
| `dbo.vSpend` | `dbo/Views/vSpend.sql` | Spend summary by type (monthly, not daily like NCA) |

**Note on naming divergence**: The NCA rollback uses period-suffix names (`vIssuanceD`, `vRevenueD`) indicating daily granularity with period joins. The US rollback uses root names (`vIssuance`, `vRevenue`) with inline monthly date normalization. These are parallel schemas with different aggregation strategies.

### Tables: None defined in this project
### Stored Procedures: None
### Functions: None
### Triggers: None

---

## Referenced External Objects (not defined here)

| Table | Location | Data Category |
|---|---|---|
| `dbo.tblGLLinks` | **LOCAL** (this database) | GL account to reporting line code mapping — financially significant config |
| `dbo.tblissuance` | atlys_rv_nus primary | Program load issuance |
| `dbo.revenue` | atlys_rv_nus primary | Revenue ledger |
| `dbo.tblFVD_Revenue` | atlys_rv_nus primary | FVD adjustments |
| `dbo.tblfdrcosts` | atlys_rv_nus primary | FDR processing costs |
| `dbo.tblgprecords` | atlys_rv_nus primary | GP cost records |
| `dbo.tblPlastics` | atlys_rv_nus primary | Card production |
| `dbo.tblSpend` | atlys_rv_nus primary | Spend data |
| GP ERP tables (`RM00101`, `SOP10102`, etc.) | Cross-database (US GP) | Customer and billing data |

---

## Sensitive Data Field Assessment

### PCI DSS Cardholder Data
**None found.** No PANs, CVV, track data, or PIN values are present in any view definition.

### PII Assessment
| Field | View | Notes |
|---|---|---|
| `CUSTNAME` (via GP RM00101) | `vPrograms` | Business entity name (B2B), not consumer PII |
| `acctg_name` | `vRevenueT0` | Client accounting name — business entity |
| `PROGRAM_MGR` | `vPrograms` | Internal employee identifier |

### Financially Significant Data

| Field | Location | Sensitivity |
|---|---|---|
| `gl_acct_num`, `line_cde` | `tblGLLinks`, `vRevenue` | GL mapping configuration — financial control data |
| `amount`, `price` | `revenue`, `vRevenueT0` | Program revenue figures |
| `alloc_grp` | `tblGLLinks` | Revenue allocation group codes |

The `tblGLLinks` table is a financially significant configuration table because it determines how revenue is categorized in financial reports. Changes to this table could misstate financial results.

---

## Key Architectural Difference: US vs. NCA Rollback

| Feature | atlys_rv_nus_r (US) | atlys_rv_nca_r (NCA) |
|---|---|---|
| Date aggregation | Monthly (inline formula) | Daily with vPeriods join |
| GL mapping source | LOCAL `tblGLLinks` | Cross-DB from ATLYS_Rv_NUS_R |
| View count | 12 | 13 |
| Extra NCA views | N/A | `vPeriods` (NCA has period dimension) |
| `vIssuanceD` | `vIssuance` (no period join) | `vIssuanceD` (with period join) |

---

## Encryption at Rest
No encryption DDL present. TDE and column-level encryption must be verified at the SQL Server instance level.

## Data Classification Summary

| Category | Present | Detail |
|---|---|---|
| PCI DSS CDE | No | No cardholder data |
| Consumer PII | No | Business entity names only |
| Financial program data | Yes | Revenue, cost, issuance — internal |
| GL configuration | Yes | `tblGLLinks` — shared across regional DBs |

## PCI DSS CDE Scope
**OUT OF SCOPE.** No cardholder data present. The `tblGLLinks` table is a financial configuration object, not a payment data object.

## Referential Integrity
No foreign keys defined in this project. The `tblGLLinks` table is referenced by NCA databases via cross-database join; consistency relies on application-layer controls.

## Data Retention
Not defined in this project. Managed in upstream operational databases.
