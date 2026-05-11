# DS_DB_vendor — Business Analyst Assessment

## 1. Repository Identity

| Attribute | Value |
|---|---|
| Repository name | DS_DB_vendor |
| Solution file | vendor.sln |
| Project name (sqlproj) | Vendor |
| SQL Server target | SQL Server 2016 (DSP: Sql130DatabaseSchemaProvider) |
| Build tool | Visual Studio SSDT, MSBuild ToolsVersion 4.0, .NET 4.5 |
| Project GUID | 690897c0-7f3a-4093-b866-fcdeefbd1c59 |

---

## 2. Business Purpose

The Vendor database is Onbe's **FDR (First Data Resources) processor integration and cardholder data hub**. It serves as the primary interface between Onbe's operational platform and the FDR card processing network, storing received cardholder data files, processing chargeback workflows, logging IVR (Interactive Voice Response) interactions, and providing the staging area for NESS (Negative Screening Service) OFAC/sanctions screening extracts.

The database has four functional schemas, each representing a distinct business domain:

1. **dbo** — FDR file import tables, IVR call logging, chargeback processing queue, NESS hits, and miscellaneous operational tables
2. **GBBase** — Global Bank Base data: `CustomerMaster`, `AuthorizedTransactions`, `PostedTransactions`, and `ReconVBase` — the core cardholder and transaction repository sourced from FDR file loads
3. **GBLoads** — ETL control schema: file tracking (`Files`, `FileSteps`), load log (`Log`), staging tables (`tmpNESSTable`), and the NESS extract procedures
4. **GBMap** — Reporting views (`DDA_Card_Account_Detail`, `Authorized_Transaction_Detail`, `Posted_Transaction_Detail`, `ReconV`) that join GBBase tables for downstream consumption

---

## 3. Business Processes Supported

### 3.1 FDR Processor File Ingestion
FDR sends daily file feeds containing cardholder data, transaction data, and card status updates. These are loaded into staging tables (`fdr_import_cd_012`, `fdr_import_cd_014`, `fdr_import_cd_051`, `fdr_import_cd_063`, `fdr_import_bm_406`, `fdr_import_dd_096`, `fdr_import_sd_091`) and then processed into `GBBase.CustomerMaster`, `GBBase.AuthorizedTransactions`, and `GBBase.PostedTransactions` through the `GBLoads.uspUpdateCustomerMaster` procedure.

The `GBLoads.Files` table tracks each file loaded (file name, start/end time, record count, status), providing a complete file ingestion audit trail.

### 3.2 NESS OFAC/Sanctions Screening Extracts
`GBLoads.uspNESSDailyExtract` (`GBLoads/Stored Procedures/uspNESSDailyExtract.sql`) extracts cardholder data (DDA number, last name, first name, full address) from `GBMap.DDA_Card_Account_Detail` for submission to the NESS screening engine. The procedure supports a configurable date range, defaulting to the prior day's records (`@DateRange = 1`), with automatic 3-day lookback on Mondays to capture weekend activity.

`GBLoads.uspNESSWeeklyExtract` provides the weekly version of the same extract. The `dbo.ness_hits` table receives NESS screening results back from the vendor — storing matched cardholder name, address, nationality, passport, birth date, matched SDN list alias, matched address, and disposition outcome (`disposition_id`, `reviewer_id`, `final`).

### 3.3 Chargeback Processing Workflow
The chargeback subsystem (`chargeback_process_queue`, `chargeback_process_status`, `chargeback_process_service`, `chargeback_rules`, `chargeback_profile_status_code`) manages an automated chargeback initiation and tracking pipeline. Stored procedures `chargeback_process_begin`, `chargeback_process_service`, `chargeback_process_callback`, and `chargeback_process_end` implement a state machine for chargeback processing:
- `chargeback_process_begin` creates a new process status record and returns the process ID
- `chargeback_process_service` performs the core chargeback work against FDR
- `chargeback_process_callback` handles async responses
- `chargeback_process_end` closes the process record

The `chargeback_process_queue` table stores per-chargeback records including `dda_number CHAR(16)`, `ticket_number`, `auth_amnt`, `tx_amnt`, `cb_amount`, `reason_code`, and processing status.

### 3.4 IVR (Interactive Voice Response) Call Logging
The IVR subsystem records every cardholder call to Onbe's automated phone service:
- `dbo.IVR_CallLog` — primary call record (session ID, ANI/DNIS, call start/end, duration, card number last 10 digits, ZIP, date of birth, language, activation status, lost/stolen request flag, transfer number)
- `dbo.IVR_CallLog_MenuChoices` — menu choices made during the call
- `dbo.IVR_ArkadinData` — Arkadin conferencing integration data
- `dbo.IVR_Fraud_Call_Log` — calls identified as potentially fraudulent

Six stored procedures manage IVR data: `usp_IVR_CallLog_INS`, `usp_IVR_CallLog_INS_From_RC`, `usp_IVR_CallLog_MenuChoices_INS`, `usp_IVR_ArkadinData_INS`, `usp_IVR_Fraud_Call_Log_INS`, and `usp_IVR_CallLog_Cleanup` (periodic cleanup of old call records).

### 3.5 FDR Report Processing
The `fdr_process_crf_*` tables (`fdr_process_crf_file`, `fdr_process_crf_file_detail`, `fdr_process_crf_status`) and `fdr_process_dcaf_*` tables manage FDR CRF (Card Request File) and DCAF (Debit Card Account File) processing. The DCAF tables store card hash, DDA number, expiration date, balance, and card status data received from FDR.

### 3.6 CitiShare File Processing
The `dbo.citishare_process_warehouse_file` table tracks CitiShare warehouse file processing — indicating a legacy integration with Citibank's share processing platform that predates the full FDR migration.

### 3.7 Thank You / Rewards Shipping Reports
The `thankyou_get_shipping_report*` stored procedures (4 variants including a date-range version, a current production version, a "new" version, and an archived 2009 version) generate shipping reports for the Thank You rewards program, tracking card fulfillment and delivery.

---

## 4. Data Stored

| Table/View | Key Sensitive Fields | Sensitivity |
|---|---|---|
| `GBBase.CustomerMaster` | `SSN VARCHAR(50)` plaintext, `CardNumber VARCHAR(100)`, `ECN VARBINARY(256)` (encrypted card), `ESN VARBINARY(256)` (encrypted SSN?), `EBD VARBINARY(256)` (encrypted DOB?), full name, address, phone, DOB | CRITICAL |
| `dbo.fdr_cardholder_master` | `card_number CHAR(16)` full PAN, `cardholder_name CHAR(54)`, `expiration DATETIME` | CRITICAL |
| `dbo.ness_hits` | Cardholder name, address, nationality, passport, birth_date, matched SDN list entries | CRITICAL |
| `dbo.IVR_CallLog` | `card_number VARCHAR(10)` (partial), `dob VARCHAR(12)`, `zip`, ANI (caller phone number) | HIGH |
| `GBBase.AuthorizedTransactions` | `CardNumber VARCHAR(30)`, `ECN VARBINARY(256)`, `AccountNumber`, transaction amount, merchant data | HIGH |
| `GBBase.PostedTransactions` | `CardNumber VARCHAR(30)`, `ECN VARBINARY(256)`, transaction amount, settlement date | HIGH |
| `GBMap.DDA_Card_Account_Detail` | View joining CustomerMaster: SSN, CardNumber, full name, address, DOB | CRITICAL |

---

## 5. Regulatory Relevance

### 5.1 PCI DSS — Highest Relevance
The Vendor database stores `fdr_cardholder_master.card_number CHAR(16)` (full PAN) and `GBBase.CustomerMaster.CardNumber VARCHAR(100)` without masking. **PCI DSS Requirement 3.3** requires that PAN be masked when displayed and **Requirement 3.4** requires PAN to be rendered unreadable anywhere it is stored. The presence of full card numbers in VARCHAR columns constitutes a direct PCI DSS compliance violation for any system not designated as the CDE, and even within the CDE, strong protection (truncation, tokenisation, or encryption with separately managed keys) is required.

### 5.2 OFAC — Direct Obligation
The NESS extract and `ness_hits` table represent Onbe's primary OFAC compliance mechanism for this customer population. The `uspNESSDailyExtract` procedure extracts records where `PICreated > @startdate AND PICreated > @enddate` (note the bug: both conditions use `>` rather than one being `>=` or between, potentially excluding boundary records). The `ness_hits` table stores the OFAC match results and their disposition — these records must be retained for BSA examination purposes.

### 5.3 GDPR / CCPA
`GBBase.CustomerMaster` stores full cardholder PII (name, address, DOB, SSN) for EU and other international cardholders (given the international product context). Any right-to-erasure (GDPR Art 17) or right-to-deletion (CCPA 1798.105) request must purge records from `CustomerMaster`, `AuthorizedTransactions`, `PostedTransactions`, and the associated CDC change tables.

### 5.4 Reg E
The chargeback processing tables (`chargeback_process_queue`, `chargeback_process_status`) support Reg E dispute resolution workflows. The `reason_code` and status tracking fields enable monitoring of Reg E-mandated dispute resolution timelines (10-day provisional credit, 45-day investigation).

### 5.5 BSA / AML
The NESS hit records in `dbo.ness_hits` serve as the documentary evidence of sanctions screening. The `disposition_id`, `reviewer_id`, and `final` fields track how each OFAC hit was resolved — this is a core BSA Program record that must be preserved for examination.

---

## 6. Named Service Account Consumers

The `Vendor_Select` role (`Security/Vendor_Select.sql`) grants SELECT access to 20+ accounts including all major production service accounts:
- `NAM\PPA_PRD_APISVC`, `NAM\PPA_PRD_OPSVC`, `NAM\PPA_PRD_CZSVC`, `NAM\PPA_PRD_ORDERSVC`
- `NAM\PPA_PRD_CSASVC`, `NAM\PPA_PRD_ECORESVC`, `NAM\PPA_PRD_BMCSVC`, `NAM\PPA_PRD_SCHSVC`
- `NAM\PPA_PRD_CSWSVC`, `NAM\PPA_PRD_IVRWSVC`, `NAM\PPA_PRD_ECAPSVC`, `NAM\PPA_PRD_NROLLSVC`
- `APPSUPPORT`, `report`, `CB_OFFICE\ProductionSupport-Admin`, `report_full`, `abat_vendor`, `NAM\PROD_CPP_APAC`

`db_owner` is granted to `vendor`, `NAM\jd62380`, and `NAM\PPA_PRD_ABAT` (`Security/RoleMemberships.sql`, lines 1–10) — giving these accounts unrestricted read and write access to all tables including `GBBase.CustomerMaster` with its plaintext SSN field.
