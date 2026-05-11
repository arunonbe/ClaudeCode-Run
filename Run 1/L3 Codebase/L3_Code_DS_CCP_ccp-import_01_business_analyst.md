# Business Analyst View — DS_CCP_ccp-import

## Business Purpose
The CCP-Import project ingests external data files from financial network partners (FIS/Wirecard, Mastercard, and WDP) into the CCP Operational Data Store (ODS). It is the inbound data-ingestion leg of the CCP pipeline, receiving daily settlement, fee, and transaction files from card network processors and loading them into SQL Server staging tables for downstream reporting and reconciliation. The project also includes an aggregated network settlement import specific to Sunrise Banks (SRB).

## Capabilities
| Package | Data Source | Business Function |
|---------|------------|-----------------|
| `fis_import_dailyfee.dtsx` | FIS SFTP | Imports daily fee summary: Settlement Date, Institution ID/Name, Client ID/Name, fee amounts |
| `fis_import_dailyreport.dtsx` | FIS SFTP | Imports FIS daily report data |
| `fis_import_plusISAfee.dtsx` | FIS SFTP | Imports FIS plus-ISA (International Service Assessment) fee data |
| `mc_import_summary.dtsx` | Mastercard SFTP | Imports Mastercard daily settlement summary (fixed-width format: TransFunc, ProcCode, Orig, IRD, etc.) |
| `wdp_import_unpostedtrans.dtsx` | WDP SFTP | Imports WDP unposted transactions |
| `ccp_import_aggnetworksettlement.dtsx` | ODS (internal) | Aggregates network settlement data; parameterised by financial institution (default: SRB) and T_minus days |
| `Files_sftp.dtsx` | Multiple SFTPs | SFTP file retrieval orchestration |

## Key Business Entities Imported
- **Daily Fee Record** — Settlement Date, Institution ID, Institution Name, Client ID, Client Name, fee amounts (FIS format, CSV)
- **Mastercard Settlement Summary** — TransFunc (transaction function), ProcCode (processing code), Orig (origin), IRD (interchange rate designator) — fixed-width format
- **WDP Unposted Transaction** — transaction records from WDP processor not yet settled
- **Aggregated Network Settlement** — rolled-up settlement totals per financial institution per day (parameterised by `p_financial_institution` and `T_minus`)

## Business Rules
1. FIS daily fee files arrive via SFTP from `sftp-qa.nam.wirecard.com` (user `ccp-uat`).
2. Mastercard summary files arrive via Mastercard SFTP (configurable host/credentials).
3. WDP files use PGP encryption (`WDP_PGPKey` / `WDP_PGPPassphrase` parameters); WDP files must be decrypted before import.
4. All SFTP transfers are enable/disable-gated per processor (`FIS_SFTP_Enable`, `MC_SFTP_Enable`, `WDP_SFTP_Enable`).
5. `ccp_import_aggnetworksettlement.dtsx` runs with `T_minus=1` (imports yesterday's data) and targets a specific financial institution.
6. An SFTP execution utility is referenced: `t-phl-db01.wirecard.lan` hosts the SFTP execution module (`SFTP_Server` parameter).
7. Email alerts fire when files are not found.

## Compliance Relevance
- Daily fee and settlement data is used for NACHA-required reconciliation.
- Mastercard settlement data is subject to card network rules (MC Settlement Agreement).
- WDP PGP-encrypted files indicate a vendor requirement for data-in-transit protection — compliance with partner security requirements.
- Unposted transaction data may contain partial card numbers or account references — potential PCI DSS Requirement 3 consideration.

## Risks
- SFTP defaults (`FIS_SFTP_Enable=false`) mean a configuration error (failing to set to `true` in production) would silently skip all imports.
- PGP key file paths (`WDP_PGPKey`) are configurable but empty in the repo — must be provisioned correctly on the server.
- `t-phl-db01.wirecard.lan` SFTP_Server reference is a legacy Wirecard internal hostname.
- WDP PGP passphrase is a sensitive parameter; empty in dev but must be protected in production.
