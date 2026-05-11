# Solution Architect View — DS_CCP_ccp-export-to-legacy

## Architecture Summary
SSIS Project Deployment Model solution containing 5 data-export packages, 1 SFTP delivery package, and 1 file-archiving package. The project bridges the CCP system (ODS SQL Server + Oracle DWH) to the legacy Ecount platform via SFTP-delivered flat files. Architecturally it is a simpler variant of `ccp-export`, targeting a single destination (legacy Ecount SFTP) with financial/billing data rather than cardholder/transaction data.

## Package Inventory
| Package | Data Type | Output File Pattern |
|---------|-----------|---------------------|
| `Export_billing_audit.dtsx` | Billing audit | `wdccp_billing_audit_AllYYYYMMDD.csv` |
| `Export_billing_detail.dtsx` | Billing detail | (billing detail file) |
| `Export_fvd_deferred.dtsx` | FVD deferred amounts | (FVD deferred file) |
| `Export_fvd_revenue.dtsx` | FVD revenue | `wdccp_fvd_revenue_AllYYYYMMDD.csv` |
| `Export_fvd_singleload.dtsx` | FVD single load | (FVD singleload file) |
| `Files_sftp.dtsx` | SFTP delivery | n/a (orchestration) |
| `Archive_Processed_Files.dtsx` | File archiving | n/a (file move) |

## Connection Manager Summary
| Manager | Type | Target |
|---------|------|--------|
| `ODS.conmgr` | OLEDB (SQLNCLI11.1) | `d-phl-db01.wirecard.lan,1433` / `ODS` — Integrated Security |
| `CCP - DWH.conmgr` | ADO.NET Oracle | TNS `dwh_dev` (dev) — password empty in dev .conmgr |
| `SMTP Connection Manager.conmgr` | SMTP | Mail server from parameter |
| `Files_sftp.dtsx` | SFTP | `sftp-qa.nam.wirecard.com:22` (QA default) |

## Security Assessment
| Area | Finding | Severity |
|------|---------|---------|
| DPAPI-encrypted SFTP credentials | Machine-bound; not enterprise key managed | High |
| QA SFTP hostname as default | Production env override required; risk of misconfiguration | Medium |
| Flat files at `C:\ETL\Work\` | Financial data (amounts, program IDs) at rest in plaintext | Medium |
| No file integrity verification | No hash/checksum of files before or after transfer | Medium |
| SSDT version mixing (14 + 15) | Potential package format incompatibility | Low |
| Archive before delivery confirmation | File could be archived without confirmed SFTP receipt | Medium |

## Technical Debt
1. **Transitional project** — this entire project is technical debt; it exists only to bridge two generations of systems.
2. **DPAPI secrets** — must be migrated to proper secret management.
3. **Wirecard-branded hostnames** — `sftp-qa.nam.wirecard.com`, `ccp-uat` — legacy credentials / QA values.
4. **No automated testing** — no validation that extracted billing amounts match source DB totals.
5. **No explicit delivery-confirmed archiving** — archive step should be conditioned on SFTP success.

## Gen-3 Migration Recommendations
1. **Priority: decommission this project** once legacy Ecount is retired. No Gen-3 equivalent should be built for the same purpose.
2. If legacy Ecount persists longer than expected, replace SSIS with ADF or Airflow pipeline that uses Azure Key Vault for SFTP credentials.
3. Add a delivery-confirmation step: only archive after receiving SFTP server acknowledgement (file rename or receipt file).
4. Implement financial reconciliation checksum: sum of FVD revenue amounts in output file must match source DB aggregate before file is delivered.
5. Define a formal decommission date and owner for this project in the architecture registry.
