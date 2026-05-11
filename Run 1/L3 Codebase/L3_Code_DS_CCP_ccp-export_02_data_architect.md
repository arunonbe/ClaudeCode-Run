# Data Architect View — DS_CCP_ccp-export

## Data Stores
| Store | Type | Connection Details | Direction |
|-------|------|--------------------|-----------|
| ODS (Operational Data Store) | SQL Server 2017+ | `d-phl-db01.wirecard.lan,1433`, db `ODS`, Integrated Security (SSPI) | Source (read) |
| CCP DWH | Oracle (System.Data.OracleClient) | TNS alias `dwh_aws_ssh`, user `rm_bi_user` | Source (read) |
| Flat File Work Area | File system | `C:\ETL\Work\` (configurable via `BankTempFolder` parameter) | Staging (write) |
| Sunrise Banks SFTP | SFTP | `ftp.sunrisebanks.com:22`, key file `C:\ETL\Cert\id_sunrise_rsa` | Destination (write) |
| Finance Copy SFTP | SFTP | `sftp-qa.nam.wirecard.com:22` (QA value), remote path `Inbound\ToFinance\` | Destination (write) |
| OAS SFTP | SFTP | Hostname configurable; user/password as project parameters | Destination (write) |

## Schema: Key Output File Formats
### `sunrise_wdccp_customer_YYYYMMDD.txt` (Account Export)
Pipe-delimited columns: `Record Type | Program Currency | Account Identifier | Account Create Date | Card Number | ...`

### `sunrise_wdccp_postedtran_YYYYMMDD.txt` (Transaction Export)
Pipe-delimited columns: `RecordType | UniqueTransactionId | SettlementDate | TransactionDate | Amount | Fee | Description | TransactionCode | ...`

### Finance/OAS Files
CSV format (`wdccp_billing_audit_AllYYYYMMDD.csv`) — separate billing and fee files for Finance.

## Sensitive Data Inventory
| Field | File | Classification | PCI DSS Scope |
|-------|------|---------------|---------------|
| Card Number | `sunrise_wdccp_customer_*` | PAN / SAD | YES — CDE scope |
| Account Identifier | Multiple account files | Cardholder reference | Conditional |
| Transaction Amount | Transaction files | Financial | PCI DSS Req 3 |
| Settlement Amount | Settlement files | Financial | Regulatory |
| Fee Amount | Fee files | Financial | Regulatory |

**Card Number field is present in account export files — this is confirmed CDE data.**

## Encryption and Data Protection
- ODS connection: Windows Integrated Security (SSPI) — no password in connection manager.
- DWH (Oracle) connection: Password stored as DPAPI-encrypted blob in `CCP - DWH.conmgr` (machine-bound; marked `Sensitive="1"`).
- SFTP credentials (Bank password, passphrase, Finance Copy passphrase, OAS passphrase): DPAPI-encrypted in `Project.params` (marked `Sensitive="1"`).
- Flat files at `C:\ETL\Work\`: **No encryption at rest.** Files containing card numbers sit in plaintext on the ETL server during processing.
- SFTP transport: SSH key-based (`id_sunrise_rsa`, `id_ntt_rsa`) — satisfies PCI DSS Req 4.2.

## Data Flow
```
[ODS SQL Server] ──OLEDB──►┐
[DWH Oracle]   ──ADO.NET──►│  SSIS package  ──► pipe-delimited file (C:\ETL\Work\)
                            │                         │
                            └─ (per-package transforms)│
                                                       ▼
                                              Files_sftp.dtsx
                                                       │
                                    ┌──────────────────┼────────────────────┐
                                    ▼                  ▼                    ▼
                             Sunrise SFTP      Finance Copy SFTP        OAS SFTP
```

## Data Quality Controls
- File naming includes date suffix (`YYYYMMDD`) for uniqueness.
- Package parameter `T_minus` (where present) controls date window.
- No checksums or record-count validation visible in package metadata.
- No deduplication logic visible at the SSIS package level (handled upstream in DB queries).

## Compliance Gaps
1. **PCI DSS Req 3.4** — Card Number in flat files at `C:\ETL\Work\` is not masked or tokenised; constitutes unprotected PAN storage.
2. **PCI DSS Req 3.5** — DPAPI encryption of secrets is machine-bound; no enterprise key management integration.
3. **PCI DSS Req 12.3.2** — No documented file retention / purge schedule for `C:\ETL\Work\` staging files.
4. **NACHA** — Settlement file accuracy and reconciliation gaps are not validated end-to-end within the pipeline.
5. **PCI DSS Req 10.2** — No logging of file-transfer success/failure in a centralised audit log.
