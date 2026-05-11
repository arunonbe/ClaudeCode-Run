# DevOps / Operations — wirecard_automated-database-migration_LIB

## Build System
- **Tool**: Apache Maven 3.x via Maven Wrapper (`mvnw` / `mvnw.cmd`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` — Onbe/Wirecard internal prepaid parent
- **Group ID**: `com.wirecard.issuing`
- **Artefact ID**: `automated-database-migration`, version `2.0.0`
- **Packaging**: `jar`
- **Java version**: `maven.compiler.source/target = 21`
- **Key dependencies**: `spring-boot` (compile, version from parent BOM), `liquibase-core` (compile, version from parent BOM)
- **Build enforcement**: `maven-enforcer-plugin` with `banTransitiveDependencies` rule (excludes `com.wirecard*`); SNAPSHOT dependencies are banned.

## CI/CD Pipeline
- **Platform**: GitHub Actions
- **CodeQL**: `.github/workflows/codeql.yml` — automated SAST scan (scheduled + `workflow_dispatch`).
- **GitHub Packages publish**: `.github/workflows/github-package-publish.yml` — publishes JAR to GitHub Packages registry.
- **Dependabot**: `.github/dependabot.yml` present.
- No GitLab CI pipeline (this is the GitHub-hosted version of the library).

## Configuration Management
- No `application.yml` or `application.properties` in this library. All configuration is injected by the consuming application.
- Required properties at consuming-app level:
  - `liquibase.change-log` — classpath path to Liquibase master changelog
  - `spring.datasource.url` — JDBC URL of target database
  - `spring.datasource.username` — database user
- No Spring profiles defined in the library.

## Observability
- `AutomatedDatabaseDeploymentConfiguration` logs `INFO`-level messages for `dbUrl` and `dbUser` using Apache Commons Logging.
- `DatabaseMigrationHandlerImpl` does not log migration progress — only throws `RuntimeException` on error. This means no visibility into which changeset is being applied during execution.
- No metrics, no distributed tracing.

## Infrastructure Dependencies
- **Target database**: Oracle (primary) or H2 (in-memory for testing) — JDBC driver must be on the classpath of the consuming application.
- **Liquibase classpath resources**: Changelog XML files must be provided by the consuming application's classpath.
- **GitHub Packages**: Publishes to `github.com/OnbeEast` package registry.

## Operational Risks
1. **No structured logging in migration handler**: Exceptions from Liquibase are swallowed into a generic `RuntimeException("Error performing DB migration.", ex)`. Operators have no granular detail about which changeset failed or why.
2. **`DATABASECHANGELOGLOCK` contention**: If the migration JVM is killed mid-run, Liquibase's lock table remains locked. The next run will fail with a lock timeout. Manual lock clearing (`DELETE FROM DATABASECHANGELOGLOCK WHERE LOCKED=1`) is required — no automated lock release mechanism is present.
3. **No rollback support exposed**: `DatabaseMigrationHandler` interface has `applyChanges()` and `generateSqlFile()` only. There is no `rollback()` method. A failed migration requires manual DBA intervention.
4. **`banTransitiveDependencies` Maven enforcer**: This rule ensures no unexpected transitive dependencies enter the JAR. While good for supply-chain hygiene, it can cause build failures when upstream libraries add new transitive dependencies — requiring explicit allowlisting.
5. **Version `2.0.0` is a non-SNAPSHOT release**: Once published, patches cannot replace it without a version bump. Consuming applications must be updated to pick up fixes.
6. **`ExtendedSpringLiquibase.afterPropertiesSet()` is a silent no-op**: If a consuming developer registers the `ExtendedSpringLiquibase` bean directly without using the runner, migrations will silently not execute — no warning or exception is raised.

## CI/CD
- GitHub Actions workflows provide CodeQL SAST and GitHub Packages publish.
- No automated integration tests against a real Oracle instance are present in this repository.
- No deployment pipeline for the library itself (it is a compile-time dependency, not a deployed service).
