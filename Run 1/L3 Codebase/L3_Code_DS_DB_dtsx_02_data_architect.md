# DS_DB_dtsx — Data Architect View

## Repository Type

This repository contains no SQL DDL for database objects. It is exclusively an archive of SSIS `.dtsx` package files and `.dtsConfig` external configuration files. All data objects referenced are in external databases (`Ecountcore`, `Ecountcore_Process_SS`, `cf_report`, `DYNAMICS`, `ecnt`). The data architecture assessment focuses on: package-level data flows, connection managers, sensitive data fields touched, and security of connection configuration.

---

## Complete Package Inventory

### PROD Environment (`PROD/p-na-bat03/D/c-base/`)

| Path | Package Name | SSIS Format Version |
|---|---|---|
| `bin/SSIS/AMLMantasETLNAM.dtsx` | AMLMantasETLNAM | SSIS 3 (SQL Server 2012) |
| `bin/SSIS/backup/AMLMantasETLNAM.dtsx` | AMLMantasETLNAM (backup) | SSIS 3 |
| `bin/SSIS/kuldip_backup/AMLMantasETLNAM.dtsx` | AMLMantasETLNAM (backup) | SSIS 3 |
| `runtime/BankProcessQueue/sunriseprod/Daily_Reconciliation_Files.dtsx` | Daily_Reconciliation_Files | SSIS 3 |
| `runtime/BankProcessQueue/sunriseprod/Daily_Reconciliation_Files_QA.dtsx` | Daily_Reconciliation_Files_QA | SSIS 3 |
| `runtime/batch/SSIS/BinBankETL.dtsx` | BinBankETL | SSIS 3 |
| `runtime/batch/SSIS/BinBankETL-old.dtsx` | BinBankETL (old) | SSIS 3 |
| `runtime/batch/SSIS/FDR_Import_DD031.dtsx` | FDR_Import_DD031 | SSIS 3 |
| `runtime/batch/SSIS/IVR_CallLogs.dtsx` | IVR_CallLogs | SSIS 3 |
| `runtime/ndmroot/citiprod/download/INVHJRCPTS/SSIS/CITI_INV_HJRCPTS_File_Processor.dtsx` | CITI_INV_HJRCPTS_File_Processor | SSIS 3 |
| `runtime/ndmroot/citiprod/download/INVHJVLM/SSIS/CITI_INV_HJVLM_File_Processor.dtsx` | CITI_INV_HJVLM_File_Processor | SSIS 3 |
| `runtime/ndmroot/citiprod/download/INVPLASTDUD/SSIS/CITI_INV_PLASTDUD_File_Processor.dtsx` | CITI_INV_PLASTDUD_File_Processor | SSIS 3 |
| `runtime/ndmroot/citiprod/download/INVPLASTICS/SSIS/CITI_INV_PLASTICS_File_Processor.dtsx` | CITI_INV_PLASTICS_File_Processor | SSIS 3 |
| `runtime/ndmroot/citiprod/download/INVPLASTPOS/SSIS/CITI_INV_PLASTPOS_File_Processor.dtsx` | CITI_INV_PLASTPOS_File_Processor | SSIS 3 |
| `runtime/ndmroot/citiprod/download/NAOTCardStatus/SSIS/NAOT_Card_Ship_File_Processor.dtsx` | NAOT_Card_Ship_File_Processor | SSIS 3 |
| `runtime/personix/download/CARDSTATUS/SSIS/Fiserv_Card_Ship_File_Processor.dtsx` | Fiserv_Card_Ship_File_Processor | SSIS 3 |
| `runtime/returned_checks/ssis/Returned_Checks.dtsx` | Returned_Checks | SSIS 3 |
| `Backup/06172018/JIRA 15/Returned_Checks.dtsx` | Returned_Checks (backup) | SSIS 3 |

### QA Environment (`QA/q-na-bat03/c-base/`)

| Path | Package Name |
|---|---|
| `bin/SSIS/AMLMantasETL.dtsx` | AMLMantasETL |
| `bin/SSIS/AMLMantasETLNAMPAT.dtsx` | AMLMantasETLNAMPAT |
| `bin/SSIS/AMLMantasETLNAMUAT.dtsx` | AMLMantasETLNAMUAT |
| `runtime/BankProcessQueue/sunrisestage/Daily_Reconciliation_Files.dtsx` | Daily_Reconciliation_Files |
| `runtime/batch/SSIS/BinBankETL.dtsx` | BinBankETL |
| `runtime/batch/SSIS/BinBankETL_old.dtsx` | BinBankETL_old |
| `runtime/batch/SSIS/FDR_Import_DD031.dtsx` | FDR_Import_DD031 |
| `runtime/ndmroot/citistage/SSIS/AMLMantasETLNAM.dtsx` | AMLMantasETLNAM |
| `runtime/ndmroot/citistage/download/NAOTCARDSTATUS/SSIS/NAOT_Card_Ship_File_Processor.dtsx` | NAOT_Card_Ship_File_Processor |
| `runtime/ndmroot/SSIS/AMLMantasETLNAM.dtsx` | AMLMantasETLNAM |
| `runtime/personix/download/CARDSTATUS/SSIS/Fiserv_Card_Ship_File_Processor.dtsx` | Fiserv_Card_Ship_File_Processor |
| `runtime/personix/download/CARDSTATUS/Fiserv_Card_Ship_File_Processor.dtsx` | Fiserv_Card_Ship_File_Processor |
| `runtime/Returned_Checks/SSIS/Returned_Checks.dtsx` | Returned_Checks |
| `backup/20180118/Returned_Checks_bkp.dtsx` | Returned_Checks (backup) |

### Configuration Files

| File | Environment | Purpose |
|---|---|---|
| `QA/q-na-bat03/c-base/runtime/ndmroot/SSIS/Mantas_NAM_UAT.dtsConfig` | QA/UAT | External config for AMLMantasETLNAM — overrides connection strings and passwords |
| `QA/q-na-bat03/c-base/runtime/ndmroot/SSIS/Mantas_NAM_UAT_backup.dtsConfig` | QA/UAT | Backup copy of above |
| `QA/q-na-bat03/c-base/runtime/ndmroot/citistage/SSIS/Mantas_NAM_UAT.dtsConfig` | QA/Stage | Stage-specific config |

---

## Connection Managers in AMLMantasETLNAM.dtsx

| Connection Name | Connection String / Server | Database | User |
|---|---|---|---|
| `DomesticReporting` | `ppamwdcPDsql4A1\ppamwdcPDsql4A1` / `p-db06-ha.nam.wirecard.sys\db06` | `Ecountcore_Process_SS` | `report` |
| `DYNAMICS` | `p-db08-ha.nam.wirecard.sys\db08` | `DYNAMICS` (Great Plains) | `report` |
| `GPCompanies` | `p-db08-ha.nam.wirecard.sys\db08` | `ecnt` | `report` |
| `Reporting` | `PPAMWDCUDSQL1C1\PPAMWDCUDSQL1C1` | `cf_report` | `report` |
| Various flat file connections | Local filesystem paths (`C:\...`) | N/A | N/A |

Connection managers in the `.dtsx` use **SQL Server Authentication** (`User ID=report`). Passwords are not embedded in the `.dtsx` files (ProtectionLevel=2 = EncryptSensitiveWithUserKey) but are present in plaintext in the `.dtsConfig` files (see Security section below).

---

## Data Flows — AMLMantasETLNAM.dtsx

The package extracts AML data via stored procedure calls into flat-file outputs destined for Oracle Mantas:

| Data Flow Component | Source Object | Destination File | Sensitive Fields |
|---|---|---|---|
| AccountFileExtract | `uspAMLAccountExtract` (SP on Ecountcore_Process_SS) | `Account_*.dat` | Account Identifier, Registration Type, **Primary Customer Account Password** (field name visible in column mapping) |
| AccountCustomerRole | SQL query | `AccountCustomerRole_*.dat` | Customer role / account linkage |
| AccountAddressFile | SQL query | `AccountAddress_*.dat` | Cardholder address data — **PII** |
| AccountBalance | SQL query | `AccountBalance_*.dat` | Account balance |
| FrontOfficeTransaction | SQL query | `FrontOfficeTransaction_*.dat` | Transaction data — **financial** |
| FrontOfficeTransactionParty | SQL query | `FrontOfficeTransactionParty_*.dat` | Party to transaction |
| ExchangeRateFile | SQL query | `FXTest.dat` | FX rates |
| EndOfJobFile | Signal file | `PREPAID_EMEA_MANTAS_FEED_*.eoj` | None |

---

## Sensitive Data Fields — Flagged

| Field | Package / Location | Data Classification | PCI/Regulatory Issue |
|---|---|---|---|
| **`Primary Customer Account Password`** | `AMLMantasETLNAM.dtsx`, AccountFileExtract column mapping (lines 765, 7382–7386, 8930–9920) | Customer credential | Sensitive — must not flow to AML flat files unmasked |
| **`cvv`** | `fdr_process_dd031_data` table (sourced via `FDR_Import_DD031.dtsx`) | SAD — CVV/CVC2 | **PCI DSS CRITICAL**: CVV must not be stored post-authorisation (Req 3.3.1) |
| **Account address data** | AccountAddress flat file from Mantas ETL | PII | CCPA / GDPR concern for cardholder address |
| **Account identifiers** | All Mantas ETL flat files | Cardholder account number | PCI DSS CDE scope |
| **DDA number** | FDR DD031 import, Returned Checks | Account number | PCI DSS |
| **Card number (plaintext in connection test data)** | Dev/test path `C:\Project\Development\SSIS\Mantas\output\TestData\` | PAN | PCI DSS Req 3 — test data with production-format card data must be sanitised |

---

## Encryption at Rest

- Package ProtectionLevel is set to `2` (EncryptSensitiveWithUserKey) in PROD packages — this means sensitive connection properties are encrypted using the Windows account under which the package was saved, **not** a transferable key. When packages are deployed to a different account/machine, the encryption is lost and values default to empty.
- The `.dtsConfig` files store passwords in **plaintext XML** — no encryption whatsoever.
- There is no evidence of SQL Server TDE on the source databases referenced by these packages.

---

## PCI DSS CDE Scope Assessment

The packages directly connect to `Ecountcore` and `Ecountcore_Process_SS`, which are confirmed CDE databases. Therefore:
- The batch server `p-na-bat03` executing these packages is **in-scope for PCI DSS**.
- The `.dtsConfig` files containing plaintext passwords must be treated as sensitive CDE artefacts.
- The flat-file output directory for Mantas feeds (on the filesystem of `p-na-bat03`) contains cardholder account data and must be in-scope.

---

## Data Retention

No explicit data retention policy is encoded in this repository. Flat file outputs to Oracle Mantas are written to filesystem directories with date-stamped names; no automated cleanup scripts are present. This represents an operational gap — cardholder data in output files may accumulate indefinitely on the batch server.
