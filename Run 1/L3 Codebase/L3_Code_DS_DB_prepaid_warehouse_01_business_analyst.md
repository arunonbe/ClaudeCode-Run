# DS_DB_prepaid_warehouse — Business Analyst Assessment

## 1. Repository Identity

| Attribute | Value |
|---|---|
| Repository name | DS_DB_prepaid_warehouse |
| Project name (sqlproj) | Prepaid_Warehouse |
| Solution file | Prepaid_Warehouse.sln |
| SQL Server target | SQL Server 2016 (DSP: Sql130DatabaseSchemaProvider) |
| Build tool | Visual Studio SSDT, MSBuild ToolsVersion 4.0, .NET 4.6.1 |
| Project GUID | 9004f41c-dc2a-4f19-8261-835666869c7f |

---

## 2. Business Purpose

The Prepaid Warehouse is the **US prepaid data warehouse** — the primary analytical and reporting database that aggregates historical transaction activity, cardholder lifecycle events, payment issuance records, and program performance metrics for the Onbe US prepaid card portfolio. It serves as the single authoritative source for management reporting, business intelligence, client-facing analytics, financial reconciliation, and regulatory reporting across the US prepaid business.

The database feeds downstream consumers including Crystal Reports, OLAP cubes, ad-hoc SQL reporting tools, and external data feed recipients (e.g., the TTS data feed used for third-party partner reporting). It is not an OLTP system; it is loaded from operational sources via ETL/CDC pipelines.

---

## 3. Business Processes Supported

### 3.1 Program Performance Reporting
Stored procedures prefixed `rpt_std_issuance*` and `rpt_std_header*` provide standard issuance aggregate and detail reports used by client services and relationship management teams. These span program-level payment counts, utilization volumes, and breakage analytics.

### 3.2 Transaction Spend Analytics
Procedures `rpt_Aggregate_spending_By_Addenda`, `rpt_Aggregate_spending_By_mcc`, `rpt_Aggregate_spending_By_merchant`, `rpt_Aggregate_Spending_by_MCC_and_Merchant`, and `rpt_Aggregate_spending_By_site_id` provide multi-dimensional spend aggregation broken down by merchant category code (MCC), merchant identity, addenda data, and site/program identifier.

### 3.3 Claimable Payment and Issuance Reporting
`rpt_claimable_payment` and `rpt_claimable_payment_summary` track claimable payment lifecycles — relevant to Reg E unclaimed funds, escheatment obligations, and revenue recognition.

### 3.4 Risk and Negative Balance Reporting
A set of `Rpt_Risk_*` stored procedures serves the Enterprise Risk group:
- `Rpt_Risk_Negative_Balance_By_Channel` / `_and_Bank` — daily monitoring of accounts with negative balance exposure
- `Rpt_Risk_New_Accounts_Current_Snapshot` / `Rpt_Risk_Prior_Snapshot` — account snapshot comparison for risk trending
- `Rpt_Risk_Reversal_Amounts` / `_By_Bank` — tracks credit reversals
- `Rpt_Risk_WriteOff_Collections_By_Channel` / `_and_Bank` — write-off and collections performance

These feed directly into operational risk decisions, provisioning, and loss accounting.

### 3.5 Card Inventory and Re-Issuance Tracking
`rpt_Inventory_Management_Report_card*` procedures (multiple dated variants from 2013) and `rpt_Card_number_shortage_report`, `rpt_back_order_report` support card inventory operations and fulfillment.

### 3.6 Financial Reconciliation
Tables `Reconcile_DailyLoad`, `Reconcile_HistoryLoad`, `Reconcile_RunningBalance`, `Reconcile_Transaction_Cube`, `Reconcile_DailyLoad_History` support daily and historical financial reconciliation between warehouse aggregates and operational system records.

### 3.7 Pricing and Utilization Analytics
`Rpt_Pricing_Utilization_At_Card_Expiration` and `Rpt_Pricing_Utilization_By_Month` feed pricing team analysis of breakage and utilization patterns for contract modeling.

### 3.8 Third-Party Data Feeds
`rpt_TTS_data_feed` and `rpt_TTS_data_feed_Citi` produce periodic data feeds delivered to the TTS (Total Transaction Services) partner and Citi. These feeds include program-level transaction volumes and active card counts.

### 3.9 T-Mobile Credit Reporting
`rpt_t_mobile_credit_reporting` and `rpt_T_Mobile_weekly02182014` serve a specific client program (T-Mobile) — demonstrating the warehouse supports white-label reporting obligations for named brand partners.

### 3.10 DDA Verification Tracking
`DDAVerification` table family (Steps 1–4) and associated sprocs track the multi-step verification of Demand Deposit Account (DDA/ACH) numbers, relevant to direct deposit and reload compliance.

### 3.11 OLAP Cube Incremental Feeds
Procedures prefixed `sprocInc_Create_ColumnStore_*` rebuild columnstore indexes for OLAP consumption; `_OLAPInc` fact tables and views support incremental OLAP loads.

---

## 4. Data Stored — Key Subject Areas

| Subject Area | Primary Tables | Sensitivity |
|---|---|---|
| Cardholder identity | `dim.DimAccountHolder` | **HIGH** — contains FirstName, LastName, Address1/2, ZipCode, City, State, Country, HomePhone, BusinessPhone, HomeEmail, BusinessEmail |
| Account/DDA identifiers | `dim.DimAccountHolder.DDANumber` (CHAR 16), `fact.FactCardAccountDetail.DDANumber` | **HIGH** — full DDA number stored in plain text |
| Payment transactions | `fact.FactPaymentTransactions`, `fact.FactPaymentTransactions_OLAPInc` | Moderate — amounts, dates, program keys, DDA number |
| Utilization (spend) transactions | `fact.FactUtilizationTransactions`, views | Moderate — merchant, MCC, amount, DDA number |
| Card emboss detail | `fact.FactCardEmbossDetail` | Moderate — card ID, fulfillment dates |
| Card account status | `fact.FactCardAccountDetail` | Moderate — block codes, card type, access level |
| Job service actions | `fact.FactJobSvcActions` | Low-Moderate |
| Staging/CDC feeds | `stagingdata.*` tables | Moderate — raw CDC extracts from operational systems |
| Risk collections/write-offs | `dbo.Risk_Collections`, `Risk_WriteOffs`, `Risk_NegativeBalance_Snapshot` | Moderate |
| Program and product metadata | `dim.DimProgram`, `dim.DimProduct`, `dim.DimBIN` | Low |

---

## 5. Regulatory Relevance

### 5.1 PCI DSS
The `dim.DimAccountHolder` table contains full cardholder name plus full DDA account number (16-character DDA, equivalent to account number). While DDA numbers are not technically PANs (they are ACH routing identifiers), they are closely associated with card accounts and constitute sensitive account data. The warehouse does **not** appear to store raw Primary Account Numbers (PANs/card numbers) directly in the dimensional model; however, the table `dbo.temp_fdr_card_number_bins` and `stagingdata.Hold_fdr_card_number_bins` reference card number BIN ranges, and the DDA number tied to a card ID in `FactCardAccountDetail` creates a linkage. DDA masking and access controls must be reviewed under PCI DSS Requirement 3.3.

### 5.2 GDPR / CCPA / Privacy
`dim.DimAccountHolder` stores first name, last name, full mailing address, phone numbers, and email addresses for US cardholders. Under CCPA, these are "personal information" subject to right-to-delete and right-to-know obligations. No anonymisation or pseudonymisation is evident from the schema. Data retention limits are not encoded in the schema (no purge/archive procedures observed).

### 5.3 Reg E / NACHA
Claimable payment and unclaimed payment reports (`rpt_Unclaimed_Payments_Reminder`, `rpt_claimable_payment`) support Reg E compliance for disputed transactions. DDA verification tables support NACHA ACH origination requirements.

### 5.4 Escheatment / State Unclaimed Property
`dim.DimAccountHolder.EscheatmentStatus` and `EscheatmentExpireDate` fields, combined with claimable payment reports, feed the escheatment reporting process required by state unclaimed property laws.

### 5.5 BSA/AML
Risk write-off and negative balance tables provide data that may feed BSA suspicious activity monitoring. The warehouse itself does not execute AML logic (that resides in RiskDB), but it is a data source for analytics that inform SAR filing decisions.

---

## 6. Named Security Roles and Access

The `Security/` folder defines database-level roles and members:
- `cf_report_Execute`, `cf_report_Select` — reporting roles
- `NAM_GTS_ECNT_DAT_PPDW_NA_RptgUsers` — named reporting user group for the Prepaid DW
- `NAM_PPA_PRD_ABAT` — production service account (ABAT batch automation)
- Individual `emer_*` accounts — emergency access accounts (elevated, time-limited DBA access)
- `ifs_infosec`, `ifs_gidadb` — InfoSec monitoring accounts
- `FortiDBRptRole` — FortiDB database activity monitoring role
- `vascan` — VA/vulnerability scanning account
- `scpardb` — SCAR/PAR DBA account

The presence of `NAM_PROD.sql` and `NAM_PROD_CPP.sql` security files indicates this database is deployed in the NAM (North America) production domain with CPP (Card Processing Platform) service account access.

---

## 7. Data Retention and Archival

No explicit data retention policy is encoded in the DDL. The history tables (`ETL_Master_History`, `Reconcile_DailyLoad_History`) suggest indefinite accumulation. Partition functions (`TransactionPartitionFunction`, `AcctSnapshotPartitionFunction`, `JobSvcPartitionFunction`) are defined in `Storage/` and the procedure `sprocInc_Remove_Oldest_Snapshot_Partition` suggests a rolling partition drop strategy for `FactAccountSnapshot`, but this is only implemented for snapshot data, not for the full transaction history or cardholder dimension.

---

## 8. Key Business Risks

1. **PII in analytical tables without masking** — `dim.DimAccountHolder` stores cardholder name, address, phone, and email in plaintext. If the warehouse is accessible to BI tools or reporting users who are not authorised for PII, this constitutes a data access control failure.
2. **No explicit data retention enforcement** — the warehouse accumulates historical data with no schema-encoded retention policy, creating regulatory exposure under CCPA (right to deletion) and potential PCI DSS Requirement 3.1 violations.
3. **DDA number as clear-text identifier** — the 16-character DDA number is the primary key across fact and dimension tables, stored without masking, enabling account-level linkage across all analytic queries.
4. **Multiple "work" and "hold" staging tables** — numerous staging tables (e.g., `PaymentWork`, `FactPaymentTransactionsHold`) retain intermediate ETL data that may contain sensitive fields beyond the production cycle.
