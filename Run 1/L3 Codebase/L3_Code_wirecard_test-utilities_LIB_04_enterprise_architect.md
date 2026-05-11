# Enterprise Architect Report — wirecard_test-utilities_LIB

## Platform Generation

**Gen-2 (Wirecard/Northlane) with Gen-3 build pipeline.** The library's business origin is Wirecard issuing (package `com.wirecard.utilities.testutil`), but like the actuator-utils library, it has been migrated to GitHub Actions with Java 21 and GitHub Packages. The test infrastructure it provides (embedded SFTP, embedded email, PGP key material) is designed for Gen-2 Spring Batch microservices.

## Integration Patterns

- **Embedded test infrastructure pattern**: Provides embedded SFTP (Apache SSHD) and SMTP (GreenMail) servers that replace real external dependencies in integration tests. This is the standard pattern for testing file-based bank integrations.
- **Spring lifecycle integration**: `EmbeddedSftpServer` implements `InitializingBean` and `SmartLifecycle` — it integrates cleanly with the Spring application context lifecycle in test environments.
- **Classpath resource management**: `TestUtils` provides utility methods for managing classpath resources in batch file processing tests, supporting the Spring Batch integration testing pattern.

## External Dependencies

- `com.wirecard.issuing:utilities:2.0.0` — the main Wirecard utilities library (PGP, JSON, datetime, money, path, unique ID utilities). The actual PGP implementation lives here.
- `org.apache.sshd:sshd-core/scp/sftp` — Apache SSHD for embedded SFTP server.
- `com.icegreen:greenmail` — embedded SMTP server.
- `jakarta.mail-api` — Jakarta Mail API.
- `com.parents:prepaid-parent:6.0.12` — shared parent BOM.
- GitHub Packages (`onbe/onbe_maven_releases`) — artifact publication.

## Position in the Broader Platform

`test-utilities` is a **cross-cutting test infrastructure concern** for all Gen-2 issuing microservices. Every service that interacts with SFTP (sg-bank-agent, NAM bank agent, wire transfer agent, sftp-common-utilities) uses this library for integration testing. Its quality directly affects the reliability of the test suites for these cardholder-critical services.

The presence of production validation components (`CountryCode`, `CurrencyCode`) in this library indicates a module boundary issue — these validators should be in a dedicated `validation-utils` module, not in test utilities. Consuming these validators requires including the full test-utilities JAR, which bundles SFTP servers, email servers, and PGP keys into the production classpath.

## Migration Blockers

- The `CountryCode` and `CurrencyCode` validators in `src/main/java` are consumed by production services. Migrating them to a separate module requires coordinating changes across all consuming services.
- The PGP private key (`0x6392B27D-sec.asc`) in `src/main/resources` means any service that includes `test-utilities` on its compile classpath has access to the private key. This key must be rotated and removed from the repository.
- If Gen-3 services adopt Testcontainers for SFTP testing (the modern approach), this library becomes redundant for new services. Existing Gen-2 services would continue to use it.

## Strategic Status

**Maintenance mode — security remediation required.** The library provides legitimate test infrastructure value but has critical security issues (committed PGP private key, hardcoded SFTP credentials) that must be resolved immediately. The production validation components (`CountryCode`, `CurrencyCode`) should be extracted to a separate module to prevent test infrastructure from being packaged into production deployments. For Gen-3 services, consider Testcontainers as the replacement for the embedded SFTP pattern.
