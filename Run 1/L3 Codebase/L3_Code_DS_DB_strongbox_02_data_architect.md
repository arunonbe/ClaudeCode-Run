# DS_DB_strongbox — Data Architect Assessment

## 1. Schema Architecture

StrongBox uses a single `dbo` schema with a minimal object set — 4 tables, 9 stored procedures, 4 synonyms, and a security layer. This simplicity is by design: the database is a **dedicated PII vault** with a narrow, well-defined API surface.

---

## 2. Complete Table Inventory

### 2.1 `dbo.secure_data_store`
File: `dbo/Tables/secure_data_store.sql`

```sql
CREATE TABLE [dbo].[secure_data_store] (
    [data_value_id]    INT            IDENTITY (1, 1) NOT NULL,  -- surrogate PK
    [data_value]       VARCHAR (8000) NOT NULL,                   -- encrypted PII blob
    [symmetric_key_id] INT            NOT NULL,                   -- FK to symmetric_key_store
    CONSTRAINT [PK_secure_data_store] PRIMARY KEY NONCLUSTERED ([data_value_id] ASC) WITH (FILLFACTOR = 90)
);
```

**Critical fields:**
- `data_value` — VARCHAR(8000) storing the encrypted PII payload. The maximum 8000-character size accommodates base64-encoded encrypted data. The column type is VARCHAR (not VARBINARY), meaning the ciphertext is stored as a character string. This implies the encryption output is base64-encoded before storage.
- `symmetric_key_id` — references the symmetric key used to encrypt this specific data blob. The key is in the same database.

**No foreign key constraint** is defined between `secure_data_store.symmetric_key_id` and `symmetric_key_store.symmetric_key_id`. This is a referential integrity gap — orphaned data records or orphaned key records are possible.

**No indexes beyond the PK** — queries by `symmetric_key_id` require a full table scan.

---

### 2.2 `dbo.symmetric_key_store`
File: `dbo/Tables/symmetric_key_store.sql`

```sql
CREATE TABLE [dbo].[symmetric_key_store] (
    [asymmetric_key_name] VARCHAR (50)   NOT NULL,  -- FK (by name) to asymmetric_key_store
    [symmetric_key_id]    INT            IDENTITY (1, 1) NOT NULL,  -- surrogate PK
    [symmetric_key_value] VARCHAR (4000) NOT NULL,   -- the symmetric (AES) key material
    CONSTRAINT [PK_symmetric_key_store] PRIMARY KEY NONCLUSTERED ([symmetric_key_id] ASC) WITH (FILLFACTOR = 90)
);
```

**Critical fields:**
- `symmetric_key_value` — VARCHAR(4000) storing the **symmetric encryption key in plaintext VARCHAR**. This is the key used to encrypt/decrypt the PII in `secure_data_store`. If this field contains the actual AES key bytes (base64-encoded), then the key is stored **unencrypted** in the database alongside the data it protects.
- `asymmetric_key_name` — a VARCHAR reference (not a proper FK) to `asymmetric_key_store.key_name`. This is the conceptual "parent" key — the asymmetric key that is supposed to protect the symmetric key.

**Critical observation:** The `symmetric_key_value` is stored as a plain VARCHAR. There is no evidence that the symmetric key is itself encrypted (wrapped) using the asymmetric key. If the symmetric key is stored unencrypted in this table, then the three-tier key hierarchy provides no cryptographic isolation — the symmetric key is just as readable as the data it protects.

---

### 2.3 `dbo.asymmetric_key_store`
File: `dbo/Tables/asymmetric_key_store.sql`

```sql
CREATE TABLE [dbo].[asymmetric_key_store] (
    [public_key_value]  VARCHAR (4000) NOT NULL,   -- RSA public key
    [private_key_value] VARCHAR (4000) NOT NULL,   -- RSA private key
    [key_name]          VARCHAR (50)   NOT NULL,   -- key identifier
    [key_id]            INT            IDENTITY (1, 1) NOT NULL,
    CONSTRAINT [PK_asymmetric_key_store] PRIMARY KEY NONCLUSTERED ([key_name] ASC) WITH (FILLFACTOR = 90),
    CONSTRAINT [IX_asymmetric_key_store] UNIQUE NONCLUSTERED ([key_name] ASC) WITH (FILLFACTOR = 90)
);
```

**CRITICAL FINDING:** **Both the public key and the private key of the RSA key pair are stored in the same table, in the same database, in plaintext VARCHAR columns.**

- `private_key_value` — VARCHAR(4000) — the RSA private key stored in plaintext (base64-encoded PEM or DER format)
- `public_key_value` — VARCHAR(4000) — the RSA public key

Storing the private key in the same database as the data it is designed to protect completely eliminates the security benefit of asymmetric encryption. The private key is required to decrypt; its presence in the database means **anyone with database read access can decrypt all PII stored in StrongBox**.

---

### 2.4 `dbo.Results`
File: `dbo/Tables/Results.sql`

```sql
CREATE TABLE [dbo].[Results] (
    [public_key_value]  VARCHAR (4000) NOT NULL,
    [private_key_value] VARCHAR (4000) NOT NULL,
    [key_name]          VARCHAR (50)   NOT NULL,
    [key_id]            INT            NOT NULL
);
```

The `Results` table mirrors the `asymmetric_key_store` schema but has **no primary key, no constraints, and no identity column**. It appears to be a **temporary or diagnostic table** used for ad-hoc operations (e.g., `INSERT INTO Results SELECT * FROM asymmetric_key_store`). The presence of this table in the production schema is a significant concern:
- It may have been used to dump all private keys for debugging purposes
- If data was ever inserted and not cleaned up, all private keys are accessible in an unprotected, unconstrained table
- This table should be audited for data in production and dropped if empty

---

## 3. Complete Stored Procedure Inventory

| Procedure | File | Purpose | Security Notes |
|---|---|---|---|
| `sb_get_data` | `sb_get_data.sql` | Retrieve encrypted data + ALL key material | **Returns private key in output** |
| `sb_insert_data` | `sb_insert_data.sql` | Insert encrypted data blob | Requires pre-existing symmetric_key_id |
| `sb_update_data` | `sb_update_data.sql` | Update encrypted data value | No key rotation — updates data only |
| `sb_delete_data` | `sb_delete_data.sql` | Delete data + associated symmetric key | Correct cryptographic erasure |
| `sb_get_symmetric_key` | `sb_get_symmetric_key.sql` | Retrieve symmetric key + parent asymmetric key | Returns private key |
| `sb_get_asymmetric_key` | `sb_get_asymmetric_key.sql` | Retrieve asymmetric key pair by name | **Returns private key as output parameter** |
| `sb_insert_symmetric_key` | `sb_insert_symmetric_key.sql` | Insert new symmetric key | |
| `sb_insert_asymmetric_key` | `sb_insert_asymmetric_key.sql` | Insert new asymmetric key pair | Checks for duplicate name |
| `sb_insert_key_and_data` | `sb_insert_key_and_data.sql` | Insert symmetric key + data in one transaction | Atomic insert |

---

## 4. Synonyms

| Synonym | Points To | Purpose |
|---|---|---|
| `hwniv_SysMembers` | `Ecountcore_Process.dbo.sysmembers` | Reference to EcountCore system membership table |
| `hwniv_SysObjects` | `Ecountcore_Process.dbo.sysobjects` | Reference to EcountCore system objects |
| `hwniv_SysProtects` | `Ecountcore_Process.dbo.sysprotects` | Reference to EcountCore security protections |
| `hwniv_SysUsers` | `Ecountcore_Process.dbo.sysusers` | Reference to EcountCore system users |

These synonyms reference the `Ecountcore_Process` database's system catalog tables (`sysmembers`, `sysobjects`, `sysprotects`, `sysusers`). The `hwniv_` prefix may indicate a historical Havelin (a legacy company) integration. The purpose of accessing the EcountCore system catalog from StrongBox is unclear and requires investigation — it may be used for permission checking or may be a legacy artifact.

---

## 5. Key Management Architecture Analysis

### 5.1 Designed Architecture
The intended three-tier key hierarchy:
```
[RSA Private Key] --> [wrapped Symmetric Key] --> [encrypted PII data]
```

### 5.2 Actual Architecture (as Implemented)
Based on code inspection:
```
[RSA Private Key stored in asymmetric_key_store VARCHAR]
[Symmetric Key stored in symmetric_key_store VARCHAR]  
[Encrypted PII stored in secure_data_store VARCHAR]
All three in the SAME database, all readable by SAME roles
```

The `symmetric_key_value` in `symmetric_key_store` is stored as VARCHAR(4000). If this value is an unencrypted (plain or base64) AES key rather than an RSA-wrapped (encrypted) key, then:
- The symmetric key is not protected by the asymmetric key
- The asymmetric key hierarchy is not actually used for key protection
- The `asymmetric_key_name` in `symmetric_key_store` is just a label/grouping field, not a cryptographic protection mechanism

The actual encryption/decryption is performed **outside** the database by the calling service. The database stores all inputs (ciphertext + keys) and returns them via `sb_get_data`. The encryption algorithm, mode, padding, and IV handling are entirely in the client application — **not verifiable from this repository**.

---

## 6. Database-Level vs. Application-Level Encryption

StrongBox does NOT use SQL Server's built-in encryption features:
- No `CREATE SYMMETRIC KEY ... WITH ALGORITHM = AES_256` (SQL Server TDE or CLE)
- No `CREATE ASYMMETRIC KEY` (SQL Server asymmetric key objects)
- No `CREATE CERTIFICATE` (SQL Server certificates)
- No `OPEN SYMMETRIC KEY ... DECRYPTBYASYMKEY`

All encryption is application-level — the database is a plain key-value store for opaque character strings. SQL Server has no knowledge that the `data_value` column contains ciphertext or that `symmetric_key_value` contains key material. This means:
- SQL Server's built-in key management features (key hierarchy, automatic key rotation, HSM integration via Extensible Key Management) are unused
- There is no SQL Server audit of key retrieval operations beyond the general stored procedure execution audit
- The `Results` table with raw key material is accessible via a simple SELECT

---

## 7. `sb_get_data` — Full Key Material Exposure

`dbo/Stored Procedures/sb_get_data.sql`, lines 12–21:

```sql
SELECT @data_value = d.data_value, 
 @symmetric_key = s.symmetric_key_value, @symmetric_key_id = s.symmetric_key_id,
 @private_key = a.private_key_value, @public_key = a.public_key_value,
 @key_name = a.key_name, @asymmetric_key_id = a.key_id
FROM secure_data_store d, symmetric_key_store s, asymmetric_key_store a
WHERE (d.data_value_id = @data_id) AND 
 (d.symmetric_key_id = s.symmetric_key_id) AND
 (s.asymmetric_key_name = a.key_name)
```

A single stored procedure call returns: the encrypted data, the symmetric key, the symmetric key ID, the private RSA key, the public RSA key, the key name, and the asymmetric key ID. **All material required to decrypt the PII is returned in a single procedure call to any caller with `Strongbox_Execute` role membership.**
