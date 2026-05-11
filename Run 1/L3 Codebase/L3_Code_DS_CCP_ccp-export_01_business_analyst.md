# Business Analyst View — DS_CCP_ccp-export

## Business Purpose
The CCP-Export project is a collection of SQL Server Integration Services (SSIS) packages that extract CCP (Card/Cardholder Program) data from the internal ODS (Operational Data Store) and Oracle DWH (Data Warehouse), format it into pipe-delimited or CSV flat files, and deliver those files to external bank partners (primarily Sunrise Banks) and internal finance teams via SFTP. It is the outbound data-delivery leg of the CCP data pipeline.

## Capabilities
| Package | Business Function |
|---------|-----------------|
| `sunrise_export_account.dtsx` | Exports cardholder account records to Sunrise Banks (pipe-delimited, file: `sunrise_wdccp_customer_YYYYMMDD.txt`) |
| `sunrise_export_transaction.dtsx` | Exports posted transaction records to Sunrise Banks (pipe-delimited, file: `sunrise_wdccp_postedtran_YYYYMMDD.txt`) |
| `sunrise_export_balance.dtsx` | Exports account balance data to Sunrise Banks |
| `sunrise_export_cardstatus.dtsx` | Exports card status information to Sunrise Banks |
| `sunrise_export_Interchange.dtsx` | Exports interchange data |
| `sunrise_export_NetworkSettlement.dtsx` | Exports network settlement data |
| `sunrise_export_daily_recon_network.dtsx` | Daily network reconciliation export |
| `sunrise_export_daily_recon_sellingdeposit.dtsx` | Daily selling deposit reconciliation export |
| `sunrise_export_daily_recon_total_cardholder_balance.dtsx` | Daily total cardholder balance reconciliation |
| `oas_export_sunrise_fis_dailyfees.dtsx` | OAS daily fee export to Sunrise and FIS |
| `oas_export_sunrise_fis_settlement.dtsx` | OAS settlement export to Sunrise and FIS |
| `Files_sftp.dtsx` | SFTP file transfer orchestration package |

## Key Business Entities
- **Account** — cardholder account with Program Currency, Account Identifier, Create Date, Card Number fields
- **Transaction** — posted transaction with Unique Transaction ID, Settlement Date, Transaction Date, Amount, Fee, Description, Transaction Code
- **Balance** — cardholder account balance
- **Card Status** — active/inactive/blocked card state
- **Interchange** — card network interchange amounts
- **Network Settlement** — daily network settlement totals
- **Daily Reconciliation** — daily recon data across network, selling deposit, and total cardholder balance views

## Business Rules / Flows
1. Packages extract from ODS (SQL Server) and/or DWH (Oracle `dwh_aws_ssh`).
2. Data is written to pipe-delimited flat files in `C:\ETL\Work\` (local staging).
3. Files are optionally transferred to Sunrise Banks SFTP (`ftp.sunrisebanks.com`) and/or a Finance Copy SFTP (`sftp-qa.nam.wirecard.com`, folder `Inbound\ToFinance\`).
4. An OAS SFTP channel also exists for OAS-specific exports.
5. `Files_sftp.dtsx` handles the SFTP delivery step; SFTP can be enabled/disabled per project parameter.
6. Email notifications are sent when expected files do not exist (`NotifyEmailAddress` parameter).

## Compliance Relevance
- Exports include Card Number field (in `sunrise_export_account.dtsx`) — this is within the card data environment (CDE) scope and subject to PCI DSS Requirement 4 (protect data in transit) and Requirement 3 (protect stored data).
- Settlement and reconciliation data flows are relevant to NACHA (ACH settlement) and financial reporting obligations.
- File transfer to external bank partners must use encrypted channels (SFTP with key-based auth satisfies PCI DSS Req 4.2).

## Risks
- Card Number is exported in flat files; if files are not deleted promptly from `C:\ETL\Work\`, unencrypted card data persists at rest.
- DWH connection manager (`CCP - DWH.conmgr`) contains DPAPI-encrypted password stored in the `.conmgr` file — key is machine-bound; package cannot run on a different server without re-entering the password.
- Wirecardbranded SFTP endpoints (`sftp-qa.nam.wirecard.com`) suggest QA/legacy settings still in repository.
- No explicit file-deletion step for work files after SFTP transfer is confirmed visible in the package metadata examined.
