# Data Architect View — xplatform-library_LIB

## Data Stores
| Store | Type | Access | Notes |
|---|---|---|---|
| INI-style config files | Flat file | `ConfigurationFile` parser | Read from filesystem; used for platform configuration |
| RPC-based config (Director) | Remote service | `ConfigDB` / RPC client | Configuration values fetched via custom RPC; results cached locally |
| SwarmCache (JGroups) | In-memory distributed | `CacheManager` / `SwarmCache` | Cluster-aware object cache; no persistent store |
| StrongBox data repositories | Abstracted (SPI) | `DataRepository` / `DataRepositoryConnection` | Secure encrypted data store; implementation-defined (JDBC-backed by default) |
| Log files / encrypted log store | File / encrypted file | `FastFile`, `EncryptedStoreDestination` | Log output; encrypted destination available |
| JDBC databases (generic) | Relational (SQL Server) | `JdbcConnection`, `JdbcStoredProc` | JDBC wrappers used by calling code for any relational database |

## Schema
This is a utility library; it does not own a database schema. It provides the JDBC and stored procedure infrastructure that consuming code uses to interact with the eCount Core Database and JobSvc Database (schema owned by xplatform_LIB consumers).

## Sensitive Data
| Data Element | Classification | Location |
|---|---|---|
| Encryption keys (symmetric, asymmetric) | Credentials / crypto material | `StrongBox` SPI; `CryptoKey` / `CryptoKeyPair` objects in memory |
| Plaintext data passed to cipher operations | Potentially CHD / PII | `CryptoCipher.encrypt/decrypt` parameters — transient in-memory |
| Log content | Potentially CHD / PII | `SystemLog` / `Logger` — log entries may contain sensitive fields depending on caller |
| SMTP credentials (if used) | Credentials | `EmailDestination` / `SimpleMailer` — SMTP auth not directly visible |
| Symmetric key material in RPC | Credentials | `rpcConnection`, `rpcHttpMapXmlClient` — key material may transit custom RPC |

## Encryption
- **Symmetric algorithms provided:** DES, 3DES (TripleDES/DES3), DESX, RC2, RC4, RC5, Twofish — implementations in `com.cbase.pi.encryption.symmetric.*`
- **Asymmetric algorithms provided:** RSA (`RsaCipher`, `RsaKey`) with block cipher variants; DSA signing
- **Hashing:** MD5 (`com.cbase.pi.encryption.hashes.MD5`), SHA1 (`SHA1`) — both weak by modern standards
- **Key agreement:** Diffie-Hellman (`DiffieHellmanKeyAgreement`)
- **Jsafe SDK wrapper:** `JsafeCipher` / `JsafeKey` — wraps the RSA Data Security Jsafe commercial library
- **IVs:** `CryptoIV` class; `DESedeFactory.generateInitializationVector()` in xsso_SVC returns a hardcoded IV `"12345678"` — this is a separate repo concern but uses this library's infrastructure
- **StrongBox:** `AsymmetricKeyStore`, `SymmetricKeyStore`, `SecureDataStore` SPIs for managed key/data storage

## Data Flow
```
Calling code (xplatform_LIB, services)
        |
        +---> ConfigurationFile (read INI config files from filesystem)
        |
        +---> ConfigDB (RPC call to Director for config values)
        |
        +---> CacheManager -> SwarmCache (JGroups multicast cluster cache)
        |
        +---> CryptoCipher / CryptoFactory (in-memory encryption/decryption)
        |
        +---> StrongBox DataRepository (encrypted data store — JDBC backend)
        |
        +---> JdbcConnection / JdbcStoredProc (SQL access to any configured DB)
        |
        +---> SystemLog -> various Destinations (file, email, network, encrypted)
```

## Data Quality and Retention
- Library provides infrastructure only — data quality rules are the responsibility of calling code
- Log retention is configurable via `QueuedFileDestination` / `CircularBufferDestination` — no enforced retention policy
- Cache entries in SwarmCache expire per cache configuration — no persistent state

## Compliance Gaps
- **MD5 and SHA1** are present and usable — if used for data integrity or password hashing, this violates PCI DSS Req 6.3 (strong cryptography) and NIST SP 800-131A deprecation guidance
- **RC4, DES, RC2** — broken symmetric algorithms; presence in a production library is a PCI DSS compliance concern (Req 6.3.3 mandates only strong cryptography)
- **Jsafe SDK** — legacy commercial crypto library (`jsafe` dependency); current CVE status and FIPS 140-2/3 certification unknown
- **Hardcoded IV pattern** (visible in xsso_SVC's `DESedeFactory.java:38`) uses this library's infrastructure — a fixed IV for symmetric encryption is a critical cryptographic flaw
- **StrongBox JDBC SPI** — if key material is stored in the database without HSM protection, this does not meet PCI DSS key custodian requirements
- **`EncryptedLogDestination`** — existence of this class suggests logs may contain sensitive data; encryption of logs at rest is a positive control but the key management for log encryption is not auditable here
