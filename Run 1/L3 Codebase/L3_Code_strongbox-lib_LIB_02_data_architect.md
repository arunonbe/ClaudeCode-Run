# Data Architect View — strongbox-lib_LIB

## Data Stores
| Store | Type | Description |
|-------|------|-------------|
| StrongBox SQL Server | Microsoft SQL Server (JTDS driver) | Dedicated database named `StrongBox`. Stores encrypted symmetric keys, encrypted data blobs, and asymmetric key pairs. |

Test config reveals server `ppamwdcudsql1b1.nam.nsroot.net` (stage) and `ppamwdcdifsql1:2232` (test) — both are hardcoded in `spring.xml` test config.

## Schema / Tables
The DAO calls the following stored procedures, which imply these tables/objects:

| Stored Procedure | Implied Table/Entity | Key Columns |
|-----------------|---------------------|-------------|
| `sb_get_data` | Data table | `data_id`, `data_value` (encrypted blob), `symmetric_key`, `symmetric_key_id`, `private_key`, `public_key`, `key_name`, `asymmetric_key_id` |
| `sb_get_asymmetric_key` | Asymmetric key table | `key_name`, public/private key blobs |
| `sb_insert_symmetric_key` | Symmetric key table | Encrypted symmetric key blob, asymmetric key reference |
| `sb_insert_data` | Data table | Encrypted data blob, symmetric key reference |

Full DDL is not present in this repository; the stored procedures are defined on the SQL Server directly.

## Sensitive Data Classification
| Data | Classification | PCI DSS Scope | GLBA Scope |
|------|---------------|---------------|------------|
| SSN | PII / Sensitive Personal Information | Indirectly (cardholder PII) | Yes |
| Date of Birth | PII | Indirectly | Yes |
| Bank Account Numbers | Financial account data | Yes (SAD-adjacent for ACH) | Yes |
| RSA Private Keys | Cryptographic key material | PCI DSS Req 3.5 | — |
| AES/DESede Symmetric Keys | Cryptographic key material (encrypted at rest) | PCI DSS Req 3.5 | — |

Per README: "An application used to store sensitive cardholder information (SSN, Date of Birth, Bank accounts)."

## Encryption
| Layer | Algorithm | Mode | Padding | Version |
|-------|-----------|------|---------|---------|
| Asymmetric (key encryption) | RSA | ECB | NoPadding | V1 |
| Symmetric (data encryption) | DESede (3DES) | CBC | PKCS5Padding | V1 |
| Asymmetric (key encryption) | RSA | ECB | NoPadding | V2 |
| Symmetric (data encryption) | AES | CBC | PKCS5Padding | V2 (128-bit) |

Key storage encoding: V1 uses hex; V2 uses Base64.

The MASTER RSA key pair is stored in the StrongBox SQL database itself. There is no evidence of an HSM or external key management system (KMS).

## Data Flow
```
Caller (ECount Core / Job Service / Repo Service)
    |
    | [Object to encrypt]
    v
StrongBoxXMLRPCClient (or direct RepositoryService)
    |
    | [XML-RPC HTTP]
    v
RepositoryService (strongbox-impl)
    |
    +-- Load MASTER RSA key (from DB, cached in-process HashMap)
    +-- Generate random symmetric key
    +-- Encrypt sym key with RSA MASTER
    +-- Encrypt data with sym key
    +-- Store sym key + data in StrongBox SQL Server
    |
    | [Returns opaque reference token]
    v
Caller stores reference token (not the data)
```

## Data Quality and Retention
- No retention policy is defined in the code.
- No purge/delete stored procedure is visible in the implemented DAO (`SbDeleteData` class exists but is not wired in `StrongBoxJDBCDAOImpl`).
- No audit logging of access to decrypted data is observed (only exception logging).

## Compliance Gaps
| Gap | Standard | Severity |
|-----|----------|----------|
| RSA private key stored in the same SQL database as encrypted data — no separation of key custodianship | PCI DSS Req 3.5.1 | Critical |
| DESede (3DES) is deprecated by NIST (SP 800-131A Rev.2) and disallowed in PCI DSS v4.0 for new implementations | PCI DSS Req 3.6 | High |
| RSA/ECB/NoPadding is cryptographically insecure (no semantic security, vulnerable to chosen-ciphertext attack) | PCI DSS Req 3.6 | High |
| AES-128 CBC without authenticated encryption (no AEAD / GCM mode) — susceptible to padding oracle if not protected at transport layer | PCI DSS Req 3.6 | Medium |
| No key rotation mechanism observed in code | PCI DSS Req 3.6.1 | High |
| No delete/purge capability wired in production DAO | Data minimisation (GLBA/GDPR) | Medium |
| Hardcoded test credentials in `spring.xml` (`b2cstage`/`b2cstage`, `[REDACTED — rotate immediately]`/`[REDACTED — rotate immediately]`) | PCI DSS Req 8 | High (test scope) |
