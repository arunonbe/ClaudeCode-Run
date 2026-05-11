# Solution Architect Analysis — DS_DB_ATL_atlys_e (atlys_e)

## Technical Debt Register

### TD-1: Deprecated Password Hashing Algorithm
**File:** `dbo/Tables/tblUsers.sql` lines 35–43 (trgUsers trigger)  
**Description:** Passwords are hashed using `PWDENCRYPT(CAST(pwd AS varchar))`. `PWDENCRYPT` is a SQL Server-internal function, deprecated since SQL Server 2012, that uses SHA-1 with a proprietary salt. SHA-1 is not approved for password storage under NIST SP 800-63B or PCI DSS v4.0.1 Requirement 8.3.6. The trigger re-hashes on every password update, and comparison is performed via `PWDCOMPARE()`.  
**Impact:** Critical. Any attacker with read access to `tblUsers` can attempt offline SHA-1 dictionary attacks against extracted hashes.  
**Remediation:** Migrate password storage to the application tier using bcrypt, Argon2, or PBKDF2. Remove in-database password management entirely and integrate with an identity provider (Azure AD / Entra ID).  
**Priority:** P1 — PCI DSS Req 8.3.6

---

### TD-2: SQL Compatibility Level 90 (SQL Server 2005)
**File:** `atlys_e.sqlproj` line 63  
**Description:** The database is running at compatibility level 90, which uses the SQL Server 2005 query optimiser. This prevents use of modern features (window functions with enhanced syntax, STRING_AGG, TRIM, JSON, etc.) and limits performance optimisations available in newer cardinality estimators.  
**Impact:** Medium. Query performance may be suboptimal; newer T-SQL idioms cannot be used.  
**Remediation:** Test all stored procedures at compat level 130 (SQL 2016) minimum and upgrade.  
**Priority:** P2

---

### TD-3: Hard-Coded Three-Part Cross-Database Names
**File:** Multiple — `sys_calc_dormancy.sql` (atlys_fc_nca), `sys_copy_table_data.sql` (atlys_fc_nca), all satellite databases.  
**Description:** All satellite databases reference `ATLYS_E.dbo.*` using hard-coded three-part names. This creates a tight coupling that prevents renaming the database, migrating to a different server name, or using Azure SQL Database.  
**Impact:** High. Major migration blocker.  
**Remediation:** Introduce database synonyms (`CREATE SYNONYM`) or a configuration table mapping logical to physical database names. Refactor cross-database calls to use the synonym layer.  
**Priority:** P2

---

### TD-4: No TDE / Backup Encryption
**File:** `atlys_e.sqlproj` line 51 (`<IsEncryptionOn>False</IsEncryptionOn>`)  
**Description:** Transparent Data Encryption is not enabled. Backup files written to disk or backup media are unencrypted.  
**Impact:** High. Loss of backup media results in cleartext exposure of all database contents including user credentials.  
**Remediation:** Enable TDE. Additionally, encrypt backups at the SQL Server Agent or backup-tool level.  
**Priority:** P1 — PCI DSS Req 3.5

---

### TD-5: CHECK Constraint Using DB_ID() at Write Time
**File:** `dbo/Tables/tblCompanies.sql` line 20  
**Description:** The CHECK constraint on `tblCompanies` validates that `fc_db_name` and `rev_db_name` exist as live databases by calling `DB_ID()`. This means the constraint fails during disaster recovery scenarios if the satellite databases have not yet been restored, blocking all company record writes.  
**Impact:** Medium. Potential DR failure scenario.  
**Remediation:** Move this validation to application-level code or a scheduled validation job. Remove the CHECK constraint.  
**Priority:** P3

---

### TD-6: BULK_LOGGED Recovery Model
**File:** `atlys_e.sqlproj` line 84  
**Description:** `BULK_LOGGED` prevents point-in-time recovery during bulk operations. In a regulated financial environment this is inappropriate.  
**Impact:** Medium. Restricted RPO window.  
**Remediation:** Switch to `FULL` recovery model and implement a regular transaction log backup schedule.  
**Priority:** P2

---

### TD-7: Dynamic SQL in sys_cross_tab
**File:** `dbo/Stored Procedures/sys_cross_tab.sql` (also sys_cross_tab1)  
**Description:** `sys_cross_tab` constructs dynamic SQL strings from parameters such as `@selectstr1`, `@fromstr`, `@groupstr`, `@havingstr`, `@joinstr`, `@formula`, `@selectstr3`, `@selectstr4`. These are validated by `dbo.sys_chkstr()` before use (lines 62–76), which is a partial mitigation. However, `sys_chkstr` may not cover all injection vectors, and the logic depends on a string-inspection function rather than true parameterisation.  
**Impact:** Medium. SQL injection risk if `sys_chkstr` has gaps; also makes code harder to review statically.  
**Remediation:** Audit `sys_chkstr` for completeness. Consider replacing the generic cross-tab engine with typed stored procedures for each specific report. At minimum, ensure all inputs are validated against an allowlist of known column/table names before concatenation.  
**Priority:** P2

---

## Security Vulnerabilities

### SV-1: PWDENCRYPT Weak Credential Storage (Critical)
See TD-1. Attack vector: database read access. CVSS context: Confidentiality HIGH.

### SV-2: Excessive Grants to Prod_Support_Update Role
**File:** `Security/Permissions.sql` lines 163–293  
**Description:** The `Prod_Support_Update` database role is granted INSERT and UPDATE on every table in `atlys_e`, including `tblUsers` and `tblUsersS`. This means any principal mapped to `Prod_Support_Update` can modify user records, change passwords, and alter account status directly in production without going through application logic.  
**Impact:** High. Violates PCI DSS Req 7 (least-privilege access). Allows privilege escalation.  
**Remediation:** Restrict `Prod_Support_Update` to only the tables that require operational support. Remove INSERT/UPDATE on `tblUsers`, `tblUsersC`, `tblUsersR`, `tblUsersS` from this role entirely, or require a break-glass procedure.  
**Priority:** P1

### SV-3: db_owner Role Assignment to 'raf'
**File:** `Security/RoleMemberships.sql` (atlys_fc_nca) line 1: `EXECUTE sp_addrolemember @rolename = N'db_owner', @membername = N'raf'`  
**Description:** The login `raf` is a member of `db_owner` in at least the fc_nca database and is also a member of `ATLYS_APP_GRP` in atlys_e (`Security/ATLYS_APP_GRP.sql` line 6). `db_owner` membership grants all permissions including schema changes, user management, and data manipulation in the database. This is inappropriate for a production application account.  
**Impact:** Critical. Privilege escalation. PCI DSS Req 7.2 violation.  
**Remediation:** Remove `raf` from `db_owner`. Assign only the minimum required permissions.  
**Priority:** P1

### SV-4: db_datawriter for NAM\UAT and NAM\PROD_ITOPS
**File:** `Security/RoleMemberships.sql` line 53–57  
**Description:** `NAM\UAT` is granted `db_datawriter` in fee-calculation databases. UAT environment accounts should not have write access to production databases.  
**Impact:** High. Potential for test data contamination of production.  
**Remediation:** Verify that `NAM\UAT` login is only present in non-production instances. If this file is deployed to production, remove the `db_datawriter` role assignment.  
**Priority:** P1

### SV-5: Password Policy — No Special Character Requirement
**File:** `dbo/Functions/sys_chkpwd.sql` lines 30–31 (commented out)  
**Description:** Special character and lowercase character requirements are commented out. The current policy enforces only length ≥8, one alpha, one numeric. PCI DSS Req 8.3.6 requires passwords to be at least 12 characters for new implementations.  
**Impact:** Medium. Weak password policy.  
**Remediation:** Uncomment and extend the special-character check, and increase minimum length to 12.  
**Priority:** P2

### SV-6: No Audit Log for User Credential Changes
**Description:** There is no explicit audit log table recording when `tblUsers.pwd` is changed, by whom, or from which context. The trigger `trgUsers` re-hashes but does not log the event.  
**Impact:** Medium. Inability to detect and investigate credential tampering. PCI DSS Req 10.2 requires logging of all changes to authentication credentials.  
**Remediation:** Add audit logging in `trgUsers` writing change events (user, timestamp, changed_by) to a dedicated audit table.  
**Priority:** P1

---

## All Object Names with Purpose

### Tables
| Object | Purpose |
|---|---|
| tblUsers | Application users |
| tblUserGroups | User role groups |
| tblUserGroupRights | Group-to-right assignments |
| tblUserRightTypes | Right type enumeration |
| tblUsersC | User configuration attributes |
| tblUsersR | User regional attributes |
| tblUsersS | User settings (enabled flag sync) |
| tblCompanies | Company registry (routing hub) |
| tblCountries | ISO country reference |
| tblCountriesC | Country config |
| tblCurrencies | ISO currency reference |
| tblExchRates | Actual exchange rates |
| tblFCExchRates | Forecast exchange rates |
| tblRegions | Sales regions |
| tblRegionsC | Region config |
| tblSalesReps | Sales representatives |
| tblSalesRepsC | Sales rep config |
| tblSalesRepsV | Sales rep view config |
| tblRelMgrs | Relationship managers |
| tblRelMgrsC | RM config |
| tblRelMgrsV | RM view config |
| tblAcctMgrs | Account managers |
| tblAcctMgrsC | AM config |
| tblAcctMgrsV | AM view config |
| tblPrgPrefixes | BIN prefix ranges |
| tblSystems | Processing system registry |
| tblTxInstances | Transaction-system instances |
| tblInterfaces | GL interface definitions |
| tblPaths | File/cube paths |
| tblPathTypes | Path type enumeration |
| tblMsgs | Internal messages |
| tblMsgsTo | Message recipients |
| tblMsgsRefTypes | Message reference types |
| combine_dtl | Data combination detail |
| combine_log | Data combination log |

### Triggers
| Object | Table | Purpose |
|---|---|---|
| trgUsers | tblUsers | Password re-hashing; cascade name/role changes to SalesReps/RelMgrs/AcctMgrs |

---

## Remediation Priority Summary

| Priority | Issue |
|---|---|
| P1 — Immediate | PWDENCRYPT credential storage (SV-1, TD-1) |
| P1 — Immediate | No TDE / backup encryption (TD-4, SV not numbered) |
| P1 — Immediate | db_owner for 'raf' (SV-3) |
| P1 — Immediate | Excessive Prod_Support_Update grants (SV-2) |
| P1 — Immediate | UAT account with db_datawriter in prod (SV-4) |
| P1 — Immediate | No audit log for credential changes (SV-6) |
| P2 — Near-term | Upgrade compat level to 130+ (TD-2) |
| P2 — Near-term | Implement CI/CD pipeline |
| P2 — Near-term | Switch to FULL recovery model (TD-6) |
| P2 — Near-term | Strengthen password policy min-length (SV-5) |
| P2 — Near-term | Audit sys_cross_tab injection guards (TD-7) |
| P3 — Planned | Refactor cross-database hard-coded names (TD-3) |
| P3 — Planned | Remove DB_ID() CHECK constraint (TD-5) |
