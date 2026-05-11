# DS_DB_CBTS — Solution Architect View

## 1. Technical Debt Summary

| Category | Severity |
|---|---|
| Plaintext foreign bank account numbers | CRITICAL |
| No column-level encryption on PII fields | HIGH |
| TDE status unconfirmed | HIGH |
| Named individual access grants in source control | MEDIUM |
| No automated deployment pipeline for DDL repo | MEDIUM |
| Unbounded history table growth | MEDIUM |
| Empty README / no operational documentation | LOW |

---

## 2. Security Vulnerabilities

### VULN-01: Plaintext Foreign Bank Account Storage — `BENEFICIARY.ACCOUNT_NUMBER` (CRITICAL)

**File**: `Database Objects/Tables/dbo.BENEFICIARY.sql`, line 23

```
[ACCOUNT_NUMBER] [varchar](50) NULL,
```

Foreign bank account numbers are stored in plaintext. Combined with `ROUTING_CODE` (VARCHAR 50) and `SWIFT_BIC_CODE` (VARCHAR 12), a compromise of this table provides sufficient information to initiate fraudulent wire transfers to beneficiary bank accounts. There is no encryption, tokenisation, or masking applied to these fields.

**Remediation**: Encrypt `ACCOUNT_NUMBER`, `ROUTING_CODE`, and `SWIFT_BIC_CODE` at the column level using SQL Server Always Encrypted, or route storage through a payment-data token vault. If Always Encrypted is used, the Java application layer (Spring Data JPA) requires JDBC driver support for encrypted column access.

---

### VULN-02: Plaintext PII on BENEFICIARY and REMITTER (HIGH)

**File**: `dbo.BENEFICIARY.sql` lines 13–14, 18–19; `dbo.REMITTER.sql` lines 12–13

First name, last name, email, and phone number are stored in plaintext VARCHAR columns. Under GDPR, these are personal data of the beneficiary (potentially an EEA resident). No pseudonymisation or encryption at column level is applied.

**Remediation**: Apply pseudonymisation for non-operational use cases; document data-processing basis and cross-border transfer mechanism under GDPR Chapter V.

---

### VULN-03: Individual Named Grants in Security Scripts (MEDIUM)

**Files**: `Security/NAM Brenda.Pereira.sql`, `Security/NAM TCS_L2.sql`

Named individuals and teams have access grants stored in SQL scripts in source control. If these scripts are executed on production and personnel change, access permissions may not be revoked in a timely manner.

**Remediation**: 
1. Replace individual/team named grants with role-based access (AD group → SQL role → database permissions).
2. Implement an access review process (PCI DSS Req 7.3) to periodically certify all database accounts.
3. Remove individual-named scripts from source control; replace with role-membership scripts.

---

### VULN-04: Spring Batch Context May Contain Sensitive Data (MEDIUM)

**File**: `dbo.BATCH_JOB_EXECUTION_CONTEXT.sql`

```sql
[SERIALIZED_CONTEXT] NVARCHAR(MAX) NULL
```

Spring Batch serialises job execution context as Java objects to this column. If job parameters include remitter/beneficiary personal data or account identifiers, this column becomes a PII sink that is not classified or controlled. The column is NVARCHAR(MAX), meaning it can store arbitrary data.

**Remediation**: Audit Spring Batch job configurations to confirm no PII is serialised into execution context. If PII is present, implement a custom serialiser that redacts sensitive fields.

---

### VULN-05: No TDE Confirmation (HIGH)

TDE is not configurable in DDL scripts; it is a SQL Server instance-level setting. Given `BENEFICIARY.ACCOUNT_NUMBER` stores plaintext foreign bank account numbers, TDE must be confirmed active at the database level. Without TDE, a physical media compromise of the SQL Server data files exposes all beneficiary bank account data in plaintext.

**Remediation**: Confirm TDE is enabled on the CBTS database. Rotate the TDE encryption key per PCI DSS Req 3.6 schedule.

---

## 3. Database Object Catalogue

### Tables (22 total)

| Table | Brief Description |
|---|---|
| `ADDRESS` | Shared address entity for both cardholder and bank address |
| `BENEFICIARY` | Overseas payment recipient: name, bank details, SWIFT, address |
| `BENEFICIARY_REGULATORY_RULE` | Regulatory rule associations per beneficiary |
| `BATCH_JOB_INSTANCE` | Spring Batch — job definition instances |
| `BATCH_JOB_EXECUTION` | Spring Batch — per-run execution records |
| `BATCH_JOB_EXECUTION_CONTEXT` | Spring Batch — serialised job context |
| `BATCH_JOB_EXECUTION_PARAMS` | Spring Batch — job parameter values |
| `BATCH_JOB_EXECUTION_SEQ` | Spring Batch — job execution ID sequence |
| `BATCH_JOB_SEQ` | Spring Batch — job instance ID sequence |
| `BATCH_STEP_EXECUTION` | Spring Batch — per-step execution metrics |
| `BATCH_STEP_EXECUTION_CONTEXT` | Spring Batch — serialised step context |
| `BATCH_STEP_EXECUTION_SEQ` | Spring Batch — step execution ID sequence |
| `DATABASECHANGELOG` | Liquibase — executed migration log |
| `DATABASECHANGELOGLOCK` | Liquibase — deployment lock |
| `RATE` | FX rate quotation: currency pair, value, status, gateway reference |
| `RATE_HISTORY` | Audit history of rate record changes |
| `RECON_FILE` | Reconciliation file tracking (T+1 settlement) |
| `REMITTER` | US sender: name, address, account identifier, brand |
| `TRANSFER` | Transfer execution: rate, beneficiary, fee, status, gateway transfer ID |
| `TRANSFER_HISTORY` | Audit history of transfer record changes |
| `TRANSFER_RETURN` | Gateway-returned/rejected transfers: wire number, reason, FX rate |

### Stored Procedures: None
### Views: None
### Functions: None

All business logic resides in the Java Spring Batch application layer.

---

## 4. Remediation Priority List

### Priority 1 — Immediate (P1, within 30 days)

| ID | Finding | Action |
|---|---|---|
| REM-01 | `BENEFICIARY.ACCOUNT_NUMBER`, `ROUTING_CODE`, `SWIFT_BIC_CODE` — plaintext | Implement column-level encryption or token vault; classify under Tier 1 data policy |
| REM-02 | TDE status unconfirmed | Verify TDE on CBTS database; enable if not active |
| REM-03 | Individual named grants in security scripts | Revoke individual grants; replace with AD group-based role assignments |

### Priority 2 — Short-term (P2, within 90 days)

| ID | Finding | Action |
|---|---|---|
| REM-04 | BENEFICIARY/REMITTER PII in plaintext | Apply pseudonymisation or column encryption for non-operational access paths |
| REM-05 | Spring Batch context may contain PII | Audit Spring Batch job configurations; implement redacting serialiser |
| REM-06 | No data retention policy on TRANSFER_HISTORY, RATE_HISTORY | Define 5-year FinCEN retention + archival strategy; implement purge after retention window |
| REM-07 | Empty README | Document operational runbook, deployment process, restart procedure |

### Priority 3 — Medium-term (P3, within 180 days)

| ID | Finding | Action |
|---|---|---|
| REM-08 | No CI/CD pipeline for DDL repository | Add schema validation workflow |
| REM-09 | GDPR cross-border transfer documentation | Document legal basis for cross-border personal data transfers (GDPR Art. 46) |
| REM-10 | Gateway single-dependency architecture | Document gateway failover/fallback procedures |
