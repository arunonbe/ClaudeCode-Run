# Solution Architect View — DS_CCP_ccp-export

## Architecture Summary
SSIS Project Deployment Model solution (`ccp-export.sln`) containing 11 data-export packages and one SFTP orchestration package. Each export package reads from ODS (SQL Server) or CCP DWH (Oracle), writes a pipe-delimited or CSV flat file to a local staging directory, then optionally transfers the file via SFTP. The project uses shared project-level connection managers (`ODS.conmgr`, `CCP - DWH.conmgr`, `SMTP Connection Manager.conmgr`, `Files_sftp.dtsx`) and project parameters (`Project.params`) for environment-specific values.

## Package Inventory
| Package | Sources | Output File Pattern |
|---------|---------|---------------------|
| `sunrise_export_account.dtsx` | ODS | `sunrise_wdccp_customer_YYYYMMDD.txt` |
| `sunrise_export_transaction.dtsx` | ODS | `sunrise_wdccp_postedtran_YYYYMMDD.txt` |
| `sunrise_export_balance.dtsx` | ODS | (balance file) |
| `sunrise_export_cardstatus.dtsx` | ODS | (card status file) |
| `sunrise_export_Interchange.dtsx` | ODS/DWH | (interchange file) |
| `sunrise_export_NetworkSettlement.dtsx` | ODS | (network settlement file) |
| `sunrise_export_daily_recon_network.dtsx` | ODS | (daily network recon) |
| `sunrise_export_daily_recon_sellingdeposit.dtsx` | ODS | (daily selling deposit recon) |
| `sunrise_export_daily_recon_total_cardholder_balance.dtsx` | ODS | (total balance recon) |
| `oas_export_sunrise_fis_dailyfees.dtsx` | ODS | (daily fees) |
| `oas_export_sunrise_fis_settlement.dtsx` | ODS | (settlement) |
| `Files_sftp.dtsx` | Local file system | SFTP delivery |

## Connection Manager Summary
| Manager | Type | Target | Auth |
|---------|------|--------|------|
| `ODS.conmgr` | OLEDB (SQLNCLI11.1) | `d-phl-db01.wirecard.lan,1433` / `ODS` | Integrated Security (SSPI) |
| `CCP - DWH.conmgr` | ADO.NET Oracle | TNS `dwh_aws_ssh` / user `rm_bi_user` | Password (DPAPI-encrypted) |
| `SMTP Connection Manager.conmgr` | SMTP | (server from `MailServerAccount` param) | (configured at runtime) |
| `Files_sftp.dtsx` | SFTP | Multiple endpoints via params | SSH key + passphrase (DPAPI) |

## Security Assessment
| Area | Finding | Severity |
|------|---------|---------|
| Card Number in output files | PAN exported in plaintext flat files at `C:\ETL\Work\` | Critical — PCI DSS |
| DPAPI-encrypted SFTP passwords in Project.params | Machine-bound; not portable; may be readable on compromised host | High |
| Oracle DWH password DPAPI-encrypted in .conmgr | Same machine-binding risk | High |
| `wirecardccpdev` SFTP username in params | Legacy/QA value; may indicate old credentials in use | Medium |
| No TLS for ODS connection | Integrated Security over internal network — acceptable if network is segmented | Low |
| No file integrity verification | No checksums on generated files before/after SFTP transfer | Medium |

## Technical Debt
1. **Oracle Client 12** — legacy 32-bit Oracle client required; blocks containerisation and modern SSIS IR deployment.
2. **DPAPI secrets** — non-portable; requires manual secret re-entry on any server migration.
3. **Wirecard-branded endpoints** — `sftp-qa.nam.wirecard.com`, `ccp-uat` username, `wirecardccpdev` reflect pre-Onbe branding.
4. **No automated tests** — SSIS packages have no unit or integration test framework.
5. **Hardcoded local paths** (`C:\ETL\Work\`, `C:\ETL\Cert\`) — prevent deployment flexibility.

## Gen-3 Migration Recommendations
1. Replace SSIS with a cloud-native pipeline (Azure Data Factory, AWS Glue, or Apache Airflow).
2. Move secrets to Azure Key Vault or AWS Secrets Manager; inject at runtime via pipeline parameters.
3. Replace flat-file SFTP delivery with encrypted SFTP with PGP-encrypted files, or negotiate API delivery with Sunrise Banks.
4. Mask or tokenise Card Number before writing to staging files; unmask only at point of delivery.
5. Implement post-transfer file deletion with audit log entry.
6. Add automated data-quality checks (record counts, amount totals) comparing source DB to output file.
