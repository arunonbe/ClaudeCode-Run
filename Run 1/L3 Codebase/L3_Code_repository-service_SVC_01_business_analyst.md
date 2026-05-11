# Business Analyst Analysis: repository-service_SVC

## Business Purpose
repository-service_SVC is the backend J2EE service that implements the file repository for the Onbe prepaid card platform. It provides a centralised, audited file storage and retrieval service for all platform components — including batch processing systems, client zone web applications, and reporting tools.

The service manages the lifecycle of files associated with prepaid card programs and member accounts: storing, retrieving, associating, and attributing files, with support for both PGP and BTRADE encryption profiles. It supports multiple file transfer protocols (FTP, SFTP, HTTP) and is exposed via XML-RPC for legacy consumers.

## Capabilities
1. **StoreFile**: Accept a file from a caller, optionally encrypt it (PGP or BTRADE), and persist it to a program-specific storage path.
2. **RetrieveFile**: Retrieve a stored file, optionally decrypting it, and return it to the caller.
3. **FileInquiry**: List files matching search criteria (by member, program, date range, attributes).
4. **SetFileAttributes**: Update metadata attributes on a stored file (e.g., processing status flags).
5. **AssociateFile / DeassociateFile**: Link or unlink a file to/from additional program contexts.
6. **File Encryption/Decryption**: PGP encryption via external GPG binary; BTRADE encryption via external BTRADE process.
7. **Passphrase/Key Management**: Retrieve PGP passphrases from the StrongBox secrets service.
8. **Audit Trail**: `RepositoryCreateFileAudit` stored procedure creates an audit record for each file operation.
9. **File Transfer**: FTP, SFTP, and HTTP transfer drivers for inbound/outbound file movement.

## Key Business Entities
| Entity | Description |
|---|---|
| RepositoryFile | Core domain object: file content + ECountFileDefinition |
| ECountFileDefinition | File metadata: name, program_id, file_type, path, dates |
| ECountFileDefinitionWithDate | Extends ECountFileDefinition with effective dates |
| ECountFileAttributes | Key-value attributes on a file (e.g., encryption status, processing status) |
| ECountFileJournal | Journal/audit entry for a file event |
| ECountClientHost | Source/target host configuration |
| RepositoryFileEncryptionProfile | Encryption config: key references, passphrase StrongBox reference, signature flag |
| RepositoryAssociatedFileDefinition | Links a file to an additional program/context |
| OverwriteModes | Enum: controls overwrite behaviour on store |

## Business Rules
- Files are stored in program-specific directory paths looked up from the database via `RepositoryGetFileTypePath`.
- Overwrite modes control whether an existing file can be replaced.
- PGP encryption requires a public key to be configured in `app_profile_program_fulfillment`; missing key causes `CRYPTO_ENCRYPTION_PROFILE_NOT_CONFIGURED` error.
- Passphrases for PGP signing are retrieved from StrongBox (secrets vault) at encryption time; a null passphrase from StrongBox results in a warning (not a fatal error) — file may be signed without passphrase.
- BTRADE encryption delegates to an external binary process via `BTRADEExternalCommands`.
- PGP decryption removes `.asc`, `.pgp`, or `.gpg` extension to determine the original filename.
- All file operations must be performed within a valid member/program context.
- File association/deassociation links files to additional program contexts beyond their origin.

## Business Flows
### File Store Flow
1. Consumer calls `StoreFile` via XML-RPC client.
2. Service validates inputs, looks up file type path, checks for existing file per overwrite mode.
3. If encryption is configured: retrieves encryption profile, fetches passphrase from StrongBox, calls PGP or BTRADE external process.
4. Stages file to temporary path, then commits to target path.
5. Creates database record via `RepositoryCreateFile` stored procedure.
6. Creates audit record via `RepositoryCreateFileAudit` stored procedure.

### File Retrieve Flow
1. Consumer calls `RetrieveFile` via XML-RPC.
2. Service looks up file definition from database.
3. If file is encrypted, retrieves decryption profile and passphrase, decrypts via external process.
4. Returns file content to consumer.

## Compliance Relevance
- Files stored may include batch disbursement files, card issuance files, and reconciliation reports containing PII and potentially PANs.
- PGP encryption capability is a PCI DSS control for protecting data in transit/at rest for sensitive batch files.
- StrongBox integration for passphrase management is a key management control.
- Audit trail via stored procedure supports PCI DSS Requirement 10 (audit logs) and SOC 2 change management evidence.

## Risks (Business Perspective)
- **External process encryption**: PGP/BTRADE encryption delegates to external binaries; process execution failures silently produce a non-zero return code error. No retry logic.
- **Null passphrase tolerance**: PGP encryption continues with null passphrase (warning only at `PGPEncryption.java:121`), potentially producing unsigned/unprotected files.
- **FTP protocol**: Some transfer configurations use plain FTP — unacceptable for files containing CHD.
- **Missing key in StrongBox**: If StrongBox is unavailable or misconfigured, encryption silently proceeds without passphrase protection.
