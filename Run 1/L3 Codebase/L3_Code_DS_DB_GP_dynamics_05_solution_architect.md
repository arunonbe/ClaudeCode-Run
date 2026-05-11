# DS_DB_GP_dynamics — Solution Architect View

## 1. Critical Security Findings

### 1.1 CRITICAL — Plaintext Passwords Committed to Source Control

**Files**: `Security/gplain.sql`, `Security/crystal.sql`, `Security/ISAUser.sql`, `Security/report.sql` (and potentially others)

```
Security/gplain.sql   — CREATE LOGIN [gplain]   WITH PASSWORD = N'vzBi{Wnnif|<cvd{Mbf|mbvemsFT7_&#$!~<skvSlqkvwoh9'
Security/crystal.sql  — CREATE LOGIN [crystal]  WITH PASSWORD = N'vzi{nn8^if|c+PvUd6{bfGmbmsFT7_&#$!~<7.vesvR#ymlq'
Security/ISAUser.sql  — CREATE LOGIN [ISAUser]  WITH PASSWORD = N'|aP{p1fnpf;uEw$oq+jfgezwmsFT7_&#$!~<c|aCsyBawfIp'
Security/report.sql   — CREATE LOGIN [report]   WITH PASSWORD = N'vzi{Rnnif|Bc,k+vd{.bfNmbmsFT7_&#$!~<vesvlqkoht_b'
```

These are **plaintext SQL Authentication passwords committed to a Git repository**. Any person with read access to this repo (current or historical) has these credentials. The accounts are members of `DYNGRP` which has `SELECT, INSERT, DELETE, UPDATE` on all GP tables.

**Impact**:
- `crystal` is typically used for Crystal Reports connections — broad read access to all GP financial data.
- `report` has read access to financial tables.
- `gplain` is a general GP login with broad data access.
- `ISAUser` is an ISA (Internet Security and Acceleration / InfoSec) account.

**Immediate actions required**:
1. Rotate all four passwords immediately. Do not include new passwords in source control.
2. Remove password literals from all `.sql` files — use `MUST_CHANGE` or `HASHED` syntax, or migrate to Windows Authentication.
3. Audit Git history to determine when these credentials were first committed and whether any unauthorised access occurred.
4. Assess whether the same credentials exist in regional GP repos (ECAN, ECNT, EMEAM, EAST — confirmed the pattern repeats).

**Note**: This finding constitutes a PCI DSS Requirement 8.6.1 violation (shared accounts with known passwords) and a SOX IT control failure.

### 1.2 HIGH — `amAutoGrant` Dynamic SQL Without Input Validation

**File**: `dbo/Stored Procedures/Procs1/amAutoGrant.sql`

```sql
create procedure amAutoGrant @tablename char(150) output as
  SET @command = 'grant SELECT,INSERT,DELETE,UPDATE on '+rtrim(@tablename)+' to DYNGRP'
  EXEC (@command)
```

`@tablename` is concatenated directly into a GRANT statement and executed. A caller passing `'DYNGRP; EXEC xp_cmdshell ''...''; --'` as `@tablename` could execute arbitrary code (SQL injection via GRANT statement). The `amAutoGrantsys` procedure has the same pattern.

**Remediation**: Wrap `@tablename` with `QUOTENAME()` and validate against `sys.objects` before granting. Use `EXECUTE AS` scope to limit blast radius.

### 1.3 HIGH — `SY01400.PASSWORD` Weak Hashing

**File**: `dbo/Tables/SY01400.sql` — `PASSWORD BINARY(16) NOT NULL`

GP stores user passwords as a 16-byte binary. The GP encryption algorithm (historically DES/MD5-based) does not meet current PCI DSS Requirement 8.3.6 standards for password hashing (salted + strong one-way function such as PBKDF2/bcrypt/Argon2). This is a vendor limitation of Dynamics GP; the remediation path is through GP's built-in Windows Authentication (Active Directory) which delegates credential storage to AD.

**Recommendation**: Mandate Windows Authentication for all GP users; disable SQL Authentication login mode for DYNAMICS where feasible. This also eliminates the credential-in-source-control problem.

---

## 2. Technical Debt Register

| ID | Debt Item | Location | Severity |
|----|-----------|----------|----------|
| TD-1 | Plaintext passwords in Security scripts | `Security/gplain.sql`, `crystal.sql`, `ISAUser.sql`, `report.sql` | Critical |
| TD-2 | `amAutoGrant` dynamic SQL injection | `dbo/Stored Procedures/Procs1/amAutoGrant.sql` | High |
| TD-3 | Weak GP password hashing (BINARY 16) | `dbo/Tables/SY01400.sql` | High |
| TD-4 | SQL Server 2008 R2 schema provider in SSDT | `dynamics.sqlproj` | Medium |
| TD-5 | No CI/CD pipeline | Repository root | High |
| TD-6 | Mixed SQL + Windows Authentication | `Security/` folder | Medium |
| TD-7 | `SearchAllTables` full-scan proc in production | `dbo/Stored Procedures/Procs1/SearchAllTables.sql` | Medium |
| TD-8 | Very large SSDT project (322 KB .sqlproj) — long build times | `dynamics.sqlproj` | Low |

---

## 3. All Object Names with Purpose

### Key Tables (selected)
- `SY01400` — GP user master: userIDs, usernames, PASSWORD hash, security class, UI preferences.
- `SY01500` — Company master: company IDs, names, addresses, tax registrations.
- `SY10500` — User-to-security-role-per-company mapping.
- `SY10550` — User alternate/modified forms and reports assignment.
- `SLB10000–SLB90000` (20 tables) — Budget master, amounts, ranges, categories, period breakdowns.
- `WDC40000–WDC51102` (8 tables) — Document workflow state machine tables.
- `MC00100, MC40200–MC60200` (6 tables) — Multi-currency rate and setup tables.
- `UPR10300–UPR41600` (9 tables) — Payroll employee and processing tables.
- `GPS_SQL_Error_Codes` — Custom error code registry for GP SQL errors.
- `DBVERSION`, `DB_Upgrade`, `SYUPDATE` — GP schema version tracking.
- `zAuditGPUserSec` — Audit trail table for all user security changes (SOX control).
- `ERB10000–ERB90500` (17 tables) — eReceipt document builder tables.

### Key Stored Procedures
- `amAutoGrant` / `amAutoGrantsys` — Grants DYNGRP access to new GP tables (dynamic SQL risk).
- `ASI_SP_*` (14 procedures) — SmartList lookup procedures for accounts, customers, vendors, employees, documents.
- `eConnectOut`, `eConnectOutCreate`, `eConnectOutCreateProc`, `eConnectOutTriggers`, `eConnectOutVerify` — eConnect outbound integration layer.
- `sar_rpt_all_user`, `sar_rpt_human_resource_administrator`, `sar_rpt_power_user`, `sar_rpt_rapid` — Security audit report procedures.
- `SearchAllTables` — Full-scan search across all GP tables.
- `erAvailableCompanies`, `erAvailableCompaniesWithUserAccessFlag` — Company accessibility queries.
- `rsaUpdateMessageCenter` — GP message center update.
- `omcGetTasks`, `omcImportRates`, `omcSaveRates` — Multi-currency task and rate management.
- `mcEuroCheckForUnpostedICTrx` — Intercompany unposted transaction check.
- `smAddRecordAddedRecord`, `smAddRelationMSTR`, `smBindTableDefaults` (etc.) — GP SmartModule framework.

### Views
- `ORG00101`, `ORG10000`, `ORG10100` — Organisation hierarchy views.
- `SY10000` — Security role assignment view.

### Audit Triggers
- `AuditGPUserCreateUpdateDelete` (on SY01400) — Captures all user account changes.
- `AuditGPUserCreateDeleteSY10550` (on SY10550) — Captures alternate forms/reports changes.
- `AuditGPUserCreateUpdateDeleteSY10500` (on SY10500) — Captures role assignment changes.
- `AuditGPUserCreateUpdateDeleteSY60100` (on SY60100) — Captures additional security changes.

---

## 4. Remediation Priority

| Priority | Item | Action |
|----------|------|--------|
| P0 | TD-1 — Plaintext passwords | Rotate immediately; remove from repo; enforce Windows Authentication |
| P0 | TD-2 — `amAutoGrant` injection | Wrap with `QUOTENAME()` and `sys.objects` validation |
| P1 | TD-3 — Weak password hashing | Migrate all GP users to Windows Authentication; disable SQL Auth |
| P1 | TD-5 — No CI/CD | Implement automated DACPAC build + deploy pipeline |
| P2 | TD-4 — Stale schema provider | Update to current SQL Server version (Sql130/Sql150/Sql160) |
| P2 | TD-6 — Mixed authentication | Standardise on Windows Authentication across all GP logins |
| P3 | TD-7 — `SearchAllTables` in production | Restrict execution to non-production environments only |
| P3 | TD-8 — Large .sqlproj | Consider splitting into multiple linked SSDT projects |
