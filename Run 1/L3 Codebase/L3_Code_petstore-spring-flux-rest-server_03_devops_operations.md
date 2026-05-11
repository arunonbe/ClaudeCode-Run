# DevOps & Operations Report — petstore-spring-flux-rest-server

## Build System

- **Build tool:** Apache Maven with Maven Wrapper (`mvnw`)
- **Parent POM:** `com.onbe.spring.boot:onbe-spring-boot-parent:0.0.22-SNAPSHOT`
- **Java version:** 21
- **Multi-module structure:** 3 modules — `petstore-spring-flux-rest-server-api` (OpenAPI-generated interfaces), `petstore-spring-flux-rest-server-impl` (business logic), `petstore-spring-flux-rest-server-boot` (Spring Boot fat JAR, Docker packaging)
- **Maven config:** `.mvn/maven.config` — contains Maven build arguments applied to all executions (content not read, but standard pattern includes `-s settings.xml` for GitHub Packages auth)
- **Maven wrapper JAR:** `.mvn/wrapper/maven-wrapper.jar` is committed (older pattern; newer Maven wrappers use a download script instead) — review for wrapper integrity

## CI/CD Pipeline

**Workflow:** `.github/workflows/deployment.yml`

This is a full deployment pipeline:
- **Trigger:** Pull request (opened/synchronize/labeled on selected paths) or push to `main`
- **Reusable workflow:** `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@feature/spring-boot-build-image` (note: `@feature/...` branch — not pinned to a stable ref)
- **Application name:** `petstoreflux`
- **Pact pacticipant:** `petstoreflux-api` (consumer-driven contract testing)
- **APIM publication:** Internal APIM only (`INTERNAL_APIM: true`, `EXTERNAL_APIM: false`)
- **Docker image tag:** `0.5.1` (static — does not use `${project.version}`)
- **Container scan:** Disabled (`CONTAINER_SCAN: false`) with comment "container scan frequently fails, so disabling it temporarily"
- **CodeQL:** Enabled
- **Maven args:** `-q -s .mvn/wrapper/settings.xml -Dmaven.test.skip=false -U -P github`
- **OpenAPI spec path:** `petstore/v2/petstore-expanded-openapi.yaml` (downloaded from central openapi-doc repo)

**Additional workflow:** `.github/workflows/codeql.yml` — scheduled weekly CodeQL scan (Wednesdays, 08:23 UTC)

**Additional workflow:** `.github/workflows/app-config.yml` — likely Azure App Configuration update workflow

## Deployment Model

**Containerized deployment to Azure (AKS or Azure Container Apps):**

Dockerfile: `petstore-spring-flux-rest-server-boot/Dockerfile`
- Base image: `bellsoft/liberica-openjre-alpine:21` (BellSoft Liberica JRE 21 on Alpine Linux)
- Entrypoint: `/bin/bash -c "source ./startup.sh; java $JAVA_TOOL_OPTIONS -jar ./${JAR_NAME}"`
- Initial heap: `-Xms512m`
- `startup.sh` is sourced before JVM launch — contains environment-specific initialization (content not included in Dockerfile review)
- No `EXPOSE` directive — port is configured at application level

**Docker Compose:** `compose.yaml` — used for local development with SQL Server container

**Dapr sidecar:** `dapr-components/` directory contains `local-secret-store.yaml` and `dapr-secrets.json` for local Dapr development. In production, the Dapr sidecar is injected by Kubernetes.

**Azure App Configuration:** `app-config/qa/appsettings.json` — QA environment App Configuration settings (Azure App Configuration stores).

## Runtime Environment

- **JVM:** Java 21, BellSoft Liberica OpenJRE (Alpine variant)
- **Spring Boot:** 3.4.3 (via parent)
- **Reactive runtime:** Project Reactor / Spring WebFlux (Netty embedded server)
- **Database:** Microsoft SQL Server (R2DBC reactive driver)
- **Dapr sidecar:** Required at runtime for secrets loading (enabled by default in `application.yaml`)
- **Port (production):** Port 80 (from onbe-spring-default.yaml in QA/prod profile)
- **Port (local):** Not explicitly configured in application.yaml — Spring Boot default (8080) likely

## Secrets Management

- **Database credentials:** `SPRING_R2DBC_USERNAME` loaded from Dapr secret store. Database password not listed in secrets configuration — verify separately.
- **Merchant enrichment token:** `MERCHANTENRICHMENT_TRIPLE_APITOKEN` loaded from Dapr secret store.
- **Local development secrets:** `dapr-components/dapr-secrets.json` — file-based local secret store (values are development placeholders; not actual credentials)
- **GitHub Packages:** Settings.xml-based with CI-injected credentials (`secrets: inherit`)

## Observability

- **Logging:** Structured Logstash JSON (from `onbe-spring-boot-starter-logback`)
- **Log correlation test:** `LogCorrelationTests.java` explicitly tests that trace IDs are included in log output — demonstrating correct distributed tracing log correlation
- **Metrics:** Micrometer + Prometheus (from `onbe-spring-default.yaml`)
- **Tracing:** Brave tracer injected into `PetStoreConfig` — indicates Spring Cloud Sleuth/Micrometer Tracing integration
- **Health probes:** `/hc` (liveness/readiness) via Spring Boot Actuator
- **BlockHound:** `BlockHoundTests.java` verifies no blocking calls in reactive code path
- **Container scan:** Currently disabled in CI — this is a gap

## EOL / Risk Assessment

- **`bellsoft/liberica-openjre-alpine:21`:** No `:latest` or date-pinned digest — using a floating tag means the base image content may change between builds. Pin to a specific digest for reproducible builds.
- **Container scan disabled:** `CONTAINER_SCAN: false` means CVEs in the container image (including Alpine OS packages and JRE vulnerabilities) are not being detected. This must be re-enabled — the "temporarily" comment has no target date.
- **Maven wrapper JAR committed:** The `maven-wrapper.jar` in `.mvn/wrapper/` is a binary artifact in source control. This is a known supply chain risk (the JVM executes this JAR during build). The modern approach uses a script-based wrapper. Verify the JAR's checksum against the official Maven wrapper release.
- **`@feature/spring-boot-build-image` CI workflow reference:** Non-stable branch reference in production CI — should be pinned to `@main` or a tagged release.
- **Static Docker tag `0.5.1`:** Does not auto-increment with the application version. This could lead to tag collisions or confusion about which code version is in a container.
