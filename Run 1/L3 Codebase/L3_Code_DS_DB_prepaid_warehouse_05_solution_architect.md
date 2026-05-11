# DS_DB_prepaid_warehouse — Solution Architect Assessment

## 1. Security Vulnerability Assessment

### 1.1 CRITICAL: PII Stored Unmasked in Analytical Tables
**Finding:** `dim.DimAccountHolder` (file: `dim/Tables/DimAccountHolder.sql`, lines 21–35) stores cardholder FirstName, LastName, MiddleName, SuffixName, Address1, Address2, ZipCode, City, State, Country, HomePhone, BusinessPhone, HomeEmail, and BusinessEmail in **plaintext VARCHAR columns**.

**Impact:** Any user with `db_datareader` or reporting role access can query the full PII set for every cardholder in the US prepaid portfolio. The `NAM_GTS_ECNT_DAT_PPDW_NA_RptgUsers` AD group has this access. This violates the principle of minimum necessary access and creates CCPA/GDPR exposure.

**Remediation (Priority: P1):**
- Implement SQL Server Dynamic Data Masking on name, address, phone, and email columns.
- Alternatively, remove PII from the warehouse and join to a secure identity service at reporting time.
- Implement column-level access controls: grant unmasked access only to authorised roles.

### 1.2 HIGH: DDA Numbers Stored Unmasked in Fact Tables
**Finding:** `fact.FactPaymentTransactions` (`FactPaymentTransactions.sql`, line 6), `fact.FactUtilizationTransactions`, and `fact.FactCardAccountDetail` all store `DDANumber` in plaintext (CHAR/VARCHAR 16). The DDA number is the primary account identifier linking a cardholder to their prepaid card account.

**Impact:** Full account numbers are exposed in OLAP-accessible columnstore indexes, increasing the attack surface during a data breach.

**Remediation (Priority: P1):**
- Apply Dynamic Data Masking or tokenise DDA numbers using a surrogate key for all reporting consumers.
- Restrict `SELECT` on DDA columns to a named role with business justification requirement.

### 1.3 HIGH: No Data Retention Enforcement
**Finding:** No DELETE, TRUNCATE, or archive stored procedures exist for the dimension or fact tables other than partition rolling for `FactAccountSnapshot`. Historical PII in `DimAccountHolder` accumulates indefinitely.

**Impact:** CCPA right-to-deletion requests cannot be systematically honoured. The database may retain PII for former cardholders for years beyond any business or regulatory need.

**Remediation (Priority: P1):**
- Define and implement a data retention policy procedure (e.g., anonymise `DimAccountHolder` PII fields for accounts inactive > N years).
- Document retention periods per data element in the data dictionary.

### 1.4 MEDIUM: Linked Server Exposes Production Query Surface
**Finding:** Multiple stored procedures reference `[REPORTINGDBSERVER].Ecountcore_SS.dbo.*` directly. This linked server provides read access from the warehouse to production operational data.

**Impact:** A compromised warehouse database can query operational cardholder data via the linked server, widening the blast radius of a warehouse-level breach.

**Remediation (Priority: P2):**
- Restrict linked server permissions to minimum required tables.
- Prefer pre-staged data landing in the `stagingdata` schema over live linked server queries from reporting procedures.

### 1.5 MEDIUM: `SqlServerVerification = False` Suppresses Build Validation
**Finding:** `Prepaid_Warehouse.sqlproj`, line 22: `<SqlServerVerification>False</SqlServerVerification>`.

**Impact:** SQL syntax errors and broken references are not caught at build time. Invalid SQL can be committed, deployed, and fail at runtime in production.

**Remediation (Priority: P2):**
- Enable `SqlServerVerification = True` and fix any resulting build errors.
- Add a CI pipeline build step that runs DACPAC compilation and fails the build on error.

---

## 2. All Database Objects with Purpose

### 2.1 Stored Procedures (dbo schema — reporting)

| Procedure | Purpose |
|---|---|
| `rpt_Aggregate_spending_By_Addenda` | Spend aggregated by addenda code |
| `rpt_Aggregate_spending_By_Addenda_Merchant_Name` | Spend by addenda + merchant name |
| `rpt_Aggregate_spending_By_mcc` | Spend by MCC |
| `rpt_Aggregate_Spending_by_MCC_and_Merchant` | Spend by MCC + merchant |
| `rpt_Aggregate_spending_By_merchant` | Spend by merchant |
| `rpt_Aggregate_spending_By_site_id` | Spend by site/program ID |
| `rpt_Aggregate_spending_By_site_id_api_dda_creation` | Spend + DDA creation by site |
| `rpt_Aggregate_spending_By_site_id_api_dda_creation_Merchant` | Spend + DDA + merchant |
| `rpt_Aggregate_spending_By_site_id_api_dda_creation_v2` | V2 variant |
| `rpt_back_order_report` | Card inventory back-order report |
| `rpt_Card_number_shortage_report` | Card number inventory shortage |
| `rpt_claimable_payment` | Claimable payment detail |
| `rpt_claimable_payment_summary` | Claimable payment summary |
| `rpt_Inventory_Management_Report_card` | Card inventory management |
| `rpt_Inventory_Management_Report_card_reissue_*` | Re-issuance inventory (3 dated variants — dead code) |
| `rpt_payment_detail` | Payment detail report |
| `Rpt_Pricing_Utilization_At_Card_Expiration` | Pricing/breakage at expiry |
| `Rpt_Pricing_Utilization_By_Month` | Monthly pricing/utilisation |
| `Rpt_Program_ReIssue_Cnt` | Re-issue count by program |
| `Rpt_Risk_Negative_Balance_By_Channel` | Risk: negative balance by channel |
| `Rpt_Risk_Negative_Balance_By_Channel_and_Bank` | Risk: negative balance by channel + bank |
| `Rpt_Risk_Negative_Balance_By_Channel_and_Bank_v1` | V1 variant (dead code) |
| `Rpt_Risk_New_Accounts_Current_Snapshot` | Risk: new accounts snapshot |
| `Rpt_Risk_Prior_Snapshot` | Risk: prior period snapshot |
| `Rpt_Risk_Reversal_Amounts` | Risk: reversal amounts |
| `Rpt_Risk_Reversal_Amounts_By_Bank` | Risk: reversals by bank |
| `Rpt_Risk_WriteOff_Collections_By_Channel` | Risk: write-offs + collections |
| `Rpt_Risk_WriteOff_Collections_By_Channel_and_Bank` | Risk: write-offs by channel + bank |
| `rpt_site_id_variance_report` | Site ID variance report |
| `rpt_site_id_variance_reporttab2` | Tab 2 of variance report |
| `rpt_std_header` | Standard report header |
| `rpt_std_header_new` | New variant standard header |
| `rpt_std_issuance_detail` | Standard issuance detail |
| `rpt_std_issuanceaggregate` | Standard issuance aggregate |
| `rpt_t_mobile_credit_reporting` | T-Mobile credit report |
| `rpt_T_Mobile_weekly02182014` | T-Mobile weekly (dated — dead code) |
| `rpt_Top_Aggregate_Spend_Center_Detail` | Top spend centre detail |
| `rpt_transaction_journals_MCC` | Transaction journal by MCC |
| `rpt_TTS_data_feed` | TTS partner data feed |
| `rpt_TTS_data_feed_Citi` | Citi TTS data feed |
| `rpt_Unclaimed_Payments_Reminder` | Unclaimed payments reminder |
| `rpt_util_get_report_ppd` | Utility: get PPD report parameters |
| `sproc_DeDupe_GFCIDs` | De-duplicate GFCID values |
| `sproc_Defrag_Indexes` | Index defragmentation |
| `sproc_Denormalize_Labels` | Denormalise label data |
| `sproc_Insert_ClaimablePayment_History` | Insert claimable payment history |
| `sproc_Insert_InferredPromos` | Insert inferred promotions |
| `sproc_Insert_Into_DDAVerification*` | DDA verification loading (4 steps) |
| `sproc_Insert_Into_dimAccountHolderWork` | Load account holder work |
| `sproc_Insert_Into_DimBIN*` | Load BIN dimension |
| `sproc_Insert_Into_DimEnrollment` | Load enrollment dimension |
| `sproc_Insert_Into_DimGeography*` | Load geography dimension |
| `sproc_Insert_Into_DimMerchantWork` | Load merchant work |
| `sproc_Insert_Into_DimProduct*` | Load product dimension |
| `sproc_Insert_Into_DimProgram*` | Load program dimension |
| `sproc_Insert_Into_DimSpend*` | Load spend dimension |
| `sproc_Insert_Into_ETLMasterHistory` | Log ETL run to history |
| `sproc_Insert_Into_FactCardAccountDetail` | Load card account detail fact |
| `sproc_Insert_Into_FactCardEmbossDetail` | Load emboss detail fact |
| `sproc_Insert_Into_FactJobSvcActions` | Load job service actions fact |
| `sproc_Insert_Into_FactOtherTransactions*` | Load other transactions fact (3 variants) |
| `sproc_Insert_Into_FactPaymentTransactions*` | Load payment transactions fact (4 variants) |
| `sproc_Insert_Into_FactTransactionAccounts` | Load transaction accounts fact |
| `sproc_Insert_Into_FactUnknownTransactions*` | Load unknown transactions fact |
| `sproc_Insert_Into_FactUtilizationTransactions*` | Load utilisation fact (3 variants) |
| `sproc_Insert_Into_Journal_*` | Load journal summary tables (3) |
| `sproc_Insert_Into_ProgramIssuanceMapWork` | Load program issuance map work |
| `sproc_Insert_Merchant_History` | Insert merchant history |
| `sproc_Insert_new_GFCIDs` | Insert new GFCIDs |
| `sproc_Insert_New_Into_Dim*` | New record inserts for 4 dimensions |
| `sproc_Insert_New_Program_Issuance` | Insert new program issuance mapping |
| `sproc_Insert_New_Promotions` | Insert new promotions |
| `sproc_Insert_ReIssued_Payments` | Insert re-issued payment records |
| `sproc_ReMap_Fact*Work` | Re-map fact work tables (3) |
| `sproc_Update_Account_Summ` | Update account summary |
| `sproc_Update_AccountPaymentKey` | Update account payment surrogate key |
| `sproc_Update_AccountSpendKey` | Update account spend surrogate key |
| `sproc_Update_AccountStatusKey` | Update account status surrogate key |
| `sproc_Update_AccountType_Age` | Update account type and age |
| `sproc_Update_AccountUtilizationKey` | Update account utilisation surrogate key |
| `sproc_Update_Allotments_History` | Update allotments history |
| `sproc_Update_CompanionCard_Accounts` | Update companion card accounts |
| `sproc_Update_DimInferredPromosWork` | Update inferred promo work |
| `sproc_Update_DimProduct` | Update product dimension |
| `sproc_Update_DimProgram` | Update program dimension |
| `sproc_Update_Existing_GFCIDs` | Update existing GFCIDs |
| `sproc_Update_Existing_Program_Issuance` | Update existing program issuance |
| `sproc_Update_FactCardEmbossDetail` | Update emboss detail fact |
| `sproc_Update_Journal_*` | Update journal summaries (3) |
| `sproc_Update_Original_PaymentStatus_History` | Update original payment status history |
| `sproc_Update_PaymentStatus_History` | Update payment status history |
| `sproc_Update_SpendDetailKey` | Update spend detail key |
| `sproc_Update_SpendType` | Update spend type |
| `sproc_Update_StdMerchantName` | Update standardised merchant name |
| `sprocInc_*` | ~50 incremental ETL procedures (see 02_data_architect.md for list) |
| `sprocRisk_*` | 6 risk data population procedures |
| `util_get_date_range` | Utility: compute date range |
| `stagingdata.cdc_stage_data_capure` | CDC capture staging procedure |

---

## 3. Technical Debt Remediation Priority

| Priority | Item | Effort | Risk |
|---|---|---|---|
| P1 — Immediate | Apply Dynamic Data Masking to `DimAccountHolder` PII columns | Medium (1–2 weeks) | CCPA, GDPR |
| P1 — Immediate | Implement data retention and deletion procedures | Medium (2–4 weeks) | CCPA right-to-delete |
| P1 — Immediate | Audit and restrict `db_datareader` role membership | Low (days) | Least-privilege |
| P2 — Short term | Set up CI/CD pipeline for DACPAC build validation | Medium (1–2 weeks) | Deployment quality |
| P2 — Short term | Enable `SqlServerVerification = True` | Low (days + fixes) | Build quality |
| P2 — Short term | Remove or archive dead-code dated procedure variants | Low (days) | Maintainability |
| P2 — Short term | Review and restrict linked server permissions | Low (days) | Security boundary |
| P3 — Medium term | Evaluate masking/tokenisation of DDA numbers in fact tables | High (months) | Data exposure |
| P3 — Medium term | Migrate to event-driven ETL with explicit SLA monitoring | Very High | Operational risk |

---

## 4. Compliance Gap Summary

| Regulation | Gap | Severity |
|---|---|---|
| CCPA / GDPR | No data retention limits; no anonymisation for inactive cardholders | Critical |
| PCI DSS Req 3.3 | DDA numbers in plaintext in analytical tables accessible to reporting users | High |
| PCI DSS Req 7 | `db_datareader` grants broad access — least privilege not enforced for PII columns | High |
| PCI DSS Req 10 | No CI/CD pipeline for change auditing; deployments may be unlogged | Medium |
| NIST CSF | No automated security validation in build pipeline | Medium |
