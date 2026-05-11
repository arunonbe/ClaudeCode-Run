# Data Architect View — DS_CCP_ccp-export-to-legacy

## Data Stores
| Store | Type | Connection | Direction |
|-------|------|-----------|-----------|
| ODS (Operational Data Store) | SQL Server | `d-phl-db01.wirecard.lan,1433` / `ODS`, Integrated Security | Source (read) |
| CCP DWH | Oracle ADO.NET | TNS `dwh_dev` (dev) / `dwh_aws_ssh` (prod), user `rm_bi_user` | Source (read) |
| Flat File Work Area | File system | `C:\ETL\Work\` (via `TempFolder` parameter) | Staging (write + delete) |
| Legacy Ecount SFTP | SFTP | `sftp-qa.nam.wirecard.com:22` (QA default), user `ccp-uat` | Destination (write) |
| Archive Location | File system | (defined in `Archive_Processed_Files.dtsx`) | Archive (write) |

## Schema: Output File Formats
### Billing Audit (`wdccp_billing_audit_AllYYYYMMDD.csv`)
Pipe-delimited with column header row. Fields: `Date | Program | Promotion | Access_Level | Billing_Event | ...`

### FVD Revenue (`wdccp_fvd_revenue_AllYYYYMMDD.csv`)
Pipe-delimited with column header row. Fields: `Revenue_Date | Issuance_Date | Program | Amount | Financial_Institution`
- `Amount` is a high-precision decimal (DataPrecision=19, DataScale=5)

### FVD Deferred / Single Load
Similar pipe-delimited CSV format (specific columns not fully examined but follow same pattern).

## Sensitive Data Inventory
| Field | File | Classification |
|-------|------|---------------|
| Program ID | Billing audit, FVD | Operational reference |
| Promotion ID | Billing audit | Operational reference |
| Amount (FVD revenue) | FVD revenue | Financial — high precision |
| Financial Institution | FVD revenue | Business partner reference |
| Access_Level | Billing audit | Cardholder access control |
| Billing_Event | Billing audit | Billing action type |

No direct PAN/card numbers confirmed in these files (unlike ccp-export). However, Promotion ID and Program ID can be used to link to cardholder accounts — indirect PII linkage risk.

## Encryption and Data Protection
- ODS: Windows Integrated Security (SSPI) — no password stored.
- DWH: Password DPAPI-encrypted in `CCP - DWH.conmgr`; dev config uses TNS `dwh_dev` (password blank in dev `.conmgr`).
- SFTP credentials: `Legacy_SFTPPassword` and `Legacy_SFTPPassphrase` are DPAPI-encrypted (empty in dev; must be set for production).
- Flat files: No encryption at rest during staging.

## Data Flow
```
[ODS SQL Server] ──► Export_billing_audit.dtsx ──► wdccp_billing_audit_*.csv
[DWH Oracle]     ──► Export_fvd_revenue.dtsx   ──► wdccp_fvd_revenue_*.csv
                     Export_fvd_deferred.dtsx  ──► (deferred file)
                     Export_billing_detail.dtsx──► (billing detail)
                     Export_fvd_singleload.dtsx──► (singleload file)
                                  │
                                  ▼
                          Files_sftp.dtsx ──► Legacy Ecount SFTP
                                  │
                                  ▼
                     Archive_Processed_Files.dtsx ──► Archive folder
```

## Data Quality
- Column-header rows in output files (confirmed by `DTS:ColumnNamesInFirstDataRow="True"`).
- Amount field uses high-precision decimal (19,5) — appropriate for financial reconciliation.
- No record-count validation or hash comparison visible between source DB and output file.
- Archive step provides implicit confirmation that a file was produced; does not confirm SFTP delivery success.

## Compliance Gaps
1. **SOC 1 / Financial Controls** — no end-to-end integrity proof (hash/checksum) that the legacy platform received identical data to what was extracted from ODS/DWH.
2. **NACHA** — ACH-related financial amounts in FVD files should be reconciled against NACHA settlement reports; no automated reconciliation visible.
3. **Reg E** — Billing event audit data must be retained for dispute resolution; retention policy and deletion schedule not defined in this repo.
4. **PCI DSS Req 3.5** — DPAPI machine-bound encryption is not an enterprise key-management solution.
