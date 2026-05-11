# Business Analyst Report — DS_CCP_wired-output

## Repository Overview

DS_CCP_wired-output is the **final-mile report generation and delivery SSIS project** for the WIRED product. It contains all SSIS packages responsible for reading subscription configuration from the WIRED database, generating report files from the pre-populated cache tables, and delivering those files to clients via WEP portal SFTP, client SFTP servers, or email.

The Visual Studio Integration Services project (`wired-output.dtproj`) contains 12 SSIS packages and a project parameters file, targeting the SSISDB on p-db09. This is the execution layer that directly serves client reporting obligations.

## Business Processes Supported

### 1. Master Report Output Orchestration (`wired_master_output.dtsx`)
This is the top-level orchestration package that drives the entire report delivery pipeline. It contains:
- A `Data Flow Task` — likely reads `WIRED.dbo.report_requests` to determine which subscriptions are due for execution on the current date
- A `Foreach Loop Container` — iterates over due subscriptions
- An `Execute Package Task` — calls `call_report_packages.dtsx` for each due subscription

The orchestration pattern matches the `report_schedule.ScheduleMatch` computed column design: for each request where `ScheduleMatch = 1` for today's date, the package is called.

### 2. Report Package Dispatch (`call_report_packages.dtsx` — 59,952 bytes)
The largest package in the project. This orchestration layer determines which specific report package to execute based on `ReportName` from `report_requests`, and calls the appropriate individual report package.

### 3. Individual Report Generation Packages

| Package | Report Type | Source Data |
|---|---|---|
| `rpt_Program_Balance_Report.dtsx` | Programme Balance Report | `WIRED.dbo.cache_pbr` + `WIRED.dbo.rpt_ProgramBalanceReport` |
| `rpt_Program_Balance_Report_Plus Fee.dtsx` | PBR Plus Fee variant | `WIRED.dbo.cache_pbr` + fee data |
| `rpt_Aggregate_Spending.dtsx` | Aggregate Spending Report | `WIRED.dbo.cache_AggSpend` |
| `rpt_Card_Ship_Date.dtsx` | Card Ship Date Report | `WIRED.dbo.cache_CardShipDate` |
| `rpt_Rapid_Undeliverable_Cards_Report.dtsx` | RAPID Undeliverable Cards | `WIRED.dbo.cache_RapidUndeliverableCards` |
| `report_template.dtsx` | Template/base package | Shared base logic |

### 4. Report File Delivery

| Package | Delivery Channel | Destination |
|---|---|---|
| `send_wep.dtsx` (7,307 bytes) | WEP (Wirecard Extranet Portal) SFTP | `sftp.amer1.wirecard.com` (from `Project.params`) |
| `send_client_sftp.dtsx` (1,388 bytes) | Client SFTP | Client-specific SFTP server (from `report_requests.DeliverySpecification`) |

Email delivery is handled through SSIS send mail tasks within the individual report packages or orchestration layer (SMTP Connection Manager is present).

### 5. Project Parameters (`Project.params` — 6,806 bytes)

Key parameters include:
- `wep_directory`: `C:\ETL\Out\WEP` — local staging directory for WEP deliveries
- `wep_sftp_hostname`: `sftp.amer1.wirecard.com` — **production WEP SFTP endpoint**
- `wep_sftp_port`: `22`
- `wep_sftp_username`: (empty — provided via SSISDB environment)
- Additional SFTP credential parameters (sensitive)

**Notable**: Unlike DS_CCP_wired-caching, the `wep_sftp_hostname` default here is `sftp.amer1.wirecard.com` — a production-looking Wirecard Americas SFTP endpoint. This is a committed production endpoint reference.

## Business Outputs Delivered

Based on seed data in DS_CCP_wired `insert_report_requests.sql`, the following report types are delivered:

| Report | Formats | Delivery Methods | Schedules |
|---|---|---|---|
| Program Balance Report | PDF, XLSX, CSV | WEP SFTP, Email | Daily all (`DAll`), Weekly Monday (`WMon`), Monthly 7th (`M7`) |
| Program Balance Report Plus Fee | PDF, XLSX | WEP SFTP | Weekly Thursday (`WThu`) |
| Card Ship Date | XLSX, PDF | WEP SFTP, Email | Daily all (`DAll`), Weekly weekday (`DWkd`), Weekly Thursday (`WThu`) |
| RAPID Undeliverable Cards Report | XLSX, PDF | WEP SFTP, Email | Weekly Friday/Thursday (`WFri`, `WThu`) |
| Aggregate Spending | XLSX, PDF | WEP SFTP, Email | Monthly 7th (`M7`), Quarterly First (`QFst`), Yearly Last (`YLst`) |

## Data Flows

```
WIRED.dbo.report_requests (subscription config)
    └─► wired_master_output.dtsx (orchestrator)
        └─► call_report_packages.dtsx
            ├─► rpt_Program_Balance_Report.dtsx
            │   └─► WIRED.dbo.rpt_ProgramBalanceReport (proc) + cache_pbr
            ├─► rpt_Aggregate_Spending.dtsx
            │   └─► WIRED.dbo.cache_AggSpend
            ├─► rpt_Card_Ship_Date.dtsx
            │   └─► WIRED.dbo.cache_CardShipDate
            └─► rpt_Rapid_Undeliverable_Cards_Report.dtsx
                └─► WIRED.dbo.cache_RapidUndeliverableCards
                    ↓ (report files)
            ├─► send_wep.dtsx → sftp.amer1.wirecard.com (WEP portal)
            ├─► send_client_sftp.dtsx → client SFTP server
            └─► SMTP send mail → client email addresses
```

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | Report output contains programme-level financial data (no PANs). Delivery via SFTP to `sftp.amer1.wirecard.com` requires transport encryption — SFTP provides SSH encryption satisfying PCI DSS Req 4.2.1. **Not CDE scope for data content.** |
| **SOC 1 Type II** | Programme Balance Reports are financial statements delivered to clients. Accuracy, completeness, and timely delivery are SOC 1 financial reporting controls. Failures in delivery should be logged and alerted. |
| **GDPR / CCPA** | Report files are delivered to client email addresses stored in `report_requests.DeliverySpecification`. Email delivery involves personal data (email addresses). |
| **Client Contractual Obligations** | Report delivery schedules represent contractual SLA commitments to clients. Late or failed delivery creates contractual exposure. |

## Integration Points

| System | Direction | Notes |
|---|---|---|
| WIRED DB (cache tables) | Read | Source data for all reports |
| WIRED DB (`report_requests`, `report_schedule`) | Read | Subscription config and schedule evaluation |
| WIRED DB (`report_requests_log`) | Write | Execution status logging |
| `sftp.amer1.wirecard.com` (WEP) | Write | WEP portal delivery |
| Client SFTP servers | Write | Direct client delivery |
| SMTP server | Write | Email delivery |
| DS_CCP_wired-caching | Upstream dependency | Must run before output to populate cache |
| SQL Agent on p-db09 | Orchestration | `wired_report_output` job triggers this project |
