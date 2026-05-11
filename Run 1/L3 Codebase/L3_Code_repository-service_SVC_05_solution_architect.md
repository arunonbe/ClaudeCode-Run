# Solution Architect Analysis: repository-service_SVC

## Technical Architecture
- **Language**: Java 21
- **Framework**: Spring (XML configuration, no Spring Boot)
- **Deployment**: WAR on JBoss/WildFly
- **API Protocol**: XML-RPC (Apache XML-RPC 3.1.4)
- **Database**: SQL Server via JDBC stored procedures (`RepositoryServiceDAOJDBCImpl`)
- **Encryption**: External GPG binary (PGP) + external BTRADE binary
- **Secrets**: StrongBox (`strongbox-impl:2.0.1`, `strongbox-client:2.0.1`)
- **File Transfer**: Strategy pattern — FTP (`FTPDriver`), SFTP (dependency present), HTTP (`HTTPDriver`)
- **Logging**: SLF4J + Lombok `@Slf4j`

### Module Structure
```
repository-common/
  - Domain: ECountFile, ECountFileDefinition(WithDate), ECountFileAttributes, ECountFileJournal,
            ECountClientHost, ECountFileInquiryCriteria, OverwriteModes, RepositoryFile,
            RepositoryFileAttributes, RepositoryFileEncryptionProfile
  - Constants: EncryptionProfileCodes, EcountFileAttributeCodes, FileTypes, ConnectionModes,
               SubmissionChannels, TransferTypes, BTRADE_ERRORCODES, PGPErrorCodes
  - Service Interfaces: IRepositoryService
  - DAO Interface: RepositoryServiceDAO
  - Crypto Interface: ICryptoService
  - Service I/O: AssociateFileInput/Output, DeassociateFileInput/Output,
                 FileInquiryInput/Output, RetrieveFileInput/Output,
                 SetFileAttributesInput/Output, StoreFileInput/Output

repository-svc/
  - DAO Impl: RepositoryServiceDAOJDBCImpl (stored procedure calls)
  - Stored Procedure Classes (15+): RepositoryCreateFile, RepositoryStageFile, etc.
  - Encryption: PGPEncryption, BTRADEEncryption + corresponding external command helpers
  - File Transfer: FileTransferLibrary, FileTransferFactory, FTPClient/FTPDriver, FTPControlSocket, FTPDataSocket
  - Library Layer: RepositoryServiceLibrary, RepositoryCryptoLibrary
  - Config Domain: Configuration, FTPConfig, HTTPConfig, HostConfig, CryptographyConfiguration,
                   PGPCryptographyConfiguration, BTradeCryptographyConfiguration, RepositoryConfiguration
  - Helpers: ObjectCopy, RepositoryDateParser
  - Context: RepositoryContext, RepositoryLibraryContext

repository-war/
  - WAR packaging; XML-RPC servlet endpoint wiring

repository-client/
  - RepositoryServiceXMLRPCClient: Consumer-facing XML-RPC client
  - Input/Output POJOs for each operation (mirroring repository-common service I/O)
```

## API Surface
XML-RPC operations exposed by the service (inferred from service I/O classes):
- `storeFile(StoreFileInput)` → `StoreFileOutput`
- `retrieveFile(RetrieveFileInput)` → `RetrieveFileOutput`
- `fileInquiry(FileInquiryInput)` → `FileInquiryOutput`
- `setFileAttributes(SetFileAttributesInput)` → `SetFileAttributesOutput`
- `associateFile(AssociateFileInput)` → `AssociateFileOutput`
- `deassociateFile(DeassociateFileInput)` → `DeassociateFileOutput`

All operations are accessible via the XML-RPC endpoint URL configured in the WAR.

## Security Posture

### Authentication & Authorisation
- XML-RPC endpoint authentication: not visible in this repository; depends on app server and XML-RPC framework configuration.
- No application-level authorisation checks visible in the service implementation.
- File access scoped by memberId/programId parameters — trust placed in callers.

### Cryptography
- PGP encryption via external GPG binary. Passphrase retrieved from StrongBox.
- **Critical issue**: `PGPEncryption.java:121` — null passphrase from StrongBox generates only a warning; encryption proceeds without passphrase-based signing. This means files could be stored without the expected protection if StrongBox returns null.
- BTRADE encryption: external binary process; error codes defined in `BTRADE_ERRORCODES.java`.
- TLS for XML-RPC transport: depends on app server configuration (not visible here).

### Secrets Management
- PGP passphrases managed via StrongBox (`RepositoryService.repositoryServiceRead(sboxreference, ...)`).
- Passphrase is retrieved in-memory and passed to the external GPG process — it exists in process memory briefly.
- Encryption key names (public key IDs) are stored in the database in `app_profile_program_fulfillment`.

### Command Injection Risk
- `PGPExternalCommands` and `BTRADEExternalCommands` construct shell commands using parameters derived from database-stored values (key names, file paths). If any database value is adversarially controlled, command injection is possible.

### Known CVEs / Vulnerable Dependencies
| Library | Version | Risk |
|---|---|---|
| Apache XML-RPC | 3.1.4 | CVE-2016-5002 (XXE), CVE-2016-5003 (content-type header injection) — CRITICAL |
| `ecountcore-common` | 3.1.6 | Internal; security posture unknown |
| `strongbox-impl` | 2.0.1 | Internal; security posture unknown |
| `xplatformlibrary` (transitive via parent) | Various | Legacy; check for known issues |

## Technical Debt
1. **XML-RPC with known CVEs** (`xmlrpc:3.1.4`): CVE-2016-5002 (XXE), CVE-2016-5003 — must be upgraded or replaced.
2. **External binary crypto** (`PGPExternalCommands`, `BTRADEExternalCommands`): Shell-out to external process is fragile, hard to monitor, and introduces command injection risk.
3. **Null passphrase tolerance** (`PGPEncryption.java:121-122`): Encryption silently succeeds without passphrase if StrongBox returns null.
4. **Plain FTP transport** (`FTPDriver.java`, `FTPClient.java`, `FTPControlSocket.java`): Transmits file data unencrypted.
5. **`FTPTest.java` in production main source** (`repository-svc/src/main/java/.../FTPTest.java`): Operational test utility in production source tree.
6. **SNAPSHOT version `3.0.4-SNAPSHOT`**: Non-release artifact version.
7. **Spring XML config only**: No Spring Boot; configuration is verbose XML with no profiles or environment variable abstractions.
8. **Dual input/output class sets**: `repository-client` and `repository-common` both define parallel Input/Output classes for each operation (e.g., `AssociateFileInput` exists in both); this duplication creates maintenance risk.

## Gen-3 Migration Requirements
1. Replace XML-RPC with REST API (OpenAPI-specified, Spring Boot).
2. Replace external GPG binary with Bouncy Castle Java PGP library.
3. Replace BTRADE external binary with a supported Java encryption library or migrate to PGP.
4. Eliminate plain FTP transport; mandate SFTP or Azure Blob Storage.
5. Replace Spring XML config with Spring Boot `@Configuration`.
6. Replace stored procedure calls with JPA repositories or Spring Data JDBC.
7. Containerise (Docker); remove WAR/JBoss dependency.
8. Add health check endpoint (`/actuator/health`).
9. Add structured metrics and distributed tracing.
10. Enforce non-null passphrase as hard failure (not warning).

## Code-Level Risks (File:Line References)
- `PGPEncryption.java:113-122` — null passphrase from StrongBox is only warned, not failed; encryption proceeds potentially unsigned.
- `PGPExternalCommands.java` — constructs shell command with parameters from database; potential command injection.
- `BTRADEExternalCommands.java` — same concern as above.
- `FTPDriver.java` / `FTPClient.java` / `FTPControlSocket.java` / `FTPDataSocket.java` — plain FTP implementation; PCI DSS Req 4.2 violation for CHD-containing files.
- `FTPTest.java` (`repository-svc/src/main/java/com/ecount/repository/library/FTPTest.java`) — operational utility in production source; should be in test scope or removed.
- `RepositoryServiceXMLRPCClientTest.java` — `repository-client` module has a test; check that it is not connecting to production endpoints.
