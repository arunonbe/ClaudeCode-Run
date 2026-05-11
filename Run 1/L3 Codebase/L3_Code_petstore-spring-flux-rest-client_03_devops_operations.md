# DevOps & Operations Report — petstore-spring-flux-rest-client

## Build System

- **Build tool:** Apache Maven with Maven Wrapper (`mvnw`)
- **Parent POM:** `com.onbe.spring.boot:onbe-spring-boot-parent:0.0.22-SNAPSHOT`
- **Java version:** 21
- **Multi-module structure:** 3 modules:
  - `petstore-spring-flux-rest-client-api` — OpenAPI-generated WebClient client interfaces
  - `petstore-spring-flux-rest-client-impl` — Client wrapper, WebClient customizer, configuration
  - `petstore-spring-flux-rest-client-boot` — Spring Boot application, tests, test resources
- **Key dependencies:** `onbe-spring-boot-starter`, `onbe-spring-boot-starter-test`

## CI/CD Pipeline

**Workflows:**
- `.github/workflows/github-package-publish.yml` — Package publication to GitHub Packages (PR and manual trigger)
- `.github/workflows/codeql.yml` — Scheduled weekly CodeQL analysis
- `.github/dependabot.yml` — Automated dependency update PRs

**`github-package-publish.yml` details:**
- Reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@feature/spring-boot-build-image` (non-stable branch ref)
- CodeQL enabled (`CODEQL_QUALITY: true`)
- Tests run (`-Dmaven.test.skip=false`)
- Profile: `github` (for GitHub Packages registry)

Notable: Unlike `petstore-spring-flux-rest-server`, the client repo does **not** have a deployment workflow — it publishes as a library/artifact, suggesting it is consumed as a dependency by other services rather than being deployed independently.

## Deployment Model

The client application appears to be published to GitHub Packages as a Maven library (similar to `onbe-spring-boot`). Consuming services import the client API artifact (`petstore-spring-flux-rest-client-api`) to get the generated WebClient stubs. The boot module serves as a demo application that exercises the client in a complete Spring Boot context.

If the boot module is deployed as a standalone application, it has no Dockerfile or deployment workflow — it would require the consuming team to add their own containerization. The `compose.yaml` in the boot module suggests it's primarily used for local development with Docker Compose.

## Runtime Environment

- **JVM:** Java 21 (virtual threads enabled: `spring.threads.virtual.enabled: true`)
- **Spring Stack:** Spring WebFlux (reactive) — Netty embedded server
- **Port:** 8080 (local)
- **Dependencies at runtime:**
  - WebClient connection: Target Petstore server (configurable via `petstore.webclient.base-url`)
  - Dapr sidecar: If Dapr secrets are configured (test uses local-secret-store)
  - Testcontainers: Docker daemon for integration tests (ACR image pull tests require Azure credentials)

## Secrets Management

- **Runtime secrets:** Dapr integration via `dapr-secrets.json` (local test only). Production would use Dapr + Azure Key Vault.
- **API authentication:** Not implemented in the reference — in production, the WebClient would need to inject an `Authorization` header (OAuth 2.0 Bearer token or API key) as a `defaultHeader` or `ExchangeFilterFunction`.
- **ACR image pull credentials:** `PetStoreAcrImageTestContainerTests` pulls images from Azure Container Registry. ACR credentials must be available to the test execution environment (CI runner must have MSI or service principal access to the ACR).
- **No hardcoded credentials** detected in source files reviewed.

## Observability

- **Micrometer Observation:** `ObservationRegistry` wired into `WebClient.Builder` for automatic HTTP client span recording.
- **Logging:** Structured Logstash JSON (from `onbe-spring-boot-starter` defaults). Test resources include both `log4j2-test.xml` and `logback-spring-test.xml` — suggesting the test configuration exercises both logging backends.
- **Tracing:** WebClient automatically propagates trace context (W3C TraceContext / Zipkin B3) when `ObservationRegistry` is configured.
- **Metrics:** Micrometer HTTP client metrics automatically captured when `ObservationRegistry` is set.
- **No health endpoint configured** in the client's `application.yaml` — as a library/client, this may be intentional if the boot module is not deployed as a standalone health-checkable service.

## EOL / Risk Assessment

- Java 21: LTS, actively maintained — no risk.
- Spring Boot 3.4.3: Current — no risk.
- `@feature/spring-boot-build-image` CI ref: Non-stable branch — same risk as other repos in the fleet.
- `onbe-spring-boot-parent:0.0.22-SNAPSHOT`: SNAPSHOT parent — non-reproducible builds, as discussed in the parent repo analysis.
- No Docker image produced — no container scanning gap.
- ACR integration tests require Docker daemon and Azure credentials — may fail in environments without Docker or Azure access, reducing test reliability in some CI configurations.
- `WireMock` tests: WireMock 3.12.0 (managed in parent) — current stable version, low risk.
