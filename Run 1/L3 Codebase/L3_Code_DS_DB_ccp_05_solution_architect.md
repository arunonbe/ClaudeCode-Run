# DS_DB_ccp — Solution Architect View

## 1. Technical Debt Summary

| Category | Severity |
|---|---|
| SSN stored in plaintext in 3 tables (production, staging, archive) | CRITICAL |
| DOB stored in plaintext in 3 tables | HIGH |
| Full cardholder PII in plaintext | HIGH |
| No column-level encryption | HIGH |
| TDE status unconfirmed | HIGH |
| Archive tables grow unbounded (SSN included in archive rows) | HIGH |
| SQL Server 2012 DACPAC target | HIGH |
| No CI/CD pipeline | MEDIUM |
| UPDATE triggers missing (PII changes not archived) | MEDIUM |

---

## 2. Security Vulnerabilities

### VULN-01: SSN Stored in Plaintext — `NAM_BIN_ACCOUNTS.SSN` (CRITICAL)

**File**: `dbo/Tables/NAM_BIN_ACCOUNTS.sql`, line 27

```sql
[SSN] NVARCHAR (50) NULL,
```

Social Security Numbers are stored without encryption or masking in the production table, staging table (`NAM_BIN_ACCOUNTS_STG.sql`), and archive table (`NAM_BIN_ACCOUNTS_ARCHIVE.sql`). This violates GLBA Safeguards Rule (16 CFR Part 314) requirements to implement safeguards for NPPI. A SQL Server credential compromise, a misconfigured query in cf_report, or an overprivileged service account would expose SSNs for all cardholders in the program.

**Remediation**:
1. Encrypt `SSN` at column level using SQL Server Always Encrypted or transparent column encryption.
2. Apply the same encryption to `NAM_BIN_ACCOUNTS_STG.SSN` and `NAM_BIN_ACCOUNTS_ARCHIVE.SSN`.
3. If SSN is not required for any operational or reporting function, truncate and null the column; remove from file import.
4. Assess whether SSN is required in the FI batch file at all — many programs use tokenised identifiers instead.

---

### VULN-02: DOB Stored in Plaintext — `NAM_BIN_ACCOUNTS.DOB` (HIGH)

**File**: `dbo/Tables/NAM_BIN_ACCOUNTS.sql`, line 26

```sql
[DOB] DATE NULL,
```

Date of birth is stored without encryption across production, staging, and archive tables. Combined with first name, last name, and SSN, this constitutes a complete identity theft dataset. Under CCPA, birthdate is defined as sensitive personal information (Cal. Civ. Code § 1798.140(ae)(1)(A)).

---

### VULN-03: Full PII Set in Staging Table Without Additional Controls (HIGH)

`NAM_BIN_ACCOUNTS_STG` contains the same SSN, DOB, name, address, phone, and email data as the production table. Staging tables are often:
- Excluded from access control reviews
- Truncated manually rather than on a defined schedule
- Not included in encryption key rotation processes
- Not audited for data access

A failed job run could leave SSN data in the staging table indefinitely, exposed to any user with read access to the CCP database.

---

### VULN-04: Archive Tables Contain Unlimited SSN History (HIGH)

`TR_NAM_BIN_ACCOUNTS_D` fires on every DELETE (triggered by `sp_process_NAM_BIN_ACCOUNTS` every daily batch cycle). This means SSN data for every cardholder in every batch since the first data load is permanently accumulated in `NAM_BIN_ACCOUNTS_ARCHIVE`. There is no deletion, masking, or purge mechanism for the archive table. The archive table is the highest-volume PII data store in CCP.

---

### VULN-05: No UPDATE Trigger — PII Changes Not Tracked (MEDIUM)

**File**: `dbo/Tables/NAM_BIN_ACCOUNTS.sql`

Triggers are FOR DELETE only. If a cardholder's SSN or name changes between batch files (e.g., a name correction), the `sp_process_NAM_BIN_ACCOUNTS` procedure **deletes the old record** (triggering archive) and inserts the new record. The historical SSN is preserved in the archive. However, if updates were made directly to the table outside the stored procedure flow, no audit trail would be captured. An explicit `FOR UPDATE` trigger capturing changed PII fields would provide more robust audit coverage.

---

### VULN-06: `CreateUser` Captures SUSER_NAME() — Privilege Escalation Risk (LOW-MEDIUM)

**File**: `dbo/Stored Procedures/sp_process_NAM_BIN_ACCOUNTS.sql`, line 96

```sql
,[CreateUser] = SUSER_NAME()
```

This records the SQL Server login name of the service account running the stored procedure. If the service account is shared across multiple applications (a common anti-pattern), the `CreateUser` field does not provide meaningful individual attribution. If the service account is overprivileged (e.g., `db_owner`), this does not flag data loaded under elevated credentials.

---

## 3. Complete Object Catalogue

### Tables (23 total)

| Table | Purpose |
|---|---|
| `NAM_BIN_ACCOUNTS` | Production cardholder account data from FI batch |
| `NAM_BIN_ACCOUNTS_STG` | Staging for incoming account file |
| `NAM_BIN_ACCOUNTS_ARCHIVE` | Deleted-row archive (holds SSN, DOB, full PII) |
| `NAM_BIN_TRANSACTION` | Production transaction records from FI batch |
| `NAM_BIN_TRANSACTION_STG` | Staging for transaction file |
| `NAM_BIN_TRANSACTION_ARCHIVE` | Transaction deleted-row archive |
| `NAM_BIN_BALANCES` | Production balance records by account and date |
| `NAM_BIN_BALANCES_STG` | Staging for balance file |
| `NAM_BIN_BALANCES_ARCHIVE` | Balance deleted-row archive |
| `NAM_BIN_CARD_STATUS` | Production card status by account and date |
| `NAM_BIN_CARD_STATUS_STG` | Staging for card status file |
| `NAM_BIN_CARD_STATUS_ARCHIVE` | Card status deleted-row archive |
| `Billing_Audit` | Billing audit production records |
| `Billing_Audit_STG` | Billing audit staging |
| `Billing_Detail` | Billing detail production records |
| `Billing_Detail_STG` | Billing detail staging |
| `Billing_Events` | Billing event triggers |
| `FVD_Deferred` | Deferred fee/value data production |
| `FVD_Deferred_STG` | Deferred staging |
| `FVD_Revenue` | Revenue fee/value data production |
| `FVD_Revenue_STG` | Revenue staging |
| `FVD_SingleLoad_STG` | Single-load fee staging |
| `FISERV_INVENTORY` | Physical card stock inventory from Fiserv |
| `package_execution` | SSIS/job execution metadata |
| `package_execution_log` | Job execution log detail |

### Stored Procedures (12)

| Procedure | Purpose |
|---|---|
| `sp_process_NAM_BIN_ACCOUNTS` | Stage → production account load |
| `sp_process_NAM_BIN_BALANCES` | Stage → production balance load |
| `sp_process_NAM_BIN_CARD_STATUS` | Stage → production card status load |
| `sp_process_NAM_BIN_TRANSACTION` | Stage → production transaction load |
| `sp_process_Billing_Audit` | Stage → production billing audit |
| `sp_process_Billing_Detail` | Stage → production billing detail |
| `sp_process_FVD_Deferred` | Stage → production deferred fees |
| `sp_process_FVD_Revenue` | Stage → production revenue fees |
| `sp_process_FVD_SingleLoad` | Stage → production single-load fees |
| `get_package_last_execution_date` | Return most recent successful execution date |
| `set_package_execution` | Record package execution start |
| `remove_package_imported_data` | Remove previously imported batch data |

### Triggers (4)

| Trigger | Table | Event |
|---|---|---|
| `TR_NAM_BIN_ACCOUNTS_D` | NAM_BIN_ACCOUNTS | DELETE |
| `TR_NAM_BIN_TRANSACTION_D` | NAM_BIN_TRANSACTION | DELETE |
| `TR_NAM_BIN_BALANCES_D` | NAM_BIN_BALANCES | DELETE |
| `TR_NAM_BIN_CARD_STATUS_D` | NAM_BIN_CARD_STATUS | DELETE |

---

## 4. Remediation Priority List

### Priority 1 — Immediate (P1, within 30 days)

| ID | Finding | Action |
|---|---|---|
| REM-01 | `NAM_BIN_ACCOUNTS.SSN` — plaintext in production, staging, archive | Encrypt with Always Encrypted or column encryption; assess with CISO and Legal |
| REM-02 | `NAM_BIN_ACCOUNTS.DOB` — plaintext | Encrypt or evaluate if DOB is needed operationally |
| REM-03 | TDE status unconfirmed | Verify and enable TDE on CCP database |

### Priority 2 — Short-term (P2, within 90 days)

| ID | Finding | Action |
|---|---|---|
| REM-04 | `NAM_BIN_ACCOUNTS_STG.SSN` — staging table not hardened | Apply same encryption and access controls to staging as production |
| REM-05 | `NAM_BIN_ACCOUNTS_ARCHIVE` — unbounded SSN accumulation | Define retention policy; implement purge after regulatory retention window (2 years Reg E) |
| REM-06 | Missing UPDATE trigger | Add FOR UPDATE trigger to `NAM_BIN_ACCOUNTS` to track PII changes |
| REM-07 | No CI/CD pipeline | Implement deployment validation workflow |

### Priority 3 — Medium-term (P3, within 180 days)

| ID | Finding | Action |
|---|---|---|
| REM-08 | Evaluate SSN necessity | Review whether SSN is required in FI batch file; negotiate SSN removal or tokenisation at source |
| REM-09 | Archive table archival strategy | Move archive data to a separate cold-storage database with stricter access controls |
| REM-10 | SQL Server 2012 DACPAC target | Upgrade to current SQL Server target |
