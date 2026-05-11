# DS_DB_GP_two — Business Analyst Report

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_GP_two |
| Internal alias | GP Two / Second GP Instance |
| Project file | `two.sqlproj` (GUID `c4bbbd7f-0136-4e30-8a51-494c17c67359`) |
| SQL Server version target | SQL Server 2008 (DSP `Sql100DatabaseSchemaProvider`) |
| Collation | `SQL_Latin1_General_CP1_CI_AS` |
| Compatibility level | 100 (SQL Server 2008) |

## 2. Business Purpose

`DS_DB_GP_two` is a second Microsoft Dynamics GP company database within Onbe's East GP deployment. The project name "two" and the minimal README (containing only the word "two") suggest this is either:

1. **A second US-domiciled legal entity** — common in Dynamics GP multi-company deployments where a holding company and operating company maintain separate GP books.
2. **A shared-services or corporate entity** — handling inter-company accounting, central payroll, or treasury operations that serve multiple subsidiaries.
3. **An historical entity** — representing a former business line, acquired entity, or predecessor company whose books are maintained for compliance but are no longer operationally active.

The smaller Security folder (only `DYNGRP`, `DYNWORKFLOWGRP`, `NAM_PROD`, `NAM_sitescope_AD`, `NAM_svc_gp_prd`, and report roles — no individual named users unlike EMXN) suggests this is a **service-oriented or lower-traffic entity** with more controlled access.

## 3. Core Business Processes Supported

`DS_DB_GP_two` carries the full Microsoft Dynamics GP schema, matching the EMXN entity in structural terms:

### 3.1 General Ledger (GL Module)
Full GL chart of accounts, journal entry workflow, period and fiscal year management. Tables `GL00100`–`GL70501` are present.

### 3.2 Accounts Payable / Payables Management (PM Module)
Vendor master, open payables, payment runs, 1099 reporting. `PM00200` holds vendor Tax IDs and phone numbers.

### 3.3 Accounts Receivable / Receivables Management (RM Module)
Customer master, open receivables, cash receipts, aging. `RM00101` holds customer phone numbers and addresses.

### 3.4 Sales Order Processing (SOP Module)
Sales orders, shipments, invoicing. SOP tables `SOP10100`–`SOP70100`.

### 3.5 Purchase Order Processing (POP Module)
Purchase orders, receipts, three-way matching. POP tables `POP10100`–`POP70100`.

### 3.6 Inventory (IV Module)
Item master, quantities, costing. IV tables `IV00101`–`IV70500`.

### 3.7 Human Resources / Payroll (UPR Module)
Employee master (`UPR00100`) with SSN, DOB, demographics, payroll history. **PII-sensitive module.**

### 3.8 Fixed Assets (AF Module)
Asset register, depreciation books, retirements.

### 3.9 Field Service / Contract Management
Service call tables, contract lines, RMAs/RTVs.

### 3.10 Multi-Currency
Given the entity's role as potentially a shared-services or holding company, multi-currency transactions (USD as functional currency) are expected.

## 4. Key Differentiation from GP_EMXN

| Dimension | DS_DB_GP_emxn | DS_DB_GP_two |
|-----------|--------------|--------------|
| Named entity | Mexico (EMXN) | Unknown/Second entity ("two") |
| Security principals | ~200 named individuals + groups | ~10 groups only (cleaner) |
| Tables (Tables1) | 1,000 | 1,000 |
| Tables (Tables2) | 78 | 15 |
| Stored Procedures | 16,594 | 15,923 |
| Views | 143 | 250 |
| Functions | 193 | 193 |

The higher view count (250 vs 143) in GP_two is notable — suggesting more custom reporting views have been created for this entity, possibly indicating heavier reporting or BI consumption.

## 5. Data Stored and Data Classification

Identical PII categories to GP_EMXN apply:

| Data Category | Tables | PII/Sensitive Flag |
|---------------|--------|--------------------|
| Employee SSN | `UPR00100.SOCSCNUM` | **CRITICAL PII** |
| Employee DOB, gender, ethnicity | `UPR00100` | **HIGH PII** |
| Vendor Tax ID | `PM00200.TXIDNMBR` | **HIGH — Tax ID** |
| Customer phone numbers | `RM00101.PHONE1/2/3` | **MEDIUM PII** |
| Email addresses | `SY01200.INET1–INET8` | **MEDIUM PII** |
| Financial GL transactions | `GL20000` | Business confidential |
| Payroll transactions | `UPR10100` | Financial / PII |

## 6. Regulatory Relevance

### PCI DSS
GP_two is **not a CDE**. No PANs or cardholder data expected. Connected-system controls apply — network segmentation from the CDE must be maintained.

### SOC 1 / SOC 2
As a financial reporting system, GP_two is in-scope for SOC 1 (internal controls over financial reporting). User access, change management, and completeness/accuracy of journal entries are auditable control objectives.

### US Tax / IRS
If GP_two is a US entity, `UPR00100` payroll data is subject to IRS Form W-2 reporting requirements. Vendor 1099 data in `PM00200.TEN99TYPE` and `PM00200.TEN99BOXNUMBER` is subject to IRS 1099 filing.

### GLBA
If the entity handles consumer financial data in any form (e.g., insurance disbursements, auto finance), GLBA safeguards apply to any PII.

## 7. Data Flows

```
External Inputs                    GP Two Database              Downstream
───────────────────────            ────────────────────         ──────────────────
Vendor invoices (AP)           →   PM10000, PM20000        →   ETL to DS_ETL_finance-gp
Employee payroll inputs        →   UPR10100–UPR10200       →   GL distributions
Intercompany from other GP     →   GL10000 (journals)      →   GL20000 (posted)
Bank statements (reconcil.)    →   CM20301                 →   GL reconciliation
GP ETL jobs                    ←────────────────────────────── Data warehouse feeds
```

## 8. Integration Points

- **DS_ETL_great-plains**: Extracts financial data from GP_two tables to ODS/warehouse.
- **DS_ETL_finance-gp**: Finance ETL pipeline.
- **Reporting**: Crystal Reports via `DS_RPT_crystal-invoice-templates-us`.
- **GP intercompany**: GP_two may receive or post intercompany entries from GP_EAST, GP_EMXN.
- `NAM_svc_gp_prd` service account (in Security folder) — production GP service account for integration.
- `NAM_sitescope_AD` — HP SiteScope monitoring integration.

## 9. Operational Context

The service account `NAM_svc_gp_prd` (present in `two.sqlproj` Security folder) is shared with the GP production service tier. Unlike GP_EMXN which has ~200 named individual SQL logins, GP_two has a much cleaner access model with only group-based and service-account logins — indicating better governance hygiene, or a less-actively-used entity.

The higher view count (250) versus GP_EMXN (143) may reflect historical BI/reporting customisation work done specifically for this entity's stakeholders.
