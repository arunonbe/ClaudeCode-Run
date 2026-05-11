# DevOps & Operations Report — onbe-spring-boot

## Build System

- **Build tool:** Apache Maven with Maven Wrapper (`mvnw` / `mvnw.cmd`)
- **Maven wrapper version:** Specified in `.mvn/wrapper/maven-wrapper.properties`
- **Multi-module structure:** 16 modules including core, autoconfigure, reactor, logback, log4j2, data-r2dbc, azure-storage, web, test, and their corresponding starters
- **Java version:** 21 (enforced via `maven-enforcer-plugin` requiring `[21,)`)
- **Kotlin version:** 2.1.10 (language version 2.0)
- **Spring Boot version:** 3.4.3 (inherited from `onbe-spring-boot-parent`)
- **Parent POM:** `com.onbe.spring.boot:onbe-spring-boot-parent:0.0.22-SNAPSHOT`

## CI/CD Pipeline

- **Platform:** GitHub Actions
- **Workflow file:** `.github/workflows/github-package-publish.yml`
- **Reusable workflow:** Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@feature/spring-boot-build-image` — a centralized CI setup repository
- **Trigger:** `workflow_dispatch` (manual) and `pull_request` (opened/synchronize/reopened) targeting `main` branch
- **CodeQL:** Enabled (`CODEQL_QUALITY: true`) for static security analysis
- **Dependency updates:** Disabled in CI (`UPDATE_DEPENDENCIES: false`)
- **Dependabot:** Configured in `.github/dependabot.yml` for automated dependency PRs
- **Maven build flags:** `-P github -Dmaven.test.skip=false -s ./.mvn/wrapper/settings.xml` — tests run, GitHub Packages profile active
- **Artifact publication:** GitHub Packages (Maven registry) — referenced by `settings.xml`

## Deployment Model

This is a library, not a deployable application (`<packaging>pom</packaging>` for the root, library JARs for submodules). It is published to GitHub Packages and consumed as Maven dependencies by other Onbe services. No Dockerfile, Kubernetes manifests, or Azure deployment configuration exists in this repo — deployment of consuming services is handled in their own repos.

## Runtime Environment

- **JVM:** Java 21 (LTS, actively supported — not EOL)
- **Spring Boot:** 3.4.3 (current maintenance stream)
- **Kotlin:** 2.1.10
- **Virtual threads:** Enabled by default in the bundled default YAML configuration
- **Server:** No embedded server in this library. Consuming services use Spring Boot's embedded Tomcat or Netty depending on whether they include `spring-boot-starter-web` (MVC) or `spring-boot-starter-webflux` (Reactor/Netty)

## Secrets Management

- **Runtime secrets:** Dapr sidecar integration (`DaprSecretsConfiguration`) pulls secrets from the configured store (Azure Key Vault in production) at application startup. Secret names are externalized via `dapr.secrets.secrets` list in configuration.
- **Build-time secrets:** `settings.xml` contains credentials for GitHub Packages registry access. These credentials are injected via GitHub Actions `secrets: inherit`.
- **No hardcoded credentials** detected in the source or configuration files.
- **`.env` / `dotenv` support:** `spring-dotenv` (v4.0.0) is managed in the parent POM for local development convenience — not for production use.

## Observability

- **Metrics:** Micrometer with Prometheus exporter configured (`management.endpoint.prometheus.access: read_only`). App name tag attached to all metrics (`app_name: ${spring.application.name}`).
- **Tracing:** Zipkin/OpenTelemetry tracing support included. Sampling probability is 1.0 in local profile; not set in QA/prod (relies on infrastructure-level defaults).
- **Logging:** Structured JSON (Logstash format) for both console and file. Uses `onbe-common-structured-logback-spring.xml` from the logback starter module.
- **Health probes:** Liveness (`/hc/livez`) and readiness (`/hc/readyz`) enabled via Spring Boot Actuator. Exposed endpoints in QA/prod: `health`, `metrics`, `info`, `prometheus`, `appconfiguration-refresh`.
- **Actuator shutdown endpoint:** Disabled (`management.endpoints.web.endpoint.shutdown.enabled: false`).
- **BlockHound:** Optional dependency for detecting illegal blocking calls in reactive code. Conditionally included via `io.projectreactor.tools:blockhound`.

## EOL Runtimes / CVE Concerns

- Java 21 is LTS and actively maintained — no EOL risk.
- Spring Boot 3.4.3 is current — no known critical CVEs at time of analysis.
- `lmax-disruptor` is pinned at 3.4.4 with an explicit comment "Do not upgrade to 4.x until Spring Boot/Log4j2 supports it" — this is a known intentional version hold, not a neglected dependency, but should be tracked as Spring Boot adds Log4j2 4.x support.
- Kotlin 2.1.10 is current stable.
- The reusable CI workflow references `@feature/spring-boot-build-image` branch (not `@main`) — this is flagged in a comment as "for testing" and should be pinned to a stable ref in production workflows.
- CycloneDX SBOM is generated at package phase — this enables downstream vulnerability scanning with tools like Dependency-Track.
