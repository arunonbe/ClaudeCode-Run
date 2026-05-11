# DS_DB_strongbox — Business Analyst Assessment

## 1. Repository Identity

| Attribute | Value |
|---|---|
| Repository name | DS_DB_strongbox |
| Project name (sqlproj) | StrongBox |
| Solution file | StrongBox.sln |
| SQL Server target | SQL Server 2012 (DSP: Sql110DatabaseSchemaProvider) |
| Build tool | Visual Studio SSDT, MSBuild ToolsVersion 4.0, .NET 4.6.1 |
| Project GUID | bc5ba6d6-f072-4efb-9bb8-0fb78e11cc5e |

---

## 2. Business Purpose

StrongBox is Onbe's **PII encryption vault** — a centralised key management and encrypted data storage database. Its purpose is to store sensitive personally identifiable information (PII) in encrypted form and to provide the cryptographic keys required to decrypt it. Every service in the Onbe platform that needs to store or retrieve PII — SSN, date of birth, driver's licence numbers, and potentially biometric identifiers — interacts with StrongBox.

StrongBox implements a **three-tier key hierarchy**:
1. **Asymmetric key pair** (public/private RSA key) stored in `asymmetric_key_store` — the master key
2. **Symmetric key** (AES key) stored encrypted in `symmetric_key_store`, protected by the asymmetric key name reference
3. **Encrypted data blob** stored in `secure_data_store`, associated with the symmetric key used to encrypt it

The design intent is that:
- The symmetric key encrypts the actual PII data
- The asymmetric key encrypts (or is used to identify) the symmetric key
- A caller must know the asymmetric key name and have the private key to retrieve the symmetric key, which is then used to decrypt the data

**Critical observation:** As detailed in the Data Architect assessment, both the private key and the symmetric key are stored in **the same database as the encrypted data**. This fundamentally undermines the security model — an attacker with database read access can retrieve both the ciphertext and the key material needed to decrypt it.

---

## 3. Business Processes Supported

### 3.1 PII Storage on Enrollment / Account Opening
When a cardholder provides PII (SSN, DOB, driver's licence) during enrollment, the enrollment service (`NAM_PPA_PRD_NROLLSVC`) calls StrongBox to:
1. Insert a new asymmetric key (if not already registered): `sb_insert_asymmetric_key`
2. Store the PII: `sb_insert_key_and_data` — which inserts both a new symmetric key and the encrypted data in a single transaction, returning `symmetric_key_id` and `data_id`

The calling service stores only the `data_id` in its own database; to retrieve the PII, it provides the `data_id` to `sb_get_data`.

### 3.2 PII Retrieval for Verification
When PII needs to be verified (e.g., identity check for password reset, KYC re-verification), authorised services call `sb_get_data(@data_id)`, which returns:
- The encrypted data value (`data_value`)
- The symmetric key (`symmetric_key_value`)
- The private key (`private_key_value`)
- The public key (`public_key_value`)
- The asymmetric key name (`key_name`)

**The stored procedure returns ALL key material alongside the encrypted data in a single query.** The caller is expected to perform the actual decryption client-side.

### 3.3 PII Update
When PII changes (e.g., cardholder updates their SSN or address), `sb_update_data(@data_id, @data_value, @symmetric_key_id)` updates the encrypted value and optionally the symmetric key association.

### 3.4 PII Deletion
`sb_delete_data(@data_id)` removes both the encrypted data record and its associated symmetric key from the database. This supports:
- CCPA right-to-deletion requests
- GDPR Article 17 right to erasure
- Account closure PII purge obligations

The delete operation removes the symmetric key when the data record is deleted — this is a correct cryptographic erasure approach (key deletion renders ciphertext permanently unrecoverable).

### 3.5 Key Management
- `sb_insert_asymmetric_key` — registers a new RSA key pair. Checks for duplicate key names and raises an error if the key already exists.
- `sb_insert_symmetric_key` — inserts a new symmetric key referencing an asymmetric key name
- `sb_get_symmetric_key` — retrieves a symmetric key and its parent asymmetric key details
- `sb_get_asymmetric_key` — retrieves an asymmetric key by name (returns both public AND private key)

---

## 4. Data Stored

| Table | Data | Sensitivity |
|---|---|---|
| `secure_data_store` | `data_value` VARCHAR(8000) — **encrypted PII blobs** | CRITICAL |
| `symmetric_key_store` | `symmetric_key_value` VARCHAR(4000) — **symmetric encryption keys** | CRITICAL |
| `asymmetric_key_store` | `public_key_value` VARCHAR(4000) — RSA public key; `private_key_value` VARCHAR(4000) — **RSA private key** | CRITICAL |
| `Results` | Temporary result table (no PK, appears to mirror `asymmetric_key_store` structure) | CRITICAL — possibly a debugging/diagnostic table |

---

## 5. Regulatory Relevance

### 5.1 PCI DSS — Highest Relevance
StrongBox is directly implicated in **PCI DSS Requirement 3** (Protect Stored Account Data):
- **Req 3.5** — Protect all keys used to secure cardholder data against disclosure and misuse. Keys must be stored in the fewest possible locations. **The current design stores private keys and symmetric keys in the same database as the encrypted data — this violates the spirit of Req 3.5.**
- **Req 3.7** — Ensure that security policies and operational procedures for protecting stored account data are documented, in use, and known to all affected parties.
- **Req 3.6** — Document and implement all key-management procedures including key generation, distribution, storage, access, retirement, and replacement.

### 5.2 GDPR Article 32
"Appropriate technical measures" for protecting personal data include pseudonymisation and encryption. StrongBox provides the encryption layer for PII. However, if the private key is co-located with the encrypted data, the encryption provides minimal protection against a database-level breach.

### 5.3 CCPA
StrongBox's `sb_delete_data` procedure supports the right-to-deletion workflow by cryptographically erasing PII (deleting the key makes the ciphertext permanently unrecoverable). This is a correct implementation of "verifiable consumer request" deletion under CCPA 1798.105.

### 5.4 GLBA
GLBA Safeguards Rule requires financial institutions to implement technical safeguards for customer financial data. StrongBox is Onbe's primary GLBA-relevant PII protection mechanism.

---

## 6. Named Consumers — Breadth of PII Exposure

The `Strongbox_Execute` and `Strongbox_Select` roles include virtually every production service account:
- `NAM_PPA_PRD_APISVC` — main API platform
- `NAM_PPA_PRD_ECORESVC` — core transaction engine
- `NAM_PPA_PRD_CSASVC` — customer service API
- `NAM_PPA_PRD_CZSVC` — client zone
- `NAM_PPA_PRD_ORDERSVC` — order management
- `NAM_PPA_PRD_BMCSVC` — BMC batch/monitoring
- `NAM_PPA_PRD_SCHSVC` — scheduler
- `NAM_PPA_PRD_CSWSVC` — customer service web
- `NAM_PPA_PRD_IVRWSVC` — IVR
- `NAM_PPA_PRD_ECAPSVC` — ECAP
- `NAM_PPA_PRD_NROLLSVC` — enrollment
- `NAM_PPA_PRD_OPSVC` — operations
- `NAM_PPA_PRD_SQL` — SQL service account
- `NAM\PROD_CPP` / `NAM\PROD_CPP_APAC` — production CPP accounts
- Multiple `emer_*` emergency access accounts

The breadth of access means that a compromise of **any** of these 12+ service accounts provides the ability to call `sb_get_data` and retrieve both the encrypted PII and the decryption keys. This broad access is a fundamental security architecture weakness.
