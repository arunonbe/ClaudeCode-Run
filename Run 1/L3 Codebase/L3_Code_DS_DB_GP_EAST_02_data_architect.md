# DS_DB_GP_EAST — Data Architect View

## 1. Repository Status

**This repository contains no SQL source objects.** The repository is a near-empty skeleton with only a `README.md` file. No tables, views, stored procedures, functions, triggers, indexes, or SSDT project files are present.

---

## 2. Intended Scope (Inferred from README)

The README states the repository "Houses a Collection of Modified Stored Procedures, Views (ECAN, ECNT, etc.)." Based on this and the GP multi-company architecture:

### 2.1 Expected Database Objects (Not Yet Present)

If the repository were populated consistent with its sibling repos (DS_DB_GP_ecan, DS_DB_GP_ecnt), it would be expected to contain:

**Views (analogous to ECAN/ECNT view sets):**
- `BankerAllSOView` — Union of open and history Sales Order documents for Banker SVC
- `BankerSOView` — Open Sales Orders view
- `BankerHistSOView` — Historical Sales Orders view
- `BankerProgram` — Program master view mapping GP customers to prepaid programs
- `BankerPayment` / `BankerCashReceipts` / `BankerACH` — Payment and receipt views
- `eCountBankTransactions` / `eCountBankHistTransactions` — GL-level bank transaction views
- `PROGRAMS` — Program/customer master view

**Stored Procedures (analogous to ECAN/ECNT procedure sets):**
- `banker_get_program_info` — Returns program credit limit, currency, and balance
- `banker_get_documents` — Returns Sales Order documents by program and job
- `banker_get_payments` — Returns payment documents
- `banker_get_free_funds` / `banker_get_unsettled_funds` — Balance computation procedures
- `banker_get_gp_job_info`, `banker_get_gp_payment_info`, `banker_get_gp_program_info` — GP-specific info retrieval
- `client_refund_*` procedures — Client refund processing

**Functions (analogous to ECAN/ECNT):**
- `banker_get_required_deposit_date` — Business-day deposit date calculation
- `banker_get_sum_saved_credit_memos`, `banker_get_sum_saved_invoices_per_program_promo` — Financial sum functions
- `DYN_FUNC_*` series (~150 functions) — GP enumeration/code translation functions
- `FA_FUNC_*` series — Fixed assets code functions
- `FS_FUNC_*` series — Field service code functions

---

## 3. Sensitive Data Assessment (Projected)

If populated per the ECAN/ECNT pattern, this database would handle:

| Data Category | Classification | Notes |
|---------------|---------------|-------|
| Program financial balances (GP sales documents) | Financial — not PCI CDE | Invoice amounts, credit limits, account balances for prepaid programs |
| Payment/receipt amounts | Financial — not PCI CDE | ACH, check, and cash receipt totals |
| GL journal entries | Financial | General ledger debits and credits |
| Vendor/customer master data | Quasi-PII | Company names, addresses, tax IDs |
| Employee data (if UPR/payroll views included) | PII / NPI | Would be GLBA-scoped |

**PCI DSS CDE Assessment**: GP databases do not store PANs or other SAD. They are **not in the CDE** but are **connected financial systems** that provide funding context for card programs. PCI DSS Requirement 6 (secure system maintenance) and Requirement 12 (information security policy) apply.

---

## 4. Data Retention

Cannot be assessed — no objects present.

---

## 5. Cross-Database Dependencies (Projected)

If populated, this database would likely reference:
- The same base GP tables as ECAN/ECNT (`SOP10100`, `SOP30200`, `GL20000`, `GL00100`, `RM00101`, `RM00103`, `PM*` etc.) within the EAST company GP database.
- `DYNAMICS` system database for company registration lookup.
- Potentially cross-reference ECAN or ECNT for shared program data.

---

## 6. Recommendation

**Gap**: The production database server almost certainly contains stored procedures, views, or schema modifications for the EAST region that are not represented in source control. This constitutes a **schema drift** risk — the database cannot be reproducibly deployed from source code.

**Action**: Use SSDT Schema Compare against the production EAST company database to identify all custom objects and commit them to this repository with appropriate documentation.
