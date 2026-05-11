# DS_DB_cf_report — Enterprise Architect View

## 1. Platform Generation Assessment

**Generation: Gen-1.5 — Hybrid Gen-1 (eCount/CitiPrepaid) and Gen-2 (Wirecard/Northlane) reporting layer**

Evidence:
- **No SSDT project**: Unlike CCP (SSDT + DACPAC) and cbaseapp (SSDT + DACPAC), cf_report uses plain SQL scripts. This is consistent with a database that was organically grown over many years rather than formally engineered — typical of Gen-1 reporting databases that pre-date structured SQL project tooling.
- **eCount-era function naming**: The `app_func_*`, `util_func_*`, `rpt_func_*` naming conventions are eCount Gen-1 conventions. Functions such as `app_func_dda_get_balance`, `app_func_get_member_by_dda`, `fn_puid_encode`/`fn_puid_decode` are unambiguously eCount/CitiPrepaid era.
- **Citi references**: `Quickscreen_AML_Corporate_Unusual_Activity` queries `ecountcore_ss.dbo.citi_process_nacha_status` and `ecountcore_process_ss.dbo.citi_process_nacha_file`, referencing Citi-era data. The comment block on `app_BI_Transaction_File` mentions "non-citi account under Citi programs" (line 21), placing the initial development in the Citi integration period.
- **Wirecard/NAM BIN era additions**: The `BINBANK` schema was added in the Wirecard/NAM era. The procedures that generate Bank Integration files for `NAM` programs, and the `NA_ATLYS` view schema (Atlys is a Wirecard-era product), are Gen-2 additions layered on top of the Gen-1 base.
- **`CREATE OR ALTER`**: The use of `CREATE OR ALTER PROCEDURE` (SQL Server 2016+ syntax) in BINBANK procedures confirms recent additions use newer SQL Server syntax, while the dbo schema procedures retain Gen-1 era style.
- **DeltaSql change management**: The structured DeltaSql pattern was introduced in the Wirecard/Onbe era as a discipline. The April 2026 delta scripts confirm ongoing maintenance.
- **Citi PUID encode/decode**: `fn_puid_encode` and `fn_puid_decode` encode the Citi Physical Unique Identifier — an artifact of the CitiPrepaid Gen-1 card management system that is still referenced in reporting procedures.

---

## 2. Role in the Onbe Payments Architecture

cf_report is the **central reporting and regulatory output hub** for Onbe's Gen-1/Gen-2 cardholder platform. It occupies the position between the raw operational databases and external recipients (bank partners, regulators, clients).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          ONBE PAYMENTS PLATFORM                              │
│                                                                              │
│  ┌──────────────┐    Linked Server    ┌────────────────────────────────┐     │
│  │  ecountcore  │ ──────────────────► │  cf_report (this DB)           │     │
│  │  (Gen-1 core)│  fdr_dda_account_  │  Central reporting + regulatory │     │
│  │              │  journal, etc.      │  output hub                     │     │
│  └──────────────┘                    └─────┬─────────┬────────┬────────┘     │
│                                           │         │        │               │
│  ┌──────────────┐    Linked Server         │         │        │               │
│  │  ecountcore  │ ──────────────────►      │         │        │               │
│  │  _process    │  citi_process_nacha       │         │        │               │
│  └──────────────┘                         │         │        │               │
│                                           ▼         ▼        ▼               │
│  ┌──────────┐   Linked Server   ┌──────────┐ ┌────────┐ ┌──────────┐        │
│  │   CCP    │ ─────────────────►│Bank FI   │ │NAUPA   │ │Mantas    │        │
│  │ (Gen-2)  │  NAM_BIN_*        │Integration│ │Escheate│ │(Oracle   │        │
│  └──────────┘                   │Files     │ │ment    │ │FCRM/AML) │        │
│                                 └──────────┘ └────────┘ └──────────┘        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Upstream Data Sources
- **ecountcore** (via `ECountcore_ss` linked server): Primary source of transaction journal (`fdr_dda_account_journal`), card accounts (`fdr_card_account`), program/bank mappings, NACHA status tables, claimable payment data
- **ecountcore_process** (via `Ecountcore_Process_SS` linked server): Process-level data including debit ACH file records, ATM/ACH STAR file records
- **CCP** (via cf_report BINBANK procedures that reference `NAM_BIN_*` tables): BIN-level account, transaction, balance, and card status data from Fiserv batch files

### Downstream Recipients
- **Bank Financial Institution (FI)**: `BINBANK.app_BI_Transaction_File`, `app_BI_Account_Balance_File`, `app_BI_Card_Status_File`, `app_BI_TransactionInternational_File` generate daily Bank Integration files
- **ACH Network (via NACHA)**: `usp_nacha_queue_file` and related procedures generate NACHA ACH files for fund delivery to prepaid cardholders
- **Oracle Financial Services FCRM / Mantas**: The `mantas` schema populates the Mantas AML transaction monitoring system with account holder and transaction data
- **State Unclaimed Property Offices**: `escheatment_naupa_*` procedures generate NAUPA-format unclaimed property filings for each of the 50 US states
- **FinCEN (via BSA)**: `Fincen_process_export` and AML Quickscreen procedures produce outputs supporting Suspicious Activity Report (SAR) filings
- **Clients**: Client-facing reports consumed via SQL queries or file generation from cf_report

---

## 3. Integration Patterns

| Integration | Mechanism | Direction | Notes |
|---|---|---|---|
| ecountcore | Linked server (`ECountcore_ss`) | cf_report reads ecountcore | Hard-coded server name; tightly coupled |
| ecountcore_process | Linked server (`Ecountcore_Process_SS`) | cf_report reads ecountcore_process | Hard-coded server name |
| CCP | Linked server or direct DB query | cf_report reads CCP NAM_ tables | cf_report generates BI files from CCP data |
| Mantas/Oracle FCRM | Table population via `mantas.*` SPs | cf_report writes to mantas schema; Mantas reads | Batch data feed |
| NACHA ACH network | File generation via `usp_nacha_print_section_*` | cf_report generates output | File transport not in scope of this repo |
| FI Bank Integration | File generation via `app_BI_*` procedures | cf_report generates output | File transport not in scope |
| NAUPA escheatment | `escheatment_naupa_*` procedures | cf_report generates output | Annual filing |
| FinCEN/BSA | `Fincen_process_*` tables + Quickscreen output | cf_report generates output | Law enforcement regulatory |

---

## 4. Cross-Database Dependency Map

cf_report is the most highly coupled database in the analysis batch. It depends on at minimum 4 other databases:

| Dependency | Linked Server | Tables Referenced |
|---|---|---|
| ecountcore | `ECountcore_ss` | `fdr_dda_account_journal`, `fdr_card_account`, `fdr_dda_account`, `core_profile_programs_bank_effective_vw`, `claimable_payment_transaction`, `citi_process_nacha_status`, `app_func_get_card_number_by_id_masked` |
| ecountcore_process | `Ecountcore_Process_SS` | `fdr_process_debitach_file`, `fdr_process_atmach_star_file`, `citi_process_nacha_file` |
| CCP | (direct or linked) | `NAM_BIN_ACCOUNTS`, `NAM_BIN_TRANSACTION`, `NAM_BIN_BALANCES`, `NAM_BIN_CARD_STATUS` |
| tbl_Country_Codes | (referenced in `app_BI_Transaction_File` line 133) | Used for ISO country code lookup; likely a cf_report local table |

Any schema change in ecountcore, ecountcore_process, or CCP that alters table structures or removes columns **will silently break cf_report stored procedures** at runtime — there is no compile-time detection for linked-server references.

---

## 5. Migration Complexity Assessment

### Complexity Rating: VERY HIGH

Factors:
1. **Multi-schema layered design**: 8+ schemas with cross-schema dependencies make atomic migration difficult. Objects in `dbo` call `BINBANK` functions; `mantas` views join `dbo` tables.
2. **Linked server coupling**: 4+ upstream databases accessed via linked server. Any migration must preserve or replace these integration points.
3. **100+ stored procedures**: Many with complex business logic (escheatment state rules, NACHA file assembly, AML screening). Rewriting or migrating these procedures requires domain expertise in each area.
4. **Multiple obsolete versions**: Triplicate procedure versions (`_old`, current, `_New`) make it unclear which version is authoritative. Migration must audit all versions before decommissioning.
5. **Personal workspace schemas**: The `CB_OFFICE_*` schemas may contain data and logic used informally by operations teams. An inventory and disposition decision is required for each.
6. **Regulatory output**: cf_report produces NACHA ACH files, NAUPA escheatment filings, and FinCEN BSA outputs. Any migration of these procedures requires compliance validation before go-live.
7. **DeltaSql change scripts without tracking**: No execution tracking table — it is not possible to determine definitively which delta scripts have been applied to production without external records.

---

## 6. Strategic Observations

1. **Central point of failure for compliance outputs**: cf_report is the single database responsible for NACHA ACH, NAUPA escheatment, and Mantas AML data feeds. A database outage or failed deployment affects all three regulatory output streams simultaneously. A Gen-3 architecture would decompose these into separate purpose-built microservices with independent deployment cycles.

2. **Reporting database acting as application database**: cf_report contains business-logic functions (`app_func_dda_get_balance`, `app_func_card_expiration_is_reissue`) that are queried by upstream application services. This violates the separation of concerns principle and makes cf_report a de facto application service rather than a pure reporting store.

3. **Data duplication with source systems**: cf_report's `BINBANK.Account` table duplicates cardholder PII that already exists in ecountcore (`fdr_dda_account`) and CCP (`NAM_BIN_ACCOUNTS`). This creates three sources of truth for cardholder address and status, with no synchronization mechanism visible in the repository.

4. **Personal workspace governance gap**: Individual analyst workspaces in `CB_OFFICE_*` schemas represent an organizational behavior pattern — analysts use the production reporting database as a personal analytics environment. This practice needs formal governance: personal work should be done in a dedicated analyst sandbox, not the production reporting database.

5. **Galileo references**: Views named `galileo_dda_account`, `galileo_user_enrollment`, `galileo_user_registration`, `galileo_pending_ach` indicate that a Galileo Financial Technologies integration was added to cf_report at some point. Galileo is a competing card-processing platform. These views may reflect data from a program portfolio that uses Galileo's platform alongside eCount — a multi-processor architecture that adds further complexity to the data model.
