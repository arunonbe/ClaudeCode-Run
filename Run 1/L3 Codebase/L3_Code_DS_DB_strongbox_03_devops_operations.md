# DS_DB_strongbox — DevOps and Operations Assessment

## 1. Build and Deployment Pipeline

### 1.1 Project Type
Standard SSDT project targeting **SQL Server 2012** (`DSP: Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider`). This is the same older SQL Server target as the international warehouse. SQL Server 2012 reached end of extended support in July 2022. For a PCI DSS-regulated PII vault, running on an unsupported database engine is a critical compliance gap.

### 1.2 CI/CD
**No CI/CD pipeline is present.** Given that StrongBox is the most sensitive database in the platform — storing all PII encryption keys and ciphertext — **the absence of a gated, reviewed, and audited deployment pipeline is the highest-risk DevOps finding in the entire portfolio**.

Any change to StrongBox schema or stored procedures:
- Is not automatically validated
- May not require a security review
- Could introduce vulnerabilities in the key management API (e.g., logging key material, adding unintended SELECT access)

### 1.3 DACPAC Artefact
No pre-built DACPAC is committed to this repository (unlike riskdb which has `RiskDBv1.0.0.0.dacpac`). Deployments rely solely on the SSDT project build output.

---

## 2. Security Role Architecture

### 2.1 Defined Roles (from Security folder)

| Role | Permissions | Members |
|---|---|---|
| `Strongbox_Execute` | EXECUTE on stored procedures | 12 service accounts + 8 emer_* accounts + PROD_CPP variants |
| `Strongbox_Select` | SELECT on tables | Same set (plus NAM\PROD_CPP) |
| `Strongbox_Update` | UPDATE on tables | Subset |
| `Strongbox_Delete` | DELETE on tables | Subset |
| `Strongbox_Schema_View` | VIEW DEFINITION on schema | Subset |

**Critical observation:** `Strongbox_Select` grants direct table SELECT access to all three key tables (`asymmetric_key_store`, `symmetric_key_store`, `secure_data_store`) plus the `Results` table. Members of `Strongbox_Select` can execute `SELECT * FROM asymmetric_key_store` and retrieve all private keys **without going through the stored procedure API**.

The stored procedure API (`sb_get_data`) returns only the key material for a specific `data_id`. Direct table SELECT access bypasses this per-record access control and allows bulk key extraction.

**Members of Strongbox_Select who can bulk-query keys:**
- `NAM\PROD_CPP` — production CPP service account
- `NAM\PPA_PRD_APISVC` — API service
- `emer_*` emergency accounts (8 individuals)
- `NAM\PPA_PRD_SQL` — SQL service account
- `NAM\PROD_CPP_APAC` — APAC production account

### 2.2 `db_datareader` Membership
`RoleMemberships.sql` (lines 41–88) shows that `B2C`, multiple `emer_*` accounts, and `NAM\PROD_CPP` are members of `db_datareader`. `db_datareader` grants SELECT on ALL tables in the database, including `asymmetric_key_store.private_key_value` and `symmetric_key_store.symmetric_key_value`.

`db_datareader` should not be used for a PII vault database. All access must be through the role-based stored procedure API, with SELECT on individual tables restricted to a minimum necessary set.

### 2.3 `db_datawriter` Membership
`RoleMemberships.sql` (lines 89–131) shows `B2C`, `emer_*` accounts, and others are members of `db_datawriter`. `db_datawriter` grants INSERT/UPDATE/DELETE on ALL tables — including the ability to insert fake key material or corrupt existing keys.

---

## 3. Operational Dependencies

### 3.1 Dependency on EcountCore (via Synonyms)
The four synonyms (`hwniv_SysMembers`, `hwniv_SysObjects`, `hwniv_SysProtects`, `hwniv_SysUsers`) reference the `Ecountcore_Process` database. If `Ecountcore_Process` is unavailable, procedures that reference these synonyms will fail. The operational impact depends on how these synonyms are used — if they are used for access control checks, StrongBox operations could fail during EcountCore maintenance windows.

### 3.2 Platform-Wide Dependency
StrongBox is a **hard dependency for every service** that stores or retrieves PII. If StrongBox is unavailable:
- Enrollment fails (cannot store PII for new cardholders)
- Identity verification fails (cannot retrieve PII for existing cardholders)
- Password reset/account recovery may fail if PII verification is required
- Customer service operations requiring PII access fail

StrongBox has no visible high-availability or disaster recovery configuration in the repository. Any downtime is platform-wide PII service downtime.

---

## 4. Key Operational Risks

### 4.1 No Key Rotation Procedure
There is no stored procedure for key rotation in the repository. Key rotation is a fundamental key management requirement (PCI DSS Req 3.6.4 — periodic cryptographic key rotation). Without a key rotation capability:
- Old keys are never replaced
- Compromised keys cannot be cycled without manual intervention
- If a symmetric key is compromised, the only remediation is to re-encrypt all associated data with a new key — which requires a new procedure

### 4.2 `Results` Table — Potential Key Dump Table
The `dbo.Results` table has the same schema as `asymmetric_key_store` but no PK, constraints, or identity. Its only plausible use is as a staging or debugging table for key operations. If data was ever inserted into this table and not cleaned up, all private key material is exposed in an unprotected, queryable table.

**Operational action required:** Verify in production whether `dbo.Results` contains any rows. If so, truncate immediately after forensic investigation.

### 4.3 SQL Server 2012 Target — Critical
- PCI DSS Requirement 6.3: Apply security patches within defined SLA
- SQL Server 2012 has not received security patches since July 2022
- Any SQL Server 2012 engine vulnerabilities discovered after July 2022 are permanently unpatched in this deployment

### 4.4 No Audit of Key Access
SQL Server 2012 does not support fine-grained column-level audit. If `sb_get_asymmetric_key` is called 1,000 times per day, there is no procedure in this repository to monitor that volume or alert on anomalous key access patterns. Key exfiltration could occur without detection.

---

## 5. Backup and Recovery

### 5.1 Backup Criticality
Loss of the StrongBox database means:
- All PII stored by Onbe is permanently encrypted and unrecoverable (symmetric keys are gone)
- All affected cardholders must be re-enrolled with new PII
- This is a catastrophic compliance and operational failure

The backup strategy for StrongBox must be:
- Full backup: daily minimum
- Transaction log backup: every 15–30 minutes
- Recovery testing: quarterly

None of this is encoded in the repository — it is entirely an operations responsibility.

### 5.2 Backup Security
Backups of StrongBox contain all private keys and encrypted PII. **Backups must be encrypted** using a key not stored in the StrongBox database itself (to avoid the same co-location vulnerability). Backup encryption key management must be independently controlled.

---

## 6. Change Management Gaps

1. **No peer review requirement** for StrongBox changes visible in CI/CD configuration
2. **No security review requirement** for changes to the key management API
3. **No change freeze policy** for this PCI DSS-scoped database
4. Individual emergency accounts (`emer_*`) can make changes directly in production without a pipeline
