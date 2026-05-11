# DevOps / Operations — wirecard_sftp-common-utilities_LIB

## Build System
- **Build tool**: Maven (mvnw wrapper)
- **Java version**: 21 (source and target — `maven.compiler.source=21`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12`
- **Artifact**: `com.wirecard.issuing:sftp-common-utilities:2.0.0`
- **Packaging**: JAR via `maven-jar-plugin`
- **Notable**: This repo uses Maven + Java 21, unlike the Gradle + Java 8 pattern of FTC, NAM-bank-agent, wire-transfer-agent — indicates it has been modernised more recently

## CI/CD Pipeline (GitHub Actions)
Two workflows found:

### github-package-publish.yml
- Trigger: push to `main`, pull request to `main`, `workflow_dispatch` (manual with version override)
- Uses Onbe reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`
- Build args: `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` (tests skipped in publish workflow)
- Inherits secrets from calling repository

### codeql.yml
- CodeQL static analysis for security scanning (GitHub Advanced Security)

### dependabot.yml
- Dependabot configured — automated dependency update PRs

## Publishing
- **GitHub Packages**: Published to GitHub Package Registry (via `om-ci-setup` reusable workflow)
- This is the only repo in the set using GitHub Packages rather than internal Nexus — further evidence of modernisation
- Maven settings in `.mvn/wrapper/settings.xml` (credentials for GitHub Packages injected via secrets)

## Configuration Management
- Library is stateless — no runtime configuration of its own beyond what consumers inject
- Maven wrapper properties in `.mvn/wrapper/maven-wrapper.properties`
- Parent POM `prepaid-parent:6.0.12` manages dependency versions; specific versions not overridden in this POM

## Observability
- `@Slf4j` (Lombok) logging in both tasklets — logs filenames on download/upload
- No Actuator — it is a library, not a standalone service
- No metrics emitted — upload/download success/failure is captured only via Spring Batch step outcome

## Infrastructure Dependencies
| Dependency | Purpose | Notes |
|---|---|---|
| Remote SFTP server | File exchange target | Configured by consuming service |
| Local filesystem | Staging directories | Consuming service must have write access |
| GitHub Actions | CI/CD | `Onbe/om-ci-setup` reusable workflow |
| GitHub Packages | Artifact distribution | Modern replacement for Nexus |
| Parent POM Nexus (prepaid-parent) | Dependency management | `com.parents:prepaid-parent` must be resolvable |

## Operational Risks
1. `Dmaven.test.skip` in publish workflow — tests are not run during publish; a broken version could be published without failing CI
2. `@Retryable` without explicit configuration — default behavior (3 retries, no backoff) may cause thundering-herd on SFTP server during outages
3. `Files.walk(outputPath)` without depth limit in `PublishSftpUploadTasklet` — processes subdirectories; could upload unintended files
4. No SFTP connection pool management observed — each tasklet execution creates a new session
5. `setAllowUnknownKeys(true)` in `BatchCommonChannelConfig` — all consuming services inherit this misconfiguration
6. FileOutputStream resource leak in `ImportSftpDownloadTasklet.doWithInputStream()` — the inner `FileOutputStream` is not wrapped in try-with-resources
