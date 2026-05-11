# core2-common_LIB — DevOps & Operations View

## Build & Packaging

| Property | Value |
|---|---|
| Build tool | Maven (Maven Wrapper 3.9.5 via `.mvn/wrapper/maven-wrapper.properties`) |
| Java source/target | 21 (`pom.xml` lines 14–15) |
| Artifact coordinates | `com.ecount.service.Core2:common:2.0.0` |
| Packaging | `jar` |
| Parent POM | `com.parents:prepaid-parent:6.0.12` |
| Runtime dependency | `commons-beanutils:commons-beanutils` (version managed by parent POM) |
| Build plugin | `maven-jar-plugin` (version managed by parent POM) |
| Enforcer plugin | `maven-enforcer-plugin` with `banTransitiveDependencies` rule; exceptions for `org.springframework.boot:*` and `commons-beanutils:commons-beanutils` |

### Build Command
```
mvn clean install -Dmaven.test.skip
```
(as documented in `README.md`; tests are skipped — no test sources are present in the repository)

### Dependency Note
The parent POM (`com.parents:prepaid-parent:6.0.12`) is resolved from the Onbe GitHub Packages registry (`https://maven.pkg.github.com/onbe/onbe_maven_releases`). Authentication requires a `GITHUB_TOKEN` environment variable, configured in `.mvn/wrapper/settings.xml`.

---

## Deployment

This library is **not deployed as a service**. It is published as a JAR artifact to GitHub Packages (Maven registry) and consumed as a compile-time dependency by other Core2 services.

**Published to**: `https://maven.pkg.github.com/onbe/onbe_maven_releases`

Consumers declare this artifact as:
```xml
<dependency>
    <groupId>com.ecount.service.Core2</groupId>
    <artifactId>common</artifactId>
    <version>2.0.0</version>
</dependency>
```

No Dockerfile, Helm chart, Kubernetes manifest, or deployment descriptor exists in this repository — consistent with a library-only project.

---

## Configuration Management

All configuration is external to this library:

| Configuration Item | Location | Notes |
|---|---|---|
| Maven repo credentials | `$env:GITHUB_TOKEN` (environment variable) | Used in `.mvn/wrapper/settings.xml` via `${env.GITHUB_TOKEN}` |
| Maven settings | `.mvn/wrapper/settings.xml` | Defines GitHub Packages repo; committed to source control (no secrets) |
| Parent POM version | `pom.xml` line 9 | Hardcoded `6.0.12`; requires manual bump |
| Library version | `pom.xml` line 19 | Hardcoded `2.0.0`; auto-increment available via CI workflow |
| Dependabot | `.github/dependabot.yml` | Weekly Maven dependency updates scheduled |

There are no `application.properties`, `application.yml`, environment-specific config files, or Spring Boot auto-configuration in this library.

---

## Observability

**None present in this library.** There are:
- No logging statements (no SLF4J, Log4j, or java.util.logging imports).
- No metrics instrumentation (no Micrometer, Prometheus, etc.).
- No tracing annotations (no OpenTelemetry or similar).
- No health-check interfaces.

All observability must be implemented by the consuming services. The exception types (`CoreException`, `ServiceException`, `ECSDebitServiceExceptions`) carry numeric error codes and messages that consuming services can log.

---

## Infrastructure Dependencies

| Dependency | Type | Evidence |
|---|---|---|
| GitHub Packages Maven registry | External SaaS | `.mvn/wrapper/settings.xml`; `github-package-publish.yml` |
| Onbe `om-ci-setup` GitHub org workflows | Shared CI pipeline | `github-package-publish.yml` line 38: `uses: Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` |
| Onbe `om-ci-setup` CodeQL workflow | Shared security scanning | `codeql.yml` line 7: `uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` |
| `com.parents:prepaid-parent:6.0.12` | Parent POM | Must be resolvable from GitHub Packages at build time |
| Apache Maven Central | Maven build tooling | `distributionUrl` in `maven-wrapper.properties` |

Runtime infrastructure dependencies (inferred from code but external to this library):
- Relational database accessed via JDBC (`java.sql.ResultSet` in `SQLMapper`).
- "Strong box" / PII vault service (referenced in `IMemberService` Javadoc).
- "Director" service for secure profile lookup (referenced in `IMemberService` Javadoc).
- JMS message broker (referenced by `ECSDebitServiceExceptions`: `ECSJMSCommunicationError`, `ECSJMSMesgReceiveError`).
- ECS (Electronic Clearing Service / debit processor) via MLI protocol (`ECSDebitServiceExceptions`: `InvalidECSMLIRequest`, `ECSMLIResponseError`).

---

## Operational Risks

1. **No tests**: The `README.md` build command uses `-Dmaven.test.skip` and no test sources exist. The CI workflow (`MAVEN_BUILD_ARGS: "-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip"`) also skips tests. Breaking changes to interfaces (e.g., adding a required method to `IMemberService`) will not be caught until consumers fail to compile.

2. **Version pinned at 2.0.0**: The POM version is hardcoded. The `auto-increment` CI option (`github-package-publish.yml` line 10–13) relies on the shared `om-ci-setup` pipeline to bump the version. If the pipeline does not increment, all publishes overwrite the same version, which is incompatible with Maven's immutable artifact contract.

3. **Static mutable `MetaDataCache`**: `SQLMapper.metaDataCache` is a `private static MetaDataCache` (initialized in a static block at `SQLMapper.java` lines 33–42). In an application server with multiple reloads, this static state persists across redeploys and may hold stale column metadata.

4. **`String.intern()` usage in MetaDataCache**: `MetaDataCache.getMetaData()` (line 25) calls `metaDataKey.intern()` as a synchronization monitor. The JVM string intern pool is not bounded; if cache keys are derived from user input or large sets of class names, this will grow without bound.

5. **`clazz.newInstance()` deprecated API**: `SQLMapper.createObject()` (line 405) uses `clazz.newInstance()`, which is deprecated since Java 9 and removed in Java 17+. With Java 21 as the target, this call may generate warnings or fail for certain classes. The replacement is `clazz.getDeclaredConstructor().newInstance()`.

6. **Dependency on `om-ci-setup@main`**: Both CI workflows (`codeql.yml`, `github-package-publish.yml`) reference `Onbe/om-ci-setup/.github/workflows/...@main` (floating reference). A breaking change to the shared workflow will immediately affect all builds of this library.

7. **Parent POM resolution requirement**: Builds fail if `com.parents:prepaid-parent:6.0.12` is not available in the configured registry. Loss of access to GitHub Packages (e.g., token expiry, repository deletion) will break all builds.

---

## CI/CD

### GitHub Actions Workflows

**`github-package-publish.yml`** — Triggered on:
- Manual dispatch (`workflow_dispatch`) with optional `version-tag`, `auto-increment`, `dry-run`, `update-dependencies` inputs.
- Push to `main` branch (excluding changes to `.mvn/**`, `.github/**`, `mvnw`, `mvnw.cmd`).
- Pull request to `main` (opened, synchronize, reopened).

Delegates to shared Onbe pipeline:
```yaml
uses: Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main
secrets: inherit
with:
  MAVEN_BUILD_ARGS: "-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip"
```

**`codeql.yml`** — Triggered on:
- Manual dispatch.
- Weekly schedule: Fridays at 17:53 UTC (`cron: '53 17 * * 5'`).

Delegates to:
```yaml
uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
with:
  java-runner: "['ubuntu-latest']"
```

**`dependabot.yml`** — Maven dependency version updates on a weekly schedule.

### No Stages, No Integration Tests
The CI pipeline produces a single output: a JAR published to GitHub Packages. There are no build stages for unit tests, integration tests, or code-coverage thresholds. CodeQL scanning is the only automated quality gate beyond compilation.
