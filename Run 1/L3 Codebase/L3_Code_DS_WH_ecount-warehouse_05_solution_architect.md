# DS_WH_ecount-warehouse — Solution Architect Report

## Technical Debt Register

### TD-1: Deprecated `.smdl` Report Model Format — CRITICAL
**Files**: All 7 `.smdl` files in `ecount.warehouse.models/`
**Description**: Microsoft deprecated the `.smdl` Report Model format in SQL Server Reporting Services 2012 and removed it entirely in SSRS 2017. Any SSRS upgrade beyond 2016 will render these semantic models non-functional.
**Impact**: Loss of `AccountHolder Detail.smdl`, `All Transaction Detail.smdl`, and 5 other models, breaking any reports that use the Report Model as their data source rather than a direct MDX or SQL query.
**Remediation Priority**: HIGH — Must be resolved before any SSRS infrastructure upgrade.

### TD-2: SSAS Multidimensional (Legacy) vs. Tabular
**Files**: `Prepaid_DW_OLAP/Prepaid_DW_OLAP.dwproj`, all `.cube` and `.dim` files
**Description**: SSAS Multidimensional is in maintenance mode. Microsoft's investment is in SSAS Tabular and Azure Analysis Services. MDX query language expertise is becoming scarce.
**Impact**: No new Microsoft features for SSAS Multidimensional; Azure Analysis Services does not support Multidimensional models.
**Remediation Priority**: MEDIUM — Plan migration to Tabular within 3 years.

### TD-3: No Automated Deployment Pipeline
**Files**: Repository root — no CI/CD files
**Description**: SSAS deployment is manual, performed via Visual Studio SSDT or SSAS Deployment Wizard. This violates PCI DSS Requirement 6.4 (change management for production deployments).
**Remediation Priority**: HIGH — Required for PCI DSS compliance.

### TD-4: Data Source View Last Updated 2017
**Files**: `Prepaid_DW_OLAP/Prepaid Warehouse.dsv` (line 5: `LastSchemaUpdate 2017-06-05`)
**Description**: The DSV defines the logical schema of the underlying `prepaid_warehouse` database tables/views as SSAS understands them. Any schema change in `prepaid_warehouse` since June 2017 is invisible to SSAS.
**Remediation Priority**: HIGH — Requires immediate DSV refresh and re-validation of all cube bindings.

### TD-5: Potential Credentials in `.rds` Files
**Files**: `reports.*/cf_report 4A1.rds`, `reports.*/Prepaid Warehouse.rds`, `reports.*/Prepaid_transactions.rds`
**Description**: SSRS Data Source (`.rds`) files may contain embedded SQL Server usernames and passwords for the warehouse database connection. These are committed to the git repository.
**Remediation Priority**: CRITICAL — Requires immediate audit; if credentials are present, they must be rotated and the files updated to use Windows Integrated Security or a secrets store.

---

## Security Vulnerabilities

### SEC-1: Single SSAS Role `CubeReader` — No Data Segregation
**File**: `Prepaid_DW_OLAP/CubeReader.role`
**Description**: A single `CubeReader` role grants access to all cubes. There are no MDX member filters on the Program or Access Level dimensions. Any service account or user with `CubeReader` role can query all client programs' data.
**PCI DSS Relevance**: Requirement 7 (Restrict Access to System Components) — data should be accessible only to those with a legitimate business need. Cross-client data access by client portal service accounts would violate multi-tenant data isolation.
**Remediation**: Add `DimProgram_vw.ProgramId` member filters to scope each role to allowed programs; create per-client roles or parameterize via dynamic security.

### SEC-2: PII in Warehouse Without Masking Policy
**File**: `Prepaid_DW_OLAP/Account.dim` (references `DimAccountHolder_vw`)
**Description**: The `DimAccountHolder_vw` dimension carries cardholder PII (name, address, email). There is no evidence of masking or pseudonymization at the warehouse layer.
**GDPR/CCPA Relevance**: Purpose limitation — PII should only be present if there is a documented legitimate purpose for each field. Full names and addresses in aggregate analytical reports should be masked unless the report explicitly requires individual-level identification.
**Remediation**: Implement column-level masking in `DimAccountHolder_vw` for all reports that do not require full PII; use `DynamicDataMasking` or view-based masking in SQL Server.

---

## All Dimension and Cube Objects Identified

### Cubes (5 total)
| Object | File | Purpose |
|---|---|---|
| `Prepaid Transactions` | `Prepaid Transactions.cube` | Card spending and fee transaction analytics |
| `Prepaid Issuance` | `Prepaid Issuance.cube` | Payment and card issuance tracking |
| `Account Snapshot` | `Account Snapshot.cube` | Point-in-time account state |
| `Prepaid Card Accounts` | `Prepaid Card Accounts.cube` | Account-level lifecycle |
| `JobSvc Actions` | `JobSvc Actions.cube` | Job service event tracking |

### Dimensions (25 total — `.dim` files)
| Dimension | File | Key Risk |
|---|---|---|
| Account | `Account.dim` | References `DimAccountHolder_vw` (PII) |
| Access Level | `Access Level.dim` | Controls data access segmentation |
| Account Create Date | `Account Create Date.dim` | Date hierarchy |
| Account Payments | `Account Payments.dim` | Payment summary |
| Account Spend | `Account Spend.dim` | Spend aggregation |
| Account Status | `Account Status.dim` | Lifecycle state |
| Account Utilization | `Account Utilization.dim` | Utilization metrics |
| Activation Code | `Activation Code.dim` | Card activation method |
| BIN | `BIN.dim` | Bank ID Number — partial PAN context |
| Card Account Create Date | `Card Account Create Date.dim` | Card open date |
| Card Block Code | `Card Block Code.dim` | Freeze/block codes |
| Card Expire Date | `Card Expire Date.dim` | Expiry date |
| Card Type | `Card Type.dim` | Virtual/physical/DDA |
| First Card Account Create Date | `First Card Account Create Date.dim` | First card event |
| First Payment Date | `First Payment Date.dim` | First load event |
| First Spend Date | `First Spend Date.dim` | First spend event |
| First Utilization Date | `First Utilization Date.dim` | First utilization |
| Geography | `Geography.dim` | State/ZIP for spend analysis |
| GL Company | `GL Company.dim` | Finance company codes |
| Issuance Type | `Issuance Type.dim` | Issuance method codes |
| Last Payment Date | `Last Payment Date.dim` | Most recent load |
| Last Spend Date | `Last Spend Date.dim` | Most recent spend |
| Last Utilization Date | `Last Utilization Date.dim` | Most recent utilization |
| Merchant | `Merchant.dim` | MCC, merchant name |
| Payment Claim Date | `Payment Claim Date.dim` | Claim event date |
| Payment Expiration Date | `Payment Expiration Date.dim` | Payment expiry |
| Payment Issue Date | `Payment Issue Date.dim` | Payment issue date |
| Payment Status | `Payment Status.dim` | Payment lifecycle |
| Prepaid Settlement Date | `Prepaid Settlement Date.dim` | Settlement date |
| Process Date | `Process Date.dim` | ETL process date |
| Processor Settlement Date | `Processor Settlement Date.dim` | Processor settlement |
| Product | `Product.dim` | Product type |
| Program | `Program.dim` | Program/client identifier |
| Transaction Type | `Transaction Type.dim` | Transaction classification |

---

## Report Inventory with Purpose

### reports.root (14 reports)
| Report | Purpose |
|---|---|
| `Account_Balance_Aging.rdl` | Balance aging by account vintage — escheatment input |
| `Aggregate Spending with Total Dollars report -By Category.rdl` | MCC category spending summary |
| `Aggregate Spending with Total Dollars report -By Merchant.rdl` | Merchant-level spending |
| `Aggregate_Spending_report_by_Addenda.rdl` | Addenda-tagged spending |
| `Aggregate_Spending_with_Total_Dollars_*` (multiple) | Various aggregate spend views |
| `Cardholder_Journals.rdl` | Individual cardholder transaction journal — **high PII** |
| `Cards Last Month.rdl` | Monthly card issuance count |
| `Card_Number_Shortage_Report.rdl` | BIN/card inventory depletion alert |
| `ExpiredIssuance_AHDetailModel.rdl` | Expired issuance with account holder detail — **high PII** |
| `Inventory Management Report*.rdl` | Card inventory levels |
| `Program_ReIssue_Counts.rdl` | Reissuance counts by program |
| `Site_ID_Variance_report.rdl` | Site ID reconciliation |
| `T Mobile Weekly Billing.rdl` | T-Mobile client billing report |
| `Time_to_Spend.rdl` | Days from issuance to first spend |

### reports.Client Services Reports (selected)
| Report | Purpose |
|---|---|
| `MasterCAM.rdl` (233 KB) | Master client account management — **primary client report** |
| `multiCAM.rdl` (897 KB) | Multi-program CAM report — **largest, highest complexity** |
| `Account Funding and Pre-Sweep Balance Report.rdl` | Pre-sweep fund balance |
| `Breakage Summary Report.rdl` | Unused balance / breakage |
| `Bulk Payment By State.rdl` / `Bulk Payment Summary.rdl` | APF bulk payment stats |
| `Program Information Extract.rdl` | Program config data extract for clients |

---

## Remediation Priority Matrix

| Item | Priority | Effort | Risk if Unaddressed |
|---|---|---|---|
| Audit `.rds` files for embedded credentials | P1 — Immediate | Low | PCI DSS 8.3.1 violation |
| Implement SSAS role member filters for program data segregation | P1 — Immediate | Medium | Cross-client data exposure |
| Remediate stale DSV (2017) | P1 — High | High | Silent analytical errors |
| Add CI/CD pipeline for SSAS deployment | P2 — 30 days | Medium | PCI DSS 6.4 violation |
| Deprecate `.smdl` files — migrate to direct SSRS datasets | P2 — 90 days | High | SSRS upgrade blocker |
| Document data lineage from operational DB to cube to report | P2 — 60 days | Low | Audit/governance gap |
| Migrate SSAS Multidimensional to Tabular | P3 — 12 months | Very High | Long-term supportability |
| Implement column-level PII masking in warehouse views | P2 — 60 days | Medium | GDPR/CCPA data minimization |
