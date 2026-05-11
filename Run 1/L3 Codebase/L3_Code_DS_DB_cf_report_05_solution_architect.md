# Solution Architect Report — DS_DB_cf_report

## 1. Technical Architecture

`DS_DB_cf_report` is **not an SSDT project** — there is no `.sqlproj` file. The repository stores SQL scripts in a directory hierarchy organised by schema and object type under `cf-report/`. Change management is handled through `DeltaSql/` dated delta scripts. The database is not deployable from a DACPAC; all deployments are script-based.

**Project characteristics:**
- No project file (no `.sqlproj`, no `.sln`)
- No build artefact — scripts are applied directly to the target instance
- Change management: `DeltaSql/` folder with forward and rollback scripts per change set
- Most recently updated: April 2026 (`STBR-5652` delta set, `DeltaSql/2026-04-12/`)
- SQL Server version: inferred SQL Server 2016+ from `CREATE OR ALTER PROCEDURE` syntax in BINBANK procedures (not available before SQL Server 2016 SP1)
- Compatibility level: not declared in repository — must be verified on production instance

**Schema composition (8+ schemas):**

| Schema | Object Count | Purpose |
|---|---|---|
| `dbo` | 100+ procedures, 80+ tables, 80+ functions, 70+ views | Core cardholder reporting, escheatment, AML, NACHA |
| `BINBANK` | 19 procedures, 25+ tables | Bank Integration file generation; NACHA ACH pipeline |
| `mantas` | 10 procedures, 13+ tables | Oracle Financial Services Mantas AML data feed |
| `ECNT_AB` | 1 procedure, 2 tables | Plastic renewal processing |
| `ISA` | 1 table | ISA event type reference |
| `NAOT` | 7 tables | OTC procurement tracking |
| `NA_ATLYS` | Views | Atlys-format BIN reporting views |
| `CB_OFFICE_*` (4 schemas) | Miscellaneous tables/functions | Individual analyst workspaces (production governance risk) |

---

## 2. API Surface

`cf_report` does not expose a REST or gRPC API. It is consumed by calling applications via SQL Server connections using stored procedure execution. Key API boundaries:

### 2.1 Bank Integration File Generation API (BINBANK schema)
- `BINBANK.app_BI_Transaction_File` — daily transaction file for bank FI
- `BINBANK.app_BI_Account_Balance_File` — daily account balance file
- `BINBANK.app_BI_Card_Status_File` — daily card status file
- `BINBANK.app_BI_TransactionInternational_File` — international transaction file
- `BINBANK.app_BI_Account_File` — account file

### 2.2 NACHA ACH Pipeline API (BINBANK schema)
- `BINBANK.usp_nacha_queue_file` — queue a NACHA file for generation
- `BINBANK.usp_nacha_print_section_*` (7 procedures) — generate individual NACHA file sections (file header, batch header, entry detail, entry footer addenda, batch trailer, file trailer, file trailer padding)
- `BINBANK.usp_nacha_source_load` / `usp_nacha_source_load_batch` / `usp_nacha_source_load_entry_detail` — NACHA source data loading pipeline

### 2.3 AML / Mantas Feed API (mantas schema)
- `mantas.sp_AML_Front_Office_Transaction` — AML front office transaction population
- `mantas.sp_AML_Front_Office_Transaction_Party` — AML party data population
- `mantas.uspAccountTablePopulate` / `uspInitialAccountTablePopulate` — Mantas account feed
- `mantas.uspGetE2EData` / `uspGetE2EHeaderFooter` — Mantas end-to-end file generation

### 2.4 Escheatment API (dbo schema)
- `dbo.app_escheatment_process_prepare` / `app_escheatment_account_commit` / `app_escheatment_process_commit` — escheatment lifecycle
- `dbo.escheatment_naupa_get_property` / `escheatment_naupa_get_summary` — NAUPA unclaimed property file generation
- `dbo.escheatment_report_by_state` / `escheatment_report_prepare` — state-level reporting

### 2.5 AML Quickscreen API (dbo schema)
- `dbo.Quickscreen_AML_Corporate_Unusual_Activity` — AML transaction screening
- `dbo.Quickscreen_AML_Corporate_Unusual_Activity_Multiple_Deposits` — multiple deposit detection
- `dbo.DailyRiskReports` — daily BSA/AML risk report generation

### 2.6 Key Functions Used as Application Services (dbo schema)
These functions are called by upstream application services — `cf_report` acts as an application service layer, not just a reporting database:
- `dbo.app_func_dda_get_balance(@dda_number)` — balance lookup
- `dbo.app_func_dda_get_open_to_buy(@dda_number)` — available balance
- `dbo.app_func_card_expiration_is_reissue(@card_id)` — reissue determination
- `dbo.app_func_escheatment_is_account_escheatable(@dda_number, ...)` — escheateability

---

## 3. Security Posture

| Control | Status | Finding |
|---|---|---|
| No SSDT / no DACPAC | Architecture | No compile-time validation of cross-database references; silent failures when upstream schemas change |
| Linked server references | Active | `ECountcore_ss` and `Ecountcore_Process_SS` linked servers; tightly coupled to ecountcore and ecountcore_process |
| Column-level encryption | None observed | Cardholder name, DDA numbers, bank account numbers stored without column encryption |
| TDE | Not verifiable from repo | Cannot confirm from SQL scripts alone; must verify on production instance |
| `BINBANK.nacha_file_entry_detail.dfi_account_number` | Plain text | Bank account numbers in NACHA entry detail stored as VARCHAR(17) without encryption |
| Analyst workspace schemas | `CB_OFFICE_*` schemas in production | Four individual analyst personal schemas in the production reporting database; violates least-privilege and data governance |
| `CREATE OR ALTER` pattern | BINBANK procedures | Idempotent deployment — same script can be re-run; acceptable for delta-script deployment model |
| DeltaSql rollback scripts | Present for all STBR-4812 and STBR-5652 changes | Mature rollback capability for recent changes |
| FortiDB DAM | Not visible in scripts | No `FortiDBRptRole` in cf_report scripts; security monitoring status must be independently confirmed |
| FinCEN data in plain tables | `dbo.Fincen_process_export` / `dbo.Fincen_process_import` | FinCEN BSA data stored in plain tables; regulatory sensitivity requires access controls and encryption |

---

## 4. Technical Debt

| Item | File/Location | Impact |
|---|---|---|
| Not an SSDT project | Architecture | No compile-time schema validation; no DACPAC deployment; no automated drift detection |
| Linked server tight coupling | `app_BI_Transaction_File.sql:107-134`, `Quickscreen_AML_Corporate_Unusual_Activity.sql:43-60` | Schema changes in ecountcore/ecountcore_process silently break cf_report at runtime |
| Object version proliferation | `dbo` schema | Triplicate versions of procedures (`_old`, current, `_New`) for card expiration functions and others; multiple `_debug`, `_jwu` personal variants |
| Analyst workspace schemas | `CB_OFFICE_BLogano`, `CB_OFFICE_HNaylor`, `CB_OFFICE_JWu`, `CB_OFFICE_SQuarshie` | Personal data and functions in production database; unmanaged lifecycle |
| No execution tracking for DeltaSql | `DeltaSql/` folder | No table tracks which delta scripts have been applied to production; deployment state must be inferred from manual records |
| `BINBANK.nacha_file_entry_detail.dfi_account_number` unencrypted | `BINBANK` schema DDL | Bank account numbers in NACHA entries stored as plain VARCHAR; PCI/NACHA security gap |
| `dbo.Fincen_process_export` plain data | `dbo` schema | FinCEN BSA export data in plain table — law enforcement sensitivity |
| Galileo views | `galileo_*` views in `dbo` | Galileo Financial Technologies integration views present; status (active/retired) unknown |
| Three-generation card expiration functions | `app_func_card_expiration_is_reissue`, `_New`, `_old` | Three versions deployed simultaneously; caller resolution unclear |
| `CB_OFFICE_JWu.app_func_get_access_level_by_dda2` | `CB_OFFICE_JWu` schema | Personal copy of an access-level function in a personal production schema — could silently diverge from the authoritative version |
| Personal balance debug function variant | `rpt_func_card_expiration_get_count_jwu` | Named after developer (JWu); a personal variant deployed to production |
| DeltaSql change sets show ongoing activity in 2026 | `DeltaSql/2026-03-*/` and `DeltaSql/2026-04-*/` | This database is actively maintained (as of April 2026 per STBR-5652 delta set); it is not dormant |

---

## 5. Gen-3 Migration Requirements

| Requirement | Description |
|---|---|
| Decompose into purpose-built microservices | cf_report's 8+ schemas should become separate services: ACH/NACHA Service, AML Data Feed Service, Escheatment Service, Bank Integration File Service |
| Replace linked server coupling | `ECountcore_ss` and `Ecountcore_Process_SS` linked server calls must be replaced with service APIs or message-based event consumption |
| Migrate NACHA pipeline | `BINBANK.usp_nacha_*` procedures + NACHA table schema must be migrated to a dedicated ACH processing service (e.g., Moov Finance, Dwolla, or custom) |
| Migrate Mantas AML feed | `mantas.*` schema must be replaced with a modern API-based feed to the AML platform (Oracle FCRM or replacement) |
| Migrate escheatment processing | `app_escheatment_*` procedures and NAUPA output generation must move to a dedicated Unclaimed Property Service with state-level rule management |
| Resolve all procedure versions | All `_old` / `_New` / `_debug` / personal variants must be inventoried and retired before migration; authoritative version must be identified for each |
| Remove analyst workspace schemas | `CB_OFFICE_*` schemas must be inventoried, data extracted, and removed; analysts must be migrated to a dedicated analytics environment |
| Add DeltaSql execution tracking | Before any migration, add a script execution tracking table to definitively establish production schema state |
| Classify `dda_number` definitively | `BINBANK.Account.dda_number CHAR(16)` — determine if this is a token or a PAN for final PCI CDE scope assessment |
| Encrypt NACHA bank account numbers | `BINBANK.nacha_file_entry_detail.dfi_account_number` must be encrypted at column level or tokenised before any cloud migration |

---

## 6. Code-Level Risks

| Risk | File:Line | Notes |
|---|---|---|
| Silent linked server failure | `app_BI_Transaction_File.sql:107-134` | If `ECountcore_ss` linked server is unavailable, the Bank Integration file procedure fails with a runtime error — no fallback or alerting |
| AML Quickscreen queries Citi-era tables | `Quickscreen_AML_Corporate_Unusual_Activity.sql:43-60` — `ecountcore_ss.dbo.citi_process_nacha_status` | Queries a `citi_process_nacha_status` table; if this Citi-era table is retired, AML screening silently fails |
| `BINBANK.Account.secure_profile VARCHAR(250)` | `BINBANK` schema DDL | Column named `secure_profile` with no documented content definition — may contain encoded PII or authentication data; requires classification before migration |
| Multiple `app_func_card_expiration_is_reissue` versions | `dbo` schema | Three versions deployed simultaneously (`_old`, current, `_New`); callers may invoke different versions depending on how they reference the function |
| FinCEN data accessible to analyst schemas | `CB_OFFICE_*` schemas | Analysts with access to their personal schemas in the same database have read access to `dbo.Fincen_process_export` unless explicit DENY is applied — not visible in scripts |
| `DeltaSql` scripts without tracking table | `DeltaSql/` folder | No `DeltaSql_ExecutionLog` or similar table means production schema state is ambiguous; a migration assessment requires running all delta scripts against a known baseline and comparing |
| `app_BI_Transaction_File` joined on `tbl_Country_Codes` | `app_BI_Transaction_File.sql:133` | Country code reference join on a table whose schema is not in this repository; if `tbl_Country_Codes` is missing or has column changes, this procedure silently returns incorrect ISO country codes on transaction records |
