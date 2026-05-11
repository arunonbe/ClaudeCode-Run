# Solution Architect Analysis — DS_DB_ATL_atlys_fc_nca (atlys_fc_nca)

## Technical Debt Register

### TD-1: Hard-Coded Server Name Conditional in Business Logic
**File:** `dbo/Stored Procedures/sys_calc_dormancy.sql` line 43  
**Code:** `AND CAST(@@SERVERNAME AS char(1)) IN ('Q', 'P', 'C')`  
**Description:** The dormancy calculation procedure uses a server-name prefix check to decide whether to retrieve actual maintenance fee data from the SSAS cube. Servers not matching this pattern silently bypass the cube data path. This means a DR failover to a differently-named server, or any environment rename, will cause the maintenance fee calculation to produce incorrect (all-forecast, no-actual) results without error.  
**Impact:** Critical — silent financial calculation error propagates to GL amortisation entries.  
**Remediation:** Replace server-name detection with a configurable environment flag stored in `tblControls` or equivalent.  
**Priority:** P1

### TD-2: No TRY/CATCH Error Handling in Calculation Procedures
**Files:** `sys_calc_issue.sql`, `sys_calc_dormancy.sql`, `sys_calc_comm.sql`, `sys_calc_interchange.sql`, `sys_calc_plastic.sql`, `sys_calc_recur.sql`, `sys_calc_reissue.sql`  
**Description:** None of the core fee calculation procedures wrap their logic in TRY/CATCH blocks. An arithmetic error, null dereference, or FK constraint violation during a recalculation will leave `tblForecast_data` in a partially updated state without rollback.  
**Impact:** High — data integrity risk. Partial writes to financial forecast tables.  
**Remediation:** Wrap all calculation procedures in `BEGIN TRY … BEGIN CATCH … ROLLBACK … END CATCH` blocks. Log errors to an error log table.  
**Priority:** P1

### TD-3: Deprecated TEXT Data Type
**File:** `dbo/Tables/tblForecast_data.sql`  
**Description:** `notes TEXT NULL` — the `TEXT` data type is deprecated since SQL Server 2005. It cannot be used in string functions without `CAST`/`CONVERT`, cannot be used in APPLY expressions, and prevents use of modern string operations.  
**Impact:** Low-medium. Code maintainability and future compatibility risk.  
**Remediation:** Alter `notes` to `NVARCHAR(MAX)`.  
**Priority:** P3

### TD-4: FLOAT Data Type for Financial Amounts
**File:** `cursforecast.sql`, `tblIssuance.sql`, `tblForecast_data.sql`, `tblSpend.sql`  
**Description:** Financial amounts (e.g., `forecast_amt FLOAT(53)`, `fvd_rate FLOAT`, `load_fee FLOAT`) use the `FLOAT` data type, which is an approximate numeric type subject to floating-point rounding errors. Financial calculations — especially when accumulated over many months — can accumulate rounding errors.  
**Impact:** Medium — potential penny-off discrepancies in financial reporting and GL entries.  
**Remediation:** Migrate financial amounts to `DECIMAL`/`NUMERIC` with appropriate precision and scale.  
**Priority:** P2

### TD-5: Code Duplication with atlys_fc_nus
**Description:** `atlys_fc_nca` and `atlys_fc_nus` have identical stored procedure sets, indicating the codebase was duplicated for the US region rather than parameterised. Any fix must be applied twice.  
**Impact:** Medium — maintenance burden; divergence risk.  
**Remediation:** Consider a region parameterisation strategy, or establish a synchronised deployment pipeline that applies changes to all regional instances simultaneously.  
**Priority:** P2

### TD-6: BULK_LOGGED Recovery Model
As documented in `atlys_e`. Same finding here.  
**Priority:** P2

### TD-7: No TDE
As documented in `atlys_e`. Financial forecast data in plaintext.  
**Priority:** P1

---

## Security Vulnerabilities

### SV-1: db_owner for 'raf' Login
**File:** `Security/RoleMemberships.sql` line 1  
**Code:** `EXECUTE sp_addrolemember @rolename = N'db_owner', @membername = N'raf'`  
**Description:** The `raf` login is a `db_owner` in `atlys_fc_nca`. This grants full DDL and DML permissions including the ability to drop tables, truncate financial forecast data, modify stored procedures, and manage users.  
**Impact:** Critical — PCI DSS Req 7 violation. Privilege escalation path.  
**Remediation:** Remove `raf` from `db_owner`. Assign only application-tier permissions (EXECUTE on relevant procedures).  
**Priority:** P1

### SV-2: db_datawriter for NAM\UAT in Production
**File:** `Security/RoleMemberships.sql` line 53  
**Code:** `EXECUTE sp_addrolemember @rolename = N'db_datawriter', @membername = N'NAM\UAT'`  
**Description:** UAT environment login has data-write access. If this file is deployed to production, the UAT account can modify financial forecast records.  
**Impact:** High — test account with write access to production financial data.  
**Remediation:** Remove `NAM\UAT` from `db_datawriter` in production. Manage environment-specific logins outside the SSDT project.  
**Priority:** P1

### SV-3: Dynamic SQL in sys_copy_table_data with Incomplete Validation
**File:** `dbo/Stored Procedures/sys_copy_table_data.sql`  
**Description:** This procedure builds and executes dynamic SQL statements using table names provided as parameters (`@table`, `@tablename`, `@keycolumns`, etc.). Validation is performed by `ATLYS_E.dbo.sys_chkstr`, which inspects for suspicious characters. However, `sys_chkstr` is a string-inspection function, not a full SQL parser. The construction at lines 39–50 uses `QUOTENAME` for table names (which is correct) but the `@deletewhere` parameter (line 39) is concatenated without QUOTENAME: `' WHERE EXISTS IN (SELECT NULL FROM dbo.' + QUOTENAME(@table) + ' WHERE )' + @deletewhere`. This pattern could be vulnerable to injection if `@deletewhere` contains a valid-but-malicious WHERE clause.  
**Impact:** Medium — potential SQL injection if `sys_chkstr` has gaps.  
**Remediation:** Replace `@deletewhere` free-text concatenation with fully parameterised patterns. Restrict EXECUTE permission on this procedure to DBA roles only.  
**Priority:** P2

### SV-4: Notes Columns with Uncontrolled Free Text
**Files:** `cursforecast.sql` (`notes NTEXT`), `tblForecast_data.sql` (`notes TEXT`)  
**Description:** Free-text notes fields may contain sensitive client information, deal terms, or PII entered by analysts. No data classification or masking controls are applied.  
**Impact:** Low-medium — unclassified data accumulation.  
**Remediation:** Add data classification labels; implement a periodic review process; consider masking in non-production environments.  
**Priority:** P3

---

## All Object Names with Purpose

### Tables
| Object | Purpose |
|---|---|
| cursforecast | Program master with all fee assumptions |
| tblForecast_data | Monthly forecast revenue by line code |
| tblForecast_Version | Named forecast version registry |
| tblForecast_Fees | Per-version fee overrides |
| tblForecastChangeLog | Audit trail of program include/exclude changes |
| tblIssuance | Monthly issuance volumes |
| tblPlastics | Physical card volumes |
| tblSpend | Spend transaction volumes |
| tblCommissions | Sales rep commission records |
| tblAmort_Tables_1 / tblAmort_Tables_2 | Dormancy recognition schedule tables |
| tblDash_data | Pre-aggregated dashboard data |
| tblControls | Period control dates |
| tblPrgDflt | Default fee assumptions |
| tblCosts | External vendor costs |

### Triggers
| Object | Table | Purpose |
|---|---|---|
| trg_exclude | cursforecast | Logs include/exclude changes to tblForecastChangeLog |

### Key Stored Procedures by Category
| Category | Procedures |
|---|---|
| Fee Calculation | sys_calc_issue, sys_calc_dormancy, sys_calc_comm, sys_calc_interchange, sys_calc_plastic, sys_calc_recur, sys_calc_reissue |
| Forecast Management | sys_create_forecast, sys_new_program, sys_recalc_forecast, sys_program (and variants) |
| Revenue Reporting | sys_revenue_cross_tab (and ~10 variants), sys_actual_summary |
| Issuance Reporting | sys_issuance_cross_tab (and variants) |
| Commission Reporting | sys_comm (and ~6 variants) |
| Cost Management | sys_costs_cross_tab (and variants), sys_costs_post |
| Amortisation | sys_amortization (and variants including _rev_post, _issuance_post) |
| Variance | sys_variance_details, sys_variance_lines, sys_variance_summary |
| Dashboard | sys_dash (and variants) |
| Deferred Revenue | sys_deferredrevenue_cross_tab (and variants) |
| Utilities | sys_copy_table_data, sys_controls, sys_renumber, sys_custnames, sys_custnums |

---

## Remediation Priority Summary

| Priority | Issue |
|---|---|
| P1 — Immediate | Server-name logic in dormancy calc (TD-1) |
| P1 — Immediate | No TRY/CATCH in calculation procs (TD-2) |
| P1 — Immediate | db_owner for 'raf' (SV-1) |
| P1 — Immediate | UAT account db_datawriter in prod (SV-2) |
| P1 — Immediate | No TDE (TD-7) |
| P2 — Near-term | FLOAT for financial amounts (TD-4) |
| P2 — Near-term | sys_copy_table_data injection risk (SV-3) |
| P2 — Near-term | Code duplication with atlys_fc_nus (TD-5) |
| P2 — Near-term | BULK_LOGGED recovery model (TD-6) |
| P3 — Planned | TEXT data type migration (TD-3) |
| P3 — Planned | Notes column data classification (SV-4) |
