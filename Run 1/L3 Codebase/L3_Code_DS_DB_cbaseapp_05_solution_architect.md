# DS_DB_cbaseapp — Solution Architect View

## 1. Technical Debt Summary

| Category | Count / Severity |
|---|---|
| SQL injection via unparameterised dynamic SQL | 2 confirmed critical procedures |
| Plaintext sensitive data (PAN / credential fields) | 2 confirmed fields |
| Missing TDE confirmation | 1 database-wide gap |
| Excessive db_owner grants in RoleMemberships | 12 service accounts (in related dbadmin) |
| Stored procedure count without test coverage | 781 |
| Legacy SQL Server 2012 target | Database-wide |
| Cross-database hard-coded linked-server names | 2 procedures |
| Historical/dead tables in schema | ~15 tables with rollback/backup/date suffixes |
| Missing data-retention policy | All PII and CHD tables |
| Password field without confirmed hash algorithm | 1 field |

---

## 2. Security Vulnerabilities

### VULN-01: SQL Injection — `csa_forward_search` (CRITICAL)

**File**: `dbo/Stored Procedures/csa_forward_search.sql`, lines 20–68

The procedure builds `@strSQL` (VARCHAR 3000) by concatenating user-supplied parameters directly:
```sql
IF @username IS NOT NULL SET @strVariableWhere = @strVariableWhere + ' and uvi.username like ''' + @username + '%'' '
IF @lastname  IS NOT NULL SET @strVariableWhere = @strVariableWhere + ' and upi.last_name like ''' + @lastname + '%'' '
```
Then calls `Exec (@strSQL)`. A CSA user supplying `@username = "'; DROP TABLE cbase_user; --"` could execute arbitrary SQL. The comment `--Exec (@strSQL)` on line 70 suggests the exec is disabled in this version, but the parameterised replacement has not been implemented. This procedure has access to PII-containing tables: `user_personal_info`, `user_validation_information`, `email_address`, `address`, `user_ecount`.

**Remediation**: Rewrite using `sp_executesql` with typed parameters, or refactor to use static WHERE clauses with `OR` conditions.

---

### VULN-02: SQL Injection — `csa_GetEcountHist` (CRITICAL)

**File**: `dbo/Stored Procedures/csa_GetEcountHist.sql`, lines 13–31

```sql
set @strSql = @strSql + ' WHERE B.transaction_state = 1 and  A.device_id = ''' + @device_id + ''' UNION '
```
`@device_id` (VARCHAR 50) is concatenated directly into the dynamic SQL. The procedure then calls `Exec (@strSql)`. A malicious device_id value could inject arbitrary SQL spanning `VSQL3.ecountcore` and `VSQL1.webcert` linked-server databases.

Additionally, this procedure **drops and recreates `v_total_ecount_hist`** as a shared database object on each call — a DDL side effect that is not safe for concurrent use.

**Remediation**: Replace concatenation with `sp_executesql` parameterised query; separate the view creation into an explicit DDL script.

---

### VULN-03: Plaintext PAN Storage — `ecap_transaction_info.credit_card_number` (CRITICAL)

**File**: `dbo/Tables/ecap_transaction_info.sql`, line 4

```sql
[credit_card_number] CHAR (50) NULL,
```
A 50-character credit card number field with no encryption, masking, or tokenisation. This violates PCI DSS Requirement 3.4 (render PAN unreadable anywhere it is stored) and Requirement 3.3 (do not store SAD).

**Remediation**: 
1. Assess whether this field is still actively populated.
2. If yes: encrypt at column level or migrate to a tokenisation vault; truncate existing data to last-4 digits.
3. If no: set column to NULL, then drop the column after confirming no application references.

---

### VULN-04: Unconfirmed Password Storage Strength — `user_validation_information.password` (HIGH)

**File**: `dbo/Tables/user_validation_information.sql`, line 3; `dbo/Stored Procedures/b2c_create_user.sql`, line 9

The `password` column is VARCHAR(100). The `b2c_create_user` procedure accepts `@password varchar(100)` and inserts it directly:
```sql
insert into user_validation_information(..., password, password_type, ...)
values (..., @password, 0, ...)
```
`password_type = 0` is an integer code; the interpretation is not documented in schema. If `0` means plaintext, this is a critical credential exposure. If it means hashed, the hash algorithm is undocumented. The `b2c_login_user` procedure authenticates by:
```sql
and uvi.password = @password
```
This equality comparison suggests either plaintext storage or that hashing occurs entirely at the application layer before the procedure is called.

**Remediation**: Confirm hash algorithm used at application layer. If MD5 or SHA1 is used, migrate to bcrypt/Argon2. Document `password_type` values.

---

### VULN-05: Dynamic DDL for Monthly Session-Login Partitioning — `ddl_create_session_login` (MEDIUM)

**File**: `dbo/Stored Procedures/ddl_create_session_login.sql`

This procedure creates monthly tables (`session_login_YYYYMM`) and dynamically alters a VIEW (`session_login_info`) using `sp_executesql`. The `@ownerstr` parameter (defaulting to `user`) is used to construct table names:
```sql
set @sqlstr = N' Create Table ' + @ownerstr + N'.session_login_' + @dtstr
```
If `@ownerstr` is passed as an attacker-controlled value, it could be used for schema injection. The default `user` context mitigates this, but explicit validation of `@ownerstr` against an allowlist is absent.

---

### VULN-06: DDA Number in Plaintext — `pdm_registration.dda_number` (HIGH)

**File**: `dbo/Tables/pdm_registration.sql`, line 14

```sql
[dda_number] CHAR (16) NULL,
```
This 16-digit field is indexed (`IX_pdm_registration__dda_number`). If this stores the embossed card number (PAN), it must be protected under PCI DSS Req 3.4. No encryption or masking is present.

---

### VULN-07: Audit Trail Captures Uncontrolled Data Snapshots — `AuditTrail` (HIGH)

**File**: `dbo/Tables/AuditTrail.sql`

The `Pre_Snap` and `Post_Snap` columns (NVARCHAR 2000) capture before/after state of audited table rows. If triggers write CHD rows (PAN, cardholder name) to `AuditTrail`, this table becomes a secondary CDE table — potentially an uncontrolled one. There is no evidence of field-level masking before audit capture.

---

### VULN-08: Hard-Coded Server Names in Stored Procedures (MEDIUM)

**File**: `dbo/Stored Procedures/csa_GetEcountHist.sql`, lines 16–27

Server names `VSQL3` and `VSQL1` are hard-coded in dynamic SQL strings. These cannot be changed without modifying stored procedure code.

---

## 3. Complete Stored Procedure / Function / View Catalogue

### Functions (4)

| Name | Purpose |
|---|---|
| `dbo.bounce_func_get_member_id` | Returns member ID for bounce-processing lookup |
| `dbo.SplitString` | Splits a delimited string into a table |
| `dbo.func_get_binary_IPv4` | Converts dotted-decimal IPv4 string to binary representation |
| `dbo.func_get_string_IPv4` | Converts binary IPv4 to dotted-decimal string |

### Views (28)

| Name | Purpose |
|---|---|
| `dbo.Account_info_View` | Cardholder + address + email + transaction summary |
| `dbo.v_general_users_demographic` | User demographic summary |
| `dbo.v_buyer_info_exists` | Payment buyer existence check |
| `dbo.v_recipient_info_exists` | Payment recipient existence check |
| `dbo.v_batch_payment` | Batch payment summary |
| `dbo.view_user_email` | User email listing |
| `dbo.v_user_demographics` | Extended demographics |
| `dbo.v_total_ecount_hist` | eCount transaction history (linked-server, dynamically managed) |
| `dbo.v_pdm_registration` | PDM registration summary |
| `dbo.v_stat_reference` | Statistical reference |
| `dbo.v_bulkstat_reference` | Bulk statistical reference |
| `dbo.pdm_affiliate_meta_data` | Affiliate metadata for PDM |
| `dbo.pdm_workflow_status_overall` | PDM application status — overall |
| `dbo.pdm_workflow_status_add_funds` | PDM — add funds section status |
| `dbo.pdm_workflow_status_address` | PDM — address section status |
| `dbo.pdm_workflow_status_application_review` | PDM — review section status |
| `dbo.pdm_workflow_status_bank` | PDM — bank section status |
| `dbo.pdm_workflow_status_employment` | PDM — employment section status |
| `dbo.pdm_workflow_status_fee` | PDM — fee section status |
| `dbo.pdm_workflow_status_partial_application` | PDM — partial application status |
| `dbo.init_verification_status` | Initial enrollment verification status |
| `dbo.access_entity_certificate_program_view` | Certificate-based access entities by program |
| `dbo.access_entity_certificate_view` | Certificate access entity details |
| `dbo.access_entity_domain_view` | Domain access entity details |
| `dbo.access_entity_ip_program_view` | IP access entities by program |
| `dbo.access_entity_ip_view` | IP access entity details |
| `dbo.affiliate_locale_copy_view` | Affiliate locale copy content |
| `b2c.session_login_info` | Rolling union of monthly session-login tables (dynamically altered) |

### Stored Procedures — Selected Key Procedures (781 total)

| Procedure | Purpose |
|---|---|
| `b2c_create_user` | Creates cardholder account across cbase_user, user_validation_information, user_ecount |
| `b2c_login_user` | Authenticates B2C cardholder; enforces 5-failure lockout |
| `bc_login_user` | Alternative login for BC portal |
| `backup_create_cbase_user` | Backup user-creation procedure |
| `rs_create_user` | Rewards/Subaru user creation |
| `cbaseapp_user_inquiry` | Full cardholder profile lookup by ecount_member_id |
| `OAccount_Details_inquiry` | On-account details inquiry |
| `update_user_profile` | Updates cardholder profile |
| `update_personal_info` / `update_user_personal_info` | Updates PII fields |
| `update_user_password` / `update_password2` | Password change |
| `update_security_questions` | Updates KBA security questions |
| `update_username` | Changes username |
| `cancel_payment` | Cancels a payment record |
| `cancel_payment_request` | Cancels payment request |
| `settle_payment_request` | Settles a payment request |
| `resend_payment_request` | Re-sends payment initiation |
| `proc_batch_payment_initialize_ins` | Initialises a batch disbursement |
| `proc_batch_payment_detail_ins` | Inserts batch payment detail rows |
| `proc_release_batch_payment_upd` | Releases batch for processing |
| `proc_batch_payment_result_upd` | Updates batch result |
| `proc_fraud_score_calc` | Calculates fraud score in real-time |
| `proc_fraud_score_ecount_calc` | eCount-specific fraud calculation |
| `proc_fraud_score_new_user_ins` | Inserts initial fraud score for new user |
| `proc_fraud_score_batch_upd` | Batch fraud score update job |
| `proc_busFraudPayment_Sel` | Selects payments under fraud hold |
| `proc_busAcceptSent_Upd` | Accept sent payment (fraud workflow) |
| `proc_busRejectSent_Upd` | Reject sent payment (fraud workflow) |
| `proc_busHoldSent_Upd` | Place sent payment on hold |
| `proc_busAcceptWithdrawal_Upd` | Accept withdrawal |
| `proc_busRejectWithdrawal_Upd` | Reject withdrawal |
| `csa_forward_search` | **[SQL INJECTION RISK]** CSA member search using dynamic SQL |
| `csa_GetEcountHist` | **[SQL INJECTION RISK]** eCount history for device; drops/recreates view |
| `csa_user_info_by_member_id` | CSA member lookup by member ID |
| `csa_pdm_customer_search` | PDM customer search for CSA |
| `csa_lock_info` | CSA lock status |
| `csa_status_info` | CSA status info |
| `proc_csa_get_transaction_hist` | Transaction history for CSA |
| `csa_monetary_adjustments` | CSA monetary adjustment |
| `banker_get_cbase_user_info` | Banker portal user info |
| `banker_get_user_info` | User info for banker portal |
| `Admin_TPIN_Create_and_update` | Creates or updates admin TPIN |
| `Retrive_Admin_TPIN` | Retrieves admin TPIN |
| `ddl_create_session_login` | Dynamically creates monthly session-login tables |
| `card_balance_debit_update_job` | Batch job for card balance debits |
| `card_balance_debit_populate_recent_orders` | Populates recent debit orders |
| `cbaseapp_process_partition_maintain` | Partition maintenance |
| `proc_enroll_confirm_upd` | Enrollment confirmation update |
| `proc_enroll_get_confirm_sel` | Enrollment confirmation select |
| `proc_fraud_score_calc` | Fraud scoring |
| `service_records_rapid_post` | Service records rapid posting |
| `strongbox_ticket_create` | Creates strongbox reference ticket |
| `transfer_ticket_create` | Creates transfer claim ticket |
| `set_mfa_validation_information` | Sets MFA validation data |
| `user_otp_status_process` | OTP status processing |
| `utl_dba_db_stats_history` | DBA stats utility |

---

## 4. Remediation Priority List

### Priority 1 — Immediate (P1, within 30 days)

| ID | Finding | Action |
|---|---|---|
| REM-01 | `ecap_transaction_info.credit_card_number` — plaintext PAN | Assess active use; encrypt or truncate to last-4; notify PCI QSA |
| REM-02 | `csa_forward_search` — SQL injection via `EXEC(@strSQL)` | Rewrite with `sp_executesql` + typed parameters |
| REM-03 | `csa_GetEcountHist` — SQL injection in device_id concatenation | Rewrite with parameterised query; separate view DDL |
| REM-04 | `pdm_registration.dda_number` — 16-digit value stored in plaintext | Classify as PAN or DDA; if PAN, apply Req 3.4 remediation |
| REM-05 | `user_validation_information.password` — confirm hash algorithm | Audit application layer; migrate to bcrypt/Argon2 if MD5/SHA1 |

### Priority 2 — Short-term (P2, within 90 days)

| ID | Finding | Action |
|---|---|---|
| REM-06 | No TDE confirmation | Confirm TDE status on production; enable if not active |
| REM-07 | `AuditTrail.Pre_Snap`/`Post_Snap` may capture CHD | Add CHD field exclusion or masking to audit triggers |
| REM-08 | `ddl_create_session_login` — `@ownerstr` injection risk | Add schema allowlist validation |
| REM-09 | Missing data-retention policy | Define retention periods for PII/CHD tables; add `purge_date` columns |
| REM-10 | `pdm_registration_customer.birthdate` — DOB plaintext | Confirm encryption at rest; document data-subject deletion process |

### Priority 3 — Medium-term (P3, within 180 days)

| ID | Finding | Action |
|---|---|---|
| REM-11 | No automated deployment pipeline | Implement SSDT/dacpac CI/CD with environment gates |
| REM-12 | No unit/integration tests for 781 stored procedures | Implement tSQLt test framework for critical procedures |
| REM-13 | SQL Server 2012 DACPAC target | Update to current SQL Server target version |
| REM-14 | Hard-coded linked-server names (VSQL3, VSQL1) | Externalise via configuration or synonym objects |
| REM-15 | Historical dead tables (20+ rollback/bak/date-suffixed tables) | Audit and drop confirmed-unused tables; reduce attack surface |
| REM-16 | No OFAC/sanctions screening code in schema | Confirm sanctions screening occurs at application layer; document |
