# DS_DB_GP_ecan — Solution Architect View

## 1. Critical Security Findings

### 1.1 CRITICAL — Plaintext SQL Authentication Passwords in Security Scripts

**Files**: `Security/crystal.sql`, `Security/report.sql`, `Security/report_full.sql` (and potentially others among the ~120 individual login scripts)

- `Security/crystal.sql` — `CREATE LOGIN [crystal] WITH PASSWORD = N'[REDACTED — rotate immediately]'`
- `Security/report.sql` (line 1 pattern) — similar plaintext password

These passwords are unique per-database (different from DYNAMICS and ECNT values observed), but they are still **committed as plaintext to Git**. The `crystal` account is typically used for Crystal Reports connections and has broad read access to all GP financial tables — including program balances, invoice amounts, payment history, and journal entries for Canadian operations.

**Impact**: Anyone with Git read access can authenticate to the production ECAN database as `crystal` or `report` and read all Canadian program financial data. This is a PCI DSS Requirement 8.6.1 violation and a SOX ITGC failure.

**Immediate actions**:
1. Rotate all SQL Authentication passwords in ECAN immediately.
2. Remove password literals from all `Security/*.sql` files — replace with `MUST_CHANGE` syntax or migrate to Windows Authentication.
3. Audit access logs for `crystal`, `report`, and `report_full` logins since first commit date.

### 1.2 HIGH — `amAutoGrant` Dynamic SQL (Replicated from DYNAMICS)

**File**: `dbo/Stored Procedures/Procs1/amAutoGrant.sql`

Same pattern as DYNAMICS: `EXEC ('grant SELECT,INSERT,DELETE,UPDATE on ' + rtrim(@tablename) + ' to DYNGRP')`. Table name parameter is concatenated without `QUOTENAME()` or input validation.

### 1.3 HIGH — `banker_get_documents` XML Parameter Not Validated Against Schema

**File**: `dbo/Stored Procedures/Procs1/banker_get_documents.sql`

```sql
CREATE PROCEDURE banker_get_documents
(
    @program_id  VARCHAR(15),
    @source_id   CHAR(21),
    @doctype_ids XML
)
```

The `@doctype_ids` XML parameter is used with `.nodes()` XQuery but is not validated against an XML schema (`WITH XMLSCHEMA`). A malformed or adversarial XML input could cause unexpected query behaviour. While the XQuery pattern used (`/doctypes/id`) is not directly injectable in the same way as string concatenation, the lack of schema enforcement means malformed inputs are accepted silently.

**Remediation**: Define an XML Schema Collection and bind the `@doctype_ids` parameter to it.

### 1.4 MEDIUM — `Permissions.sql` is 118 KB — Unmaintainable Grant File

A single 118 KB permissions file containing potentially hundreds of individual GRANT statements cannot be effectively reviewed, audited, or change-managed. Any single-character change touches the entire file, making diff-based reviews meaningless.

**Remediation**: Split `Permissions.sql` by role or principal into separate files matching the `Security/` folder pattern.

### 1.5 MEDIUM — Broad `DYNGRP` Membership

The `DYNGRP` role has `SELECT, INSERT, DELETE, UPDATE` on all GP tables (enforced via `amAutoGrant`). The `DYNGRP.sql` role membership file shows ~90 named user accounts in DYNGRP. Many of these are individual users who should have read-only access (report consumers) but effectively have full write access to all ECAN tables via DYNGRP.

---

## 2. Technical Debt Register

| ID | Debt Item | Location | Severity |
|----|-----------|----------|----------|
| TD-1 | Plaintext SQL Auth passwords | `Security/crystal.sql`, `report.sql`, `report_full.sql` | Critical |
| TD-2 | `amAutoGrant` dynamic SQL | `Procs1/amAutoGrant.sql` | High |
| TD-3 | Unvalidated XML parameter in `banker_get_documents` | `Procs1/banker_get_documents.sql` | High |
| TD-4 | 118 KB monolithic `Permissions.sql` | `Security/Permissions.sql` | Medium |
| TD-5 | Broad `DYNGRP` full-write access for read-only users | `Security/DYNGRP.sql`, `Security/RoleMemberships.sql` | Medium |
| TD-6 | `Sql100` schema provider — stale GP version target | `ecan.sqlproj` | Medium |
| TD-7 | No CI/CD pipeline | Repository root | High |
| TD-8 | 18 Procs subfolders — fragmented SP organisation | `dbo/Stored Procedures/Procs1–Procs18` | Low |
| TD-9 | Individual named user SQL Auth logins (not AD-managed) | `Security/*.sql` | Medium |
| TD-10 | No custom index definitions for Banker SVC views | No index files | Low |

---

## 3. All Custom Object Names with Purpose

### Custom Functions
- `banker_get_required_deposit_date` — Business-day deposit date calculation.
- `banker_get_sum_saved_credit_memos` — Sum of non-voided credit memos for a program.
- `banker_get_sum_saved_invoices_per_program_promo` — Sum of non-voided invoices for a program/promo.
- `banker_get_sum_saved_usable_payments` — Sum of usable (settled) payments.
- `banker_get_x_days_payments` — Sum of payments within N-day window.
- `client_refund_parseStringToTable` — Parse delimited refund string to table.

### Custom Views
- `BankerAllSOView` — All (open + history) Sales Orders with job ID and tracking file.
- `BankerSOView` — Open Sales Orders.
- `BankerHistSOView` — Historical Sales Orders.
- `BankerMultSOSView` — Multi-promo Sales Orders.
- `BankerSOLineView` — Sales Order line items.
- `BankerProgram` — Program credit limit, balance, currency view.
- `BankerPayment` — Payment receipts view.
- `BankerCashReceipts` — Cash receipts view.
- `BankerACH` — ACH payments view.
- `banker_default_promo_exception` — Promo exception rules.
- `eCountBankTransactions` — Posted GL bank transactions.
- `eCountBankHistTransactions` — Historical GL bank transactions.
- `eCountBankTrxUnPosted` — Unposted GL bank transactions.
- `eCountBatchGLTrx` — Batch GL transactions.
- `eCountCOA` — Chart of accounts.
- `PROGRAMS` — Program master with GFCID, legal name, manager.
- `rsm_citidirect_ACH_DTS` — Citi Direct ACH transactions.
- `rsm_citidirect_drawdown_DTS` — Citi Direct drawdown transactions.
- `RSM_UNPOSTED_SALES_DOCS` — Unposted sales documents (RSM).
- `rsmCitiDirectTrx` — Citi Direct transaction detail.
- `rsmCDTRXView` — Citi Direct view.
- `CitiPrepaidAPAgeTBbyAccNum` — AP ageing by account number.

### Custom Stored Procedures
- `banker_get_program_info` — Program balance and credit limit lookup.
- `banker_get_documents` — Document lookup by program, source, and type.
- `banker_get_payments` — Payment lookup.
- `banker_get_free_funds` — Available fund calculation.
- `banker_get_unsettled_funds` — Unsettled fund calculation.
- `banker_get_all_unsettled_funds` — All-program unsettled summary.
- `banker_get_321_days_payments` — 321-day payment window query.
- `banker_get_ach_delay` — ACH delay configuration lookup.
- `banker_get_active_promotions` — Active promotion lookup.
- `banker_get_multiple_sos` — Multi-SO lookup.
- `banker_insert_multiple_so` — Create Sales Orders in GP.
- `banker_delete_multiple_sos` — Delete Sales Orders in GP.
- `banker_get_gp_job_info` — Job-level GP data retrieval.
- `banker_get_gp_payment_info` — Payment-level GP data retrieval.
- `banker_get_gp_program_info` — Program-level GP data retrieval.
- `banker_get_gp_promoexception_info` — Promo exception data retrieval.
- `banker_get_jobsvc_job_info` — Job service data retrieval.

---

## 4. Remediation Priority

| Priority | Item | Action |
|----------|------|--------|
| P0 | TD-1 — Plaintext passwords | Rotate all SQL Auth passwords; remove from repo; enforce Windows Auth |
| P0 | TD-2 — `amAutoGrant` injection | Wrap with `QUOTENAME()` + `sys.objects` validation |
| P1 | TD-3 — XML parameter not validated | Add XML Schema Collection for `@doctype_ids` |
| P1 | TD-7 — No CI/CD | Add automated DACPAC build + deploy pipeline |
| P2 | TD-4 — Monolithic Permissions.sql | Split into per-role/per-principal files |
| P2 | TD-5 — Broad DYNGRP write access | Create read-only role for report users; remove them from DYNGRP |
| P2 | TD-9 — Individual SQL Auth logins | Migrate to AD group-based Windows Authentication |
| P3 | TD-6 — Stale schema provider | Update to Sql130/Sql150 matching production SQL Server version |
| P3 | TD-10 — Missing indexes | Add covering indexes for `BankerAllSOView` join columns if query performance is a concern |
