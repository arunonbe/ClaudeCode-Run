# Business Analyst Report — DS_CCP_db09

## Repository Overview

DS_CCP_db09 is an operational maintenance and configuration repository for the **p-db09\db09** SQL Server instance — the dedicated database server hosting the CCP (Card/Client Processing Platform) ETL infrastructure at Wirecard/Northlane (now Onbe). The repository contains no application schema DDL; it is entirely composed of **SQL Server Agent job creation/modification scripts**, **SSISDB environment configuration scripts**, and **ODS data-patch scripts**. The naming convention follows ticket-prefixed date stamps (e.g., `20190919_namdatasvc-1349_...`), indicating a manual, migration-by-ticket deployment model.

## Business Processes Supported

### 1. Automated ETL Job Scheduling
All SQL Server Agent jobs that drive the nightly and daily CCP data pipelines run on p-db09. The repo records the creation, modification, and decommissioning of these jobs:

| Job Name | Business Purpose |
|---|---|
| `ccp_import_aggnetworksettlement` | Imports aggregated network settlement data from CCP Oracle DWH into ODS |
| `Export_billing_audit` | Exports billing audit data for legacy system consumption |
| `Export_billing_detail` | Exports line-level billing detail for legacy systems |
| `Export_fvd_deferred`, `Export_fvd_revenue`, `Export_fvd_singleload` | Export FVD (Face Value Data) categories for downstream reporting |
| `sunrise_feed_account`, `sunrise_feed_account_balance`, `sunrise_feed_card_status`, `sunrise_feed_transactions` | Daily Sunrise Banks data feeds — account, balance, card status, transaction data |
| `sunrise_recon_network_off`, `_pin`, `_pos` | Network reconciliation jobs by transaction channel (offline, PIN, POS) for Sunrise Banks |
| `sunrise_recon_selling_deposit`, `sunrise_recon_total_cardholder_balance` | Selling deposit and total cardholder balance reconciliation |
| `oas_export_sunrise_fis_settlement` | Exports FIS settlement data to OAS (Onbe/Wirecard reconciliation system) via SFTP to `sftp.wirecard.com` |
| `oas_export_sunrise_fis_dailyfees` | Exports FIS daily fee data to OAS |
| `wired_cache_refresh` | Triggers WIRED product's nightly cache refresh from CCP Oracle DWH |
| `wired_cache_GP` | Imports Great Plains (GP) financial data to WIRED PBR cache, runs 2nd/3rd of month and daily at 5:30 PM |
| `wired_report_output` | Triggers SSIS report generation and delivery pipeline |
| `wdp_import_unpostedtrans` | Imports WDP (Wirecard Data Platform) unposted transaction files |
| `Archive_Processed_Files` | Archival/deletion of processed ETL files via SSIS package |
| `mc_import_summary` | Imports Mastercard summary settlement files (6 files per day) |

### 2. Business Rules Encoded

- **Environment-aware job enablement**: All job scripts use `CASE WHEN @@SERVERNAME LIKE 'D-%' THEN 0 ... ELSE 1` to disable jobs in development/test and enable only in production (file: `20191107_namdatasvc-1527_JobsForOASExportSunriseFISPackages.sql`, lines 19–25).
- **Retry logic**: Job steps use `@retry_attempts=1, @retry_interval=1` (1 retry, 1-minute interval) as a standard pattern, added via `20190919_namdatasvc-1349_*` scripts.
- **CCP Shutdown cutover (July 2020)**: File `20200804_NAMDATASVC-2398_DB09 Disable jobs.sql` disables 17 jobs simultaneously, recording the decommissioning of the Wirecard CCP Oracle platform. This is a critical audit point — CCP Oracle processing halted; Mastercard-only files continued.
- **Bank rebranding**: File `20201113_SQ-1114 update sql agent operator and dbmail account.sql` updates email addresses from wirecard.com to northlane.com domains, encoding the Wirecard-to-Northlane corporate transition.

### 3. SSISDB Environment Configuration
File `20191107_namdatasvc-1527_ConfigurationForOASExportSunriseFISPackages.sql` configures SSISDB catalog variables for SFTP access to `sftp.wirecard.com` (production) and `sftp-test.wirecard.com` (test), including:
- SFTP username: `NAM_Recon_Reports`
- SFTP key file paths: `F:\ETL\Cert\openssh_wd_oas_prod` / `R:\ETL\Cert\openssh_wd_oas_test`
- Sensitive passphrase variable: `OASSFTPPassphrase` (stored as SSISDB sensitive parameter)

### 4. Data Corrections and Backfills
Manual data-patch scripts handle specific reconciliation gap-fills:
- `20200602_NAMDATASVC-2264_DB09 Insert into Network Settlement reporting table.sql` — inserts missing network settlement data for dates `2020-05-09` and `2020-05-28` into `ODS.dbo.RptNetworkSettlementData`.
- `20200518_NAMDATASVC-1872_DB09 Add Member Id and update tables for AF.sql` — inserts Sunrise Banks MasterCard member ID `00000023614` and corrects member ID `0172` to `00000023614` in settlement tables.
- `20191021_namdatasvc-1519_ToIncludeMissedDatesForNSandICReports.sql` — data patch to the ODS `package_execution` table for missed interchange/network settlement report dates.

### 5. Report Server Role Administration
File `20191118_NAMDATASVC-1580_UpdateUserRolesOnReportServer.sql` (not read — name indicates SSRS role configuration for the WIRED report server).

## Data Flows and Integration Points

```
Oracle CCP DWH (AWS SSH)
  --> SSIS: ccp_import_aggnetworksettlement → ODS.dbo.RptNetworkAgg
  --> SSIS: wired_cache_refresh             → WIRED.dbo.cache_*

FIS Settlement/Fee Files (flat files)
  --> SSIS: sp_FISRpt_Import*               → ODS.dbo.FISRpt*
  --> SSIS: oas_export_*                    → SFTP: sftp.wirecard.com

Mastercard Files (NAM_*_TT140*.*.* format)
  --> SSIS: mc_import_summary               → ODS.dbo.RptNetworkImport

Great Plains (GP) Financials
  --> SSIS: wired_cache_GP                  → WIRED.dbo.cache_pbr_GP

WDP Unposted Transactions
  --> SSIS: wdp_import_unpostedtrans        → ODS.dbo.RptNetworkUnposted
```

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | The ODS database (targeted by several scripts) stores PAN data (column `FISRptCardholderActivity.PAN`) — placing p-db09 firmly within the CDE. Network settlement and interchange data are payment card scheme reporting. |
| **NACHA / Reg E** | Network settlement reconciliation data pertains to electronic fund transfers subject to Reg E error resolution timelines. |
| **FIS / Mastercard Scheme Rules** | Daily FIS report imports and MC file processing enforce card network settlement obligations. |
| **SOC 1 / SOC 2** | The automated reconciliation and settlement jobs are likely in scope for financial reporting controls (SOC 1 Type II). |

## Key Observations for Business Stakeholders

1. The mass job-disable script (August 2020) marks the end of CCP Oracle processing. Jobs have not been re-enabled. p-db09 is in a **post-CCP-shutdown maintenance state** with only WIRED and limited Mastercard processing active.
2. The SFTP hostname `sftp.wirecard.com` and Confluence URL `confluence.wirecard.sys` embedded in job descriptions are legacy Wirecard infrastructure references that should be updated in runbooks.
3. All SQL Agent jobs are owned by `sa` (the system administrator account) — this is a compliance risk requiring review.
