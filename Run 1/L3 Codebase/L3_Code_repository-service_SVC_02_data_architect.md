# Data Architect Analysis: repository-service_SVC

## Data Stores
| Store | Type | Purpose |
|---|---|---|
| SQL Server (`repositorysvc` database — DS_DB_repositorysvc) | Relational DB | File metadata, file journal, file attributes, file definitions, file associations, audit trail |
| Filesystem (program-specific paths) | Local/network filesystem | Physical storage of file content |
| StrongBox (`strongbox-impl`, `strongbox-client`) | Secrets vault | PGP passphrase retrieval; referenced by `sboxReference` key |
| External PGP/BTRADE process | Subprocess | Cryptographic operations on file content |
| FTP/SFTP/HTTP servers | Remote endpoints | File transfer to/from external hosts |

## Schema / Tables
Inferred from stored procedure names in `repository-svc` module:

| Stored Procedure / Table | Operation |
|---|---|
| `RepositoryCreateFile` | INSERT new file record |
| `RepositoryCheckFileExistence` | SELECT to check if file exists |
| `RepositoryStageFile` | Staging operation before commit |
| `RepositoryRetrieveFile` | SELECT file definition + path |
| `RepositoryGetFileDefinition` | SELECT file metadata |
| `RepositoryGetFileTypePath` | SELECT program-specific file type path |
| `RepositoryGetFileAttributes` | SELECT key-value attributes for a file |
| `RepositorySetFileAttribute` | UPDATE/INSERT a file attribute |
| `RepositoryBeginSetFileAttributes` | Start attribute update transaction |
| `RepositoryCommitSetFileAttributes` | Commit attribute update transaction |
| `RepositoryCreateFileAudit` | INSERT audit record for file event |
| `RepositoryCreateFileAssociation` | INSERT file association record |
| `RepositoryRemoveFileAssociation` | DELETE file association record |
| `RepositoryGetAssociatedFileDefinitions` | SELECT associated file definitions |
| `RepositoryDeleteFile` | DELETE file record |

All data access is via stored procedures (no inline SQL visible in DAO implementation classes), providing a degree of SQL injection protection and schema abstraction.

## Sensitive Data Handled
| Data Element | Classification | Notes |
|---|---|---|
| Stored file content | Variable — may contain PII, PANs, financial data | Content is opaque to the service; sensitivity depends on program |
| PGP encryption keys (inbound/outbound) | Cryptographic material | Referenced by key name; stored in `app_profile_program_fulfillment` (external) |
| PGP passphrases | Secret | Retrieved at runtime from StrongBox; never persisted by this service |
| File definitions (names, paths, program IDs) | Internal operational data | Stored in database |
| Audit records | Operational/compliance | File event timestamps, operations, member/program context |

## Encryption
### At Rest
- File content encryption is optional and configurable per program via `RepositoryFileEncryptionProfile`.
- Supported encryption types: PGP (via external GPG binary) and BTRADE (via external BTRADE binary).
- Encrypted files are stored with `.asc` extension appended to the original filename.
- Passphrases are retrieved from StrongBox at runtime, not persisted in the database.
- Database row encryption: not visible in this codebase; depends on SQL Server TDE configuration.
- Filesystem encryption: depends on server OS configuration; not managed by this service.

### In Transit
- Service is exposed via XML-RPC; transport security depends on the HTTP layer of the app server.
- FTP transfers: plain FTP present in `FTPDriver.java` — unencrypted in transit.
- SFTP support is referenced (`sftp.version=sftp` dependency) — encrypted alternative to FTP.
- StrongBox calls: security depends on StrongBox client library implementation.

## Data Flow
```
Consumer (XML-RPC client)
  --> RepositoryServiceXMLRPCClient
        --> repository-service_SVC (XML-RPC endpoint)
              --> RepositoryServiceLibrary
                    --> RepositoryServiceDAOJDBCImpl (stored procedures) --> SQL Server
                    --> RepositoryCryptoLibrary
                          --> PGPEncryption / BTRADEEncryption
                                --> External process (GPG/BTRADE binary)
                                --> StrongBox (passphrase retrieval)
                    --> FileTransferLibrary
                          --> FTPDriver / SFTPDriver / HTTPDriver --> Remote host
```

## Data Quality / Retention
- Audit records created for all file operations (`RepositoryCreateFileAudit`).
- No data retention policy enforcement within the service itself; retention depends on external database maintenance.
- File existence check (`RepositoryCheckFileExistence`) prevents accidental overwrites when overwrite mode disallows it.

## Compliance Gaps
1. **Plain FTP** (`FTPDriver.java`, `FTPClient.java`): Transmits files (potentially containing CHD) unencrypted; violates PCI DSS Requirement 4.2.
2. **Null passphrase tolerated** (`PGPEncryption.java:121`): Warning issued but encryption proceeds, potentially producing unprotected output. Should be a hard failure for files containing CHD.
3. **Filesystem storage**: Physical file paths returned/managed by the service; filesystem access controls are outside this service's scope — must be validated at infrastructure level.
4. **External binary execution** (`PGPExternalCommands`, `BTRADEExternalCommands`): Command execution with parameters derived from database values; potential for command injection if database values are not sanitised.
5. **No CHD detection**: Service does not inspect file content to verify it meets encryption requirements; relies entirely on program configuration.
