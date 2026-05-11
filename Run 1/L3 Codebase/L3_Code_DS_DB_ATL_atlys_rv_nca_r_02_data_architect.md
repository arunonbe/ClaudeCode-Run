# Data Architect Report: DS_DB_ATL_atlys_rv_nca_r

## Overview

This SSDT database project (target SQL Server 2016, `Sql130DatabaseSchemaProvider`) contains **13 SQL views** and **no tables, stored procedures, functions, triggers, or indexes** of its own. It is a pure reporting-layer overlay that queries tables residing in the same database instance (assumed to be from the primary `atlys_rv_nca` database promoted into this schema) and cross-database references to `ATLYS_Rv_NUS_R` and `ECAN_R`.

Project GUID: `{7a2f995c-134d-48d1-ade0-2a8b34eff41e}` (`atlys_rv_nca_r.sqlproj`, line 9).

---

## Complete Database Object Inventory

### Views (13 total)

| View Name | Source File | Purpose |
|---|---|---|
| `dbo.vCosts` | `dbo/Views/vCosts.sql` | UNPIVOTs FDR and GP cost columns into row-per-metric format |
| `dbo.vCSCallTypes` | `dbo/Views/vCSCallTypes.sql` | Customer service call counts by type |
| `dbo.vGP_nc` | `dbo/Views/vGP_nc.sql` | Master GP analysis view (no commissions); 15+ UNION ALL segments |
| `dbo.vIssuanceD` | `dbo/Views/vIssuanceD.sql` | Aggregated card issuance amounts and counts by program/date/period |
| `dbo.vPeriods` | `dbo/Views/vPeriods.sql` | Calendar period dimension (date1, date2) |
| `dbo.vPlasticsD` | `dbo/Views/vPlasticsD.sql` | Aggregated plastic card production quantities |
| `dbo.vPrograms` | `dbo/Views/vPrograms.sql` | Program master from Great Plains RM00101; deduped by DEX_ROW_ID |
| `dbo.vRevenueD` | `dbo/Views/vRevenueD.sql` | Period-banded revenue detail with GL line codes |
| `dbo.vRevenueDSum` | `dbo/Views/vRevenueDSum.sql` | Period-banded revenue totals |
| `dbo.vRevenueT0` | `dbo/Views/vRevenueT0.sql` | Union of standard revenue, FVD revenue, and partner revenue |
| `dbo.vRevenueT_FVD` | `dbo/Views/vRevenueT_FVD.sql` | Face Value Discount revenue from `tblFVD_Revenue` |
| `dbo.vRevenueT_Partner` | `dbo/Views/vRevenueT_Partner.sql` | Partner revenue from Great Plains SOP tables |
| `dbo.vSpendD` | `dbo/Views/vSpendD.sql` | Period-banded spend summary by type |

### Tables: None (defined in this project)
### Stored Procedures: None
### Functions: None
### Triggers: None
### Indexes: None

---

## External Table Dependencies

The views rely on the following tables (not defined in this project):

| Table | Assumed Database | Data Category |
|---|---|---|
| `dbo.tblIssuance` | atlys_rv_nca | Program load issuance: amounts, counts |
| `dbo.tblPlastics` | atlys_rv_nca | Card emboss/plastics production |
| `dbo.tblSpend` | atlys_rv_nca | Spend transaction summaries |
| `dbo.tblfdrcosts` | atlys_rv_nca | FDR processor cost breakdown |
| `dbo.tblgprecords` | atlys_rv_nca | GP cost records (CS, Telco, IVR) |
| `dbo.tblFVD_Revenue` | atlys_rv_nca | Face Value Discount revenue |
| `dbo.revenue` | atlys_rv_nca | Core revenue ledger |
| `dbo.tblCoreVirtual` | atlys_rv_nca | Virtual card production |
| `dbo.tblCoreEmboss` | atlys_rv_nca | Physical emboss with vendor info |
| `dbo.tblCoreEmbossAdjust` | atlys_rv_nca | Emboss adjustment records |
| `dbo.tblCostsAllocMethodExtVendorRates` | atlys_rv_nca | Vendor cost allocation rates |
| `dbo.tblGLLinks` | ATLYS_Rv_NUS_R (cross-DB) | GL account to reporting line code mapping |
| `ECAN_R.dbo.RM00101` | Great Plains ERP | Customer/program master |
| `ECAN_R.dbo.RM00303` | Great Plains ERP | Customer address/country |
| `ECAN_R.dbo.rsm_customer_rollup` | Great Plains ERP | Customer hierarchy rollup |
| `ECAN_R.dbo.SOP10102` | Great Plains ERP | Posted sales order line details |
| `ECAN_R.dbo.SOP30200` | Great Plains ERP | Sales order header (history) |
| `ECAN_R.dbo.GL00100` | Great Plains ERP | GL account master |

---

## Sensitive Data Field Assessment

### PCI DSS Sensitive Authentication Data / Cardholder Data

| Field | Table | Classification | Flag |
|---|---|---|---|
| None found | — | — | No PAN, CVV, Track, PIN present |

This database contains **no cardholder data**. It is a financial analytics layer. Confirmed not in PCI DSS CDE scope.

### Personally Identifiable Information (PII)

| Field | Table/View | Notes |
|---|---|---|
| `CUSTNAME` | `vPrograms` (via `ECAN_R.RM00101`) | Client/company name from GP — business entity name, not consumer PII |
| `PROGRAM_MGR` | `vPrograms` (via `ECAN_R.RM00101.SLPRSNID`) | Internal sales person identifier |
| `acctg_name` | `vRevenueT0`, `vRevenueT_Partner` | Accounting/client name |

No SSN, DOB, government ID, or consumer-level PII identified.

### Financial Data

| Field | Table | Sensitivity |
|---|---|---|
| `amount`, `price`, `comm_amt` | `revenue` | Program-level revenue figures — internal financial data |
| `fvd_amt`, `fvd_adj` | `tblFVD_Revenue` | Face Value Discount adjustments |
| `CRDTAMNT`, `DEBITAMT` | `ECAN_R.SOP10102` | GP transaction amounts |
| `fdrcosts`, `cscosts`, etc. | `tblgprecords` | Cost records — internal |

All financial data is program-level (aggregate), not individual cardholder transaction data.

---

## Encryption at Rest

No encryption DDL (column-level encryption, Always Encrypted, TDE configuration) is present in this project's SQL files. Encryption policy for the underlying SQL Server instance is not visible in this codebase; it must be verified at the infrastructure level. Recommendation: confirm TDE is enabled on the hosting SQL Server instance.

---

## Data Classification Summary

| Category | Present | Detail |
|---|---|---|
| PCI DSS CDE data | No | No PANs, CVV, track data |
| Consumer PII | No | Client/company names only (B2B) |
| Financial program data | Yes | Revenue, cost, issuance amounts — internal |
| ERP master data | Yes | GP RM, SOP, GL records via linked server |

---

## Referential Integrity

No foreign key constraints are defined in this project (no tables). Referential integrity is enforced in the underlying operational databases. The cross-database joins (to `ATLYS_Rv_NUS_R` and `ECAN_R`) rely on application-level consistency and linked server availability; there are no declarative constraints.

---

## Data Retention

No retention policies, purge procedures, or archival logic are present in this project. Retention is managed in the upstream operational databases (`atlys_rv_nca`, `ECAN_R`).

---

## PCI DSS CDE Scope Assessment

**Conclusion: OUT OF PCI DSS CDE SCOPE.**

This database layer processes only aggregated financial metrics and GL-mapped revenue data. No primary account numbers, cardholder authentication data, or individual transaction records with card-identifying information are stored or processed. The cross-database GP references pull billing/revenue accounting data only.
