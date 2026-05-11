# DS_DB_riskdb — Business Analyst Assessment

## 1. Repository Identity

| Attribute | Value |
|---|---|
| Repository name | DS_DB_riskdb |
| Project name (sqlproj) | riskdb |
| Solution file | riskdb.sln |
| SQL Server target | SQL Server 2016 (DSP: Sql130DatabaseSchemaProvider) |
| Build tool | Visual Studio SSDT, MSBuild ToolsVersion 4.0, .NET 4.5 |
| DACPAC present | Yes — `RiskDBv1.0.0.0.dacpac` |
| Project GUID | 0f787d48-dad3-4b52-8c89-b631d551fae8 |

---

## 2. Business Purpose

The Risk Database is Onbe's **centralised risk management and analytics platform** — a large multi-purpose database serving:

1. **Fraud monitoring and detection** — daily and real-time fraud risk reports, velocity checks, CVV mismatch detection, high-dollar transaction monitoring, manual key entry detection
2. **AML (Anti-Money Laundering) case management** — AML case creation, assignment, status tracking, and monthly reporting
3. **OFAC / sanctions screening** — the `ness_hits` table in the Vendor database stores NESS (likely WorldCompliance or a similar screening engine) screening output that feeds risk decisioning
4. **Chargeback and dispute management** — `EUC_DMT_CASE*` table family and fraud report procedures (sp_FRAUD_REPORT_124 through sp_FRAUD_REPORT_173) track Reg E disputes and chargebacks
5. **DMT (Data Management Tool) back-end** — a large collection of EUC_DMT_* procedures serve Onbe's internal DMT application, which appears to be a case management and workflow tool used by Risk, Operations, and Compliance teams
6. **EUC (End User Computing) analytics** — Excel/BI add-in data feeds (`EUC_AddIn_*` procedures) for Risk and Operations analysts
7. **Operational monitoring** — daily risk monitoring reports (transaction velocity, fee reversals, high-dollar credits, ACH changes, direct deposit monitoring)

The database is extremely large and heterogeneous — the `_archived` folders and multiple `Tables1`, `Tables2`, `Tables3` sub-folders indicate significant historical accumulation, including individual ad-hoc tables committed by named users (e.g., `_archived/NAM_Byron.Young/`, `_archived/NAM_Michael.Gevaryahu/`).

---

## 3. Business Processes Supported

### 3.1 Daily Fraud Risk Reports (DailyRiskReports.sql)
The `DailyRiskReports` stored procedure (`dbo/Stored Procedures/DailyRiskReports.sql`) is the core daily fraud monitoring job. It populates the following monitoring tables from the operational data (via linked server to `[REPORTINGDBSERVER]`):

- `monitor_transaction_velocity_report` — accounts with 10+ transactions in a day, exceeding their 3-month weekly average
- `monitor_fee_reversals` — all fee reversals/credits applied by internal employees (CSRs, Risk Group)
- `monitor_cvv_mismatch_report` — transactions declined for CVV2 mismatch (decline codes 84, 85) — indicator of card-not-present fraud or manual key entry
- `monitor_high_dollar_report` — accounts with daily transaction volume $5,000+ exceeding historical tolerance
- `monitor_manual_key_report` — transactions using POS entry code '01' (manual key) for amounts >$500 with 5+ attempts — indicator of card skimming or testing
- `monitor_high_dollar_credits` — retail credit transactions ($100+) without prior debit from same merchant — Visa terms violation indicator
- `monitor_direct_deposit` — high-dollar direct deposit transactions ($5,000+)
- `monitor_ach_detail` — ACH device changes (bank account updates) with associated cardholder names, emails — **PII accessed via linked server**
- `monitor_ach_summary` — accounts with 3+ ACH device changes

### 3.2 AML Case Module (Analytics_sp_AML_Case_Module.sql)
Creates AML investigation cases for high-balance accounts (above $0 threshold) in Payroll, Maritime Payroll, and Sales Incentive verticals. The procedure:
- Queries live balances from `[REPORTINGDBSERVER].ECountcore_ss`
- Identifies top-10 highest-balance accounts per vertical not already under investigation within 3 months
- Inserts case data into `EUC_DMT_AMLCase_DATA` and `EUC_DMT_AMLCase_DATAchangesetcache`
- Hardcodes case owner as `Nathan.Sandiford` (line 512 of AML procedure) — compliance risk if this person is no longer the correct owner

### 3.3 AML/CDD Monthly Reporting
`Analytics_sp_DMT_AMLCDD_MonthlyReport` and `Analytics_sp_DMT_AMLCDD_PeriodicReview` support BSA/AML Customer Due Diligence (CDD) obligations, producing monthly and periodic review reports for the Compliance team.

### 3.4 Chargeback / Reg E Dispute Management
`sp_FRAUD_REPORT_124` through `sp_FRAUD_REPORT_173` produce reports covering:
- Chargebacks received previous day (124)
- Chargeback claim type and status counts (125)
- Chargeback cases closed previous day (127, 133, 140)
- Cases received previous month (134)
- Oldest open case and count (139)
- Cases under $200 (142)
- Pending cases (163)
- Past due cases (173)
- Reg E flag on all chargeback cases (124 — `[Reg E - Y/N <Log Information>]` field)

These feed Onbe's Reg E dispute resolution obligations (60-day resolution requirement, provisional credit rules).

### 3.5 CFPB Reporting
`Analytics_sp_CFPB_Update` suggests active CFPB (Consumer Financial Protection Bureau) reporting obligations are supported by this database. CFPB complaints and supervisory reporting are compliance obligations for prepaid card issuers under the Prepaid Rule (12 CFR 1005).

### 3.6 NOC / ACH Returns Processing
`sp_NOC_Transform_Combine_NOCFiles` processes NACHA Notification of Change (NOC) files, transforming and combining NOC data for routing number and account number correction workflows.

### 3.7 DMT Workflow Automation
Hundreds of `EUC_DMT_*` procedures automate the Data Management Tool workflow — creating, updating, and closing cases across business domains: AML cases, fraud cases, chargebacks, ATM management, program builds, pricing, contracts, stock assignment, subpoenas, vendor invoices, and entitlements management.

---

## 4. Regulatory Relevance — HIGH COMPLIANCE

### 4.1 BSA / AML
- `EUC_DMT_AMLCase_DATA`, `EUC_DMT_AMLCDD_DATA` — AML case records including DDA numbers, cardholder names, balances, and investigation status. BSA requires records related to SARs and CTRs to be retained for 5 years.
- `Analytics_sp_AML_Case_Module` — automated AML case generation from balance-based triggers
- `Analytics_sp_DMT_AMLCDD_MonthlyReport` / `PeriodicReview` — CDD program compliance reports

### 4.2 OFAC / Sanctions Screening
- The `ness_hits` table (in the Vendor database, but referenced and fed through this risk ecosystem) stores the output of NESS screening against the OFAC SDN list, EU consolidated list, and other sanctions lists.
- `GBLoads.uspNESSDailyExtract` (Vendor database) extracts cardholder data for NESS screening daily.
- **Gap identified:** There is no visible stored procedure in riskdb that implements real-time OFAC screening against a local sanctions list. Screening appears to be batch-based (daily NESS extract). This means cardholders added to the OFAC SDN list between screening cycles are not blocked until the next daily run — a potential BSA/AML Program gap.

### 4.3 Reg E
- Dispute tracking through `EUC_DMT_CASE*` tables and `sp_FRAUD_REPORT_*` procedures directly supports Reg E compliance
- `[Reg E - Y/N]` field in case data distinguishes Reg E disputes from non-Reg E chargebacks

### 4.4 CFPB
- `Analytics_sp_CFPB_Update` and `EUC_DMT_CFPBProgram_*` procedures support CFPB supervisory obligations

### 4.5 PCI DSS
- The `DailyRiskReports` procedure accesses `dda_number`, `first_name`, `last_name`, `home_email` via linked server queries to operational databases. The RiskDB itself stores derived/aggregated DDA numbers in monitoring tables.
- DDA numbers stored in `monitor_*` tables and case data are account-sensitive data.

---

## 5. Key Business Risks

1. **Hardcoded case owner** — `Analytics_sp_AML_Case_Module` line 512 hardcodes `Nathan.Sandiford` as AML case owner. If this individual is no longer in that role, new AML cases are assigned to the wrong person and may go unreviewed.
2. **Batch-only OFAC screening** — Daily NESS extract means intraday OFAC violations are not detected until next day.
3. **Ad-hoc tables committed by named individuals** — The `_archived` folder contains tables committed by individual employees. These may contain sensitive cardholder data that is not subject to standard data governance controls.
4. **AML threshold at $0** — `Analytics_sp_AML_Case_Module` line 7 sets `@Threshold int = 0`, meaning all accounts with any positive balance in Payroll/Maritime/Sales Incentive verticals are candidates for AML cases. This appears to be either a development artifact or an extremely broad monitoring threshold.
