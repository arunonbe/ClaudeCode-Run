# Data Architect Report — wirecard_test-utilities_LIB

## Data Models

No persistent data models. The library provides ephemeral test infrastructure:
- The embedded SFTP server uses an in-memory virtual filesystem (Apache SSHD `VirtualFileSystemFactory`).
- The embedded email server (GreenMail) stores messages in-memory.
- `TestUtils` operations are purely filesystem (temp directories).

Production components (`CountryCode`, `CurrencyCode`) are annotation-based validation constraints with no data model.

## Sensitive Data Identified

| Data Type | File | Severity |
|-----------|------|---------- |
| SFTP username `wirecard` | `EmbeddedSftpServer.java:36` | **HIGH** |
| SFTP password `FxDMahi4TU` | `EmbeddedSftpServer.java:38` | **HIGH** |
| PGP private key (full armored key material) | `src/main/resources/pgp/0x6392B27D-sec.asc` | **CRITICAL** |
| PGP public key | `src/main/resources/pgp/0x6392B27D-pub.asc` | LOW (public key) |
| PGP passphrase `wirecard` | `src/test/java/.../PGPUtilsTest.java:21` | **HIGH** |
| SFTP RSA public key | `src/main/resources/sftp/id_test_rsa.pub` | MEDIUM (public only) |

The most critical finding is the **PGP private key (`0x6392B27D-sec.asc`) committed to `src/main/resources/`**, which is a production source path. This means the private key is:
1. Committed to Git history (permanent record).
2. Packaged into the published `test-utilities-2.0.0.jar` artifact in GitHub Packages.
3. Accessible to anyone who can download the JAR.

If the key identifier `0x6392B27D` corresponds to a key used in any production file exchange, this constitutes a full key compromise.

## Encryption Status

The test library provides PGP encryption/decryption utilities (via `PGPUtils` from `wirecard_utilities_LIB`). The test in `PGPUtilsTest.java` exercises full encrypt/decrypt cycles. The library itself handles no data encryption at rest — it provides the tooling for tests.

## Database Schemas

None. No database access in this library.

## Data Flows in Tests

1. **SFTP testing**: Test code → `EmbeddedSftpServer` (in-memory VFS) → consuming service SFTP client → file read/write operations verified.
2. **PGP testing**: `PGPUtils.encryptFile()` with public key `0x6392B27D-pub.asc` → encrypted file → `PGPUtils.decryptFile()` with private key `0x6392B27D-sec.asc` and passphrase `wirecard`.
3. **Email testing**: GreenMail SMTP server captures outgoing emails from notification services.
4. **File utilities**: `TestUtils.clearOldDirectories()` prepares temp filesystem paths for batch processing tests.

## Retention Concerns

- The PGP private key in Git history cannot be removed without a full git-history rewrite (`git filter-branch` or BFG Repo Cleaner). If this key is or was ever used in production, all files encrypted with the corresponding public key must be considered compromised and re-encrypted.
- Test artifacts (SFTP temp files, GreenMail message stores) are ephemeral and pose no retention concern.

## PCI DSS Compliance

- **CRITICAL: PCI DSS Req. 3.5.1** — Cryptographic key material must be protected from unauthorized access. A private PGP key committed to a source code repository is accessible to all developers with repository access, violating key custodian requirements.
- **HIGH: PCI DSS Req. 2.2** — Default and hardcoded credentials (`FxDMahi4TU`) in production source code (even if intended for test use only) must be inventoried and assessed.
- **Note**: PCI DSS Req. 6.3.3 requires that all components are protected from known vulnerabilities. If the `utilities:2.0.0` dependency (from `wirecard_utilities_LIB`) contains vulnerable cryptographic implementations, this library inherits those vulnerabilities.
