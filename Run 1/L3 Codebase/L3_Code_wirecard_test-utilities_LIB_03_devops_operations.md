# DevOps / Operations Report — wirecard_test-utilities_LIB

## Build System

**Maven 3.x** via Maven Wrapper. Parent: `com.parents:prepaid-parent:6.0.12`. Produces JAR artifact (`test-utilities-2.0.0.jar`). Compiler target: Java 21.

Key build plugins:
- `maven-jar-plugin`: Standard JAR packaging.
- `maven-enforcer-plugin`: Bans transitive dependencies (except JUnit and wirecard* dependencies).

## CI/CD Pipeline

**GitHub Actions** with three workflow files:

1. **`github-package-publish.yml`**: Publishes JAR to GitHub Packages via `PAT_TOKEN` secret.
2. **`codeql.yml`**: GitHub CodeQL Java static analysis.
3. **`dependabot.yml`**: Automated dependency update PRs.

No GitLab CI configuration, confirming GitHub Actions migration is complete for this repository.

## Deployment Model

Published as a Maven JAR dependency to GitHub Packages. Consumed by all Wirecard issuing microservices that need SFTP or email integration testing. Not independently deployable.

## Runtime

- **Java 21**: Correct LTS version.
- **Spring Context** (from `prepaid-parent:6.0.12` BOM — version TBD).
- **Apache SSHD (sshd-core, sshd-scp, sshd-sftp)**: Apache SSHD is actively maintained. The version pinned by `prepaid-parent` should be verified.
- **GreenMail**: In-memory SMTP server for email testing.
- **Spring Boot Starter Test**: Test framework bundle.
- **Hamcrest**: Matcher library for assertions.
- **JUnit**: Unit testing framework (not scope:test — scoped as compile per pom.xml, which means JUnit is packaged into the produced JAR).

**Important**: JUnit is declared without `<scope>test</scope>` in `pom.xml` (line 63). This means JUnit classes are bundled into the main JAR artifact. Any service that includes `test-utilities` on its compile or runtime classpath will include JUnit in production, which is incorrect practice and adds unnecessary classes to production deployments.

## Secrets Management

**No secrets management.** Credentials are hardcoded in source code:
- `EmbeddedSftpServer.java:36`: `SFTP_USER_NAME = "wirecard"` — compile-time constant.
- `EmbeddedSftpServer.java:38`: `SFTP_PASSWORD = "FxDMahi4TU"` — compile-time constant.
- `PGPUtilsTest.java:21`: `PASSPHRASE = "wirecard"` — test constant.

PGP private key is a file in `src/main/resources/pgp/0x6392B27D-sec.asc`.

## Observability

SLF4J logging via `TestUtils` and `EmailUtils`. No metrics or tracing. This is appropriate for a test utilities library.

## EOL Runtimes / CVEs

- **Java 21**: Current — no concern.
- **BouncyCastle** (via `wirecard_utilities_LIB`): The underlying PGP utilities are assumed to use BouncyCastle. If the version is below 1.77, multiple CVEs apply (including CBC padding oracle, weak key generation).
- **Apache SSHD**: Actively maintained — verify exact version from parent BOM.
- **GreenMail 1.5.0**: Released 2017. Current version is 2.x. Version 1.5.0 may have minor issues but is low risk for test-only use.
- **JUnit (no test scope)**: JUnit in production classpath is a dependency management error; no direct CVE risk but incorrect packaging.

## Operational Notes

- The library is versioned at `2.0.0` — a release version, not a snapshot. Correct practice.
- The enforcer plugin correctly bans transitive dependencies, promoting explicit dependency declaration.
- The `EmbeddedSftpServer.isAutoStartup()` method compares `PORT == this.port` — this starts the server automatically only if the dynamically assigned `PORT` equals the configured `port`. This is a subtle behavior that could cause tests to behave differently depending on port assignment.
