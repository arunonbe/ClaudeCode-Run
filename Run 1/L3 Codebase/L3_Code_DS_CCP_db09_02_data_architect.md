# Data Architect Report — DS_CCP_db09

## Repository Nature

DS_CCP_db09 is not a schema repository. It contains **no CREATE TABLE, CREATE INDEX, or schema DDL** statements of its own. All DDL for database objects lives in sibling repos (DS_CCP_ods, DS_CCP_wired, DS_DB_ccp, etc.). This repo is exclusively an **operational script repository** for the p-db09\db09 SQL Server instance: SQL Agent job definitions, SSISDB configuration, and ODS data patches.

## Database Objects Directly Created or Modified

### SQL Server Agent Jobs (msdb)
The following SQL Agent jobs are created or modified via scripts in this repo. All jobs reside in the `msdb` database on p-db09:

| Job Name | Script File (date prefix) | Purpose |
|---|---|---|
| `Archive_Processed_Files` | `20191010_namdatasvc-1243_CopySQLAgentJobs2COB.sql` | Moves/deletes processed ETL files |
| `ccp_import_aggnetworksettlement` | same | Imports CCP Oracle agg settlement |
| `Export_billing_audit` | `20190919_..._export_billing_audit.sql` | Legacy billing audit export |
| `Export_billing_detail` | `20190919_..._export_billing_detail.sql` | Legacy billing detail export |
| `Export_fvd_deferred` | `20190919_..._export_fvd_deferred.sql` | FVD deferred export |
| `Export_fvd_revenue` | `20190919_..._export_fvd_revenue.sql` | FVD revenue export |
| `Export_fvd_singleload` | `20190919_..._export_fvd_singleload.sql` | FVD single-load export |
| `sunrise_feed_account` | `20190919_..._sunrise_feed_account.sql` | Sunrise account feed |
| `sunrise_feed_account_balance` | same | Sunrise balance feed |
| `sunrise_feed_card_status` | same | Sunrise card status feed |
| `sunrise_feed_transactions` | same | Sunrise transaction feed |
| `sunrise_recon_network_off` | same | Offline network recon |
| `sunrise_recon_network_pin` | same | PIN network recon |
| `sunrise_recon_network_pos` | same | POS network recon |
| `sunrise_recon_selling_deposit` | same | Selling deposit recon |
| `sunrise_recon_total_cardholder_balance` | same | Total cardholder balance recon |
| `oas_export_sunrise_fis_settlement` | `20191107_namdatasvc-1527_JobsForOASExportSunriseFISPackages.sql` | FIS settlement export |
| `oas_export_sunrise_fis_dailyfees` | same | FIS daily fees export |
| `wired_cache_GP` | `20191219-namdatasvc-1696_..._Import_GP_CCP_PBR.sql` | GP cache for WIRED PBR |
| `wired_cache_refresh` | referenced in `20191219...` and `20200804...` | WIRED cache refresh |
| `wired_report_output` | referenced in `20200804...` | WIRED report output |
| `wdp_import_unpostedtrans` | referenced in `20200804...` | WDP unposted transaction import |

### SSISDB Catalog Environment Variables
File `20191107_namdatasvc-1527_ConfigurationForOASExportSunriseFISPackages.sql` creates/sets the following SSISDB variables in folder `wdnam-ccp-etl`:

| Variable | Sensitive | Purpose |
|---|---|---|
| `OASSFTPPassphrase` | **YES** | SSH key passphrase for OAS SFTP |
| `OAS_SFTP` (project parameter) | No | Enables SFTP for non-Dev |
| `OAS_SFTPHostName` | No | `sftp.wirecard.com` / `sftp-test.wirecard.com` |
| `OAS_SFTPKeyFile` | No | Path to SSH key file on ETL server |
| `OAS_SFTPUserName` | No | `NAM_Recon_Reports` |

### ODS Data Modifications
Several scripts directly modify data in the `ODS` database (separate from schema DDL):

- **`ODS.dbo.RptNetworkSettlementData`**: INSERT of missing rows for `2020-05-09` and `2020-05-28` (file: `20200602_NAMDATASVC-2264_...sql`)
- **`ODS.dbo.package_execution`**: UPDATE of `execution_params` for missed dates (file: `20191021_namdatasvc-1519_...sql`)
- **`ODS.dbo.RptNetworkSettlementAssociations`**: INSERT of Sunrise Banks MC member ID `00000023614` (file: `20200518_NAMDATASVC-1872_...sql`)
- **`ODS.dbo.RptNetworkAgg`**: UPDATE `AcquirerName = 'NYCE'` where NULL (file: `20200518_...sql`)
- **`ODS.dbo.RptNetworkSettlementData`**: UPDATE SYS column from `0172` to `00000023614` (file: `20200518_...sql`)
- **`WIRED.dbo.report_parameter_lookup`**: TRUNCATE and re-seed of 30 lookup rows (file: `20191224_namdatasvc-1576-Wired_CreateTable_ReportParameterLookup.sql`)

## Sensitive Data Fields — CDE Assessment

This repo does not define tables, but scripts in it reference or touch tables that contain PCI-scope data:

| Table | Database | Sensitive Column | Classification | Flag |
|---|---|---|---|---|
| `FISRptCardholderActivity` | ODS | `PAN` VARCHAR(19) | **PRIMARY ACCOUNT NUMBER** | **CDE — PCI DSS Req 3** |
| `FISRptCardholderActivity` | ODS | `AccountNumber` VARCHAR(25) | Account identifier | **CDE candidate** |
| `RptNetworkUnposted` | ODS | `Card Number` VARCHAR(20) | Card number / PAN | **CDE — PCI DSS Req 3** |
| `RptNetworkSettlementData` | ODS | `SYS` (MemberID) | Payment network member ID | Sensitive |

The SFTP key file path `F:\ETL\Cert\openssh_wd_oas_prod` committed in `20191107_namdatasvc-1527_ConfigurationForOASExportSunriseFISPackages.sql` (line 34) constitutes a **credential path reference** checked into source control.

## Schema Design Quality

- **No schema DDL in this repo**: Design quality of the schemas themselves must be evaluated in DS_CCP_ods and DS_CCP_wired.
- **Job ownership**: All SQL Agent jobs use `@owner_login_name=N'sa'` — the built-in SA account. This violates PCI DSS Requirement 8.2 (shared/generic accounts) and makes audit trails for job execution non-attributable to individuals.
- **Hardcoded environment values**: Production server name `p-db09.nam.wirecard.sys\db09` is hardcoded in several job commands (e.g., `wired_cache_refresh` job) rather than resolved dynamically. Dynamic resolution via `@@SERVERNAME` is present in newer scripts but absent in older ones.
- **ENVREFERENCE numbers are hardcoded**: Commands like `/ENVREFERENCE 3` or `/ENVREFERENCE 4` reference SSISDB environment reference IDs by integer. These IDs are environment-specific and fragile; they will break if environments are rebuilt.

## Encryption at Rest

- The SSISDB sensitive variable `OASSFTPPassphrase` uses SSISDB's native sensitive parameter encryption (stored encrypted by the SSISDB master key). This is the correct pattern.
- No TDE (Transparent Database Encryption) evidence is detectable in this repo; TDE would be configured at the SQL Server instance level, not in these scripts.

## Data Retention

- The `Archive_Processed_Files` job provides file-level archival/deletion for ETL landing zone files. The `ODS.dbo.FilesToArchive` table (defined in DS_CCP_ods) governs retention days.
- No explicit data retention schedule for ODS tables (FISRpt*, RptNetwork*) is visible in this repo. This is a gap — PCI DSS Requirement 3.2.1 requires cardholder data retention to be minimized and governed by a formal policy.

## Referential Integrity

As a job-script repo, no FK constraints are defined here. FK relationships are defined in DS_CCP_ods.

## PCI DSS CDE Scope Assessment

**p-db09 is firmly in CDE scope.** The instance runs SSIS packages that process PAN-bearing FIS cardholder activity data, network settlement files, and unposted transaction data. The SQL Server Agent service account and SSISDB environment have access to cardholder data. All jobs that access ODS are in-scope for PCI DSS SAQ D / ROC assessment.
