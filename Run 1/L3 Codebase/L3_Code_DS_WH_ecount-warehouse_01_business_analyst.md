# DS_WH_ecount-warehouse — Business Analyst Report

## Repository Overview

`DS_WH_ecount-warehouse` is the EcountCore prepaid payments data warehouse project. It is a **SQL Server Analysis Services (SSAS)** project, built with Microsoft Visual Studio Data Tools, containing an OLAP cube suite and an associated set of SSRS (SQL Server Reporting Services) report definitions. The README (line 3) states it is "SQL Server Analysis Project containing the cubes and analytic components for eCount's Business Intelligence."

The project is structured into three top-level components:
1. `Prepaid_DW_OLAP/` — SSAS Analysis Services project (`.dwproj`, `.cube`, `.dim`, `.partitions`, `.dsv`, `.database`, `.role` files)
2. `ecount.warehouse.models/` — Semantic model definition files (`.smdl`) used for report model queries
3. `reports.*` subdirectories — Six collections of SSRS report definitions (`.rdl` files) organized by consumer and purpose

---

## Business Purpose

This repository is the **analytical and reporting backbone** of the Onbe East (formerly Northlane / eCount) prepaid card platform. Its core business functions are:

### 1. Prepaid Card Business Intelligence
The warehouse models card program performance, cardholder lifecycle, transaction volumes, and revenue data. Business consumers include:
- **Client Services** — program-level reporting on issuance, spend, breakage, and cardholder behavior
- **Finance / Accounting** — revenue recognition, fee analytics, settlement reporting
- **Risk** — month-end analysis, snapshot reports, new account surveillance
- **Pricing** — utilization at card expiration, monthly spend trajectory

### 2. OLAP Cubes for Analytical Queries
The `Prepaid_DW_OLAP/` project defines five SSAS cubes:
- **Prepaid Transactions** (`Prepaid Transactions.cube`) — core fact table for card spending events, settlement, and fee transactions
- **Prepaid Issuance** (`Prepaid Issuance.cube`) — card load events, bulk payments, APF issuances
- **Account Snapshot** (`Account Snapshot.cube`) — point-in-time balance and account state snapshots
- **Prepaid Card Accounts** (`Prepaid Card Accounts.cube`) — account-level attributes and lifecycle states
- **JobSvc Actions** (`JobSvc Actions.cube`) — job service event tracking for operational BI

### 3. SSRS Report Library
Six report project folders total approximately 60+ `.rdl` report definitions:

| Folder | Representative Reports |
|---|---|
| `reports.Client Services Reports` | MasterCAM, multiCAM, Bulk Payment Summary/By State, Program Information Extract, DDA Rewards |
| `reports.DWH_reports` | Aggregate Issuance, Claimable Payment Detail, Payment Detail, Detail Issuance |
| `reports.graph_reports` | Transaction maps by merchant/cardholder state, trend graphs |
| `reports.pricing` | Pricing Utilization At Card Expiration, Pricing Utilization By Month |
| `reports.risk` | Month-End Analysis, Month-End Analysis By Bank, Current/Prior Snapshot |
| `reports.root` | Account Balance Aging, Cardholder Journals, Card Number Shortage, Inventory Management, T-Mobile Weekly Billing |

---

## Key Business Capabilities Provided

### Cardholder / Account Analytics
The warehouse provides the analytical layer to answer: How many cardholders were issued? What is the average spend per card? What is breakage (unused balances)? How old are un-activated cards?

### Payment Issuance Reporting
Detailed issuance reports (`Detail_issuance.rdl`, `Aggregate_Issuance.rdl`) track cards issued by program, product, issuance type, and settlement date — critical for client billing and reconciliation.

### Claimable Payment Tracking
`Clamable_payment_detail.rdl` and the `Claimable Payment Issuance.smdl` semantic model support reporting on outstanding claimable payment balances, directly relevant to escheatment obligations and float management.

### Risk and Fraud Monitoring
`MonthEnd_Analysis.rdl`, `MonthEnd_Analysis_By_Bank.rdl`, `Current_Snapshot_New_Accounts.rdl`, and `Prior_Snapshot_Analysis.rdl` provide the risk team with periodic account status views used to detect fraud patterns, large-balance accounts, and anomalous activation rates.

### Client and Program Performance Reporting
`MasterCAM.rdl` and `multiCAM.rdl` are the largest report definitions (233 KB and 897 KB respectively), likely representing master client account management reports with cross-program breakdowns. The `Program Information Extract.rdl` supports data fulfillment to clients for program reconciliation.

---

## Business Rules Observed

1. **Payment Status Lifecycle** — The `Payment Status.dim` dimension indicates payments flow through discrete status codes (created, notification sent, claimed, canceled, frozen, reissued) — these mirror the `PaymentVO.Action` constants in the echeck library.
2. **Expiration Tracking** — `Payment Expiration Date.dim` and `Card Expire Date.dim` drive breakage calculations and regulatory escheatment processes.
3. **Multi-Product Support** — The `Product.dim` and `BIN.dim` dimensions support analysis across virtual, physical, and DDA (demand deposit account) prepaid products.
4. **Geography Segmentation** — `Geography.dim` (`DimGeography_vw`) enables state-level spend analysis used in the `Bulk Payment By State.rdl` report.
5. **Access Level Filtering** — `Access Level.dim` controls which cardholder data is visible at which reporting access tier, reflecting multi-tenant client segregation.

---

## Regulatory Relevance

### PCI DSS
The warehouse receives data from the operational `ecountcore` and `prepaid_warehouse` SQL Server databases. If any upstream ETL process copies card numbers into warehouse tables (even masked), PCI DSS v4.0.1 Requirements 3 and 7 apply — the warehouse server(s) and any reporting endpoints fall within the Cardholder Data Environment (CDE) or connected systems scope. The `BIN.dim` and `Account.dim` confirm BIN data flows through the warehouse; individual PANs should be masked (first 6 / last 4) in all report outputs.

### Reg E and NACHA
Claimable payment reports and DDA rewards reports (`DDA Rewards Test.rdl`, `DDA-PUID based on Account Created Date Range.rdl`) indicate ACH-funded disbursements are tracked in the warehouse. Reg E error resolution timelines and NACHA return file reconciliation require accurate warehouse records.

### GLBA / CCPA / GDPR
`DimAccountHolder_vw` contains cardholder name, address, and email attributes. If any SSRS report surfaces full cardholder PII to client portals, CCPA data minimization and GDPR purpose-limitation obligations apply. Reports should be reviewed to confirm PII is not exported in bulk CSVs without data-sharing agreements.

### Escheatment / Breakage
The Account Balance Aging (`Account_Balance_Aging.rdl`) and breakage reports (`Breakage Summary Report.rdl`) feed state escheatment processes. Inaccurate data here creates compliance exposure under state unclaimed property laws.

---

## Operational Notes

- The solution file `ecount.warehouse.sln` indicates this is a Visual Studio Data Tools project targeting SQL Server 2008–2017 era SSAS.
- The `Prepaid Warehouse.dsv` (Data Source View, created 2012-08-20, last updated 2017-06-05 per lines 4–5) references tables/views named with `Dim*` and `Fact*` prefixes in the underlying `prepaid_warehouse` SQL Server database.
- The `Domestic_OLAP.database` file and the `CubeReader.role` indicate SSAS role-based security is used to restrict cube access.
- There is no CI/CD configuration (no `.gitlab-ci.yml`, no GitHub Actions workflow) in this repository — SSAS deployments are likely manual SSDT deployments, representing an operational risk.
