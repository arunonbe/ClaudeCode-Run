# Business Analyst Report: strongbox-xmlrpc_SVC

## Business Purpose

strongbox-xmlrpc_SVC is the central cryptographic vault service for the Onbe Gen-1/Gen-2 platform, operating under the "StrongBox" brand. It stores, manages, and provides controlled access to cryptographic material including RSA asymmetric key pairs, symmetric AES keys, and PGP passphrases. It also provides PGP encryption and decryption services using externally-invoked PGP command-line tools. All services on the platform that need to perform encryption, decryption, digital signing, or key-wrapped data access depend on StrongBox.

The service exposes its capabilities via XML-RPC (a predecessor to SOAP and REST, using HTTP POST with XML payloads), consistent with its Gen-1 eCount/Citi origin (author: "OFSS" — Oracle Financial Services Software). A GitHub Actions CI/CD pipeline and Docker containerisation have been added, placing it in a hybrid Gen-1/Gen-2 operational posture.

## Capabilities

**Repository Service** (`RepositoryService`):
- `repositoryServiceWrite`: Encrypts a Java object or Map and stores the ciphertext in the StrongBox SQL Server database; returns a reference string (opaque token)
- `repositoryServiceRead`: Given a reference string, retrieves and decrypts the stored blob, returning the plaintext object
- `repositoryServiceWriteMap` / `repositoryServiceReadMap`: Map-typed variants of the above

**Crypto Service** (`CryptoService`):
- `encryptPGP`: Given a recipient key name and plaintext text, performs PGP public-key encryption by invoking an external PGP command-line binary via `PGPExternalCommands`, using a passphrase retrieved from the Repository Service
- `decryptPGP`: Given an encrypted PGP blob and the recipient key name, retrieves the passphrase from Repository Service and invokes the external PGP binary to decrypt

**Key Management** (via DAO layer):
- `SbGetAsymmetricKey`: Retrieves RSA private and public key pair by name from the vault database
- `SbGetSymmetricKey`: Retrieves symmetric key value, associated asymmetric key pair by key_id
- `SbInsertSymmetricKey` / `SbInsertData` / `SbUpdateData` / `SbDeleteData`: Full CRUD for vault-stored data

## Client and Cardholder Impact

StrongBox is the foundational security service for cardholder data protection. Every encrypted PAN, DDA number, or sensitive field in the Gen-1/Gen-2 databases was encrypted using keys managed by or accessed through StrongBox. If StrongBox is unavailable, services cannot decrypt cardholder data or encrypt new data, resulting in transaction failures and inability to serve cardholders. If StrongBox is compromised, all data protected by its keys is at risk.

## Business Rules in Code

- Key retrieval requires a named key reference; passphrases are retrieved from the Repository Service itself (the vault retrieves its own stored passphrases)
- PGP operations use a passphrase fetched from the vault to invoke an external PGP binary — the passphrase is fetched at runtime, not compiled in
- StrongBox reference strings encode the key version, data location, and encryption metadata; version `"V1"` is the current write reference version (`writeReferenceVersion = "V1"`)
- The `agent` parameter passed to Repository Service read/write operations identifies the calling service but appears to be informational only (no visible authorisation enforcement based on agent value)

## Regulatory Obligations

- **PCI DSS Requirement 3.5**: Cryptographic key management procedures require key protection; StrongBox is the key management system for the Gen-1/Gen-2 platform
- **PCI DSS Requirement 3.6**: Key management lifecycle (generation, distribution, storage, replacement, destruction) must be documented and enforced; StrongBox's database-backed key store is the central control point
- **PCI DSS Requirement 3.6.1**: Keys used to protect cardholder data must be protected by key-encrypting keys and must not be stored in cleartext; this is the critical architectural risk (see below)
- **PCI DSS Requirement 8.2**: Access to StrongBox (the key management system) must be authenticated and logged
- **NIST SP 800-57 (Key Management Guidance)**: Industry standard for key management; StrongBox's architecture should be assessed against NIST key management principles

## Key Business Risks

1. **RSA private keys co-located with encrypted data in the same database**: The StrongBox vault database stores both the ciphertext (encrypted data blobs) and the RSA private keys used to decrypt them in the same SQL Server database. A single database compromise yields both the encrypted data and the decryption keys — eliminating the protection that encryption is meant to provide. This violates PCI DSS Requirement 3.6.1 (key-encrypting keys stored separately) and NIST SP 800-57 key management principles
2. **External PGP binary invocation**: PGP operations are executed by invoking an external command-line binary (`PGPExternalCommands.PGPEncryptText/PGPDecryptText`); this introduces process injection risk, path dependency risk, and makes the crypto operation dependent on an external binary that may not be version-controlled or monitored
3. **Plaintext data written to temp files**: The `CryptoService` writes plaintext and ciphertext to temporary files on the filesystem during PGP operations; if these temp files are not securely deleted (and the code does attempt deletion via `deleteFiles()`), the plaintext data exists on disk, creating a data-at-rest exposure for the duration of the PGP operation
4. **No access control on the `agent` parameter**: The `agent` parameter identifies the calling service but there is no visible enforcement of which agent can access which keys; any service that can reach the StrongBox XML-RPC endpoint can request any key by name
