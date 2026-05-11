# Business Analyst Report — DS_CCP_ods

## Repository Overview

DS_CCP_ods defines the **Operational Data Store (ODS)** database for the CCP ETL ecosystem. This is a Visual Studio SSDT SQL project (`.sqlproj` targeting SQL Server 2016 — DSP `Sql130DatabaseSchemaProvider`) that contains the full schema for the `ODS` database: 26 tables, 20+ stored procedures, database security roles, and permissions. The ODS sits between raw ETL file ingestion and the downstream WIRED report delivery system, serving as the analytical staging and reconciliation layer for network settlement, FIS processor data, and cardholder activity.

## Business Processes Supported

### 1. FIS Processor Settlement Reconciliation
The ODS ingests daily FIS (Fidelity National Information Services) settlement and fee reports received as flat files. The import pipeline transforms three categories of FIS reports:

- **Processor Settlement** (`FISRptProcessorSettlement`, imported by `sp_FISRpt_ImportDailyProcessorSettlement`): Net settlement amounts between Wirecard/Northlane and FIS as the card processor.
- **Daily Fee Reports** (`FISRptDailyFee`, imported by `sp_FISRpt_ImportDailyFee`): Daily fees charged by FIS, including various fee categories.
- **Plus ISA Fees** (`FISRptPlusISAFee`, imported by `sp_FISRpt_ImportPlusISAFee`): International Service Assessment fees applied by card networks on cross-border transactions.
- **Cardholder Activity** (`FISRptCardholderActivity`, imported by `sp_FISRpt_ImportDailyCardholderActivity`): Individual cardholder-level transaction activity, including **PAN data**.

The import process follows a staging→production pattern: data arrives in `*Staging` tables (flat columns) and is transformed/loaded into production tables via stored procedures. Archive tables (`*Archive`) capture deleted production records via FOR DELETE triggers.

### 2. Network Settlement Reporting
The ODS aggregates Mastercard and other network settlement data for reporting to bank partners (Sunrise Banks as the issuing bank):

- `RptNetworkImport` / `RptNetworkImportStaging`: Raw Mastercard settlement file rows.
- `RptNetworkAgg` / `RptNetworkAggStaging`: Aggregated network settlement totals (imported from Oracle CCP DWH).
- `RptNetworkSettlementData`: Transformed settlement transactions grouped by type (SALES, RETURNS, CHARGEBACKS, etc.).
- `RptNetworkSettlementDescr` / `RptNetworkSettlementAssociations`: Reference data for settlement descriptions and bank-to-association mappings.

The `RptNetworkSettlementReport` stored procedure generates both Interchange and Network Settlement reports used in daily reconciliation with Sunrise Banks.

### 3. Unposted Transaction Monitoring
`RptNetworkUnposted` and `RptNetworkUnposted_Staging` capture transactions that have been authorised but not yet settled (unposted/in-flight items). The `rpt_Unposted_Transactions` procedure and `sp_RptNetworkUnposted_Data_Transform` support monitoring of card number-level unposted items. This is a Reg E relevant dataset — unposted items that remain unresolved beyond regulatory timelines require investigation.

### 4. ETL File Tracking and Archival Management
`FileIOLog` is the central audit table for all ETL file movements (inbound and outbound). Every SSIS package that reads or writes a file logs a record here with status, filename, and timestamps. `FileIOLogActivity` captures all inserts and updates to `FileIOLog` via a trigger, providing a complete change history. `FilesToArchive` governs the retention/archival policy for ETL files.

### 5. Package Execution Scheduling
`package_execution` and `package_execution_log` support a lightweight scheduler: packages record their expected execution dates and parameters, enabling the `spVerifyImport` stored procedure to validate that all required data files have been received before downstream reports are generated.

### 6. Report Delivery Verification
`spVerifyImport` validates that all prerequisite files for interchange and network settlement exports have been received for each date in a reporting period. It checks Mastercard file counts (6 files per day, reduced to 1 post-CCP shutdown), WDP unposted files (2 per day, removed post-shutdown), and Oracle CCP aggregation records. If files are missing, it sends an HTML email alert via Database Mail to the DBA operator group.

### 7. SFTP Host Management
`SFTPHosts` stores the configuration for outbound SFTP connections (hostname, key file, port, username, enabled flag). This acts as a configuration store for SSIS packages that deliver files to external parties.

## Business Rules Encoded

1. **Network settlement weekend handling**: `RptNetworkSettlementReport` (lines 54–57) collapses Saturday-into-Sunday: if `@startdate` is a Sunday, it steps back one day; if `@enddate` is a Saturday, it steps forward one day. This encodes a business rule about how weekly network settlement cycles are reported.

2. **Auth Forwarding Flag processing** (added NAMDATASVC-1812/1809): The settlement report supports filtering by Auth Forwarding (AF) flag — separating self-issued vs. forwarded-to-bank authorisations. This is a card issuer-level business rule about transaction routing.

3. **CCP Shutdown adjustment** (coded comment, line 77 and 109 of `spVerifyImport`): The validation logic was updated from requiring 6 MC files + 2 WDP files + 1 AGG record to requiring only 1 MC file after July 31, 2020 CCP shutdown. This business rule change is embedded in a SQL comment.

4. **File import idempotency**: `sp_FISRpt_ImportDailyWrapper` calls individual import procedures. The staging-to-production pattern ensures a file is not imported twice if the `FileIOLog` status tracking is respected.

5. **Cardholder activity debit/credit inversion logic**: `sp_FISRpt_ImportDailyCardholderActivity` (lines 66–88) applies sign-correction rules based on `DebitMark`/`CreditMark` values (`'-'` inverts the amount; `'*'` or `'**'` zeros it if rejected). This encodes FIS file format business rules.

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS (Level 1)** | **CRITICAL.** `FISRptCardholderActivity.PAN` stores full PANs (masked via Dynamic Data Masking at display layer, but stored as VARCHAR(19)). `RptNetworkUnposted.Card Number` also stores card numbers. This database is **in-CDE scope**. |
| **Reg E (Electronic Funds Transfer Act)** | Unposted transaction monitoring (`RptNetworkUnposted`) supports detection of EFT errors. The 3-day and 10-day resolution windows under Reg E require timely visibility of unposted items. |
| **NACHA** | Network settlement reconciliation supports ACH-adjacent interbank settlement obligations. |
| **SOC 1 Type II** | The `FileIOLog` table and `spVerifyImport` procedure provide the automated completeness controls likely tested in SOC 1 audits for financial reporting accuracy. |
| **GDPR / CCPA** | Cardholder names are not visible in these tables, but the combination of PAN, AccountNumber, and transaction data constitutes personal financial data subject to privacy regulations. |

## Integration Points

- **Upstream**: FIS flat files (`.STL`, `.IXS.csv` formats), Mastercard network files (`NAM_*_TT140*`), Oracle CCP DWH (via `ccp_import_aggnetworksettlement` SSIS package), WDP unposted transaction files (`wdccp_unposted_trx_*.csv`).
- **Downstream**: WIRED report database (reads from ODS for Network Settlement reports), OAS export to `sftp.wirecard.com` (FIS settlement/fee data for Sunrise Banks reconciliation).
- **Internal**: DS_CCP_db09 (SQL Agent job definitions that execute ODS procedures), DS_CCP_ccp-import (SSIS packages that populate ODS), DS_CCP_sftp (generic SFTP component used by OAS export packages).
