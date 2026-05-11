# Solution Architect View — DS_CCP_ccp-import

## Architecture Summary
SSIS Project Deployment Model solution containing 6 import packages, 1 SFTP receive orchestration package, and 1 DTEXEC parameters file. The project pulls files from three external partner SFTP servers (FIS, Mastercard, WDP), stages them locally, imports into ODS SQL Server, and runs a post-import aggregation step. WDP files are PGP-encrypted; all SFTP connections support SSH key or password authentication.

## Package Inventory
| Package | Input | Output (ODS table) |
|---------|-------|-------------------|
| `fis_import_dailyfee.dtsx` | CSV from FIS SFTP | Daily fee staging table |
| `fis_import_dailyreport.dtsx` | CSV from FIS SFTP | Daily report staging table |
| `fis_import_plusISAfee.dtsx` | CSV from FIS SFTP | ISA fee staging table |
| `mc_import_summary.dtsx` | Fixed-width from MC SFTP | MC settlement summary table |
| `wdp_import_unpostedtrans.dtsx` | PGP-decrypted file from WDP SFTP | Unposted transactions table |
| `ccp_import_aggnetworksettlement.dtsx` | ODS + DWH Oracle | Aggregated network settlement table |
| `Files_sftp.dtsx` | Project params | File download orchestration |
| `DTEXEC-SFTP-Receive.dtsxp` | n/a | DTEXEC run parameters |

## Connection Manager Summary
| Manager | Type | Target |
|---------|------|--------|
| `ODS.conmgr` | OLEDB (SQLNCLI11.1) | `d-phl-db01.wirecard.lan,1433` / `ODS` — Integrated Security |
| `CCP - DWH.conmgr` | ADO.NET Oracle | TNS `dwh_dev` (dev); `dwh_aws_ssh` (prod) |
| `SMTP Connection Manager.conmgr` | SMTP | Mail server |

## Security Assessment
| Area | Finding | Severity |
|------|---------|---------|
| All SFTP enables default `false` | Silent no-op if production env vars not applied | High |
| WDP PGP key path empty in repo | PGP decryption will fail until key is provisioned on server | High |
| DPAPI-encrypted SFTP/PGP credentials | Machine-bound; not enterprise key managed | High |
| WDP files decrypted to `C:\ETL\Work\` | Decrypted financial data at rest in plaintext staging area | Medium |
| `sftp-qa.nam.wirecard.com` default host | Legacy Wirecard QA endpoint; production override required | Medium |
| `t-phl-db01.wirecard.lan` SFTP server | Legacy Wirecard internal server; may not exist post-migration | Medium |
| No duplicate-row detection on import | Re-running inserts duplicates into ODS without error | Medium |
| MC fixed-width parsing | Format drift would silently corrupt data | Medium |

## Technical Debt
1. **Legacy partner endpoints** — FIS, MC, and WDP all reference legacy Wirecard/QA hostnames as defaults.
2. **File-system PGP key storage** — WDP PGP key file must be on the SSIS host; not in a secrets manager.
3. **No idempotent import** — same-day re-runs produce duplicate ODS rows; should use MERGE or staging table with dedup.
4. **Mastercard fixed-width** — no schema documentation; format changes require manual discovery and code updates.
5. **Mixed SSDT versions** — potential format inconsistency across packages.
6. **No automated testing** — no test harness validates that imported data matches expected source counts.

## Gen-3 Migration Recommendations
1. Replace SSIS with cloud-native pipeline (ADF / Airflow / AWS Glue) with native SFTP connectors.
2. Move PGP keys and SFTP credentials to Azure Key Vault or AWS Secrets Manager.
3. Implement upsert/MERGE pattern in ODS target tables to prevent duplicate rows on re-run.
4. Add schema validation for Mastercard fixed-width files: byte-count assertion on file header before parsing.
5. Implement import audit table: for each run, record (processor, run_date, file_name, record_count, status).
6. Add SFTP enable flags to environment-specific configuration (ADF linked service or Airflow variable) with `true` as production default.
