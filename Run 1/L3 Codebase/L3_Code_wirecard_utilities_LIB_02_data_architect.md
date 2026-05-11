# Data Architect View — wirecard_utilities_LIB

## Data Models

wirecard_utilities_LIB is a utility library with no persistent data store. Its data models are utility value objects and infrastructure types:

**`ThreadLocalBatchJobContext`** — thread-scoped context object:
- Batch job ID, execution metadata
- Bound to `ThreadLocal<ThreadLocalBatchJobContext>`; lifecycle managed by caller
- No persistence; cleared on thread release

**Validation types**:
- `@CountryCode` — annotation metadata (no runtime state)
- `@CurrencyCode` — annotation metadata (no runtime state)
- `CountryCodeValidator` — stateless validator using ISO 3166-1 alpha-2 list
- `CurrencyCodeValidator` — stateless validator using ISO 4217 currency code list

**`PGPUtils`** — stateless utility class (all methods static):
- No stored state; operates on stream inputs/outputs
- Key material passed as `InputStream` parameters — caller responsible for key storage
- Private key protected by passphrase (`char[] passwd`) — passphrase management is caller's responsibility

**Test utilities**:
- `EmbeddedSftpServer` — Apache SSHD-based embedded SFTP server for integration testing
- `EmailUtils` — test email interaction utilities
- Test key files: `src/test/resources/pgp/0x6392B27D-pub.asc` and `0x6392B27D-sec.asc` — PGP test key pair
- SFTP test key: `src/test/resources/sftp/id_test_rsa.pub` — SSH public key for SFTP test

## Sensitive Data Handled

| Data Category | Presence | Risk |
|---|---|---|
| PGP private keys | Passed as `InputStream` at runtime | Caller's responsibility; must come from secure key store |
| PGP private key passphrase | Passed as `char[] passwd` | Caller must zero passphrase array after use; no logging |
| PGP test keys | In test resources (`0x6392B27D-sec.asc`) | Test keys only; must not be used in production |
| SFTP test key | `id_test_rsa.pub` in test resources | Test key only |
| Encrypted file content | Stream-based; not stored | Financial data in transit encrypted by PGPUtils |
| Financial amounts | Via `MoneyUtils` | Transient computation; not stored |
| Batch job context | Via `ThreadLocalBatchJobContext` | May contain job IDs, execution metadata |

**Critical concern regarding PGP key handling**:
- `PGPUtils.decryptFile()` accepts the private key as an `InputStream keyIn` parameter. If the caller passes a key loaded from a plaintext file on disk, the private key material exists unprotected in the file system. For PCI DSS compliance (Requirement 3.6), private keys used for protecting financial file transfers must be stored in an HSM or encrypted key store.
- The passphrase is passed as `char[]` (correct practice — allows zeroing), but the calling code must zero the array after use. No guarantee is enforced by this library.

## Encryption and Protection Status

- **PGP encryption**: BouncyCastle (`bcpg-jdk15on:1.48`) providing OpenPGP (RFC 4880) implementation
  - Encryption: public key encryption via `PGPEncryptedDataGenerator`
  - Compression: configurable (`compressType` parameter)
  - Encryption algorithm: configurable (`encryptType` parameter — AES-256 should be required by policy)
  - Integrity: configurable (`withIntegrityCheck` — must always be `true` in production)
  - Armored output: configurable (`armor` parameter)
- **Decryption**: `BcPublicKeyDataDecryptorFactory` with BouncyCastle provider; integrity check verified after decryption
- **No FIPS compliance**: BouncyCastle standard provider (not FIPS 140-2 validated); if FIPS compliance is required for PCI DSS, the FIPS-validated BouncyCastle module must be used

## Database Schemas

None — the library has no database dependencies or schemas.

## Data Flows

**PGP file encryption/decryption** (primary security-sensitive data flow):
```
Calling service (Gen-2 microservice)
  → PGPUtils.encryptFile(outputStream, fileName, publicKey, armor, withIntegrityCheck, compressType, encryptType)
    → BouncyCastle (PGP operations)
      → Encrypted output stream (PGP-encrypted file)
        → SFTP / file transfer to partner bank or network

Partner file → PGPUtils.decryptFile(inputStream, outputStream, keyInputStream, passphrase)
    → BouncyCastle (PGP decryption + integrity verification)
      → Decrypted output stream
        → Calling service file processing
```

**JSON serialization**:
```
Calling service → JsonUtils.serialize/deserialize → Jackson 2.9.9 → JSON string/POJO
```

**Validation**:
```
Spring Bean Validation → CountryCodeValidator/CurrencyCodeValidator → true/false
```

## Retention Concerns

- No data stored by this library
- PGP test key files in `src/test/resources/pgp/` are committed to source — these are test keys; the secret key (`0x6392B27D-sec.asc`) must not be used for any production encryption. The key ID `0x6392B27D` should be verified against any production key stores to ensure no collision.

## PCI DSS Data Storage Compliance

- The library does not store data; it processes data in transit
- **PCI DSS Requirement 4.2.1** compliance for PGP-encrypted file transfers depends on:
  1. The calling service choosing strong encryption algorithms (AES-256, not 3DES)
  2. Integrity protection always enabled
  3. Key management meeting PCI DSS Requirement 3.6 (key generation, distribution, storage, access, retirement, destruction)
- **BouncyCastle 1.48**: This version is not FIPS 140-2 certified. If PCI DSS requires FIPS-validated cryptography for file encryption, this library must be upgraded to the BouncyCastle FIPS module
- **Jackson 2.9.9**: Known deserialization CVEs (CVE-2019-14379). If `JsonUtils` processes untrusted JSON input, this is a vulnerability. The library should be upgraded to Jackson 2.15+ and `MapperBuilder.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)` should be verified as configured appropriately.
