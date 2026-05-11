# DevOps / Operations Analysis: rubens-playground-ms

## Build System
- **Maven** single-module (mvnw wrapper present); POM schema version 4.1.0
- **Java**: Not explicitly set; parent `nexpay-parent:0.1.10-SNAPSHOT` likely provides Java 21+
- **Dockerfile**: Uses `eclipse-temurin:25-jdk-alpine` for build stage and `eclipse-temurin:25-jre-alpine` for runtime — **Java 25** (pre-release/EA as of analysis date)
- **Parent POM**: `com.onbe.nexpay:nexpay-parent:0.1.10-SNAPSHOT`
- **Artifact**: `com.onbe.stablerails:orders-api-ms:0.0.1-SNAPSHOT`
- **OpenAPI Code Generation**: `openapi-generator-maven-plugin:7.18.0` generates Spring delegate pattern code from `ordersapi.yml` at build time

## Build Outputs
| Output | Purpose |
|---|---|
| `orders-api-ms-0.0.1-SNAPSHOT.jar` | Spring Boot fat JAR |
| Docker image `orderapims:latest` | Container image |
| Generated sources in `target/generated-sources/` | OpenAPI-generated API interface + models |

## Deployment
- **Packaging**: Spring Boot fat JAR; containerised with Docker (multi-stage Dockerfile).
- **Runtime**: `eclipse-temurin:25-jre-alpine` — JRE 25 minimal image.
- **Container security**: Non-root user (`appuser`/`appgroup`) created and used — good practice.
- **Port**: 8080 exposed.
- **Health check**: `curl -f http://localhost:8080/actuator/health` (Dockerfile `HEALTHCHECK` + docker-compose `healthcheck`).
- **Target deployment**: Azure Container Apps (implied by `app.smartlink.baseUrl` default pointing to `ca-stablerails-mpv.mangoground-2a18d99d.eastus2.azurecontainerapps.io`).
- **docker-compose**: Local development setup; `network_mode: host` (all container traffic on host network).

## Configuration Management
- All runtime configuration via environment variables (12-factor app pattern):
  | Env Var | Purpose | Default |
  |---|---|---|
  | `SENDGRID_API_KEY` | SendGrid API key | None (required) |
  | `SENDGRID_FROM_EMAIL` | Sender email | `noreply@onbe.com` |
  | `SENDGRID_FROM_NAME` | Sender name | `Onbe StableRails` |
  | `SENDGRID_ENABLED` | Enable/disable email | `true` |
  | `SPRING_PROFILES_ACTIVE` | Spring profile | `dev-local` |
  | `JAVA_OPTS` | JVM options | `-Xmx512m` |
  | `DB_HOST` | DB hostname | `localhost` |
  | `DB_USER` | DB username | `postgres` |
  | `DB_PASSWORD` | DB password | `postgres` |
  | `app.smartlink.baseUrl` | Smart link base URL | Azure Container Apps URL |

- Spring Boot application properties file(s) in `src/main/resources/` (not read during this analysis but present via convention).
- Liquibase manages schema via `spring-boot-starter-liquibase`.

## Observability
- **Health check**: `/actuator/health` (Spring Boot Actuator) — active.
- **Structured logging**: SLF4J + Lombok `@Slf4j`; JSON logging likely configured via parent POM.
- **Request logging**: `log.info("createOrder with program: {}, accessLevel: {}, currency: {}", ...)` — structured parameters.
- **No distributed tracing**: No OpenTelemetry or Zipkin dependency visible.
- **No custom metrics**: No Micrometer custom gauges/counters beyond default Actuator metrics.
- **Debug logging**: `log.debug("createOrderRequest: {}", createOrderRequest)` — full request object logged at DEBUG; `Order.toString()` at line 43 would log all fields including name, DOB, address, email at DEBUG level if enabled.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|---|---|---|
| PostgreSQL | Database | Required for `dev`, `qa`, `prod` profiles |
| H2 | Embedded DB | Used for local dev and tests |
| SendGrid | External SaaS | Email delivery; API key required |
| Azure Container Apps | Cloud compute | Target deployment platform |
| `nexpay-parent:0.1.10-SNAPSHOT` | Parent POM | Provides Spring Boot BOM and common dependencies |

## Operational Risks
1. **Java 25 (EA/pre-release)**: `eclipse-temurin:25-*-alpine` — Java 25 is a pre-release JDK; using it in any environment that handles real data is a stability and support risk.
2. **SNAPSHOT parent and artifact version**: Both `nexpay-parent:0.1.10-SNAPSHOT` and `orders-api-ms:0.0.1-SNAPSHOT` are snapshots — not production-ready versioning.
3. **`DB_PASSWORD=[REDACTED — rotate immediately]` default**: docker-compose default is the well-known postgres password — must never be used in any non-local environment.
4. **`network_mode: host`** in docker-compose: Container shares host network — appropriate for local dev only; not suitable for production.
5. **Debug logging of full Order object**: `Order.toString()` logs all PII fields including DOB, address, phone, email at DEBUG level; if DEBUG is enabled in any non-dev environment, PII appears in logs.
6. **Playground classification**: Service named "playground" — operational governance must prevent production cardholder data from being processed here.
7. **springdoc-openapi-starter-webmvc-ui version 3.0.0**: Check for CVEs; version 3.0.0 may be a milestone/non-release.

## CI/CD
No Jenkinsfile or GitLab CI YAML found. The `AZURE_CLOUD_SETUP.md` file and Azure Container Apps target suggest manual deployment or an Azure Pipelines/GitHub Actions pipeline not committed to this repo.

The `Dockerfile` is multi-stage with `--build-arg GITHUB_USER` / `GITHUB_TOKEN` arguments, suggesting GitHub Packages is used for Maven dependency resolution, and a CI pipeline provides these credentials at build time.
