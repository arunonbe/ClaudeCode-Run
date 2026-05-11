# DS_DB_strongbox — Solution Architect Assessment

## 1. Critical Security and Compliance Findings

### 1.1 P0 CRITICAL: RSA Private Key Co-located with Protected Ciphertext

**Finding:** `dbo/Tables/asymmetric_key_store.sql` stores `private_key_value VARCHAR(4000)` in the same database as `dbo/Tables/secure_data_store.sql` which stores `data_value VARCHAR(8000)` (encrypted PII). The `sb_get_data` stored procedure (`dbo/Stored Procedures/sb_get_data.sql`, lines 12–21) returns both the ciphertext and the private key in a single result set.

**Regulatory Basis:**
- PCI DSS v4.0.1 Requirement 3.7.1: "Key-management procedures and processes for cryptographic keys include generation of strong keys." The intent of Req 3.7 is that keys protect data — co-location eliminates this protection entirely.
- PCI DSS Req 3.5.1: "Primary account numbers (PAN) must be secured with strong cryptography." If the private key is co-located with the encrypted PII, the effective protection is limited to SQL Server access controls alone — not cryptographic controls.
- NIST SP 800-57 Part 1 Rev 5, Section 8.1: "Cryptographic keys shall be protected against unauthorized disclosure." Co-location in a shared database undermines this requirement.
- GLBA Safeguards Rule (16 CFR 314): Requires administrative, technical, and physical safeguards for customer financial information. Storing encryption keys alongside the data they protect fails this standard.

**Impact:** Any SQL Server account with `db_datareader` membership, `Strongbox_Select` role membership, or `Strongbox_Execute` role membership can retrieve all private keys and decrypt all PII stored in Onbe's platform. The cryptographic protection layer provides no additional security beyond SQL Server login controls.

**Remediation (Priority: P0 — Immediate Action Required):**
1. Engage Security and Compliance immediately to assess current breach risk posture.
2. Long-term: migrate key management to Azure Key Vault (HSM-backed), where private keys never leave the HSM.
3. Short-term (prior to migration): restrict `db_datareader` and `db_datawriter` to service accounts strictly requiring bulk access; audit and remove any accounts that do not require table-level access.
4. Initiate a Phase 3-level re-encryption plan (see Enterprise Architect Assessment §6) under the supervision of Compliance and Security.

---

### 1.2 P0 CRITICAL: `db_datareader` / `db_datawriter` Bypasses Stored Procedure API

**Finding:** `Security/RoleMemberships.sql` (lines 41–131) shows that `B2C`, multiple `emer_*` emergency accounts, and `NAM\PROD_CPP` are members of `db_datareader` and `db_datawriter`. These fixed database roles grant SELECT / INSERT / UPDATE / DELETE on ALL tables, including `asymmetric_key_store.private_key_value` and `symmetric_key_store.symmetric_key_value`, without going through the stored procedure API (`sb_get_data`, `sb_get_asymmetric_key`).

**Impact:**
- `db_datareader` members can execute `SELECT * FROM asymmetric_key_store` and retrieve all private key material in bulk — a complete key exfiltration in a single query.
- `db_datawriter` members can INSERT, UPDATE, or DELETE rows in `asymmetric_key_store` and `symmetric_key_store` — they can replace legitimate private keys with attacker-controlled keys, effectively taking ownership of all future PII decryption.
- The access control model of the stored procedure API (returning only the key for a specific `data_id`) is entirely bypassed.

**Remediation (Priority: P0):**
1. Remove all service accounts and individual accounts from `db_datareader` and `db_datawriter` immediately.
2. Replace with minimum-necessary role-based permissions using the defined `Strongbox_Execute`, `Strongbox_Select`, `Strongbox_Update`, and `Strongbox_Delete` roles.
3. For the `emer_*` emergency accounts: implement a break-glass access procedure where elevated access requires a documented, time-limited approval workflow. Permanent `db_datareader` membership for 8 individuals is inconsistent with PCI DSS Req 7 (least privilege).

---

### 1.3 P0 CRITICAL: `Results` Table — Potential Key Dump Artifact in Production Schema

**Finding:** `dbo/Tables/Results.sql` defines a table with the exact column structure of `asymmetric_key_store` (`public_key_value VARCHAR(4000)`, `private_key_value VARCHAR(4000)`, `key_name VARCHAR(50)`, `key_id INT`) but with no primary key, no constraints, and no IDENTITY column. This is consistent with a table created to receive ad-hoc `INSERT INTO Results SELECT * FROM asymmetric_key_store` debugging operations.

**Impact:**
- If any such operation was ever performed in production and not cleaned up, all private keys are accessible in an unprotected, unconstrained table queryable by any account with table-level access.
- Even if currently empty, the presence of this table in the production schema represents an ongoing latent risk — any account that can execute ad-hoc SQL against StrongBox could dump all private keys into `Results` without triggering stored procedure-level audit.

**Remediation (Priority: P0):**
1. Immediately verify whether `dbo.Results` contains any rows in production: `SELECT COUNT(*) FROM dbo.Results;`
2. If rows exist: initiate a security incident — treat all affected private keys as compromised, assess the blast radius (which PII records were protected by those keys), notify Compliance and Legal.
3. Drop the `dbo.Results` table from the production database: `DROP TABLE dbo.Results;`
4. Update the SSDT project to remove `Results.sql` and deploy the schema change through a controlled change management process.

---

### 1.4 P0 CRITICAL: SQL Server 2012 — End-of-Life, No Security Patches

**Finding:** `StrongBox.sqlproj` targets `DSP: Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` (SQL Server 2012). SQL Server 2012 reached end of extended support in July 2022. No security patches have been issued for SQL Server 2012 engine vulnerabilities discovered after that date.

**Regulatory Basis:**
- PCI DSS v4.0.1 Requirement 6.3.3: "All system components are protected from known vulnerabilities by installing applicable security patches/updates." SQL Server 2012 cannot satisfy this requirement.
- PCI DSS Req 6.2.4: "Software-development practices prevent common vulnerabilities." Using an unpatched database engine for the PII vault is a systemic vulnerability.

**Specific Missing Security Features (available in SQL Server 2016+):**
- Dynamic Data Masking (SQL 2016): Would mask key column values in query results for non-privileged roles.
- Row-Level Security (SQL 2016): Would enforce per-row access policies without stored procedure API changes.
- Always Encrypted (SQL 2016): Would allow column-level encryption with key management outside the database engine.
- Temporal Tables (SQL 2016): Would provide built-in audit history for key record changes.

**Remediation (Priority: P0):**
1. Submit a JIRA/change request to upgrade the StrongBox database to SQL Server 2019 or 2022 as a minimum step.
2. Plan in parallel with the Azure Key Vault migration — if migration is underway, the SQL Server upgrade becomes less critical, but the EOL engine must not persist through the next PCI DSS assessment cycle.
3. Engage the Security team to document compensating controls (firewall isolation, monitoring) while the upgrade is pending, for PCI DSS QSA review.

---

### 1.5 P1 HIGH: No Key Rotation Procedure

**Finding:** The stored procedure inventory (9 procedures total) contains no key rotation procedure. There is no `sb_rotate_key`, `sb_retire_key`, or equivalent. The only relevant operation is `sb_delete_data` which deletes the symmetric key along with the data — this is cryptographic erasure, not key rotation.

**Regulatory Basis:**
- PCI DSS v4.0.1 Requirement 3.7.4: "Cryptographic keys are changed after defined use-period and whenever there is reason to believe or know that a key was or may have been compromised." Without a rotation procedure, neither scheduled rotation nor emergency rotation is operationally feasible.
- NIST SP 800-57 Part 1 Rev 5 recommends cryptoperiods of 1–2 years for symmetric keys protecting sensitive data.

**Impact:** Keys generated when StrongBox was first deployed — potentially 10+ years ago — may still be in active use. If any key was compromised at any point in the past, there is no mechanism to detect the compromise (no key access audit) or remediate it (no key rotation).

**Remediation (Priority: P1):**
1. Design and implement `sb_rotate_symmetric_key(@old_key_id, @new_key_value)` — re-encrypts all `secure_data_store` records associated with the old key under the new key.
2. Design and implement `sb_rotate_asymmetric_key(@old_key_name, @new_public_key, @new_private_key)` — re-wraps all symmetric keys associated with the old asymmetric key under the new asymmetric key pair.
3. Document the key rotation schedule and assign operational ownership to the Security team.

---

### 1.6 P1 HIGH: No HSM Integration — Keys in SQL Tables

**Finding:** StrongBox does not use SQL Server's built-in Extensible Key Management (EKM) or any Hardware Security Module (HSM) integration. All key material is stored as VARCHAR strings in SQL tables — effectively plaintext (base64-encoded at best).

**Comparison:**
| Capability | StrongBox (Current) | Azure Key Vault HSM |
|---|---|---|
| Key storage location | SQL table VARCHAR column | HSM-backed key slot |
| Private key exportable | Yes — returned by stored procedures | No — keys never leave HSM |
| Key access audit | SQL Server general audit only | Full audit log per key operation |
| Key rotation | No procedure | Automated or on-demand |
| Key destruction | DELETE row | Cryptographic destruction in HSM |
| FIPS 140-2 Level 3 | No | Yes (Premium SKU) |

**Remediation (Priority: P1, with P0 urgency if co-location fix is deprioritised):**
1. Provision an Azure Key Vault Premium tier instance (FIPS 140-2 Level 3 HSM-backed).
2. Import existing asymmetric keys into Azure Key Vault using the HSM-protected key import process (BYOK — Bring Your Own Key), following Azure Key Vault BYOK documentation.
3. Update `strongbox-lib_LIB` to use Azure Key Vault SDK for all encryption/decryption operations.

---

## 2. All Database Objects — Complete Inventory

### 2.1 Tables

| Table | Columns | Sensitivity | Notes |
|---|---|---|---|
| `dbo.secure_data_store` | `data_value_id` INT IDENTITY, `data_value` VARCHAR(8000), `symmetric_key_id` INT | CRITICAL | Encrypted PII; no FK constraint on `symmetric_key_id` |
| `dbo.symmetric_key_store` | `asymmetric_key_name` VARCHAR(50), `symmetric_key_id` INT IDENTITY, `symmetric_key_value` VARCHAR(4000) | CRITICAL | AES key stored as plain VARCHAR |
| `dbo.asymmetric_key_store` | `public_key_value` VARCHAR(4000), `private_key_value` VARCHAR(4000), `key_name` VARCHAR(50), `key_id` INT IDENTITY | CRITICAL | RSA private key in plaintext |
| `dbo.Results` | `public_key_value` VARCHAR(4000), `private_key_value` VARCHAR(4000), `key_name` VARCHAR(50), `key_id` INT | CRITICAL | No PK, no constraints — potential key dump artifact |

### 2.2 Stored Procedures

| Procedure | Purpose | Security Risk |
|---|---|---|
| `sb_get_data` | Retrieve encrypted data + ALL key material | Returns private key in single call — P0 |
| `sb_insert_data` | Insert encrypted data blob | Requires pre-existing symmetric_key_id |
| `sb_update_data` | Update encrypted data value | No key rotation performed |
| `sb_delete_data` | Delete data + symmetric key | Correct cryptographic erasure |
| `sb_get_symmetric_key` | Retrieve symmetric key + parent asymmetric key | Returns private key |
| `sb_get_asymmetric_key` | Retrieve asymmetric key pair by name | Returns private key as output parameter |
| `sb_insert_symmetric_key` | Insert new symmetric key | |
| `sb_insert_asymmetric_key` | Insert new asymmetric key pair | Duplicate name check |
| `sb_insert_key_and_data` | Insert symmetric key + data atomically | Correct atomic insert design |

### 2.3 Synonyms

| Synonym | Target | Risk |
|---|---|---|
| `hwniv_SysMembers` | `Ecountcore_Process.dbo.sysmembers` | Cross-database coupling; EcountCore outage affects StrongBox |
| `hwniv_SysObjects` | `Ecountcore_Process.dbo.sysobjects` | Legacy dependency |
| `hwniv_SysProtects` | `Ecountcore_Process.dbo.sysprotects` | Legacy dependency |
| `hwniv_SysUsers` | `Ecountcore_Process.dbo.sysusers` | Legacy dependency |

### 2.4 Security Roles

| Role | Permissions | Members |
|---|---|---|
| `Strongbox_Execute` | EXECUTE on all stored procedures | 12 production service accounts + 8 emer_* + PROD_CPP |
| `Strongbox_Select` | SELECT on all tables | Same set — allows bulk key table reads |
| `Strongbox_Update` | UPDATE on tables | Subset |
| `Strongbox_Delete` | DELETE on tables | Subset |
| `Strongbox_Schema_View` | VIEW DEFINITION | Subset |
| `db_datareader` | SELECT on ALL tables | B2C, emer_*, NAM\PROD_CPP — CRITICAL |
| `db_datawriter` | INSERT/UPDATE/DELETE on ALL tables | B2C, emer_*, others — CRITICAL |

---

## 3. Remediation Priority Table

| Priority | Finding | Effort | Regulation |
|---|---|---|---|
| P0 | Remove `db_datareader` / `db_datawriter` from all accounts | Low (hours) | PCI DSS Req 7 |
| P0 | Audit `dbo.Results` for rows; drop table if empty; incident if populated | Low | PCI DSS Req 3.7 |
| P0 | Restrict `Strongbox_Select` to minimum necessary accounts | Low | PCI DSS Req 7.2 |
| P0 | Begin Azure Key Vault migration planning (Phase 1–5) | Very High | PCI DSS Req 3.7 |
| P0 | Upgrade SQL Server 2012 or document compensating controls | Medium | PCI DSS Req 6.3.3 |
| P1 | Implement key rotation procedures | Medium | PCI DSS Req 3.7.4 |
| P1 | Implement HSM/Azure Key Vault integration | Very High | PCI DSS Req 3.7.1 |
| P1 | Implement CI/CD pipeline for StrongBox changes | Medium | PCI DSS Req 6 |
| P1 | Remove EcountCore synonym dependencies | Low | Operational risk |
| P1 | Add FK constraint between secure_data_store and symmetric_key_store | Low | Data integrity |
| P2 | Add index on secure_data_store(symmetric_key_id) | Low | Performance |
| P2 | Replace `Results` staging pattern with temp table pattern | Low | Security hygiene |
| P2 | Implement fine-grained key access audit logging | Medium | PCI DSS Req 10 |

---

## 4. Compliance Gap Summary

| Regulation | Requirement | Gap | Severity |
|---|---|---|---|
| PCI DSS v4.0.1 Req 3.5.1 | Strong cryptography for PAN/PII | Private key co-located with ciphertext — cryptographic isolation does not exist | Critical |
| PCI DSS v4.0.1 Req 3.7.1 | Key generation procedures | No documented key generation, no HSM | Critical |
| PCI DSS v4.0.1 Req 3.7.4 | Key rotation per defined schedule | No key rotation procedure exists | High |
| PCI DSS v4.0.1 Req 6.3.3 | Security patches applied | SQL Server 2012 EOL since July 2022 | Critical |
| PCI DSS v4.0.1 Req 7.2 | Least-privilege access | db_datareader/db_datawriter granted broadly | Critical |
| PCI DSS v4.0.1 Req 10.2 | Audit logs for key access | No column-level audit on key tables | High |
| GDPR Art 32 | Appropriate technical measures | Key co-location eliminates encryption protection | High |
| GLBA Safeguards Rule | Technical safeguards for financial data | Keys accessible alongside protected PII | High |
| NIST SP 800-57 | Cryptographic key management | No HSM, no rotation, no cryptoperiod enforcement | High |

---

## 5. Azure Key Vault Migration — Recommended Architecture

### 5.1 Target State

```
Azure Key Vault (Premium HSM-backed)
├── RSA-4096 private keys stored in HSM key slots
├── Keys never exported to calling application
├── All encrypt/decrypt operations performed server-side in HSM
├── RBAC: per-service-account, per-key permissions
├── Audit: every key operation logged to Azure Monitor
└── Key rotation: automated annual rotation configured

strongbox-lib_LIB (updated)
├── Calls Azure Key Vault SDK for encrypt/decrypt
├── Passes plaintext PII → Key Vault → receives ciphertext
├── Passes ciphertext → Key Vault → receives plaintext
└── Key material never returned to or stored by the library

DS_DB_strongbox (residual, simplified)
├── secure_data_store: retains ciphertext + key_id reference
│   (key_id now refers to Azure Key Vault key name, not local table)
├── asymmetric_key_store: DECOMMISSIONED (keys in Key Vault)
├── symmetric_key_store: DECOMMISSIONED (Key Vault handles key wrapping)
└── Results: DROPPED
```

### 5.2 Migration Phases

| Phase | Activity | Complexity | Owner |
|---|---|---|---|
| 1 | Provision Azure Key Vault Premium; BYOK import of existing RSA keys | High | Security + Cloud Ops |
| 2 | Update `strongbox-lib_LIB` to call Key Vault API | Medium | Platform Engineering |
| 3 | Re-encrypt all `secure_data_store` records: decrypt with old key, re-encrypt with Key Vault | Very High | Security + DBA |
| 4 | Update all 12 consuming services to use updated library | Medium | Platform Engineering |
| 5 | Audit, verify, and decommission `asymmetric_key_store` and `symmetric_key_store` | Medium | DBA + Security |

Phase 3 requires a controlled migration window. All existing ciphertext must be decrypted using the old private key (from `asymmetric_key_store`) and re-encrypted using Azure Key Vault. During this window, plaintext PII is transiently held in the migration service's process memory — this window must be carefully controlled and audited.

### 5.3 Compensating Controls During Migration

Until the Azure Key Vault migration is complete, the following compensating controls should be implemented and documented for PCI DSS QSA review:
1. Network isolation: StrongBox SQL Server instance must be in a dedicated network segment accessible only to the 12 named production service accounts — not accessible from developer or support networks.
2. FortiDB or SQL Server Audit extended events: enable audit of all SELECT operations against `asymmetric_key_store` and `symmetric_key_store`.
3. `db_datareader` / `db_datawriter` removal: this is not a compensating control — it is a mandatory immediate remediation.
4. Alert on anomalous key access volume: baseline normal `sb_get_asymmetric_key` and `sb_get_symmetric_key` call volumes; alert if call count exceeds 3x baseline within any 1-hour window.
