# autoclaim-split-svc_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool:** Apache Maven, multi-module POM.
- **Maven wrapper:** `.mvn/wrapper/maven-wrapper.properties` pins Maven `3.9.1` via the Apache Wrapper (`3.2.0`). Distribution URL points to Maven Central.
- **Module layout:**

  ```
  autoclaimsplit (parent POM — pom packaging, groupId com.ecount.service, version 2.0.0-SNAPSHOT)
  ├── autoclaimsplit-common  (JAR — domain interfaces and VOs)
  └── autoclaimsplit-svc     (JAR — service implementation)
  ```

- **Java source/target level:** Java 1.6 (`maven-compiler-plugin` in both child POMs and parent POM). This is an extremely outdated Java version (released 2006, EOL since 2013).
- **Compiler flags:** `<verbose/>` is set in `compilerArguments`, meaning every compiled class is printed during the build — this is noisy for CI pipelines.
- **Artifact coordinates:**
  - `com.ecount.service:autoclaimsplit:2.0.0-SNAPSHOT`
  - `com.ecount.service.autoclaimsplit:autoclaimsplit-common:2.0.0-SNAPSHOT`
  - `com.ecount.service.autoclaimsplit:autoclaimsplit-svc:2.0.0-SNAPSHOT`
- **Coverage reporting:** Cobertura Maven plugin is configured under `<reporting>` in the parent POM (HTML + XML formats), but Cobertura is not maintained and does not support Java 8+.
- **Test execution:** All three GitLab CI variables (`MAVEN_BUILD_OPTS`, `MAVEN_TEST_OPTS`, `MAVEN_DEPLOY_OPTS`) set `-Dmaven.test.skip=true`, meaning tests are never executed in CI.
- **No Dockerfile** is present; this is a library JAR, not a deployable container image.

## Deployment

- This repository produces **library JARs**, not a deployable service. Deployment means publishing artifacts to a Maven repository for consumption by a host service.
- **Release mechanism:** `maven-release-plugin 3.0.0-M1` and `maven-install-plugin 2.5.2` are configured.
- **Artifact registry (production):** Nexus at `https://d-na-stk01.nam.wirecard.sys:8081/nexus/content/groups/public/` — a Wirecard-era on-premise Nexus instance. Whether this is still reachable post-Northlane/Onbe is unknown.
- **Artifact registry (current):** GitHub Packages at `https://maven.pkg.github.com/onbe/onbe_maven_releases` is configured in the `nexus` Maven profile in `settings.xml`, suggesting a partial migration to GitHub-hosted artifact storage.
- **Parent POM dependency:** The root POM declares `com.citi.prepaid.service:service-parent:8` as parent. This artifact must exist in the configured Nexus/GitHub registry for builds to succeed.
- **SCM:** GitLab, at `gitlab.com/northlane/development/application-development/libraries/autoclaimsplitsvc.git`.

## Configuration Management

- **Runtime configuration file:** `file:///d:/c-base/config/service/autoclaimsplitsvc/db-config.properties` — a hardcoded Windows path (`D:` drive). This is an on-premise deployment model. No environment-variable-based or container-native configuration exists.
- **Configuration properties expected at runtime** (sourced from `db-config.properties` via `PropertyPlaceholderConfigurer` in `appCtx-AutoclaimSplit_test.xml`):
  - `director.address` — Address of the Director service for DB connection provisioning
  - `ecount.agent` — Agent identifier for the eCount Core platform
  - `cbaseapp_database` — Database name/identifier for the DBCP factory
- **Spring context:** `appCtx-AutoclaimSplit.xml` (production), `appCtx-AutoclaimSplit_test.xml` (test). Uses Spring 2.5.6 XML-based bean wiring — no annotations, no Spring Boot.
- **Credentials in SCM (critical):** `.mvn/wrapper/settings.xml` contains plaintext passwords for multiple Maven repository servers. This is a security misconfiguration that must be remediated before next build pipeline run.

## Observability

- **Logging framework:** Log4j 1.x (`log4j:log4j:1.2.15`) via Commons Logging facade.
- **Log configuration:** `log4j.properties` (test scope only — no production log configuration is present in this repository). Test config routes all logs to stdout at DEBUG level with pattern `%d{ABSOLUTE} %5p %c{1}:%L - %m%n`.
- **Log output includes:** `memberId`, `echeckId`, `programId`, device IDs, device types, allocated amounts, fee amounts, velocity limits, and raw JDBC row counts. No structured logging (JSON), no MDC/NDC correlation IDs.
- **No metrics:** No Micrometer, Prometheus, or any metrics instrumentation.
- **No health endpoints:** This is a library, not a service; no HTTP endpoints.
- **No distributed tracing:** No OpenTelemetry, Zipkin, or Sleuth integration. The `IRequestContextHolder` / `StaticRequestContextHolder` provides an agent and global request ID but this is not wired to any external tracing system.
- **No alerting configuration.**

## Infrastructure Dependencies

| Dependency | Type | Details |
|---|---|---|
| SQL Server (CbaseApp DB) | Database | Accessed via jTDS `1.2.2`; connection managed by Director `DirectorConfiguredDBCPdatasourceCreator`; database name from `cbaseapp_database` property |
| Director service | Service discovery / DB pool | `com.ecount.Core2.system.dal.ds.DirectorConfiguredDBCPdatasourceCreator`; address from `director.address` property |
| eCount Core DeviceManager | Platform service | `com.cbase.business.core.impl.DeviceManagerImpl` wired with `ECoreDevice` SPI |
| eCount Core MemberManager | Platform service | `com.cbase.business.core.impl.MemberManagerImpl` |
| eCount Core TransferManager | Platform service | `com.cbase.business.core.impl.TransferManagerImpl` (wired in test context but not used in current code) |
| eCount Core Profile Service (XML-RPC) | Profile data | Referenced via commented-out code in `AllotmentConfigLoaderImpl`; not active |
| Nexus / GitHub Packages | Artifact registry | For build and dependency resolution |
| Spring Framework 2.5.6 | Application framework | IoC container, JDBC template, Spring XML context |
| Commons DBCP 1.2.2 | Connection pooling | Transitive via Director factory |

## Operational Risks

1. **Tests always skipped in CI** — `MAVEN_TEST_SKIP=true` in all three CI phases means no regression detection runs automatically.
2. **Plaintext credentials in SCM** — Maven `settings.xml` contains repository passwords. Pipeline secrets and credentials must be rotated and externalised to CI secret stores.
3. **Hardcoded Windows file path** — `file:///d:/c-base/config/service/autoclaimsplitsvc/db-config.properties` is not portable; will fail on Linux CI runners and containerised deployments.
4. **Java 1.6 target** — No modern JVM security features, no support for TLS 1.2/1.3 by default, no virtual threads, no module system. The compiled bytecode will not run on newer JVMs under newer security policy without explicit compatibility flags.
5. **Log4j 1.x** — End-of-life; CVE-2019-17571 (SocketServer deserialization RCE) and others apply. No upgrade path to Log4j 2.x is configured.
6. **Stale SNAPSHOT version** — `2.0.0-SNAPSHOT` is not a stable release identifier. Consumers may receive unpredictable binary changes if they resolve SNAPSHOT artifacts.
7. **No `null` safety on `PaymentDTO.amount`** — `Integer` (boxed) can be null from JDBC; unboxing at `UserAllotmentAllocation` line 35 would cause `NullPointerException` at runtime.

## CI/CD

### GitLab CI (`.gitlab-ci.yml`)
- Extends a shared template at `northlane/development/application-development/configuration/ci-templates` (ref `refactor`), file `maven.gitlab-ci.yml`.
- All Maven phases have tests skipped:
  - Build: `mvn ... -Dmaven.test.skip=true`
  - Test: `mvn verify -Dmaven.test.skip=true`
  - Deploy: `mvn deploy -Dmaven.test.skip=true -Dmaven.javadoc.skip=true`
- No explicit stage definitions, Docker image selection, or environment promotions visible in this file (delegated to the shared template).

### GitHub Actions (`.github/workflows/codeql.yml`)
- Runs **CodeQL** static analysis (`Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`).
- Triggers: `workflow_dispatch` (manual) and a weekly cron schedule (`13 5 * * 1` — Mondays at 05:13 UTC).
- Runner: `self-hosted`, `X64`, `Linux`, `ubuntu-docker`.
- Only security scanning; no build/test/publish steps.

### Dependabot (`.github/dependabot.yml`)
- Maven ecosystem, root directory, weekly interval.
- Will propose dependency version bump PRs automatically.
