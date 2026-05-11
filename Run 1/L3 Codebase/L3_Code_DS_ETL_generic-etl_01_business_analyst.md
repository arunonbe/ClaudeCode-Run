# Business Analyst View — DS_ETL_generic-etl

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_generic-etl`
**Solution file:** `Generic-ETL.sln`
**SSIS project:** `ETL\ETL.dtproj`
**Git branch:** `development`
**README:** Minimal — placeholder (13 bytes)

This repository contains a **collection of reusable and miscellaneous SSIS packages** that do not fit neatly into the finance, GP, or maintenance categories. The name "generic-etl" indicates these packages were not purpose-built for a single financial process but serve multiple business use cases: FDR settlement import, IVR call log processing, CSL activity exports, network settlement, folder cleanup, and Salesforce/vendor data integration.

---

## Business Purpose

The generic ETL repository serves as a **utility toolkit** for the Onbe data services team. Its packages handle:

1. **Settlement data import** — FDR (First Data Resources) settlement file import, network settlement export
2. **Call centre data integration** — IVR call logs, cardholder contact logs for operational reporting
3. **Reference data maintenance** — CSL (Card Services List?) activity, CSA comment archiving
4. **File system management** — Folder/file cleanup utilities
5. **Third-party integrations** — Salesforce data (STARsf), vendor data updates
6. **Card lifecycle management** — IVR card activation updates

---

## Packages and Business Processes

### `FDR_Import_DD031.dtsx` (556,916 bytes — largest package)
**Business process:** Imports FDR (First Data Resources) settlement data — specifically the DD031 file type. DD031 is the First Data daily settlement/reconciliation file format used in the card processing industry. This package parses the binary/text FDR file and loads transaction records into Onbe's internal databases.

**Significance:** This is the primary **card processor settlement import** for Onbe's portfolio. Every card transaction processed by FDR must be reconciled through this package. The data includes:
- Transaction amounts
- Interchange fees
- Card-level settlement records (masked PANs)
- Merchant category codes

**Regulatory relevance:** FDR settlement data is within PCI DSS scope (masked PAN data; transaction settlement amounts). This package's data handling must comply with PCI DSS Requirements 3, 7, and 10.

### `IVR_CallLogs.dtsx` (227,720 bytes)
**Business process:** Imports IVR (Interactive Voice Response) call log data from a call centre system. IVR call logs contain cardholder interaction records: call timestamps, IVR menu selections, card inquiry events. Used for:
- Customer service analytics
- Fraud detection (unusual call patterns)
- Operational metrics reporting

**Data sensitivity:** IVR logs may contain partial card numbers (cardholders entering account numbers via keypad), timestamps, and call duration — potentially PCI DSS in-scope data.

### `RC_Contact_Log.dtsx` (156,968 bytes)
**Business process:** Recipient/Cardholder Contact Log processing. Imports contact centre interaction records (inbound calls, emails, chat) between cardholders and Onbe's customer service team. This feeds the operational reporting database for CRM and operational analytics.

### `CSL_Activity.dtsx` (49,896 bytes)
**Business process:** CSL (likely "Card Services Load" or "Client Services List") activity export. Extracts activity records — possibly card activation events, balance inquiries, or card programme milestones — for client reporting or internal tracking.

### `Add_CSA_Archive_Comment.dtsx` (72,145 bytes)
**Business process:** CSA (Customer Service Application) Archive Comment processing. Adds archive comments to transaction or account records — an audit trail maintenance function. Used to mark processed records as archived, supporting data lifecycle management and operational data housekeeping.

### `Export_Network_Settlement_Sunrise.dtsx` (34,571 bytes)
**Business process:** Exports network settlement data to Sunrise bank (a banking partner for card programme funding). Sunrise is one of the banking partners referenced in the DS_ETL_finance repo (Sunrise/Peoples/MB). This package generates Sunrise-specific settlement extracts.

### `IVR_card_activation_update.dtsx` (31,247 bytes)
**Business process:** Updates card activation status based on IVR interaction. When a cardholder activates their card via IVR, this package updates the card status in the platform database. This is a **card lifecycle management** process.

**Regulatory relevance:** Card activation status is a PCI DSS-relevant event (when a card becomes active, it enters the cardholder data environment). Accuracy of activation state affects fraud controls.

### `StarSf.dtsx` (61,136 bytes)
**Business process:** STAR (Shazam/STAR network?) Salesforce integration. Imports or exports STAR network data to/from Salesforce. The package:
- Reads an Excel spreadsheet (`STARsf_10_2020.XLSX`) from `C:\ETL\In\STARsf\`
- Sends email notifications on success/failure to `david.tran@northlane.com` and `techds@northlane.com`
- Uses SMTP server `smtp.nam.wirecard.sys`

The email address `@northlane.com` indicates this was built during the Northlane rebranding phase (Wirecard → Northlane → Onbe).

### `Folder_File_CleanUp.dtsx` (41,544 bytes)
**Business process:** File system housekeeping. Deletes or archives old files from working directories on the batch server. Prevents disk space accumulation from accumulated ETL output files.

---

## Data Flows

```
FDR settlement files (flat file)
  → FDR_Import_DD031.dtsx
    → Ecountcore_Process / cbaseapp databases

IVR call centre system
  → IVR_CallLogs.dtsx
    → cf_report (call log records)

Azure SQL Database (dw_api)
  → RC_Contact_Log.dtsx
    → internal reporting

STAR network Excel file
  → StarSf.dtsx
    → Salesforce (via Script Task)
```

---

## Schedule / Frequency

- **Daily:** `FDR_Import_DD031` (FDR files delivered daily); `IVR_CallLogs` (daily call log sync)
- **Daily/On-demand:** `IVR_card_activation_update` (near-real-time card activations)
- **Daily/Weekly:** `RC_Contact_Log` (CRM contact records sync)
- **Monthly:** `StarSf` (monthly STAR network file)
- **Nightly/Weekly:** `Folder_File_CleanUp` (file housekeeping)
- **On-demand:** `Add_CSA_Archive_Comment`, `CSL_Activity`, `Export_Network_Settlement_Sunrise`

---

## Business Rules Encoded

| Rule | Package | Detail |
|---|---|---|
| FDR file format parsing | `FDR_Import_DD031` | Fixed-format FDR DD031 file layout |
| Card activation event detection | `IVR_card_activation_update` | IVR keypad entry → activation flag update |
| Email notification on failure | `StarSf` | Sends to `techds@northlane.com` on file creation failure |
| SMTP connectivity | Project.params | `$Project::SMTPServer = smtp.nam.wirecard.sys` |

---

## Regulatory Relevance

| Regulation | Package | Notes |
|---|---|---|
| **PCI DSS Req 3, 10** | `FDR_Import_DD031` | FDR data may contain masked PANs; data access must be logged |
| **PCI DSS Req 12.3** | `IVR_card_activation_update` | Card activation state management |
| **GLBA** | `IVR_CallLogs`, `RC_Contact_Log` | Cardholder interaction records are non-public personal information |
| **Reg E** | `IVR_card_activation_update` | Card activation is a Reg E consumer rights event |
