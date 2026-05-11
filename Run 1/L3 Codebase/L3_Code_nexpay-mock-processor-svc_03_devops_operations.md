# DevOps & Operations — nexpay-mock-processor-svc

## Build
- Build tool: Maven Wrapper (`mvnw`) with Spring Boot Maven Plugin.
- Parent POM: `org.springframework.boot:spring-boot-starter-parent:4.0.2`.
- Java version: 25 (early-access at time of writing).
- Produces fat JAR: `nexpay-mock-processor-server-1.0.0-SNAPSHOT.jar`.
- No multi-module structure — single Maven module.

## Deployment
- Containerised: `Dockerfile` uses `bellsoft/liberica-openjre-alpine:25` base image.
- JAR copied to `/app`; exposed port `8085`.
- `JAVA_TOOL_OPTIONS="-Xms256m"` — only minimum heap set; no `-Xmx`.
- `docker-compose.yml` defines a single service `nexpay-mock` with a bridge network `nexpay-mock-network`.
- Volume `./logs:/app/logs` mounted for log persistence.
- Health check: `wget -q --spider http://localhost:8085/actuator/health` every 20 s, 3 retries, 45 s start period.

## Configuration Management
- Single `application.yaml`; no profile-specific overrides.
- SQLite datasource URL is hardcoded: `jdbc:sqlite:mock-responses.db`.
- No external config store (no Azure App Configuration, no Spring Cloud Config).
- Container-level environment variable `SPRING_PROFILES_ACTIVE=default` set in docker-compose.

## Observability
- Spring Boot Actuator exposed: `health`, `info`.
- Log format: Logstash structured JSON (`logging.structured.format.file: logstash`).
- Log level: `ROOT=ERROR`, `com.onbe.nexpay.mock=ERROR` — minimal logging in all profiles.
- No distributed tracing (no OTEL, no Micrometer tracing configured).
- No metrics export endpoint.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| SQLite | Embedded file DB | `mock-responses.db` local to container |
| Docker / Docker Compose | Container runtime | For local/test deployment |
| bellsoft/liberica-openjre-alpine:25 | Base image | JRE only; Alpine Linux |

## CI/CD
- GitHub Actions workflow: `codeql.yml` — CodeQL static analysis only; delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
- Dependabot configured (`.github/dependabot.yml` present).
- No build/test/deploy workflow observed — this repo appears to rely on manual Docker build or is treated as a developer-local tool.
- Maven Wrapper `settings.xml` references an internal Nexus repository for dependency resolution.

## Operational Risks
- No `-Xmx` JVM flag — unbounded heap growth in the container.
- SQLite file stored inside the container filesystem by default; data lost on container replacement unless volume-mounted.
- Port 8085 is fixed and not configurable without modifying YAML — port conflict risk.
- Spring Boot 4.0.2 / Java 25 are pre-release; stability and security patch cadence unknown.
- No secrets management: no credentials required, but any future expansion must not embed secrets in YAML.
