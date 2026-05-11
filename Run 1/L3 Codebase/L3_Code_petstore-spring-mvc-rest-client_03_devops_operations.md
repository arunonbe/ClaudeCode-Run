# DevOps & Operations Report — petstore-spring-mvc-rest-client

## Build System

- **Build tool:** Apache Maven with Maven Wrapper (`mvnw`)
- **Parent POM:** `com.onbe.spring.boot:onbe-spring-boot-parent:0.0.22-SNAPSHOT`
- **Java version:** 21
- **Multi-module structure:** 3 modules:
  - `petstore-spring-mvc-rest-client-api` — OpenAPI-generated synchronous client interfaces/models
  - `petstore-spring-mvc-rest-client-impl` — `AppConfig`, `RestClientConfigProperties`, `PetStoreRestClientCustomizer`
  - `petstore-spring-mvc-rest-client-boot` — Spring Boot application entry point, test resources, `log4j2-spring.xml`
- **Key dependencies:** `onbe-spring-boot-starter`, `onbe-spring-boot-starter-test`

## CI/CD Pipeline

**Workflows:**
- `.github/workflows/github-package-publish.yml` — Package publication to GitHub Packages (triggered on PR to `main` and `workflow_dispatch`)
- `.github/workflows/codeql.yml` — Scheduled weekly CodeQL analysis
- `.github/dependabot.yml` — Automated dependency update PRs

**`github-package-publish.yml` details:**
- Reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@feature/spring-boot-build-image` (non-stable feature branch)
- CodeQL enabled
- Tests run (`-Dmaven.test.skip=false`)
- GitHub Packages profile active

No deployment workflow — same as the WebFlux client repo. This is a library/reference, not a standalone deployed service.

## Deployment Model

As with `petstore-spring-flux-rest-client`, this appears to be published to GitHub Packages as a Maven library. The `-api` module is the primary consumable artifact. The boot module provides a runnable demo but lacks a Dockerfile and deployment workflow.

The `compose.yaml` in the boot module enables local development with Docker Compose for running the service alongside a Petstore server and any required infrastructure.

## Runtime Environment

- **JVM:** Java 21 (LTS)
- **Thread model:** Virtual threads enabled (`spring.threads.virtual.enabled: true`) — blocking I/O on virtual threads is efficient. This is the key Gen-3 improvement that makes `RestClient` (blocking) viable for high-throughput scenarios without requiring reactive programming.
- **Spring stack:** Spring MVC (not WebFlux) — Tomcat embedded server (the MVC default)
- **Port:** 8080 (local)
- **HTTP client factory:** `SimpleClientHttpRequestFactory` (non-pooled, basic `HttpURLConnection`-based)
- **Logging framework:** Log4j2 with async loggers (LMAX Disruptor required for `asyncRoot`/`asyncLogger`)

## Secrets Management

No Dapr integration in the application layer (no Dapr components directory, no `dapr.secrets` configuration). The MVC client does not appear to use Dapr for secrets at the application level — a gap compared to the WebFlux server and client references which both demonstrate Dapr integration.

For a production payment API client, secrets management would need to be added:
- Option 1: Add Dapr sidecar with `dapr.secrets.enabled=true` (consistent with other Gen-3 services)
- Option 2: Use Azure App Configuration as the secrets source (requires `spring-cloud-azure-appconfiguration-config` dependency)
- Option 3: Use Kubernetes secrets injected as environment variables (least preferred — no rotation without pod restart)

## Observability

- **Logging:** Log4j2 with async loggers. **Important conflict:** The boot module defines a `log4j2-spring.xml` that uses pattern-layout (non-Logstash JSON format) for `staging`/`prod` profiles. This contradicts the `onbe-spring-default.yaml` from `onbe-spring-boot` which mandates `logging.structured.format.console: logstash`. The Log4j2 configuration file will take precedence over the Spring Boot YAML logging configuration when present. The result in production would be non-structured logs, breaking SIEM/Logstash parsing.
- **Micrometer Observation:** `PetStoreRestClientCustomizer` wires `ObservationRegistry` for automatic HTTP client span recording.
- **Tracing:** Micrometer tracing with Spring Boot's auto-configured trace context propagation (W3C TraceContext).
- **No health endpoint:** Like the WebFlux client, no Spring Boot Actuator configuration is shown in the MVC client's `application.yaml`.
- **No Prometheus metrics endpoint:** Not explicitly configured, though it would be available if the actuator is on the classpath.

## EOL / Risk Assessment

- Java 21: LTS, no EOL risk.
- Spring Boot 3.4.3: Current, no EOL risk.
- Spring MVC + Tomcat: Current, no EOL risk. Tomcat 10.1.x is the embedded version in Spring Boot 3.4.x.
- `SimpleClientHttpRequestFactory`: Based on `HttpURLConnection` (JDK built-in) — technically EOL-agnostic since it's part of the JDK, but is the least capable HTTP factory for production use (no HTTP/2, no connection pooling, limited TLS configuration).
- Log4j2: Version managed in parent (`lmax-disruptor:3.4.4` for async logging). The parent comment notes Log4j2 4.x is intentionally held. Current Log4j2 3.x is used via Spring Boot's managed version.
- `@feature/spring-boot-build-image` CI ref: Non-stable, same fleet-wide risk as other repos.
- SNAPSHOT parent: Non-reproducible builds, same fleet-wide risk.
