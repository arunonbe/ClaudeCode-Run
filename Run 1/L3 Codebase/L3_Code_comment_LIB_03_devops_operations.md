# comment_LIB — DevOps & Operations View

## Build & Packaging

| Attribute | Value |
|---|---|
| Build tool | Apache Maven 3.9.5 (via Maven Wrapper) |
| Java version | 21 (compiler source and target, `pom.xml` lines 19–20) |
| Artifact type | JAR (packaging: `jar`) |
| GroupId | `com.ecount.services` |
| ArtifactId | `comment` |
| Version | `3.0.1` |
| Parent POM | `com.parents:prepaid-parent:6.0.12` |
| Maven Wrapper URL | `https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.5/apache-maven-3.9.5-bin.zip` |

Build command documented in `README.md`:
```
mvn clean install -Dmaven.test.skip
```

Tests are skipped by default in both the README instruction and the CI workflow (`-Dmaven.test.skip` in `github-package-publish.yml` line 39). This means the integration tests in `CommentServiceImplTest` are never run in CI.

The `maven-enforcer-plugin` is configured to ban transitive dependencies, with explicit exclusions for `org.springframework:*` and `org.springframework.boot:*`. This enforces a controlled dependency surface but requires manual exclusion management.

## Deployment

This library is **not independently deployable**. It produces a JAR that is consumed as a compile-scope dependency by other applications in the `prepaid-parent` ecosystem. Deployment occurs indirectly when a consuming application (e.g., a WAR deployed to Tomcat 10.x) bundles this JAR.

The `README.md` lists Tomcat 10.x.x+ as a prerequisite, but this applies to the consuming application rather than this library itself.

Spring wiring is performed via the XML configuration file bundled inside the JAR at:
`src/main/resources/com/ecount/services/comment/comment.xml`

Consuming applications import this bean definition file and must provide a JNDI DataSource registered as `java:comp/env/jdbc/CbaseappDataSource`.

Published to: GitHub Packages (via the `github-package-publish.yml` workflow using the shared reusable workflow `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`).

## Configuration Management

| Configuration Item | Location | Mechanism |
|---|---|---|
| Production DataSource | Consuming app's JNDI / Tomcat context.xml | JNDI lookup `java:comp/env/jdbc/CbaseappDataSource` |
| Application ID | `comment.xml` bean property `applicationId`, value `12` | Spring XML injection |
| Test DataSource | `src/test/resources/commentTest.xml` | Spring XML with hardcoded JDBC URL, username, and password |
| Maven settings (proxy/repo auth) | `.mvn/wrapper/settings.xml` | Maven settings file (contents not fully visible; used in CI with `-s ./.mvn/wrapper/settings.xml`) |
| Dependency versions | Inherited from `com.parents:prepaid-parent:6.0.12` | Parent POM BOM — no version pins in this module's `pom.xml` |

There are no `.properties` or `.yaml` application-configuration files in this library. All runtime configuration (DataSource, applicationId) is injected by the consuming application.

The `applicationId` value `12` is hardcoded in the production `comment.xml`. If a consuming application needs a different application ID it must override this bean property during Spring context assembly.

## Observability

- **Logging framework**: SLF4J with Lombok `@Slf4j` annotation. Three classes use it: `CommentServiceImpl`, `JDBCCommentorDAOImpl`, and `GetEscalationAssigneeDAOImpl`, and `AutoCommentException`.
- **Log configuration (test)**: `src/test/resources/log4j2-test.xml` routes all `com.*` logs at DEBUG level and Spring Boot at ERROR level to STDOUT.
- **Production log configuration**: Not defined in this library. The consuming application's log configuration governs production log levels and appenders.
- **What is logged**:
  - `CommentServiceImpl`: ERROR level on `RuntimeException` caught during insert operations (e.g., `log.error(e.getMessage(), e)` in all four `insertComment` overloads).
  - `JDBCCommentorDAOImpl`: INFO level logging of the `activity` parameter on every auto-comment call (`log.info("getInquiryType : " + activity)` — line 60).
  - `AutoCommentException.printStackTrace()`: Logs "Caused by:" and nested stack trace to SLF4J INFO.
- **No metrics, health checks, or distributed tracing** are implemented or exported by this library. There is no Micrometer, OpenTelemetry, or Actuator instrumentation.
- **No correlation/trace ID** is attached to log entries or database records; diagnosing a failed comment insertion requires correlating by timestamp and member ID.

## Infrastructure Dependencies

| Dependency | Scope | Version Source | Purpose |
|---|---|---|---|
| `org.springframework:spring-context` | compile | Parent POM | Spring IoC container |
| `org.springframework:spring-jdbc` | compile | Parent POM | JDBC abstraction (`StoredProcedure`, `JdbcTemplate`) |
| `commons-lang:commons-lang` | compile | Parent POM | `StringEscapeUtils.escapeJavaScript()` in `CommentHistoryValue` |
| `com.microsoft.sqlserver:mssql-jdbc` | **test only** | Parent POM | JDBC driver for integration tests against SQL Server |
| Lombok | compile (implicit via `@Slf4j`) | Parent POM | Code generation for logging |
| Microsoft SQL Server `cbaseapp` | runtime | Hardcoded in `comment.xml` / JNDI | Single database backend |
| Tomcat 10.x (consuming app) | runtime (external) | N/A | JNDI DataSource provider |
| GitHub Actions runner | CI | `ubuntu-latest` (CodeQL workflow) | CI/CD infrastructure |

Note: `mssql-jdbc` is **test scope only**. The production build does not bundle the JDBC driver; it must be present on the Tomcat server classpath or supplied by the consuming application.

## Operational Risks

1. **Tests always skipped in CI** — `MAVEN_BUILD_ARGS` in `github-package-publish.yml` includes `-Dmaven.test.skip`, so `CommentServiceImplTest` is never executed during automated builds. Regressions to stored procedure signatures or database behaviour will not be caught before publishing.

2. **Integration tests hit a live QA database** — `CommentServiceImplTest` calls `dbo.csa_insertcsdet` and `dbo.csa_insert_service_records_escalation` against the QA SQL Server. If the test suite were ever run it would write data to the QA database. There are no rollback / cleanup mechanisms in the test teardown.

3. **Hardcoded legacy hostname in test config** — The JDBC URL `q-lis-db01.nam.wirecard.sys:2231` references a Wirecard-era (pre-Onbe) hostname. If this QA server has been decommissioned or renamed, all integration tests will fail with a connection error.

4. **No connection pooling at library level** — `DriverManagerDataSource` (used in test) does not pool connections. In production, pooling is the JNDI DataSource's responsibility. Misconfiguration of the JNDI resource (no pool limits) could cause connection exhaustion under load.

5. **No circuit-breaker or retry** — All DAO calls propagate `RuntimeException` directly (caught and re-thrown as `AutoCommentException`). Transient SQL Server connectivity issues will immediately surface as failures to callers without retry or graceful degradation.

6. **Single point of failure** — No read replicas, caching, or failover is configured. All reads and writes target one `CbaseappDataSource` JNDI name.

7. **`dependabot.yml` configured for weekly Maven updates** — This is positive for dependency hygiene, but since there are no automated tests running in CI, a dependency update that breaks the library may not be caught before publishing.

## CI/CD

### Workflows

| Workflow File | Trigger | Action |
|---|---|---|
| `.github/workflows/github-package-publish.yml` | Push to `main`, PR to `main`, `workflow_dispatch` | Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`; builds and publishes JAR to GitHub Packages |
| `.github/workflows/codeql.yml` | Weekly (`cron: 0 16 * * 3` = every Wednesday at 16:00 UTC), `workflow_dispatch` | CodeQL static analysis via `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` on `ubuntu-latest` |

### Notable CI Observations

- **Reusable workflows** — Both CI workflows delegate entirely to shared Onbe CI setup workflows (`om-ci-setup` repository). The actual build, publish, and security-scan logic is not visible in this repository.
- **Secrets inheritance** — Both workflows use `secrets: inherit`, passing all repository secrets to the called workflow.
- **Version auto-increment and dry-run** — The publish workflow supports manual `version-tag` override, `auto-increment` (boolean), `dry-run` (boolean), and `update-dependencies` (boolean) inputs, suggesting the `om-ci-setup` workflow handles semver bumping.
- **No environment gates** — There are no environment approvals or deployment gates defined in either workflow file. Publishing happens automatically on any push to `main`.
- **Paths-ignore** — The publish trigger ignores changes to `.mvn/**`, `.github/**`, `mvnw`, and `mvnw.cmd` — preventing spurious builds from infrastructure-only changes.
- **PR validation** — PRs against `main` (opened, synchronised, reopened) trigger the publish workflow, which appears to build/validate without publishing (dry-run behaviour would be controlled by the shared workflow logic).
