# Business Analyst Report — DS_CCP_wired

## Repository Overview

DS_CCP_wired defines the **WIRED database** — the operational schema behind the WIRED (Wirecard Intelligent Report Engine Delivery) product. WIRED is a client-facing automated report delivery system that allows corporate clients to subscribe to scheduled financial reports (Programme Balance Reports, Card Ship Date Reports, Aggregate Spending Reports, etc.) and receive them via SFTP, the Wirecard Extranet Portal (WEP), or email on a configurable schedule.

The repository is a Visual Studio SSDT SQL project (`wired.sqlproj`, targeting SQL Server 2016) containing table DDL, stored procedures, trigger definitions, a view, SQL Agent job scripts, post-deployment seed data scripts, and security definitions.

## Business Processes Supported

### 1. Client Report Subscription Management
The WIRED system allows Data Services staff (and through a UI, potentially clients) to configure report subscriptions:
- A subscription defines: which report, which brand/programme, what file format (PDF, XLSX, CSV), what delivery method (WEP portal, email, client SFTP), what schedule (daily, weekly, monthly, quarterly), and what time slot.
- `report_requests` is the central subscription table — each row represents one active or inactive client report subscription.
- Subscriptions are managed via two stored procedures: `usp_Wired_InsertReportRequest_Manual_INS` (administrative entry) and `usp_Wired_InsertReportRequest_UI_INS` (end-user UI entry).

### 2. Automated Report Generation and Delivery
The `report_requests_log` table (referenced by `usp_Wired_SubscriptionStatus_RPT`) tracks each execution of a subscribed report — when it ran, whether it succeeded, and any error messages. The `report_timeslot` table defines the permitted delivery time windows. The `report_schedule` table encodes which calendar dates correspond to which schedule codes.

The report output SSIS project (DS_CCP_wired-output) reads from `report_requests`, determines which subscriptions are due based on `report_schedule.ScheduleMatch` computed column, and executes the appropriate report packages.

### 3. Report Delivery Scheduling Engine
`report_schedule` implements a scheduling engine through computed columns:
- `ScheduleDate`: Calculates the actual calendar date for schedule codes like `QFst` (Quarter First), `QLst` (Quarter Last), `MFst` (Month First), `MLst` (Month Last), `M{N}` (Nth of month), `DAll` (every day), `DWkd` (weekdays only), `WFri/WSat/WSun/WMon...` (specific weekday)
- `ScheduleMatch`: Returns 1 if the current `ReportDate` matches the schedule code's rule — this computed column is the on/off switch for daily WIRED execution logic

### 4. Report Catalogue Management
`report_parameter_lookup` provides a translation mapping between report-specific parameter names (e.g., `FINANCIALINSTITUTION`, `P_BRAND`, `STARTDATE`) and the common names used in the WIRED system. This decouples the report engine from the report-specific parameter naming conventions of the underlying Crystal Reports or SSRS reports.

`usp_ReportCatalog_RPT` retrieves the catalogue of available reports from what appears to be a connected SQL Server Reporting Services (SSRS) instance.

### 5. Data Caching for Report Performance
Several cache tables pre-aggregate data from the CCP Oracle DWH and GP financials to avoid slow cross-system queries at report generation time:

| Cache Table | Business Purpose |
|---|---|
| `cache_pbr` / `cache_pbr_GP` / `cache_pbr_STG` | Programme Balance Report data — financial summary per brand |
| `cache_AggSpend` / `cache_AggSpend_STG` | Aggregate Spending data per brand |
| `cache_CardShipDate` / `cache_CardShipDate_STG` | Card shipment date data |
| `cache_RapidUndeliverableCards` / `_STG` | RAPID (cards returned undeliverable) data |
| `cache_corp_client_brands` / `_STG` | Corporate client brand reference data |

Each cache has a staging (`_STG`) counterpart enabling atomic refresh via a stage-and-swap pattern.

### 6. Subscription Status Reporting
`usp_Wired_SubscriptionStatus_RPT` provides a management view of all report subscriptions with their last run status, delivery method, schedule, and success/failure history. This is used by Data Services staff to monitor report delivery health.

## Business Rules Encoded

1. **Computed filename generation** (`report_requests.ComputedFileName` computed column): The system automatically generates output filenames in the format `{BrandName_8chars}_{ReportName_nospaces}-{0000+ID}_{YYYY-MM-DD}.{extension}`. This ensures unique, traceable output filenames.

2. **Schedule matching logic** (`report_schedule.ScheduleMatch` computed column): Encodes 20+ schedule variants in a single computed column. All schedule evaluation logic is in the database, not the application layer.

3. **Subscription toggle** (`RequestEnabled` bit column): Individual subscriptions can be activated/deactivated without deletion, preserving history.

4. **PBR Brand name truncation** (within `ComputedFileName`): For Programme Balance Report Plus Fee, brand names longer than 8 characters are truncated to 8 characters in the filename. This is a specific business rule for that report type.

5. **Parameter lookup normalisation**: `report_parameter_lookup` bridges between Crystal Reports / SSRS parameter names and the standard WIRED request parameter names, allowing the WIRED engine to pass parameters to heterogeneous report types.

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | WIRED delivers financial reports to corporate clients. Report content (PBR, Aggregate Spending) does not contain PANs or cardholder PII — these are programme-level financial summaries. The `cache_pbr` tables contain brand names, financial balances, and GP accounting data — not card-level data. WIRED database is likely **outside CDE scope** (no PAN data). |
| **SOC 1 Type II** | Programme Balance Reports are financial output used by clients for reconciliation. Accuracy and completeness of WIRED report output is a financial reporting control. |
| **GDPR / CCPA** | `DeliverySpecification` in `report_requests` stores email addresses (e.g., `patricia.zysk@wirecard.com`, seen in seed data). Email addresses in `DeliverySpecification` are personal data. Approximately 14 seed records in `insert_report_requests.sql` contain personal email addresses. |

## Integration Points

- **Upstream data sources**: DS_CCP_wired-caching (populates cache tables from Oracle CCP DWH and GP), `ccp_dwh` Oracle connection (via SSH tunnel, `DWH_AWS_SSH`)
- **Downstream consumers**: DS_CCP_wired-output (reads `report_requests` and `report_schedule` to determine what to generate and deliver), SSRS/Crystal Reports (called by WIRED output packages)
- **Delivery channels**: WEP portal (`sftp.amer1.wirecard.com`), client SFTP servers, email (via SMTP/SSIS send mail task)
- **SQL Agent jobs**: Three jobs defined in `SQL Agent Scripts\` folder — `wired_cache_refresh.sql`, `wired_cache_GP.sql`, `wired_report_output.sql`
- **Report server**: `usp_ReportCatalog_RPT` queries what appears to be an SSRS report server catalog

## Data Flows

```
CCP Oracle DWH ──► wired-caching (SSIS) ──► cache_* tables ──► rpt_*.dtsx (wired-output) ──► Delivered report files
GP Financials ──► import_cache_pbr_GP ──► cache_pbr_GP ──────────────────────────────────────────────────────────►

report_requests (subscription config)
    └─► report_schedule (schedule evaluation)
        └─► wired_master_output.dtsx
            └─► call_report_packages.dtsx ──► individual rpt_*.dtsx
                └─► send_wep.dtsx / send_client_sftp.dtsx
```
