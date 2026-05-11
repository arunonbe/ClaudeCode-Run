# Data Architect Report: strongbox-xmlrpc_SVC

## Data Models

The StrongBox vault is backed by a SQL Server database (the `strongbox` database accessed via `spring-dbctx_LIB`'s `appCtx-strongbox-ds.xml`). The data model is inferred from the DAO stored procedure names and their parameter signatures:

**`sb_get_asymmetric_key` (via `SbGetAsymmetricKey.java`)**:

| Parameter | Direction | Type | Content |
|---|---|---|---|
| `name` | IN | String | Key name/identifier |
| `private_key` | OUT | String | RSA private key (plaintext in DB column) |
| `public_key` | OUT | String | RSA public key (plaintext in DB column) |
| `key_id` | OUT | int | Key identifier |

**`sb_get_symmetric_key` (via `SbGetSymmetricKey.java`)**:

| Parameter | Direction | Type | Content |
|---|---|---|---|
| `key_id` | IN | int | Symmetric key ID |
| `key_value` | OUT | String | Symmetric key bytes (plaintext in DB column) |
| `private_key` | OUT | String | Associated RSA private key |
| `public_key` | OUT | String | Associated RSA public key |
| `key_name` | OUT | String | Key name |
| `asymmetric_key_id` | OUT | int | Associated asymmetric key ID |

**Data in the vault database** (from DAO names):
- `sb_insert_data` / `sb_get_data` / `sb_update_data` / `sb_delete_data`: Stored encrypted data blobs with associated key references
- `sb_insert_symmetric_key`: Key insertion/management operations

## Critical Finding: Keys and Ciphertext Co-located in the Same Database

The most significant data architecture finding in this entire codebase:

The `sb_get_symmetric_key` stored procedure returns both `key_value` (the symmetric encryption key) and `private_key` (the RSA private key used to protect the symmetric key) in the same response from the same database. The data blobs encrypted with the symmetric keys are also stored in the same database (via `sb_insert_data`/`sb_get_data`).

This means the vault database contains:
- Encrypted data blobs (ciphertext)
- The symmetric keys that decrypt those blobs
- The RSA private keys that decrypt the symmetric keys

A single SQL query or a database backup contains everything needed to decrypt all vault-stored secrets. This is the opposite of the key management principle that key-encrypting keys must be stored separately from the data they protect (PCI DSS Req 3.6.1, NIST SP 800-57 Section 8.2.3).

## Sensitive Data Storage

The `private_key` and `public_key` fields returned by both stored procedures are typed as `String` — they are stored as string columns in the SQL Server database. RSA private keys stored as plaintext strings in a database column means:
- No column-level encryption
- Keys are visible in database backups
- Keys are visible to any SQL Server user with SELECT permission on the key tables
- Keys are visible in SQL Server query logs and Profiler traces if logging is enabled

The `key_value` (symmetric AES key material) has the same exposure.

## Data Flows

**Encryption path**:
1. Client calls `repositoryServiceWrite(agent, data)` via XML-RPC
2. `RepositoryServiceLibrary.write()` selects a symmetric key from DB (`sb_get_symmetric_key`)
3. Encrypts `data` using the symmetric key (AES or similar)
4. Stores ciphertext in DB (`sb_insert_data`)
5. Returns a reference string encoding the key_id and data_id

**Decryption path**:
1. Client calls `repositoryServiceRead(agent, reference)` via XML-RPC
2. `DataRepositoryReference.getRepositoryReference(reference)` parses the reference
3. `RepositoryServiceLibrary.read()` calls `sb_get_symmetric_key` to get the key
4. Decrypts the ciphertext blob
5. Returns plaintext object

**PGP path** (CryptoService):
1. Client calls `encryptPGP(input)` with key name and plaintext
2. `getPassphrase(passphrase_reference)` calls `repositoryServiceRead` to get the PGP passphrase from vault
3. Passphrase is written into external PGP binary invocation
4. Plaintext is written to a temp file
5. PGP binary is invoked with temp file paths and passphrase
6. Encrypted output is read from output temp file

## Retention Concerns

- Vault-stored data (passphrases, key material) has no visible TTL or rotation policy in the codebase; keys are never deleted unless explicitly via `sb_delete_data`
- RSA key pairs and symmetric keys may remain in the database indefinitely; PCI DSS Requirement 3.6.6 requires periodic key replacement
- Temp files created during PGP operations in `encryptFolderPath` and `decryptFolderPath` are deleted in a `finally` block, but if the JVM crashes between file creation and deletion, plaintext files may persist on the filesystem

## PCI DSS Compliance Assessment

- **Req 3.6.1 (CRITICAL)**: Keys co-located with ciphertext in the same database is a direct violation
- **Req 3.6.3**: Key storage must prevent unauthorised substitution; storing keys as plaintext strings in SQL Server without column encryption violates this
- **Req 3.6.6**: Periodic key replacement procedures; no mechanism visible in codebase
- **Req 8.2**: Access to the key management system must be authenticated; no authentication visible on the StrongBox XML-RPC endpoint
