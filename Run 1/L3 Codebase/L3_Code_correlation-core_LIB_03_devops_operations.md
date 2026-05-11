# correlation-core_LIB — DevOps & Operations View

## Build & Packaging

| Attribute | Value |
|---|---|
| Build tool | Apache Maven (wrapper bundled at `.mvn/wrapper/`) |
| Maven version | 3.9.5 (pinned in `.mvn/wrapper/maven-wrapper.properties`) |
| Java source / target | 21 (set in `pom.xml` `<properties>`) |
| Artifact type | JAR (`<packaging>jar</packaging>`) |
| GroupId | `com.ecount.opensource` |
| ArtifactId | `correlation-core` |
| Version | `2.0.1` |
| Parent BOM | `com.parents:prepaid-parent:6.0.12` |

The parent POM `prepaid-parent:6.0.12` is sourced from the internal GitHub Packages registry (`https://maven.pkg.github.com/onbe/onbe_maven_releases`), configured in `.mvn/wrapper/settings.xml`. No version pinning for test or logging dependencies is visible in this pom.xml — these are expected to be managed by the parent BOM.

Build command (from README):
```
mvn clean install -Dmaven.test.skip
```

The CI workflow also skips tests:
```yaml
MAVEN_BUILD_ARGS: "-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip"
```

Tests are never executed in CI — this is a deviation from standard practice and a quality risk.

## Deployment

This is a **shared library JAR**, not a deployable service. It is deployed to:

- **GitHub Packages registry:** `https://maven.pkg.github.com/onbe/onbe_maven_releases`
- Published via the reusable workflow `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`
- Authentication uses `GITHUB_TOKEN` injected via CI secrets (`secrets: inherit`)

Consumer services declare a Maven dependency on `com.ecount.opensource:correlation-core:2.0.1` and obtain it from the internal registry.

No Dockerfile, Kubernetes manifests, Helm charts, or Terraform configurations exist — consistent with a library artifact.

## Configuration Management

| Configuration Item | Location | Mechanism |
|---|---|---|
| Maven registry credentials | `.mvn/wrapper/settings.xml` | `${env.GITHUB_TOKEN}` environment variable — never hardcoded |
| Maven distribution URL | `.mvn/wrapper/maven-wrapper.properties` | Pinned to `apache-maven-3.9.5-bin.zip` from Maven Central |
| Log pattern (test only) | `src/test/resources/log4j2-test.xml` | XML — includes `%X{correlationId}` in pattern |
| Java compiler version | `pom.xml` lines 21–22 | Maven properties (`maven.compiler.source/target = 21`) |

There is no application-level configuration (no `application.properties`, `application.yml`, Spring Boot config, or similar). The library is configuration-free at runtime; the MDC key `correlationId` is hardcoded in `LogContextConstants.java`.

The `CORRELATION_ID` MDC key (`"correlationId"`), HTTP header name (`"CORRELATION-ID"`), and JMS header name (`"APP_CorrelationID"`) are compile-time constants — changing them requires a new library version and coordinated re-deployment of all consumers.

## Observability

- **Logging:** The library emits `DEBUG`-level log messages via SLF4J / Lombok `@Slf4j` in:
  - `CorrelationIDContext` — on every `requiresNew()`, `requires()`, and `clear()` call
  - `CorrelationExecutorServiceDecorator` — on every `submit()` and `execute()` call (logs `"Spicing with the correlation id ..."`)
- **Log format (test config):** `[%level] %d{yyyy-MM-dd HH:mm:ss.SSS} [%t] correlationId='%X{correlationId}' %c{1.} - %msg%n`
- **No metrics, no health endpoints, no tracing instrumentation** (no Micrometer, no OpenTelemetry, no Prometheus) — as expected for a low-level utility library.
- **Operational visibility:** Once embedded in a consumer service, the correlation ID propagates automatically into all log lines produced by Log4j2/SLF4J via MDC, enabling cross-service log correlation in any centralised log aggregation platform (e.g., Splunk, ELK).

## Infrastructure Dependencies

| Dependency | Purpose | Source |
|---|---|---|
| `com.parents:prepaid-parent:6.0.12` | Parent BOM providing dependency versions | Internal GitHub Packages |
| SLF4J API | MDC operations (`org.slf4j.MDC`) | Inherited from parent BOM |
| Log4j2 (test scope) | Log output in test (`log4j2-test.xml`) | Inherited from parent BOM |
| Lombok | `@Slf4j` annotation on `CorrelationIDContext`, `CorrelationExecutorServiceDecorator` | Inherited from parent BOM |
| JUnit 5 | Unit tests | Inherited from parent BOM |
| GitHub Actions runners | CI/CD execution | `ubuntu-latest` (CodeQL), implicit for publish workflow |
| GitHub Packages | Artifact registry (source + destination) | `https://maven.pkg.github.com/onbe/onbe_maven_releases` |

Exact dependency versions are not visible in this pom.xml — they are managed by the parent BOM. This is a risk if the parent BOM is updated without regression testing of this library.

## Operational Risks

1. **Tests skipped in CI:** `MAVEN_BUILD_ARGS` includes `-Dmaven.test.skip`; the single test class (`CorrelationLogTest`) is never executed in CI. Regressions in core propagation logic will not be caught automatically.
2. **Hardcoded MDC key names:** `LogContextConstants.CORRELATION_ID = "correlationId"` is a compile-time constant. Any rename requires coordinated library version bump and consumer updates — a significant operational coordination overhead at scale.
3. **No semantic versioning enforcement:** Version `2.0.1` is manually maintained in `pom.xml`. The CI workflow supports `auto-increment` and `version-tag` overrides but relies on manual workflow dispatch for non-main-push releases.
4. **Stale MDC on exception:** If `CorrelationCallable.doCall()` throws, the thread retains a stale correlation ID indefinitely (no `finally` block in `CorrelationCallable.call()` lines 29–34). In thread pools, this correlates subsequent unrelated requests to the wrong ID in logs.
5. **Dependency on internal registry availability:** The parent BOM and published artifact both depend on `maven.pkg.github.com/onbe/onbe_maven_releases`. GitHub Packages outages will block both builds and consumer dependency resolution.
6. **`invokeAll`/`invokeAny` not wrapped:** These paths in `CorrelationExecutorServiceDecorator` (lines 91–108) bypass correlation propagation silently with no warning log.

## CI/CD

### Workflows

**`github-package-publish.yml`**
- Trigger: push to `main` (excluding `.mvn/**`, `.github/**`, `mvnw`, `mvnw.cmd`), pull request to `main`, or manual `workflow_dispatch`
- Reuses: `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`
- Build args: `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip`
- Secrets: inherited from caller context
- Supports dry-run, version tag override, auto-increment, and dependency update flags

**`codeql.yml`**
- Trigger: weekly (`cron: '25 3 * * 0'`) and manual `workflow_dispatch`
- Reuses: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- Runner: `ubuntu-latest`
- Purpose: static security analysis (SAST)

**Dependabot**
- Ecosystem: Maven
- Schedule: weekly
- Scope: root directory (`/`)

### Pipeline Gaps
- No integration tests or contract tests
- No OWASP dependency-check or licence compliance scan visible at this repo level (may be in parent workflow)
- No SBOM generation visible
- CodeQL runs weekly, not on every push — a window exists where newly merged code is not scanned for days
