# cicd-testlib_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven, wrapped via Maven Wrapper 3.2.0 (`mvnw` / `mvnw.cmd`)
- **Maven distribution**: `apache-maven-3.9.1` pulled from `repo.maven.apache.org` (defined in `.mvn/wrapper/maven-wrapper.properties`)
- **Language / JDK target**: Java 8 (`<source>8</source>` / `<target>8</target>` in `maven-compiler-plugin`, `pom.xml` lines 74–75)
- **JDK API compatibility check**: `animal-sniffer-maven-plugin` version 1.14 runs during the `test` phase, verifying against the `java17` signature (`org.codehaus.mojo.signature:java17:1.0`). Note the inconsistency: source/target is Java 8, but the sniffer checks against Java 17 signatures. This will pass (Java 17 APIs are a superset of Java 8 APIs accessible to a Java 8 source file) but the configuration appears unintentional and may mask unintended Java 17 API usage.
- **Output artefacts** (all produced at `mvn verify`):
  - `cicd-testlib-1.0.0-SNAPSHOT.jar` — primary library JAR
  - `cicd-testlib-1.0.0-SNAPSHOT-sources.jar` — via `maven-source-plugin` 2.4 (`attach-sources` execution)
  - `cicd-testlib-1.0.0-SNAPSHOT-javadoc.jar` — via `maven-javadoc-plugin` 2.10.3 (`attach-javadocs` execution)
- **Parent POM**: `com.citi.prepaid:module-parent:7` — this parent is not in Maven Central and must resolve from the internal Nexus/GitHub Packages registry. Its plugin management, dependency management, and distribution management settings govern this project and are not visible in this repository.

## Deployment

- **Artefact distribution**: The `<scm>` block in `pom.xml` references `gitlab.com/northlane/development/application-development/libraries/cicd-testlib.git`, suggesting deployment was originally to an internal Nexus at `d-na-stk01.nam.wirecard.sys:8081`. The `settings.xml` also references `https://maven.pkg.github.com/onbe/onbe_maven_releases`, indicating a migration to GitHub Packages for release artefacts.
- **Deployment credentials**: Embedded in `.mvn/wrapper/settings.xml` (plaintext — see Data Architect view). Server IDs: `ecount.release`, `ecount.snapshot`, `nexus-qa`.
- **Version strategy**: Currently `1.0.0-SNAPSHOT`. No release version has been cut in the source tree visible here. The `maven-source-plugin` version is declared twice (plugin management at 3.2.1 and direct at 2.4); the direct declaration (2.4) overrides management — this is a configuration inconsistency.

## Configuration Management

- **No application configuration files** are present (no `application.yml`, `application.properties`, `*.env`). The library is stateless infrastructure code.
- **Maven settings** are managed via `.mvn/wrapper/settings.xml`, which is committed to the repository. This is an unusual pattern — Maven settings typically live in `~/.m2/settings.xml` or are injected by CI. Committing them enables reproducible builds but exposes credentials.
- **Repository mirrors defined in `settings.xml`**:
  - `https://repo1.maven.org/maven2` — Maven Central mirror
  - `https://d-na-stk01.nam.wirecard.sys:8081/nexus/...` — legacy Wirecard internal Nexus (likely unreachable from current infrastructure)
  - `https://maven.pkg.github.com/onbe/onbe_maven_releases` — current Onbe GitHub Packages
- **Active Maven profile**: `nexus` (set in `<activeProfiles>` at line 142 of `settings.xml`). This profile enables both the Wirecard Nexus and Maven Central repositories.

## Observability

- **No runtime observability** is provided by this library (no metrics, no health endpoints, no tracing exporters).
- **Logging support**: The library enables structured logging by injecting correlation IDs into SLF4J MDC. Consuming services that configure their appenders to include `%X{correlationId}` will automatically emit the ID on every log line.
- **Test logging config** (`src/test/resources/log4j2.xml`): Console appender with pattern `[%level] %d{yyyy-MM-dd HH:mm:ss.SSS} [%t] correlationId='%X{correlationId}' %c{1.} - %msg%n`. This configuration exists only in the `test` scope and is not shipped in the production JAR.
- **Debug logging**: `CorrelationExecutorServiceDecorator` and `CorrelationIDContext` emit `DEBUG`-level log statements on every correlation ID operation. In high-throughput services these could be noisy at DEBUG level.

## Infrastructure Dependencies

| Dependency | Version | Scope | Notes |
|---|---|---|---|
| `org.slf4j:slf4j-api` | 1.7.7 | compile | Provides `MDC`, `Logger`, `LoggerFactory`. Version 1.7.7 dates from 2014; current is 2.x |
| `org.apache.logging.log4j:log4j-core` | 2.1 | test | Log4j2 2.1 is severely outdated (released 2014); vulnerable to Log4Shell (CVE-2021-44228) and multiple subsequent CVEs — but only in test scope |
| `org.apache.logging.log4j:log4j-api` | 2.1 | test | Same as above |
| `org.apache.logging.log4j:log4j-slf4j-impl` | 2.1 | test | Same as above |
| `org.testng:testng` | 6.8.21 | test | TestNG 6.8.21 is outdated (current is 7.x); test scope only |
| `com.citi.prepaid:module-parent` | 7 | parent POM | Internal artifact; availability depends on internal registry |

**Note**: Log4j2 2.1 is critically vulnerable (Log4Shell and its variants). Although these dependencies are `test`-scoped and therefore not included in the distributed JAR, developers who build and test this library locally are exposed. CI builds running tests against this library would also be exposed if exploitable log input reaches the test environment.

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Log4j2 2.1 in test scope | High | CVE-2021-44228 (Log4Shell), CVE-2021-45046, CVE-2021-45105, CVE-2021-44832. Upgrade to log4j2 2.17.2+ or 2.20+ immediately |
| SLF4J 1.7.7 outdated | Medium | Current is 2.0.x; while no critical CVEs apply to 1.7.7 MDC functionality, security patches exist in later versions |
| TestNG 6.8.21 outdated | Low | Current is 7.x; no direct security concern for a test-scope library |
| Wirecard Nexus unreachable | Medium | `d-na-stk01.nam.wirecard.sys:8081` is almost certainly unreachable from current infrastructure; builds requiring the `nexus` profile may fail dependency resolution |
| SNAPSHOT version in production | Medium | `1.0.0-SNAPSHOT` is mutable; artefact content can change without a version bump, breaking reproducible builds |
| `settings.xml` credentials in SCM | Critical | Three plaintext passwords committed; must be rotated and removed from repository history |

## CI/CD

### GitLab CI (`.gitlab-ci.yml`)
- Inherits from a shared template: `northlane/development/application-development/configuration/ci-templates` at ref `release-test`, file `maven.gitlab-ci.yml`. The actual pipeline stages, jobs, and rules are defined in that external template and are not visible in this repository.
- All three Maven phase overrides (`MAVEN_BUILD_OPTS`, `MAVEN_TEST_OPTS`, `MAVEN_DEPLOY_OPTS`) are set to `-Dmaven.test.skip=true`. **Tests are skipped in all CI phases.** This means the single test class `CorrelationLogTest` never runs in the pipeline.

### GitHub Actions (`.github/workflows/codeql.yml`)
- **Trigger**: `workflow_dispatch` (manual) and a weekly schedule (`cron: 1 20 * * 5` — Fridays at 20:01 UTC).
- **Action**: Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` with `secrets: inherit`.
- **Runner**: `self-hosted`, `X64`, `Linux`, `ubuntu-docker` (Onbe self-hosted GitHub Actions runner).
- **Purpose**: Static code security analysis (GitHub CodeQL). Provides SAST coverage as required for PCI DSS Requirement 6.3.3 (security testing of bespoke code).

### Dependabot (`.github/dependabot.yml`)
- Configured for Maven (`package-ecosystem: "maven"`) at the repository root.
- Weekly update schedule.
- Provides automated dependency vulnerability alerts and PRs — relevant to PCI DSS Req 6.3.3 and Onbe's vulnerability management program.
