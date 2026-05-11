# DS_ETL_sykes — Business Analyst Perspective

## Repository Overview

`DS_ETL_sykes` is a Microsoft SQL Server Integration Services (SSIS) project that implements the full extract-transform-load pipeline for data received from Sykes Enterprises, Onbe's outsourced customer-service and call-centre vendor. The repository lives under the `Sykes/` sub-folder and contains a Visual Studio solution file (`Sykes.sln`), a project descriptor (`Sykes.dtproj`), an Analysis Services database stub (`Sykes.database`), one shared connection manager (`cf_report.conmgr`), a project parameters file (`Project.params`), and eight SSIS packages (`.dtsx` files). Together these components automate the ingestion and staging of Sykes-supplied operational reports into the `cf_report` SQL Server database.

## Business Context and Purpose

Sykes provides customer-service outsourcing for Onbe's prepaid-card programmes. As part of that relationship, Sykes delivers structured Excel workbooks covering:

- **Daily Performance Reports (DPR)** — `sykes_DPR.dtsx` — daily agent-productivity and handle-time metrics broken down by skill group and site. Parameters `phone_hrs_by_site_row_start = 4` and `T1HG_row_end = 255` (sykes_DPR.dtsx lines 81–94) define the sheet layout expectations.
- **Call Summary** — `sykes_call_summary.dtsx` — aggregated inbound/outbound call volumes, average handle time, and service-level adherence. Sheet data starts at row 4 (`row_start` parameter, line 96) and ends at row 35 (`row_end = 35`, line 85).
- **Monthly Invoice** — `sykes_monthly_invoice.dtsx` — Sykes billing data for reconciliation against contracted rates. The package looks for files matching `Wirecard_NA_Invoice_*.xlsx` (line 59) and reads the `PREPAID$` worksheet (line 77).
- **Turnaround Time / SLA** — `sykes_turnaround_time_SLA.dtsx` — SLA compliance metrics for vendor performance reviews.
- **Weekly Grifols** — `sykes_weekly_grifols.dtsx` — client-specific weekly call-centre performance for the Grifols plasma-collection programme. The vendor file pattern contains a trailing space: `Wirecard_North_America_Inc _Weekly_Grifols_*.xlsx` (line 64).
- **Weekly Pool Trend** — `sykes_weekly_pool_trend.dtsx` — agent-pool capacity and headcount trend data.
- **Weekly TXU** — `sykes_weekly_TXU.dtsx` — TXU (Texas utilities) programme weekly report.
- **Weekly Verizon** — `sykes_weekly_verizon.dtsx` — Verizon programme weekly call-centre data.

## Data Flows and Key Business Rules

Each package follows a consistent pattern:

1. A `Foreach Loop Container` scans the `folder_path` parameter directory (default `C:\ETL\In\SykesReports\`) for files matching `file_pattern`.
2. The matched file is copied to `temp_folder_path` (`C:\ETL\In\SykesReports\temp\`), then opened via an Excel OLE DB connection using `Microsoft.ACE.OLEDB.12.0`.
3. Rows between `row_start` and `row_end` are read, skipping Sykes-embedded headers and footers.
4. Data is cleaned through SSIS Script Components or Derived Column transformations before being written to staging tables in the `cf_report` database (`Data Source=d-na-db01.nam.wirecard.sys,2232;Initial Catalog=cf_report`, `cf_report.conmgr` line 8).
5. Processed source files are archived to the `archive_folder` (default `C:\ETL\In\SykesReports\archive\`) for auditability.

## Vendor and Programme Context

File-naming conventions reveal the multi-client nature of Sykes's engagement. T-Mobile (`Wirecard_North_America_Inc_TMOBILE_20200603.xlsx`, `sykes_call_summary.dtsx` line 30), Biolife (`Wirecard_North_America_Inc_Biolife_*.xlsx`, `sykes_call_summary.dtsx` line 65), DPR, Grifols, and Verizon programmes all have dedicated call-centre queues within Sykes. This means Onbe carries contractual SLA obligations to those clients tracked through these ETL loads.

The monthly invoice package (`sykes_monthly_invoice.dtsx`) was developed by `WIRECARD\colin.treat` (package header line 7) on `PF0VFP1H`, with the initial development path referencing `C:\Users\colin.treat\Documents\projects\wdnamcbts-1033\` (line 41). The developer's local machine path was checked in as a default parameter, which is a configuration-management concern.

## Compliance and Financial Significance

These packages process operational metrics, not cardholder PAN or sensitive authentication data. However:

- The **monthly invoice package** processes Sykes billing data that feeds Onbe's accounts-payable function. Inaccurate loads could result in incorrect vendor payments or billing disputes.
- The **`cf_report` database** is the shared reporting database used by SSRS reports in `DS_RPT_ecount-report-services`. Data quality failures here propagate to client-facing reports, potentially causing UDAAP concerns if clients receive inaccurate activity statements.
- **Grifols** is a healthcare sector client (plasma collection). Call-centre performance metrics for this client may be subject to healthcare sector SLA agreements.

## Key Business Risks

| Risk | Detail | File Reference |
|---|---|---|
| Developer path in production default | `folder_path` default references `C:\Users\colin.treat\Documents\...` | sykes_monthly_invoice.dtsx line 41 |
| Trailing space in file pattern | Grifols pattern `Wirecard_North_America_Inc _Weekly_Grifols_*` has extra space — fragile to vendor changes | sykes_weekly_grifols.dtsx line 64 |
| No centralised project parameters | `Project.params` is empty; all config is package-scoped | Project.params line 2 |
| Single target database dependency | All 8 packages target `cf_report` via one connection manager | cf_report.conmgr line 8 |
| No error notification configuration | Sykes project has no email parameters (unlike DS_ETL_warehouse which has `SuccessEmailTo`/`FailEmailTo`) | Project.params |

## Stakeholder Summary

The primary business stakeholders are: (1) the Vendor Management team responsible for Sykes SLA tracking and invoice reconciliation; (2) the Data and Analytics team who consume the `cf_report` database for client reporting; (3) programme managers for Grifols, Verizon, T-Mobile, and Biolife who rely on accurate call-centre performance data. This pipeline is operationally critical for those multi-client contractual obligations.
