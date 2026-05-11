# Solution Architect Analysis — DS_DB_ATL_atlys_fc_nus (atlys_fc_nus)

## Technical Debt Register

`atlys_fc_nus` inherits all technical debt items from `atlys_fc_nca` (see that document). The following are additional or amplified US-specific concerns:

### TD-1: Server-Name Conditional in sys_calc_dormancy (US-Amplified Risk)
**File:** `dbo/Stored Procedures/sys_calc_dormancy.sql` line 43  
**Same as NCA.** In the US context, the risk is amplified because US Reg E requires dormancy fee recognition to align precisely with disclosed fee schedules. If the server-name check fails (returning false on a renamed server), US dormancy fee calculations will use forecast-only data without actual historical fee data from the SSAS cube. This could cause:
1. Incorrect amortisation entries posted to the US GL.
2. Variance between modelled and actual dormancy revenue in US financial statements.
3. Potential Reg E disclosure misalignment if product terms are recalibrated based on incorrect fee actuals.  
**Priority:** P1

### TD-2: No Reg E Validation on dorm_wait
**File:** `dbo/Tables/cursforecast.sql`  
**Description:** No CHECK constraint enforces `dorm_wait >= 12` for US programs. Any analyst can configure a US program with a dormancy wait period shorter than 12 months, which would project dormancy fee income starting before the Reg E permitted period.  
**Impact:** High — regulatory risk. Overstatement of fee income in financial forecasts; potential Reg E violation.  
**Remediation:** Add application-layer validation or a database-level check (potentially via a trigger on `cursforecast`) that enforces `dorm_wait >= 12` when `country_code = 'US'`.  
**Priority:** P1

### TD-3: No Validation on unclaimed_months vs. State Law
**File:** `dbo/Tables/cursforecast.sql`  
**Description:** `unclaimed_months` is unconstrained. US state unclaimed property laws vary: some states require escheatment after 1 year of inactivity, others after 5 years. There is no lookup table mapping state to required escheatment period, and no validation prevents a program from being configured with an `unclaimed_months` value that violates the applicable state law.  
**Impact:** Medium-High — understatement of escheatment liability.  
**Remediation:** Create a state-escheatment reference table (state code → required escheatment months) and add a validation trigger or application check against it.  
**Priority:** P2

### TD-4: Code Duplication with atlys_fc_nca
Same as NCA TD-5. All 80+ stored procedures duplicated.  
**Priority:** P2

### TD-5: FLOAT for Financial Amounts / BULK_LOGGED / No TDE
All inherited from NCA. See NCA document.  
**Priority:** P1/P2 per individual item.

---

## Security Vulnerabilities

### SV-1: db_owner for 'raf' Login (Expected)
Based on the identical security file set to NCA (`RoleMemberships.sql`), `raf` is expected to be `db_owner` in `atlys_fc_nus` as well. **Critical — PCI DSS Req 7 violation.**  
**Priority:** P1

### SV-2: db_datawriter for NAM\UAT (Expected)
Same as NCA. UAT environment account with production write access.  
**Priority:** P1

### SV-3: US Financial Data Unencrypted
The fee forecast, commission, and BIN data for US programs are stored without TDE encryption. In a GLBA context, this is a safeguards rule finding. US regulatory data (including Reg E-related dormancy parameters, escheatment assumptions) should be encrypted at rest.  
**Priority:** P1

### SV-4: No Audit Log for Reg E Parameter Changes
**Description:** Changes to `dorm_wait` or `dorm_wait`-related parameters in `cursforecast` that affect Reg E compliance are only logged in `tblForecastChangeLog` when the `exclude` flag changes (via `trg_exclude` trigger). Direct updates to `dorm_wait`, `unclaimed_months`, or `claim_rate` are not individually logged with a before/after comparison.  
**Impact:** Medium — inability to audit Reg E parameter changes for compliance purposes.  
**Remediation:** Extend `trg_exclude` or add a separate trigger to log changes to Reg E-relevant columns (`dorm_wait`, `unclaimed_months`, `unclaimed_keep`, `claim_rate`, `country_code`) with before/after values and the identity of the modifying user.  
**Priority:** P1

---

## All Object Names with Purpose

**Identical to `atlys_fc_nca`.** See that document for the complete object list. All tables, views, functions, stored procedures, and triggers are identical in name and structure. The only operational difference is the US program data they contain.

---

## US-Specific Remediation Items (Beyond NCA)

| Priority | Item |
|---|---|
| P1 | Add dorm_wait >= 12 validation for US programs (Reg E compliance) |
| P1 | Add audit logging for Reg E parameter changes |
| P1 | Enable TDE for US financial data (GLBA safeguards) |
| P2 | Create state escheatment reference table and validation |
| P2 | Implement coordinated NCA/NUS deployment pipeline to prevent drift |

---

## Remediation Priority Summary (Consolidated, Including NCA Inheritance)

| Priority | Issue |
|---|---|
| P1 — Immediate | Server-name logic in dormancy (TD-1, amplified by Reg E) |
| P1 — Immediate | No dorm_wait Reg E validation (TD-2) |
| P1 — Immediate | No audit log for Reg E parameter changes (SV-4) |
| P1 — Immediate | db_owner for 'raf' (SV-1) |
| P1 — Immediate | UAT account db_datawriter in prod (SV-2) |
| P1 — Immediate | No TDE — US GLBA obligation (SV-3) |
| P1 — Immediate | No TRY/CATCH in calculation procs |
| P2 — Near-term | State escheatment validation table (TD-3) |
| P2 — Near-term | FLOAT for financial amounts |
| P2 — Near-term | Code duplication with NCA (TD-4) |
| P2 — Near-term | BULK_LOGGED recovery model |
| P3 — Planned | TEXT data type migration |
| P3 — Planned | Notes column data classification |
