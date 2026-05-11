# Solution Architect Report — DS_CCP_wired-output

## 1. Technical Architecture

DS_CCP_wired-output is a **SQL Server Integration Services (SSIS) project** using the Project Deployment Model (SSISDB). The build artefact is an `.ispac` package deployed to an SSISDB catalogue folder named `wdnam-ccp-etl` on the `p-db09` SQL Server instance.

**Project toolchain:**
- Project created: `2019-08-26` (`wired-output.dtproj`: `SSIS:Property Name="CreationDate"`)
- Creator: `WIRECARD\van.nguyen2` (`wired-output.dtproj` line 26)
- SSDT version: VS 2019, targeting `SQLServer2017`
- Package format version: `8` (SSIS 2017+)
- Protection level: `DontSaveSensitive` — credentials are not embedded in packages; they are provided at runtime via SSISDB environments

**Project structure (9 packages):**

| Package | Size (bytes) | Build | Description |
|---|---|---|---|
| `call_report_packages.dtsx` | 59,952 | 62 | Master dispatcher — routes subscription to report package |
| `report_template.dtsx` | — | 213 | Base template with shared logic; internal name `program_balance_report` |
| `rpt_Program_Balance_Report.dtsx` | — | 206 | Program Balance Report generator |
| `rpt_Program_Balance_Report_Plus Fee.dtsx` | — | 214 | PBR Plus Fee variant |
| `rpt_Card_Ship_Date.dtsx` | — | 215 | Card Ship Date report |
| `rpt_Rapid_Undeliverable_Cards_Report.dtsx` | — | 212 | RAPID undeliverable cards |
| `rpt_Aggregate_Spending.dtsx` | — | 218 | Aggregate Spending report |
| `send_wep.dtsx` | 7,307 | 13 | WEP SFTP delivery |
| `send_client_sftp.dtsx` | 1,388 | 2 | Direct client SFTP delivery |

Build counters show `report_template.dtsx` has the highest build count (213), confirming it is the most actively modified package.

**Connection managers (project-level):**
- `wired_db.conmgr` — SQL Server connection to WIRED database. Default server embedded in project: `d-phl-db01.wirecard.lan` (Wirecard LAN dev); overridden at runtime in production via SSISDB environment
- `SMTP Connection Manager.conmgr` — Default: `p-ops-mail1.wirecard.sys` with `UseWindowsAuthentication=True` and `EnableSsl=False` (`wired-output.dtproj` lines 147–165)

**Project parameters (Project.params):**
- `wep_directory`: `C:\ETL\Out\WEP` — local staging directory
- `wep_sftp_hostname`: `sftp.amer1.wirecard.com` — hard-coded default production WEP endpoint
- `wep_sftp_port`: 22
- `wep_sftp_username`: empty (provided via SSISDB environment)
- `wep_sftp_password`: sensitive flag set, empty default
- `wep_sftp_keyfile`: empty (supports key-based auth)
- `wep_sftp_keypassphase`: sensitive flag set (typo in parameter name — `keypassphase` not `keypassphrase`)
- `ArchiveFolder`: `C:\ETL\Out\WEP\~Archive\`
- `ReportManagerServer`: `http://d-phl-db01.wirecard.lan/ReportServer` — SSRS Report Server endpoint for report rendering

The `ReportManagerServer` parameter confirms this project uses **SQL Server Reporting Services (SSRS)** to render reports into PDF/XLSX/CSV. The report template packages call the SSRS Report Manager Web Service to generate the report file, then pass the file path to the delivery packages.

---

## 2. API Surface

This project has no external API surface. It is a batch processing system that:
- **Reads** from SQL Server (WIRED database) via OLE DB connection
- **Calls** SSRS Report Manager Web Service to render reports (`ReportManagerServer` parameter)
- **Writes** files to the local filesystem (`C:\ETL\Out\WEP\`)
- **Transfers** files via SFTP to `sftp.amer1.wirecard.com` (WEP portal) or client SFTP endpoints
- **Sends** email via SMTP (`p-ops-mail1.wirecard.sys`)

**Parameter interface (call_report_packages.dtsx):**
- `Pkg_DeliverySchedule` — required string parameter passed by the master orchestrator to control which schedule type is being processed

---

## 3. Security Posture

| Control | Status | Finding |
|---|---|---|
| Package protection level | `DontSaveSensitive` | Credentials not in source — correct practice |
| SFTP to WEP | SSH (SFTP port 22) | Transport encryption in place — satisfies PCI DSS Req 4.2.1 |
| SFTP to clients | SSH (SFTP) | Transport encryption in place |
| SMTP encryption | `EnableSsl=False` | **RISK: Email delivery uses unencrypted SMTP** (`wired-output.dtproj` line 162). If report files are sent as attachments, financial data transmitted over plaintext SMTP |
| Windows Authentication to SSRS | `UseWindowsAuthentication=True` | Appropriate for internal SSRS access |
| DB connection | Integrated Security=SSPI | Windows auth — no SQL login credentials in project |
| SSISDB environment | Not visible in repo | Credential management externalized to SSISDB — positive |
| SFTP key passphrase typo | `wep_sftp_keypassphase` | Minor: the parameter name has a typo (`keypassphase`). If key-based auth is used, the passphrase parameter name must match exactly between SSISDB environment and package parameter name |
| WEP hostname hard-coded in source | `sftp.amer1.wirecard.com` in `Project.params` | Wirecard-branded SFTP endpoint committed to source. If this endpoint is still active, it requires an active Wirecard/post-Wirecard network agreement |

---

## 4. Technical Debt

| Item | Location | Impact |
|---|---|---|
| `call_report_packages.dtsx` at 59,952 bytes | Root of project | Large monolithic dispatcher; build counter at 62 indicates repeated modifications. Adding a new report type requires modifying this package |
| Hard-coded dev server in default connection string | `wired-output.dtproj` line 59: `d-phl-db01.wirecard.lan` | Dev server hostname committed to project. Overridden by SSISDB in production but misleading in source |
| Hard-coded Wirecard WEP endpoint | `Project.params` line 40 | `sftp.amer1.wirecard.com` is a Wirecard-branded endpoint; should be replaced in any active deployment |
| SSRS dev server endpoint | `Project.params` line 189: `http://d-phl-db01.wirecard.lan/ReportServer` | Dev SSRS endpoint committed; production endpoint provided via SSISDB override |
| SMTP SSL disabled | `wired-output.dtproj` line 162 | `EnableSsl=False` for email delivery; if reports are sent as attachments this is a data security gap |
| Typo in parameter name | `Project.params` line 131: `wep_sftp_keypassphase` | Should be `wep_sftp_keypassphrase`; functional only if SSISDB environment uses the same misspelling |
| No `wired_master_output.dtsx` in project manifest | `wired-output.dtproj` SSIS:Packages section | The master orchestrator package is listed in Business Analyst notes but does not appear in the project manifest's package list. It may be a separate project or a file not committed |
| Report template (build 213) vs. individual report packages (build 206-218) | Version build counts | Report template changes most frequently; individual report packages should inherit consistently from it |

---

## 5. Gen-3 Migration Requirements

| Requirement | Description |
|---|---|
| Replace SSIS report dispatch | `call_report_packages.dtsx` (59KB) must be replaced with a subscription-driven report request service. In Gen-3, the subscription configuration (`report_requests`) would drive an event-driven or scheduled microservice |
| Replace SSRS report rendering | Each `rpt_*.dtsx` package calls SSRS to render report files. Gen-3 replacement options: Azure SSRS (SSRS on Azure VM), Power BI Paginated Reports, or a reporting microservice using a commercial library (FastReport, Telerik Reporting) |
| Replace Wirecard WEP SFTP endpoint | `sftp.amer1.wirecard.com` — client-visible endpoint; migration requires client communication and credential updates. Gen-3 equivalent would be an Onbe-branded SFTP/HTTPS delivery portal |
| Replace SMTP email delivery | Unencrypted SMTP to `p-ops-mail1.wirecard.sys` must be replaced with a modern email delivery service (SendGrid, AWS SES, Azure Communication Services) with TLS enforcement |
| Migrate subscription data | `report_requests` and `report_requests_log` tables must be migrated to the Gen-3 subscription management service |
| Client SFTP endpoint inventory | Client SFTP endpoints are stored in `report_requests.DeliverySpecification` — not in source control. A full inventory must be extracted before decommission |
| Cache data freshness assessment | If cache tables have not been refreshed since CCP Oracle DWH shutdown (~2020), migrating the delivery system alone is insufficient — the source data pipeline must be assessed first |

---

## 6. Code-Level Risks

| Risk | File | Notes |
|---|---|---|
| SMTP without TLS | `wired-output.dtproj:162` (`EnableSsl=False`) | Any report emailed as attachment is transmitted in plaintext. Severity: HIGH if reports contain financial data |
| Wirecard LAN hostname in source | `wired-output.dtproj:59`, `Project.params:189` | `d-phl-db01.wirecard.lan` and `p-ops-mail1.wirecard.sys` are internal Wirecard LAN addresses. These only resolve within the former Wirecard network. Their presence in source confirms the project was developed on Wirecard infrastructure |
| WEP hostname committed to source | `Project.params:40` | `sftp.amer1.wirecard.com` — any developer running this package without an SSISDB override will attempt to connect to the Wirecard SFTP server |
| Missing master orchestrator | Project manifest (`.dtproj`) | `wired_master_output.dtsx` (referenced in BA analysis) does not appear in the manifest package list. Either it is deployed separately or it was not committed to this repo |
| `call_report_packages.dtsx` complexity | Root of project | At 59,952 bytes with build counter 62, this package is likely a large CASE-like control flow. Its full logic cannot be reviewed without XML parsing |
| No delivery failure alerting | Architecture-level | The delivery packages do not have visible failure notification paths in the `.dtproj`. Failed SFTP deliveries would be silently written to `report_requests_log` status only |
