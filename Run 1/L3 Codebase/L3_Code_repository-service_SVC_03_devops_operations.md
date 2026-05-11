# DevOps / Operations Analysis: repository-service_SVC

## Build System
- **Maven** multi-module project (mvnw wrapper present)
- **Java**: Source/target **21**
- **Parent POM**: `com.parents:prepaid-parent:6.0.13`
- **Root artifact**: `com.ecount.service.repositoryservice:repositoryservice:3.0.4-SNAPSHOT`
- **Modules**: repository-common, repository-client, repository-svc, repository-war
- Build compiles the service core (repository-svc) and packages it into a WAR (repository-war)

## Module Build Outputs
| Module | Artifact | Purpose |
|---|---|---|
| repository-common | repository-common JAR | Domain objects, service interfaces, DAO interfaces |
| repository-client | repository-client JAR | XML-RPC client library for consumers |
| repository-svc | repository-svc JAR | Service implementation, DAOs, encryption, file transfer |
| repository-war | WAR | Deployable web application (XML-RPC endpoint) |

## Deployment
- **Packaging**: WAR deployed to a Java EE application server (JBoss/WildFly implied by naming conventions and parent POM lineage).
- `FTPTest.java` in the svc module suggests manual connectivity testing was performed against live FTP servers.
- No Dockerfile, no container manifests, no Helm charts in this repository.
- Version `3.0.4-SNAPSHOT` indicates this is not a release artifact.

## Configuration Management
- Spring XML configuration wires the service context (`RepositoryContext.xml`, `RepositoryLibraryContext.xml`).
- `RepositoryDirectorConfiguration` and `Configuration` domain objects hold runtime configuration (FTP host config, HTTP config, cryptography config, host config).
- `mdd.java` in the configuration package suggests a metadata-driven configuration class.
- External dependencies: StrongBox client configuration, SFTP configuration, database datasource — all injected via Spring XML context.
- No Spring profiles, no Azure App Configuration, no environment variable abstractions visible.

## Observability
- Logging via **SLF4J + Lombok @Slf4j** throughout repository-svc module — modern pattern.
- Info/debug/error level logging is consistently applied in encryption and DAO classes.
- No application metrics (Micrometer, etc.).
- No distributed tracing.
- No health check endpoint visible (no Actuator or equivalent).
- `FTPTest.java` (in main source, not test) provides a command-line FTP connectivity test tool — this is an operational utility left in production source.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|---|---|---|
| SQL Server (repositorysvc DB) | Database | All metadata stored here; stored procedure calls via JDBC |
| StrongBox | Secrets vault | Required for PGP passphrase retrieval |
| GPG binary | External process | Required for PGP encryption/decryption operations |
| BTRADE binary | External process | Required for BTRADE encryption operations |
| FTP/SFTP servers | Remote file hosts | Required for file transfer operations |
| XML-RPC consumers | Internal callers | All clients communicate via XML-RPC |
| `strongbox-impl:2.0.1` | Internal library | StrongBox client |
| `ecountcore-common:3.1.6` | Internal library | Core shared types |
| `xmlrpc:3.1.4` | Apache XML-RPC | RPC framework |
| `dao-util:2.0.1` | Internal library | DAO utilities |
| `ecount-system:4.0.3` | Internal library | System utilities |

## Operational Risks
1. **External binary dependencies**: GPG and BTRADE executables must be installed and accessible on the application server; any path/version change breaks encryption/decryption.
2. **SNAPSHOT version**: `3.0.4-SNAPSHOT` in apparent production use — no release process evidence.
3. **`FTPTest.java` in production source** (`repository-svc/src/main/java/com/ecount/repository/library/FTPTest.java`): Test utility left in main source tree; could expose FTP credentials or connection info if invokable.
4. **StrongBox availability**: Service cannot encrypt/decrypt files if StrongBox is unavailable (passphrase retrieval fails); no fallback or circuit breaker.
5. **No health check**: No mechanism for load balancer to detect service unavailability.
6. **Plain FTP in FTPDriver**: Any misconfiguration or default selection of FTP over SFTP exposes file content in transit.
7. **Stored procedure coupling**: All data access is via stored procedures in the `repositorysvc` database; schema changes require coordinated database and service releases.

## CI/CD
No CI/CD pipeline configuration (Jenkinsfile, GitLab CI, GitHub Actions) found in this repository. Build and deployment assumed to be managed externally.
