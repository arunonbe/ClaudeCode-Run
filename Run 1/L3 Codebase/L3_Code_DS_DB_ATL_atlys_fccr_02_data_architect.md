# Data Architect Report — DS_DB_ATL_atlys_fccr

## 1. Repository Structure and Build System

`DS_DB_ATL_atlys_fccr` is an **SSDT SQL Server Database Project** (`atlys_fccr.sqlproj`). Key project properties:
- **DSP**: `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` — SQL Server 2008 compatibility level (100)
- **CompatibilityMode**: `90` (SQL Server 2005 target) — an older compatibility level confirmed in project XML line 63
- **DefaultCollation**: `SQL_Latin1_General_CP1_CI_AS`
- **Recovery mode**: `BULK_LOGGED`
- **PageVerify**: `CHECKSUM`
- **Containment**: `None`
- **IsEncryptionOn**: `False` — TDE is not configured in the project definition
- **ServiceBrokerOption**: `DisableBroker`
- **Branch**: `development` (active git branch)

The project contains a single schema (`dbo`) with: 2 tables, 2 views, 1 function, and 78 stored procedures plus Security scripts for 24 logins/roles.

---

## 2. Complete Database Object Inventory

### 2.1 Tables

| Table | Key Columns | Sensitivity |
|---|---|---|
| `dbo.Salesforce_to_Atlys` | `Opportunity Name VARCHAR(50)`, `Account Name VARCHAR(50)`, `Program ID INT`, `Average Amount Per Card Per Load FLOAT`, `Annual Account Volume FLOAT`, `Close Date DATETIME`, `BIN Sponsor VARCHAR(50)`, `Stage VARCHAR(50)`, `Last Modified Date DATETIME`, `Import Date DATETIME` (default GETDATE()) | **MEDIUM** — commercial pipeline data; BIN Sponsor is PCI-adjacent; opportunity economics are commercially sensitive |
| `dbo.tblForecastReports` | Report configuration entries (columns inferred from context) | LOW |
| `dbo.tblForecastViews` | View configuration entries | LOW |

### 2.2 Views

| View | Purpose |
|---|---|
| `dbo.vCompanies` | Company/client list used in Atlys UI |
| `dbo.vPrograms` | Program list for Atlys UI dropdowns |

### 2.3 Functions

| Function | Purpose |
|---|---|
| `dbo.sys_prg_info()` | Returns a VARCHAR(400) column-list string used to dynamically construct Excel report column headers; includes `prg_name`, `prg_type_desc`, `channel_desc`, `First_Issue`, `first_issue_ovr`, `GFCID`, `LegalName`, `Status`, `Probability`, `Card_Type`, `Win_Date` |

### 2.4 Stored Procedures (78)

The full set of stored procedures implements Atlys fee-calculation reporting. Key groups:

| Group | Procedures |
|---|---|
| Program CRUD | `sys_program`, `sys_program_update`, `sys_program_delete`, `sys_program_ext`, `sys_program_lock`, `sys_program_search`, `sys_program_chk` |
| Forecast management | `sys_forecast_info`, `sys_forecast_lines`, `sys_forecast_update`, `sys_forecast_summary`, `sys_forecast_notes`, `sys_forecast_version`, `sys_forecast_fees`, `sys_forecast2_cross_tab`, `sys_forecast_cross_tab`, `sys_forecast_details_cross_tab`, `sys_newforecastversion`, `sys_recalc_forecast`, `sys_recalc_forecast_s`, `sys_forecastviews` |
| Commission reporting | `sys_comm`, `sys_comm_cross_tab`, `sys_comm_revenue_cross_tab`, `sys_comm_pipeline_cross_tab`, `sys_comm_type_cross_tab`, `sys_comm_payable_revenue_pipeline_cross_tab`, `sys_comm_revenue_pipeline_cross_tab`, `sys_no_comm_cross_tab`, `sys_no_comm_pipeline_cross_tab` |
| Revenue reporting | `sys_revenue_cross_tab`, `sys_revenue_lines_cross_tab`, `sys_revenue_lines_details`, `sys_revenue_lines_sum_cross_tab`, `sys_revenue_pipeline_cross_tab`, `sys_revenue_pipeline_lines_cross_tab`, `sys_revenue_pipeline_version_cross_tab`, `sys_revenue_forecast_cross_tab`, `sys_revenue_forecast_pipeline_cross_tab`, `sys_revenue_issue`, `sys_report_revenue` |
| Spend reporting | `sys_spend_cross_tab`, `sys_spend_details_cross_tab`, `sys_spend_lines`, `sys_spend_pipeline_cross_tab`, `sys_spend_issue` |
| Cost reporting | `sys_costs_cross_tab`, `sys_costs_details_cross_tab`, `sys_costs_forecast`, `sys_costs_lines`, `sys_costs_lines_cross_tab`, `sys_costs_lines_sum_cross_tab`, `sys_costs_pipeline_cross_tab`, `sys_costs_pipeline_lines_cross_tab` |
| Issuance reporting | `sys_issuance`, `sys_issuance_cross_tab`, `sys_issuance_summary`, `sys_issuance_update`, `sys_issuance_forecast_cross_tab`, `sys_issuance_pipeline_cross_tab`, `sys_issuance_forecast_pipeline_cross_tab`, `sys_issue_details_cross_tab` |
| Plastics reporting | `sys_plastics`, `sys_plastics_cross_tab`, `sys_plastics_forecast_cross_tab`, `sys_plastics_pipeline_cross_tab`, `sys_plastics_forecast_pipeline_cross_tab` |
| Deferred revenue | `sys_deferredrevenue_cross_tab`, `sys_deferredrevenue_balance_cross_tab`, `sys_deferredrevenue_pipeline_cross_tab` |
| Dashboard | `sys_dash`, `sys_dash_cross_tab`, `sys_dash_details_cross_tab`, `sys_dash_details2_cross_tab` |
| Amortization | `sys_amortization` |
| Variance | `sys_variance_details`, `sys_variance_lines`, `sys_variance_lines_pipeline`, `sys_variance_summary` |
| Salesforce integration | `sys_sf_import`, `sys_sf_upload` |
| Utility | `sys_controls`, `sys_actual_summary`, `sys_custnames`, `sys_custnums`, `sys_user_cols`, `sys_util_tables`, `sys_probability`, `sys_renumber`, `sys_cblists`, `sys_prg_cnt_cross_tab`, `sys_reports` |

---

## 3. Sensitive Data Assessment

### 3.1 BIN Data
`Salesforce_to_Atlys.BIN Sponsor VARCHAR(50)` stores the BIN sponsor name for incoming credit program opportunities. While this is a sponsor name (not a numeric BIN), the link to BIN-level program economics means this table is **adjacent to payment card program data**. Credit card BIN sponsors are directly part of the PCI DSS CDE ecosystem.

### 3.2 Deal Economics
`Salesforce_to_Atlys.Average Amount Per Card Per Load` and `Annual Account Volume` are deal-level financial forecasts. These are commercially sensitive (M&A/competitive sensitivity) but are not personal data under GDPR/CCPA.

### 3.3 GFCID (Global Financial Client ID)
`sys_prg_info()` returns `GFCID` as a program report column. GFCID is the Onbe internal client identifier — medium sensitivity as a cross-system reference key.

### 3.4 No PAN, PII, or SAD found
No cardholder PAN, CVV, track data, cardholder name, address, or social security number columns are present in this database's schema. The database is a **financial forecast and revenue modelling tool**, not a cardholder data store.

---

## 4. Encryption

| Control | Status |
|---|---|
| TDE | `IsEncryptionOn: False` in `.sqlproj` — not configured |
| Column-level encryption | None |
| Backup encryption | Not configurable from SSDT project |

**Gap**: No encryption at rest is configured. Given that `Salesforce_to_Atlys` contains deal economics and BIN sponsor data, TDE is recommended at minimum.

---

## 5. Data Flow

```
Salesforce CRM ──► (ETL/Import process) ──► Salesforce_to_Atlys (staging table)
                                                    │
                                                    ▼
                                          sys_sf_import (stored procedure)
                                                    │
                                                    ▼
                                          cursforecast (program master — implied)
                                                    │
                                                    ▼
                                  Atlys forecast/reporting stored procedures
                                                    │
                        ┌───────────────────────────┤
                        ▼                           ▼
                 Atlys UI (web app)        sys_sf_upload ──► Salesforce CRM
                 (reports & dashboards)    (revenue cross-tab fed back to SF)
```

The bidirectional Salesforce integration creates a data governance requirement: data flowing from Salesforce into Atlys (deal pipeline) and back to Salesforce (revenue forecasts) must be subject to consistent data classification and access controls on both systems.

---

## 6. Security Roles and Access

Roles/logins defined in Security scripts:

| Login/Role | Access Level |
|---|---|
| `ATLYS_APP_GRP` (database role) | Application service account (`NAM\PPA_PRD_ATLYS`) |
| `NAM_PPA_PRD_ATLYS` | Production Atlys application service account |
| `NAM_PROD` | General production read access |
| `NAM_PROD_CPP` | CPP (CitiPrepaid Platform) production access |
| `NAM_PROD_CPP_APAC` | APAC CPP production access |
| `NAM_PROD_ITOPS` | IT Operations access |
| `NAM_UAT` | UAT environment access |
| `raf` | Refer-a-Friend service account |
| `ATLYS_APP_GRP` | Application group role |
| `FortiDBRptRole` | FortiDB database activity monitoring |
| `gers_role` / `gers_read` | GERS (security scanning) roles |
| `ifs_gidadb` / `ifs_infosec` | InfoSec read access |
| `Prod_Support_Schema_View` | Schema-level view for production support |
| `Prod_Support_Select`, `Prod_Support_Update`, `Prod_Support_execute` | Production support DML and execute grants |
| `NAM_ICG_DBA_Default` | DBA access |
| `NAM_ISA_SQL_SECADMIN` | SQL Security Admin |
| `NAM_GTS_gpatmon` / `NAM_GTS_MSSQL_DBA_RO` | GTS monitoring and DBA read-only |
| `scpardb` | SCP compliance scanning read |

The presence of `Prod_Support_execute` and `Prod_Support_Update` grants indicates that production support staff can modify data in this database without going through the application layer — a data governance risk.

---

## 7. Data Quality and Retention

- The `cursforecast` program master table (implied by `sys_sf_import` logic) is the core data store but is not defined in this repository — it is likely defined in the shared Atlys infrastructure database.
- `tblForecastReports` and `tblForecastViews` are configuration tables; no retention policy is defined.
- No purge procedures found for `Salesforce_to_Atlys` — staging data may accumulate indefinitely.
- The `Import Date` column on `Salesforce_to_Atlys` (default `GETDATE()`) enables date-based purging but no procedure implements it.

---

## 8. Compliance Gaps

| Gap | Description | Risk |
|---|---|---|
| No TDE | `IsEncryptionOn: False` — data at rest is unencrypted | PCI DSS Req 3.5 (CDE-adjacent); SOC 2 |
| No purge for Salesforce_to_Atlys | Staging table has no lifecycle management | Data minimisation (GDPR Art. 5) |
| Prod_Support Update/Execute grants | Direct production data modification by support staff | SOX ITGC; PCI DSS Req 7 |
| SQL Server 2005 compat level (90) | `CompatibilityMode=90` means modern query features are disabled; potential performance and correctness risks | Technical risk |
| BULK_LOGGED recovery model | Recovery mode `BULK_LOGGED` means some bulk operations are not fully logged; point-in-time recovery is not available during bulk loads | Availability; RPO risk |
