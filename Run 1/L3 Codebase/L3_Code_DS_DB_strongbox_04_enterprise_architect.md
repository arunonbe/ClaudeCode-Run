# DS_DB_strongbox — Enterprise Architect Assessment

## 1. Platform Generation and Role

StrongBox is a **first-generation, custom-built PII encryption vault** implemented entirely within SQL Server. It targets SQL Server 2012 — one of the oldest database targets in the Onbe portfolio. The design dates from what appears to be early in the ECount/Onbe platform lifecycle, before cloud-native key management services (Azure Key Vault, AWS KMS, HashiCorp Vault) were available or widely adopted.

StrongBox occupies the **most critical position** in the Onbe platform architecture: it is the sole custodian of decryption keys for all PII stored across the platform. Every service that stores or retrieves cardholder PII depends on StrongBox.

---

## 2. Architectural Role

```
Every PII-handling service in the platform
           |
           v
      DS_DB_strongbox
      ┌─────────────────────────────────────┐
      │  asymmetric_key_store (RSA keys)    │
      │  symmetric_key_store (AES keys)     │
      │  secure_data_store (ciphertext)     │
      └─────────────────────────────────────┘
           |
           v
    Calling service decrypts PII client-side
```

StrongBox is referenced by `strongbox-lib_LIB`, `strongbox-remote-client_LIB`, and `strongbox-xmlrpc_SVC` repositories (visible in the broader listing), confirming it has:
- A Java/library client (`strongbox-lib_LIB`)
- A remote client library (`strongbox-remote-client_LIB`)
- An XML-RPC service wrapper (`strongbox-xmlrpc_SVC`)

The XML-RPC service pattern suggests this is an early-2000s era SOA design, predating REST APIs.

---

## 3. Critical Dependency Analysis

### 3.1 Services Dependent on StrongBox
Based on the `Strongbox_Execute` role members:
- All 12 major production service accounts have EXECUTE permission
- This means **the entire Onbe platform is dependent on StrongBox availability and correctness**

### 3.2 StrongBox as CDE Component
Because StrongBox stores both encrypted PII and the keys required to decrypt it, it is definitively within the Cardholder Data Environment (CDE) scope for PCI DSS. **Every PCI DSS control applicable to CDE systems applies to StrongBox**, including:
- Network segmentation from non-CDE systems
- Strong access control (Req 7, 8)
- Logging and monitoring (Req 10)
- Penetration testing (Req 11)
- Incident response (Req 12)

### 3.3 StrongBox as Processing System Dependency
The synonyms `hwniv_SysMembers`, `hwniv_SysObjects`, `hwniv_SysProtects`, `hwniv_SysUsers` create a hard dependency on the `Ecountcore_Process` database. The nature of this dependency (system catalog tables) suggests StrongBox may use EcountCore's user/permission system for some form of caller authentication or audit. This cross-database dependency means EcountCore availability affects StrongBox.

---

## 4. Fundamental Design Flaw — Co-location of Keys and Ciphertext

The most critical enterprise architecture finding is that **StrongBox co-locates encryption keys with the data they protect**:

| Problem | Industry Standard | Current StrongBox Design |
|---|---|---|
| Key storage | Keys in a Hardware Security Module (HSM) or separate key management service | Private keys in `asymmetric_key_store` in the same database |
| Key protection | Symmetric keys encrypted (key-wrapped) by HSM-protected master key | Symmetric keys stored as VARCHAR — potentially in plaintext |
| Key access | Access to keys requires separate authentication from access to data | Same database roles access both keys and data |
| Key audit | Separate audit trail for key operations | No separate key access audit |
| Key rotation | Automated by KMS | No rotation procedure exists |

The three-table design appears to implement a key hierarchy (asymmetric wraps symmetric wraps data), but if the symmetric key is stored in plaintext VARCHAR (not RSA-encrypted by the asymmetric key), the hierarchy is illusory.

---

## 5. Modern Architecture Equivalent

In a modern cloud-native architecture, StrongBox would be replaced by:

```
Azure Key Vault (or AWS KMS)
├── Stores RSA private keys in HSM-backed key slots
├── Performs encryption/decryption operations server-side (keys never leave the HSM)
├── Full audit log of every key operation (Azure Monitor / CloudTrail)
├── Role-based access control at the key level
└── Automatic key rotation

Onbe Application Services
├── Send plaintext PII → Key Vault → receive ciphertext
├── Send ciphertext → Key Vault → receive plaintext (no key exposure)
└── Keys are never returned to the calling application
```

The fundamental difference is that Azure Key Vault/AWS KMS **never return key material to the caller** — the calling application sends plaintext (for encryption) or ciphertext (for decryption) and receives the transformed value. The key never leaves the HSM. The current StrongBox design returns the raw key material to the caller, putting key protection entirely in the caller's hands.

---

## 6. Migration Complexity

Migrating StrongBox to Azure Key Vault or AWS KMS is technically achievable but operationally complex:

| Phase | Activity | Complexity |
|---|---|---|
| 1 | Deploy Azure Key Vault / import existing asymmetric keys | High — key import into HSM requires careful handling |
| 2 | Update `strongbox-lib_LIB` to call Key Vault API instead of StrongBox stored procedures | Medium |
| 3 | Re-encrypt all existing PII using Key Vault-managed keys | Very High — all existing records must be decrypted (old design) and re-encrypted (Key Vault) |
| 4 | Update all 12 consuming services to use new library | Medium |
| 5 | Verify and decommission StrongBox | Medium |

The bottleneck is Phase 3 — re-encrypting all existing PII. This requires:
- A migration service with read access to both old StrongBox and new Key Vault
- A controlled window where PII can be transitionally held in plaintext
- Atomic swap of data IDs to prevent service disruption

---

## 7. Technical Debt Summary

| Item | Severity | Notes |
|---|---|---|
| Private keys co-located with ciphertext | Critical | Eliminates cryptographic protection value |
| SQL Server 2012 — EOL | Critical | No security patches |
| `db_datareader` grants bulk key access | Critical | Bypasses stored procedure API controls |
| `db_datawriter` grants key table modification | Critical | Keys can be corrupted or replaced |
| `Results` table — no PK, contains key schema | Critical | Potential key dump artifact |
| No key rotation procedure | High | PCI DSS Req 3.6.4 |
| No CI/CD | High | Unvalidated changes to PII vault |
| XML-RPC service wrapper (legacy) | Medium | Early-2000s SOA pattern |
| EcountCore synonym dependency | Medium | Cross-database coupling |
| No HSM integration | Critical | Keys in SQL tables, not HSM |
