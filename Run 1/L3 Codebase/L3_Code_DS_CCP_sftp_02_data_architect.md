# Data Architect Report — DS_CCP_sftp

## Repository Nature — Data Architecture Scope

DS_CCP_sftp contains **no database schema objects**. There are no CREATE TABLE, CREATE VIEW, stored procedure, or index definitions. The repository is an SSIS (SQL Server Integration Services) project concerned entirely with binary file transport over SFTP. Its data architecture relevance is as an **integration component** — the mechanism by which sensitive payment data files move between systems.

## Database Objects

**None defined in this repository.**

The only database connection referenced is indirectly via the `SFTP.database` file (SSISDB catalog connection) and the `ODS.dbo.SFTPHosts` table in DS_CCP_ods which stores runtime SFTP configuration values for use by packages.

## Data Classification — Files Transported

Although the SFTP packages do not parse file content, the files they transport contain sensitive data:

| File Type | Direction | Known Content | PCI DSS Classification |
|---|---|---|---|
| FIS cardholder activity files (`.STL` files, processed by `sp_FISRpt_ImportDailyCardholderActivity`) | Inbound | **PAN (Primary Account Number)**, AccountNumber, transaction amounts, terminal data | **CDE — PAN data in transit** |
| FIS daily fee files (`.IXS.csv`) | Inbound | Fee amounts, institution codes | Financial — no PAN |
| FIS processor settlement files | Inbound | Settlement amounts, processor numbers | Financial — no PAN |
| Mastercard network files (`NAM_*_TT140*.*`) | Inbound | Network settlement records, MCC codes, amounts | Card scheme data |
| WDP unposted transaction files (`wdccp_unposted_trx_*.csv`) | Inbound | **Card numbers** (per `RptNetworkUnposted` schema — PAN equivalent) | **CDE** |
| OAS export files (FIS settlement/fee) | Outbound | Aggregated financial data | Financial |
| WIRED report files (Program Balance, Card Ship Date, etc.) | Outbound | Programme financial data, card shipping information | Client confidential |
| GP (Great Plains) export files | Inbound | Financial/GL data | Financial |

**Critical finding**: FIS cardholder activity files and WDP unposted transaction files transported by these packages contain PANs/card numbers. The SFTP packages handling these files are **in PCI DSS CDE scope as transmission components**.

## Sensitive Parameter Handling

From `Project.params`:

| Parameter | Sensitive Flag | Storage Method |
|---|---|---|
| `GP_SFTP_Password` | **YES (`SSIS:Sensitive="1"`)** | SSISDB sensitive parameter — encrypted at rest in SSISDB catalog |
| `GP_SFTP_SSHPassphrase` | **YES (`SSIS:Sensitive="1"`)** | SSISDB sensitive parameter — encrypted at rest |
| `GP_SFTP_HostName` | No | Plain text — defaults to `sftp-qa.nam.wirecard.com` |
| `GP_SFTP_SSHKey` | No | Path to key file — plain text |
| `GP_SFTP_Username` | No | Plain text |

The sensitive parameters use the SSIS `ProtectionLevel = "DontSaveSensitive"` pattern — sensitive values are not stored in the `.dtsx` files themselves (they show as empty). Actual values must be provided via SSISDB environment variables at runtime. This is the correct SSIS credential management pattern.

## Encryption in Transit

- SFTP protocol uses SSH for transport encryption. All file transfers are encrypted in transit, satisfying PCI DSS Requirement 4.2.1.
- Both password-based and SSH-key-based authentication are supported. SSH key-based authentication is more secure.
- The `GP_SFTP_SSHKey` parameter holds the path to an SSH private key file. The key file itself lives on the ETL server filesystem and is not stored in the repository or SSISDB (only the path is stored).

## Encryption at Rest (File System)

- Files in `C:\ETL\In\` and `C:\ETL\Archived\` are stored on the ETL server local filesystem. No evidence of filesystem-level encryption (BitLocker or similar) is visible in this repository.
- PCI DSS requires that PAN-bearing files be protected at rest. If FIS cardholder activity files land in `C:\ETL\In\` as unencrypted flat files, they are potentially accessible to any process or user with filesystem access to the ETL server.
- **This is a gap**: PCI DSS Requirement 3.5 applies to any location where PAN data is stored, including temporary landing zones. The ETL landing directories likely hold PAN-bearing files between SFTP receipt and SSIS processing.

## Schema Quality

Not applicable (no database schema). However, the SSISDB project-level parameter design is reasonable:
- Required parameters are flagged `Required=1` (e.g., `SourceFolder`, `filepattern`, `hostname`)
- Optional parameters are flagged `Required=0` (e.g., `archivepath`)
- Sensitive parameters correctly use `Sensitive=1` with empty default values

## Referential Integrity

Not applicable. The `ODS.dbo.SFTPHosts` table (DS_CCP_ods) serves as the relational SFTP configuration store and does have a PK (`[SFTP]` column). This package queries that table at runtime for host configuration.

## Data Flow Architecture

```
SSIS Package (Receive.dtsx)
├── Project Parameters: SourceFolder, GP_SFTP_*, NotifyEmailAddress
├── Connection: SFTP remote server (parameterised hostname/port/credentials)
└── Data Flow: Binary file download → Local landing zone (C:\ETL\In\)
    └── Archive: Move file to C:\ETL\Archived\ on success

SSIS Package (Send.dtsx)
├── Project Parameters: archivepath, filepattern, hostname, port, credentials, remotepath
├── Connection: SFTP remote server (parameterised)
└── Control Flow: Enumerate local files matching pattern → Upload each → Archive locally
```

## PCI DSS CDE Scope Assessment

**DS_CCP_sftp is in CDE scope as a transmission component.** Any system that transmits PANs is in-scope for PCI DSS under Requirement 4. Key considerations:

1. The SFTP component transmits FIS cardholder activity files containing PANs — CDE scope confirmed.
2. SSH encryption satisfies Req 4.2.1 for in-transit protection.
3. The ETL server's landing directories where files are temporarily stored after receipt are in CDE scope and require the same physical and logical access controls as the database.
4. SSISDB sensitive parameter encryption protects credentials at rest in the catalog.
5. The default `GP_SFTP_HostName = 'sftp-qa.nam.wirecard.com'` is a Wirecard QA server — this should be overridden in all deployment environments via SSISDB environment variables.
