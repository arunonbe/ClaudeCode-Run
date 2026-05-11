# DS_DB_dtsx — Business Analyst View

## Repository Overview

`DS_DB_dtsx` is a Git repository (hosted on GitLab under `northlane/development/data-services/databases/dtsx`) that stores SSIS (SQL Server Integration Services) package files (`.dtsx`) and configuration files (`.dtsConfig`) deployed to on-premises batch server infrastructure. The repository is a source-control snapshot of files physically residing on two batch servers: `p-na-bat03` (PROD) and `q-na-bat03` (QA/Stage). It does not contain application code or a build pipeline; it is a file archive of deployed ETL artefacts.

---

## Business Purpose

The packages in this repository constitute Onbe's (then Wirecard North America) legacy on-premises ETL layer. They perform:

1. **AML/BSA data feeds to Oracle Mantas** — Extracting account, transaction, customer, and address data from EcountCore and Great Plains databases and delivering them to Oracle Mantas for Anti-Money Laundering surveillance. This is a direct compliance obligation under the Bank Secrecy Act (BSA) and internal AML programme requirements.
2. **BIN/Bank ETL** — Loading BIN-to-bank mapping data into the core prepaid platform (cross-reference between card BIN ranges and issuing bank institutions).
3. **FDR File Import (DD031)** — Ingesting First Data Resources (FDR) settlement/transaction detail files (DD031 format) into the `Ecountcore_Process_SS` staging database for downstream posting.
4. **IVR Call Log Ingestion** — Importing IVR (Interactive Voice Response) call log data into the platform database.
5. **Daily Reconciliation Files** — Generating daily reconciliation data files for Sunrise bank partner.
6. **Citi NAOT Card Ship File Processing** — Processing Citi card shipping status files (NAOT format) that confirm physical card delivery events. Downstream effect: card status updates in EcountCore.
7. **Fiserv Card Ship File Processing** — Same function as above for Fiserv/Personix card fulfilment partner.
8. **Returned Checks Processing** — Extracting returned-check data from EcountCore to a CSV output file for downstream finance/operations handling. Connects directly to `p-db02.nam.wirecard.sys\db02.Ecountcore`.

---

## Processes Supported

| Package | Business Process | Regulatory Relevance |
|---|---|---|
| `AMLMantasETLNAM.dtsx` | AML surveillance data feed | BSA / AML / OFAC |
| `BinBankETL.dtsx` | BIN-bank mapping maintenance | Card network rules |
| `FDR_Import_DD031.dtsx` | FDR settlement file ingestion | PCI DSS, Reg E |
| `IVR_CallLogs.dtsx` | IVR call data import | Operational |
| `Daily_Reconciliation_Files.dtsx` | Bank partner reconciliation | Banking agreements |
| `CITI_INV_HJRCPTS_File_Processor.dtsx` | Citi inventory receipt processing | Inventory / card ordering |
| `CITI_INV_HJVLM_File_Processor.dtsx` | Citi inventory volume data | Inventory reporting |
| `CITI_INV_PLASTDUD_File_Processor.dtsx` | Citi plastic dud/defect reporting | Card quality |
| `CITI_INV_PLASTICS_File_Processor.dtsx` | Citi plastics inventory | Card stock management |
| `CITI_INV_PLASTPOS_File_Processor.dtsx` | Citi POS plastic data | Card stock management |
| `NAOT_Card_Ship_File_Processor.dtsx` | Citi NAOT card shipping status | Card lifecycle, Reg E |
| `Fiserv_Card_Ship_File_Processor.dtsx` | Fiserv card shipping status | Card lifecycle, Reg E |
| `Returned_Checks.dtsx` | Returned check extraction | NACHA / Reg E |

---

## Data Moved

- **Account data** (account identifiers, account types, registration types) fed to Mantas for AML scoring
- **Customer/cardholder data** (first name, last name, address, email, phone, date of birth — all flowing through AML extraction queries against EcountCore)
- **Transaction data** (FDR DD031 transaction records including card hash, DDA number, merchant data, CVV field from processor file, MCC codes)
- **Card shipping statuses** (card fulfilment events from Citi NAOT and Fiserv/Personix)
- **BIN-to-bank mapping** reference data
- **IVR call log records**

---

## Source and Destination Systems

| Connection Name | System | Direction |
|---|---|---|
| `Ecountcore` / `Ecountcore_Process_SS` | EcountCore production SQL Server (p-db02, p-db06) | Source |
| `DYNAMICS` | Great Plains ERP (p-db08) | Source |
| `GPCompanies` (`ecnt` catalog) | Great Plains companies DB | Source |
| `cf_report` | Reporting database | Source + Destination |
| Oracle Mantas (flat file output) | AML surveillance platform | Destination (flat files) |
| Sunrise bank partner (flat files) | Reconciliation partner | Destination |
| Citi NAOT (NDM download directories) | Card fulfilment partner | Source (file) |
| Fiserv/Personix (personix download directories) | Card fulfilment partner | Source (file) |
| SMTP (`smtp.nam.wirecard.sys`) | Email alerting | Destination |

---

## Regulatory Relevance

### PCI DSS
The AML Mantas ETL package (`AMLMantasETLNAM.dtsx`) extracts account-level data from EcountCore including fields mapped to cardholder identity. The `fdr_process_dd031_data` table ingested by `FDR_Import_DD031.dtsx` contains a `cvv` column sourced from FDR processor files — a **Critical PCI DSS finding**: CVV/CVC data must never be stored post-authorisation (PCI DSS v4.0.1 Requirement 3.3.1). The `.dtsConfig` files contain plaintext database passwords (password `[REDACTED — rotate immediately]` visible in `Mantas_NAM_UAT.dtsConfig`), violating PCI DSS Requirement 8.

### NACHA / Reg E
`Returned_Checks.dtsx` directly supports the ACH return processing workflow by extracting returned-check data from EcountCore. This is relevant to NACHA return code processing and Reg E dispute resolution timelines.

### OFAC / AML
`AMLMantasETLNAM.dtsx` is the primary ETL feeding the Oracle Mantas AML system, which is the platform used to perform OFAC sanctions screening and AML transaction monitoring. Failure of this ETL means AML alert generation may be delayed or incomplete — a direct BSA/OFAC compliance risk.

---

## Environments

| Environment | Batch Server | Configuration |
|---|---|---|
| PROD | `p-na-bat03` | `.dtsx` files in `PROD/p-na-bat03/D/c-base/...` |
| QA/Stage | `q-na-bat03` | `.dtsx` files in `QA/q-na-bat03/c-base/...`; separate `.dtsConfig` for UAT/Stage |

---

## Key Observations for Business

1. The repository contains multiple backup copies of packages (folders named `backup`, `Backup_19sept`, `kuldip_backup`, `original_backup`, `Backup_Kuldip`) indicating ad-hoc hotfix practices with no formal version control workflow.
2. Packages reference now-legacy domain names (`*.wirecard.sys`, `*.nam.wirecard.sys`) — all DNS and server references will need updating as part of any infrastructure migration.
3. The AML Mantas ETL is critical for regulatory compliance; any disruption is a reportable risk event.
4. There is no CI/CD pipeline evident in this repository — package deployment is entirely manual, file-copy based.
