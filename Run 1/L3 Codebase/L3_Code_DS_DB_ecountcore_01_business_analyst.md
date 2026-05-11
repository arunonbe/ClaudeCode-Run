# DS_DB_ecountcore — Business Analyst View

## Repository Overview

`DS_DB_ecountcore` is an SSDT SQL Server Database Project (`.sqlproj`, targeting SQL Server 2016 `Sql130DatabaseSchemaProvider`) that defines the schema for the `Ecountcore` database — the **central core database of the Onbe prepaid card platform**. The Git repository is on the `development` branch. This is the most significant database in the Onbe estate: it is the authoritative system of record for cardholder accounts, card lifecycle, ACH transactions, member identity, fee processing, and compliance.

---

## Business Purpose

The `Ecountcore` database is the **operational heart of the Onbe prepaid disbursements platform**. It supports every major business function in the prepaid card lifecycle:

1. **Card Issuance and Management** — Creating prepaid cards (eCard, prepaid debit), managing card status (block codes, activation, expiration), tracking embossing and physical card fulfilment.
2. **Member Management** — Registering cardholders (members), storing identity data (name, address, email, DOB, SSN for KYC purposes), managing member relationships and companion cards.
3. **Account (DDA) Management** — Each cardholder has a DDA (Demand Deposit Account) that holds their prepaid balance. Balance management, open-to-buy calculation, and dormancy tracking are core functions.
4. **ACH Processing** — Initiating, scheduling, and settling ACH credits and debits. This includes direct deposit, recurring loads, one-time withdrawals, NACHA file generation and posting, return handling.
5. **Fee Processing** — Assessing dormancy fees, service fees, maintenance fees, first-transaction fees, and ATM fees according to configurable per-program fee schedules.
6. **Escheatment** — Identifying dormant accounts that must be remitted to state unclaimed property authorities, processing due diligence notifications, and committing escheatment transactions.
7. **Notifications** — Delivering balance alerts, transaction notifications, card expiry notices, and marketing messages via email and SMS.
8. **Reporting and Reconciliation** — Supporting ACH batch reconciliation, FDR (First Data Resources) settlement reporting, Mellon bank ACH origination reports, and daily deposit reporting.
9. **Fraud and Risk** — KYC velocity checks, OFAC sanction blocking (via `fdr_profile_block_code` with `BLOCK_SANCTION_DECLINED`, `BLOCK_SANCTION_REFERRED`, `BLOCK_SANCTION_INPROGRESS` entries), ACH velocity controls.
10. **Archival** — Archiving closed/dormant accounts and their transaction journals.
11. **Check Issuance** — Harland check order processing for DDA accounts with check-writing capabilities.
12. **International Transfers (IEFT/WorldLink)** — FX rate processing, international ACH/wire payments via Citi WorldLink.
13. **EMV** — EMV chip card management for qualifying programs.
14. **1099 Tax Reporting** — Extracting 1099 payment data for cardholders receiving qualifying disbursements.

---

## Business Processes Supported

### ACH Processing Lifecycle
The following stored procedures (among others) drive the full ACH lifecycle:
- `ach_event_create`, `ach_event_service`, `ach_event_jobend_service` — ACH event scheduling
- `ach_transaction_create` — initiating an ACH transaction
- `ach_cancel_transaction`, `ach_void` — cancellation
- `ach_unprocessed_transaction_extract` — NACHA file building
- `achdirect_process_settlement_post` — settlement posting
- `app_func_ach_velocity_check` — velocity fraud check

### Card and Account Lifecycle
- `fdr_card_account_create` — card creation (takes plaintext card number as parameter)
- `core_device_create`, `core_device_create_eCard` — device creation
- `core_member_create`, `core_member_create_basic`, `core_member_create_extended` — member onboarding
- `fdr_dda_account_create` — DDA account creation
- Card encryption: `app_func_get_card_number_by_id` — decrypts PAN using SQL Server column encryption (`DecryptByKeyAutoCert`)

### Fee Processing
- `app_process_assess_fee`, `app_process_fee_funding`
- `fdr_process_dormancy_fee`, `fdr_process_service_fee`
- `app_process_extended_dormancy`, `app_process_teen_service_fee`

### Escheatment
- `app_process_escheatment_commit`, `app_process_escheatment_enqueue`, `app_process_escheatment_due_diligence`
- Configured via `app_profile_escheatment_rules_configure`

### OFAC / Sanctions
- `fdr_profile_block_code` reference table contains `BLOCK_SANCTION_DECLINED`, `BLOCK_SANCTION_REFERRED`, `BLOCK_SANCTION_INPROGRESS` codes used when a cardholder or transaction matches an OFAC sanctions list entry.

---

## Regulatory Relevance

### PCI DSS — CRITICAL CDE DATABASE
This database is the **primary Cardholder Data Environment (CDE) database** in the Onbe estate. It contains:
- Encrypted PANs (Primary Account Numbers) in `core_card_master.card_encrypted` column
- Card hashes in `core_card_master.card_hash`
- CVV codes in `fdr_card_account_detail.cv_code` (the column is present as per `fdr_card_account_create` procedure which inserts `@cv_code`)
- Account numbers (DDA numbers) — 16-character strings serving as account identifiers

**Every system that connects to `Ecountcore` is in PCI DSS scope.**

### NACHA / Reg E
The ACH transaction journal (`ach_transaction_journal`) and associated processing procedures directly support NACHA-compliant ACH origination, settlement, and return processing. The `ach_profile_ach_delay_configure` procedure controls NACHA effective-date rules. Return reason codes are tracked in `ach_transaction_journal.return_reason_code`. Reg E dispute resolution timelines are supported by the ACH cancellation and void capabilities.

### OFAC / AML
The `fdr_profile_block_code` table with SANCTION block codes, and the KYC velocity check (`app_func_get_kyc_velocity_check`), demonstrate OFAC and AML controls at the database level. The `app_func_ach_velocity_check` function enforces velocity limits on ACH credits, relevant to BSA suspicious activity detection.

### Escheatment (State Unclaimed Property Laws)
Dedicated escheatment processing procedures (8+ stored procedures) and configuration tables implement state-specific unclaimed property rules. The function `app_func_escheatment_get_rule_id` and `app_func_escheatment_get_rule_set` show state-level rule configuration.

### 1099 Tax Reporting (IRS)
`app_process_1099_extract` and `app_func_get_1099_ecount_payment` support IRS Form 1099-MISC/1099-NEC reporting for cardholders receiving qualifying disbursements (threshold: typically $600/year). This is a tax compliance obligation for disbursement programs.

### GDPR / CCPA / PIPEDA
Member registration data includes PII (name, address, email, phone, DOB) that is subject to privacy regulations. The database supports Canadian programs (`app_func_ach_get_effective_date`, Canadian ACH functions, `rpt_ach_withdrawal_review_CANADA`) and potentially EU programs (EMEAP references in SSIS extracts), bringing GDPR and PIPEDA into scope.

---

## Key Data Domains

| Domain | Key Tables/Objects | Sensitivity |
|---|---|---|
| Cardholder Identity | `core_member`, `core_member_basic`, `core_member_extended`, `fdr_card_account_registration` | PII — PAN, Name, Address, DOB, SSN |
| Card / Device | `core_card_master`, `fdr_card_account`, `fdr_card_account_detail` | PCI — encrypted PAN, CVV |
| Account (DDA) | `fdr_dda_account`, `fdr_dda_account_journal`, `fdr_dda_account_journal_summary` | Financial — balance, transactions |
| ACH | `ach_transaction_journal`, `ach_event_schedule` | Financial — bank routing/account |
| Transactions | `core_transaction_journal`, `fdr_card_account_journal` | Financial |
| Fees | Various `app_profile_fee_*` tables | Commercial |
| Escheatment | `app_process_escheatment_queue`, `app_profile_escheatment_config` | Legal/regulatory |
| Programs | `app_profile_program_*` tables (many) | Configuration |
| Block Codes / Sanctions | `fdr_profile_block_code` | OFAC compliance |

---

## Summary

EcountCore is a mature, feature-rich prepaid card platform database that has evolved over approximately 20 years (evidence: date references from 2003 onward in rollback scripts). It supports multiple card rails (FDR/First Data, Fiserv, Citi NAOT), multiple currencies, international programmes, and a full suite of financial services. It is the highest-risk database in the Onbe estate from a PCI DSS, NACHA, OFAC, and privacy regulation standpoint.
