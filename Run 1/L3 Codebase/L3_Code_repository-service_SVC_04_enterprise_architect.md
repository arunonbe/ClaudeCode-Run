# Enterprise Architect Analysis: repository-service_SVC

## Platform Generation
**Gen-1 / Gen-2 (transitional)**

Gen-1 characteristics:
- XML-RPC as the inter-service communication protocol
- WAR deployment to JBoss/WildFly
- Spring XML bean wiring
- Stored procedure-based data access
- External process invocation for cryptographic operations (GPG/BTRADE binary)
- FTP (unencrypted) file transfer support

Gen-2 characteristics:
- Java 21 compiler target
- Multi-module Maven project structure
- SLF4J + Lombok logging
- StrongBox integration for secrets management (modern key management pattern)
- Separate repository-client module for consumer library

## Business Domain
**Platform Infrastructure — Secure File Repository Service**

Core platform infrastructure providing centralised file storage, retrieval, and lifecycle management for all prepaid card program operations. This service is the file system backbone for batch processing, report distribution, and data exchange.

## Architectural Role
**Shared Infrastructure Service** — A centralised service consumed by virtually all other platform components that need to store or retrieve files. It enforces:
- Program-scoped file namespacing
- Audit trail for all file operations
- Encryption profile enforcement
- Multi-protocol file transfer

## Dependency Map
### Upstream (consumers of this service)
- repository_LIB (XML-RPC client)
- Client Zone web applications
- Batch processing services
- Reporting services
- Order processing services

### Downstream (dependencies of this service)
- SQL Server `repositorysvc` database
- StrongBox secrets vault
- External GPG binary
- External BTRADE binary
- FTP/SFTP remote file hosts
- `ecountcore-common` library
- `custom-files` library
- `director-client` / `profile-client`

## Integration Patterns
- **XML-RPC Server**: Primary API surface; all consumers call via XML-RPC protocol.
- **Stored Procedure Pattern**: All database operations delegated to SQL Server stored procedures.
- **External Process Integration**: Encryption via shell-out to GPG/BTRADE binaries — not a library call.
- **Passphrase Retrieval via StrongBox**: Decoupled secret management pattern.
- **File Transfer Adapters**: Strategy pattern (`FileTransferFactory`, `FileTransferLibrary`) selecting FTP/SFTP/HTTP transport.

## Strategic Status
**Rationalise / Migrate Path Required**

This service performs a critical business function (file storage and encryption) but its implementation is Gen-1:
- XML-RPC must be replaced with REST/gRPC.
- External binary crypto must be replaced with Java cryptographic library (Bouncy Castle PGP) or a cloud KMS-based approach.
- Plain FTP transport must be eliminated.
- WAR-on-JBoss must be containerised.
- Stored procedures could be retained initially but should be migrated to JPA/Flyway-managed schema.

## Migration Blockers
1. **XML-RPC protocol**: All consumers (repository_LIB and direct callers) must simultaneously migrate to a new REST API.
2. **External GPG/BTRADE binaries**: Critical dependency; replacement requires implementing or wrapping PGP in Java (Bouncy Castle) and migrating BTRADE to a supported encryption scheme.
3. **StrongBox integration**: `strongbox-impl:2.0.1` client; migration path depends on StrongBox service roadmap.
4. **Stored procedure database schema**: 15+ stored procedures in `repositorysvc` DB; schema migration requires DBA coordination.
5. **Wide consumer base**: Virtually all platform services depend on this service; any API change has wide blast radius.
6. **FTP server configurations**: External FTP server dependencies must be migrated to SFTP or cloud storage before FTP transport can be removed.
