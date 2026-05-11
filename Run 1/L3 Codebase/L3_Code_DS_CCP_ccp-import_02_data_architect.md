# Data Architect View — DS_CCP_ccp-import

## Data Stores
| Store | Type | Connection | Direction |
|-------|------|-----------|-----------|
| ODS (Operational Data Store) | SQL Server | `d-phl-db01.wirecard.lan,1433` / `ODS`, Integrated Security | Destination (write) + Source for aggregation |
| CCP DWH | Oracle ADO.NET | TNS `dwh_dev` (dev) | Source for aggregation (ccp_import_aggnetworksettlement) |
| FIS SFTP | SFTP | `sftp-qa.nam.wirecard.com:22`, user `ccp-uat` | Source (inbound files) |
| Mastercard SFTP | SFTP | Configurable (`MC_SFTP_HostName`) | Source (inbound files) |
| WDP SFTP | SFTP | Configurable (`WDP_SFTP_HostName`) | Source (inbound PGP-encrypted files) |
| Local Work Area | File system | `C:\ETL\Work\` + subdirectories | Staging (temp) |
| SFTP Execution Server | Windows host | `t-phl-db01.wirecard.lan` | SFTP module host |

## Source File Formats
### FIS Daily Fee File (CSV, comma-delimited with header)
Fields: `SETTLEMENT DATE | INSTITUTION ID | INSTITUTION NAME | CLIENT ID | CLIENT NAME | ...`
- `SETTLEMENT DATE`: date type (DataType=133)
- `INSTITUTION ID`: up to 17 chars
- `INSTITUTION NAME`: up to 30 chars
- `CLIENT ID`: up to 50 chars
- `CLIENT NAME`: up to 50 chars

### Mastercard Summary File (fixed-width, no header)
Columns (positional): `Column0 (1 char) | TransFunc (13 chars) | ProcCode (11 chars) | Orig (5 chars) | IRD (3 chars) | ...`
- Fixed-width ragged-right format; Mastercard-specific record layout

### WDP Unposted Transactions
PGP-encrypted file; decrypted before import; format details require examining `wdp_import_unpostedtrans.dtsx` fully.

### Aggregated Network Settlement
Internal SQL aggregation of settlement data in ODS; outputs to ODS tables. Parameters: `p_financial_institution` (e.g., "SRB"), `T_minus` (days offset from run date).

## Sensitive Data Inventory
| Field | Source | Classification |
|-------|--------|---------------|
| Client ID / Institution ID | FIS fee files | Business identifier |
| Settlement amounts | FIS, MC, WDP files | Financial |
| TransFunc / ProcCode | Mastercard summary | Network processing codes |
| WDP unposted transactions | WDP SFTP | May include partial account references — verify |
| WDP PGP passphrase | Project.params (sensitive=1) | Credential — must be protected |
| FIS/MC/WDP SFTP passwords | Project.params (sensitive=1) | Credential |

## Encryption and Data Protection
- FIS/MC SFTP: SSH key-based authentication supported; passwords also configurable; password fields marked sensitive (DPAPI in params).
- WDP files: PGP-encrypted in transit and at rest on SFTP server. Decrypted on the SSIS server using `WDP_PGPKey` (path to key file) and `WDP_PGPPassphrase` (DPAPI-encrypted).
- ODS connection: Windows Integrated Security — no stored password.
- DWH connection: Password empty in dev `.conmgr`; must be set for production.
- Flat files in `C:\ETL\Work\`: plaintext after FIS/MC decryption staging; WDP files decrypted locally.

## Data Flow
```
[FIS SFTP] ──SFTP──► C:\ETL\Work\ ──► fis_import_dailyfee.dtsx   ──► ODS (SQL Server)
[FIS SFTP] ──────►                ──► fis_import_dailyreport.dtsx ──►
[FIS SFTP] ──────►                ──► fis_import_plusISAfee.dtsx  ──►
[MC SFTP]  ──SFTP──►              ──► mc_import_summary.dtsx      ──►
[WDP SFTP] ──SFTP──► (PGP decrypt)──► wdp_import_unpostedtrans.dtsx ──►
                                   ──► ccp_import_aggnetworksettlement.dtsx ──► ODS
                                       (reads ODS + DWH, aggregates, writes back to ODS)
```

## Data Quality
- `ccp_import_aggnetworksettlement.dtsx` uses `T_minus=1` (yesterday) and records a completion message with `export_record_count`.
- No row-count or amount-total validation visible at the flat-file ingestion layer.
- FIS fee file uses header row (confirmed); Mastercard file is headerless fixed-width (alignment is critical).
- No duplicate-row detection visible; re-running the same day's import could produce duplicates in ODS.

## Compliance Gaps
1. **NACHA** — settlement data ingested but no automated reconciliation check comparing imported totals to expected values.
2. **PCI DSS Req 3** — WDP unposted transactions may contain account references; verify schema and apply masking if card numbers are present.
3. **PCI DSS Req 4.2** — WDP PGP encryption satisfies data-in-transit protection for WDP files; FIS and MC rely on SFTP (SSH) transport security.
4. **PCI DSS Req 10** — no centralised audit log of import execution and record counts.
5. **DPAPI secrets** — not enterprise key-managed; machine-bound risk.
