# DS_DB_acctgwf — Solution Architect Report

## 1. Complete Stored Procedure and Function Catalogue

### Stored Procedures

| Name | File | Size | Purpose |
|---|---|---|---|
| `sys_accts` | `dbo/Stored Procedures/sys_accts.sql` | 4.7 KB | GL account CRUD: list, add, update linked to company GL database via dynamic SQL |
| `sys_chkglviews` | `dbo/Stored Procedures/sys_chkglviews.sql` | 1.1 KB | Checks whether eCount or raw GP views exist in the target GL database; outputs flag |
| `sys_companies` | `dbo/Stored Procedures/sys_companies.sql` | 4.4 KB | Company list and CRUD operations |
| `sys_docs` | `dbo/Stored Procedures/sys_docs.sql` | 21.1 KB | Full document lifecycle management: list, create, attach to tasks/WPs, build nested-set tree |
| `sys_import` | `dbo/Stored Procedures/sys_import.sql` | 1.2 KB | Import stub (minimal) |
| `sys_openitems` | `dbo/Stored Procedures/sys_openitems.sql` | 4.2 KB | Open reconciliation item CRUD and clearing |
| `sys_periods` | `dbo/Stored Procedures/sys_periods.sql` | 676 B | Fiscal period lookup |
| `sys_schedules` | `dbo/Stored Procedures/sys_schedules.sql` | 5.7 KB | Schedule definition CRUD |
| `sys_tasks` | `dbo/Stored Procedures/sys_tasks.sql` | 30.2 KB | Task CRUD, completion, notes, document attachment, task replication across companies |
| `sys_tasks_execsched` | `dbo/Stored Procedures/sys_tasks_execsched.sql` | 1.2 KB | Executes schedule generation for tasks |
| `sys_types` | `dbo/Stored Procedures/sys_types.sql` | 11.7 KB | Type hierarchy CRUD (used for WP types, task types, account types) |
| `sys_user` | `dbo/Stored Procedures/sys_user.sql` | 9.5 KB | Authentication, session creation, password change/reset, user CRUD |
| `sys_wp` | `dbo/Stored Procedures/sys_wp.sql` | 23.3 KB | Workpaper lifecycle: create, list, sign, review, audit, GL account attach, WP comments |
| `sys_wpreports` | `dbo/Stored Procedures/sys_wpreports.sql` | 4.7 KB | Workpaper reporting queries |

### Functions

| Name | Type | Purpose |
|---|---|---|
| `sys_aggr_date` | Scalar | Min/max date aggregation |
| `sys_chkstr` | Scalar | Character allowlist validation (used to prevent SQL injection in dynamic object names) |
| `sys_chkuser` | Scalar | User-company access check (RBAC gate) |
| `sys_chkuserrights` | Scalar | User right type check (e.g., 'Task Manager', 'Workpapers review') |
| `sys_cinfo` | Scalar | Returns GL database name for company |
| `sys_clist` | TVF | Returns list of companies accessible to current session |
| `sys_sched` | TVF | Generates recurring schedule dates using recursive CTE |
| `sys_strGLAcctActive` | Scalar | Returns parameterised SQL string for active GL accounts query |
| `sys_strGLAccts` | Scalar | Returns parameterised SQL string for GL chart of accounts |
| `sys_strGLAcctTx` | Scalar | Returns parameterised SQL string for posted GL transactions |
| `sys_strGLAcctUnposted` | Scalar | Returns parameterised SQL string for unposted GL entries |
| `sys_uinfo` | TVF | Returns user display info for session ID |

## 2. Security Vulnerability Analysis

### 2.1 Dynamic SQL Usage

| Location | Pattern | Risk Level |
|---|---|---|
| `sys_accts.sql` line 102 | `EXEC sp_executesql @SQLStr` | LOW — SQL string is assembled from `sys_strGLAccts*` functions using fixed template strings with no user input concatenation |
| `sys_chkglviews.sql` line 27 | `EXEC sp_executesql @SQLStr, N'@o tinyint OUTPUT', @views OUTPUT` | LOW — parameterised |
| `sys_wp.sql` lines 80, 151, 635 | `EXEC sp_executesql @SQLStr, N'...'` with parameters | LOW — parameterised |
| `sys_wpreports.sql` line 87 | `EXEC sp_executesql @SQLStr, N'...'` with parameters | LOW — parameterised |
| `sys_strGLAccts.sql` | Dynamic SQL string returned includes `@db` variable (database name) | **MEDIUM** — `@db` is sourced from `tblAWCompanies.GlDbName`. If an admin modifies this value to a malicious string, the dynamic SQL could be redirected. The `sys_chkstr` function is used to validate database names elsewhere but not explicitly shown for this path. |

**Finding**: Dynamic SQL is generally used with `sp_executesql` and parameterisation. The primary residual risk is the `GlDbName` field used as a SQL object name qualifier (database name in `sys_strGLAccts`). Object names cannot be parameterised via `sp_executesql`, so this relies on `sys_chkstr` validation. Confirm that `sys_chkstr` is called before `GlDbName` is used in any dynamic SQL path.

### 2.2 Authentication and Credential Handling

| Issue | Location | Risk |
|---|---|---|
| SHA-1 password hashing | `tblAWUsers` trigger line 37; `sys_user.sql` lines 44, 135, 158 | **HIGH** — SHA-1 is cryptographically broken. Should be replaced with bcrypt/PBKDF2/Argon2. |
| Password transmitted as VARBINARY | `sys_user.sql` parameter `@pwd varchar(256)` | **MEDIUM** — Password is sent as a VARCHAR parameter. Ensure TLS/encrypted connection is enforced on all client connections. |
| Empty password check | `sys_user.sql` line 127 — checks for `0xDA39A3EE5E6B4B0D3255BFEF95601890AFD80709` (SHA-1 of empty string) | LOW — correctly blocks empty passwords |
| EMEA_ATLYS hardcoded bypass | `sys_tasks.sql` lines 19, 393 | **MEDIUM** — A specific SQL login name is hardcoded in RBAC bypass logic. This creates a permanent privileged backdoor that bypasses the standard access control model. |

### 2.3 Excessive Permission Grants

From `Security/RoleMemberships.sql`:
- `NAM\PROD`, `NAM\UAT`, `NAM\PROD_CPP`, `NAM\PROD_CPP_APAC`, `NAM\PROD_ITOPS` all have `db_datareader`. This gives broad SELECT access to ALL tables including `tblAWUsers` (containing SHA-1 password hashes). **Minimum-privilege principle violation.**
- `ifs_gidadb`, `ifs_infosec`, `scpardb`, `NAM\ISA_SQL_SECADMIN` have `db_accessadmin` + `db_securityadmin` — these are security administration roles. If these accounts are compromised, an attacker could create new logins or change role memberships.

### 2.4 Missing Encryption

- **TDE**: Not enabled (`IsEncryptionOn = False`, `acctgwf.sqlproj` line 51). Password hashes in `tblAWUsers` are unencrypted at rest.
- **Column-level encryption**: Not present on `Email` field.
- **Always Encrypted**: Not present.

## 3. Code Quality Observations

- The `sys_tasks.sql` stored procedure (30.2 KB) is heavily nested with IF/ELSE branching — cyclomatic complexity is very high. The same status query logic is repeated ~8 times with minor variations. This should be refactored using a common CTE or helper view.
- `sys_docs.sql` (21.1 KB) uses nested-set tree operations with XML path manipulation — correct but complex and difficult to maintain.
- `sys_wp.sql` (23.3 KB) contains commented-out code sections (lines visible with `--`) — these should be reviewed and removed if inactive.
- All stored procedures begin with `SET NOCOUNT ON` — correct practice for reducing network traffic.
- `BEGIN TRY / BEGIN CATCH / ROLLBACK TRANSACTION` patterns are consistently used — good transactional hygiene.
- `SCOPE_IDENTITY()` is used correctly after INSERT operations rather than `@@IDENTITY` — appropriate for trigger safety.

## 4. Technical Debt Register

| Item | Severity | File Reference |
|---|---|---|
| SHA-1 password hashing in trigger | HIGH | `dbo/Tables/tblAWUsers.sql` line 37 |
| SHA-1 password comparison in proc | HIGH | `dbo/Stored Procedures/sys_user.sql` lines 44–45, 135 |
| TDE disabled | HIGH | `acctgwf.sqlproj` line 51 |
| `EMEA_ATLYS` hardcoded login bypass | MEDIUM | `dbo/Stored Procedures/sys_tasks.sql` lines 19, 393 |
| `OPTION (MAXRECURSION 0)` in task queries | MEDIUM | `dbo/Stored Procedures/sys_tasks.sql` (multiple lines) |
| Dead table `tblAW_Docs_old` | LOW | `dbo/Tables/tblAW_Docs_old.sql` |
| Dead tables `combine_dtl`, `combine_log` | LOW | `dbo/Tables/combine_dtl.sql`, `combine_log.sql` |
| Broad `db_datareader` on credential table | MEDIUM | `Security/RoleMemberships.sql` |
| No data retention/purge mechanism | MEDIUM | Schema-wide |
| `sys_tasks.sql` excessive IF nesting | MEDIUM | `dbo/Stored Procedures/sys_tasks.sql` |

## 5. Remediation Priority List

1. **[P1 — Critical]** Replace SHA-1 hashing with bcrypt or PBKDF2 in `tblAWUsers` trigger and `sys_user` stored procedure. Coordinate a forced password reset for all users.
2. **[P1 — Critical]** Enable TDE on this database. Coordinate with infrastructure team.
3. **[P2 — High]** Remove `EMEA_ATLYS` login bypass in `sys_tasks.sql`. Replace with proper service account RBAC or stored procedure signing.
4. **[P2 — High]** Restrict `db_datareader` grants — revoke from application accounts that do not need direct table access; replace with view-level grants where possible.
5. **[P3 — Medium]** Implement a data retention policy for `tblAW_TaskHistory`, `tblAW_TaskComments`, and `tblAW_WPComments` (e.g., archive after 7 years).
6. **[P3 — Medium]** Add `MAXRECURSION` limit (e.g., 1000) to scheduled queries as a safety guard.
7. **[P4 — Low]** Drop `tblAW_Docs_old`, `combine_dtl`, `combine_log` after confirming no active references.
8. **[P4 — Low]** Add column-level encryption or masking to `tblAWUsers.Email` for GDPR compliance.
9. **[P4 — Low]** Establish CI/CD pipeline for DACPAC deployment with automated schema diff validation.
