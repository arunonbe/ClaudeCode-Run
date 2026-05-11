# 03 DevOps & Operations — ecount-system_LIB

## Build System

- Build tool: **Apache Maven** with Maven Wrapper (`.mvn/wrapper/maven-wrapper.properties`)
- Compiler target: **Java 21** (`pom.xml` lines 20–21)
- Parent POM: `com.parents:prepaid-parent:6.0.13` (`pom.xml` lines 7–11) — the Generation-2/3 parent used across the Onbe prepaid services family
- Packaging: `jar`
- Final artefact: `ecount-system-4.0.4-SNAPSHOT.jar`

Build command:
```
./mvnw clean install -Dmaven.test.skip
```
(As documented in `README.md`)

## CI/CD Pipelines

### GitHub Actions — CodeQL (`.github/workflows/codeql.yml`)

Runs GitHub CodeQL static analysis on:
- Manual trigger (`workflow_dispatch`)
- Weekly schedule (cron `52 0 * * 6` — Saturday 00:52 UTC)

Uses reusable workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
Runner: `self-hosted`, `X64`, `Linux`, `ubuntu-docker`

### GitHub Actions — Package Publish (`.github/workflows/github-package-publish.yml`)

Publishes the artefact to GitHub Packages on push. This is the CI pipeline that distributes the library to consumers.

### GitLab CI (`.gitlab-ci.yml`)

A GitLab CI pipeline file is also present, indicating the repository has been or is mirrored on both GitHub and GitLab. The GitLab pipeline likely performs the primary build and publish to Onbe's internal Nexus / Artifactory.

### Dependabot (`.github/dependabot.yml`)

Dependabot is enabled and will raise PRs for dependency version updates.

## Versioning

Current version: `4.0.4-SNAPSHOT`. The major version (4) suggests significant evolution from earlier generations. Like `ecount-host-log4j_LIB`, this is still a SNAPSHOT — indicating it has not been promoted to a formal release. However, the presence of a GitHub Packages publish workflow means each CI build may overwrite the SNAPSHOT artefact.

## Testing

Unit tests are present under `src/test/java/com/ecount/Core2/system/dal/`:

| Test Class | Purpose |
|---|---|
| `TestAllDataTypesStoredProcedure` | Tests parameter binding for all supported SQL types through the DAL framework |
| `TestDataSourceResolver` | Validates connection-string normalisation for each supported format (OLEDB, WebLogic, Microsoft JDBC, jTDS, Sybase) |
| `TestDirectorConfiguredDBCPdatasourceCreator` | Tests Director-based datasource creation |

Test resources include `log4j2-test.xml` for test-scoped logging configuration — notably using **Log4j 2**, not Log4j 1.x, for tests.

## Runtime Dependencies

| Dependency | Purpose |
|---|---|
| `director-client:2.0.2` | Contacts Director service for runtime DB configuration |
| `common:3.1.5` (ecount-core common) | Shared EcountCore utilities |
| `net.sourceforge.jtds:jtds` | SQL Server JDBC driver (legacy jTDS) |
| `org.springframework:spring-context` | Spring IoC container |
| `commons-dbcp:commons-dbcp` | Apache Commons DBCP connection pooling |
| `commons-pool:commons-pool` | Apache Commons Pool (DBCP dependency) |

## Operational Concerns

- **SNAPSHOT in production**: The `4.0.4-SNAPSHOT` version may resolve to different binaries at different build times. Consumers should pin to a release version.
- **jTDS driver**: `net.sourceforge.jtds` is a community JDBC driver that was last actively maintained circa 2013. The recommended replacement is Microsoft's official `com.microsoft.sqlserver:mssql-jdbc`, already used by Gen-3 services.
- **Commons DBCP v1 (deprecated)**: `commons-dbcp` v1 is a legacy connection-pooling library. The successor `commons-dbcp2` or HikariCP (used in `ecount-core_SVC`) should be considered.
