# 03 DevOps & Operations — ecount-core_SVC

## Build System

- Build tool: **Apache Maven** with Maven Wrapper (`.mvn/wrapper/`)
- Java version: **21** (compiler source and target, `pom.xml` lines 35–36)
- Parent POM: `com.parents:prepaid-parent:6.0.13`
- Root packaging: `pom` (multi-module)
- WAR artefact: `eCoreWar` module, final name `service.war` (`eCoreWar/pom.xml` line `<finalName>${deployment.name}</finalName>` with `deployment.name=service`)
- Version: `3.1.9-SNAPSHOT`

Build command:
```
./mvnw clean install
```

Test coverage: JaCoCo (`jacoco-maven-plugin:0.8.12`), generating HTML and CSV reports. Aggregate coverage module is `jacoco-aggregate-coverage`.

Integration tests: `maven-failsafe-plugin:3.1.2` runs `*IT.java` tests separately from unit tests.

## Container / Docker

`eCoreWar/Dockerfile` builds the container image:

1. Base image: `bellsoft/liberica-openjre-alpine:21` (Alpine Linux + Bellsoft OpenJDK 21 JRE)
2. Installs `curl` for health checks
3. Downloads and installs **Apache Tomcat 10.1.42** from the official Apache archive
4. Configures Tomcat properties (property source = environment variables, skip JAR scanning)
5. Copies tomcat-lib JARs (see below), `service.war`, and QA cert
6. Imports QA TLS certificate into the JVM truststore via `keytool`
7. Exposes port 80
8. Sets `CBASE_HOME_URL=file:///cbase` environment variable
9. Sets `JAVA_OPTS` with `--add-opens` for module system compatibility
10. Creates a dedicated OS user `PPA_QA_MQ` in group `NAM` for running the Tomcat process (non-root)
11. Runs `catalina.sh run`

### Tomcat Library JARs copied at build time (`eCoreWar/pom.xml` lines 250–328)
- `commons-logging:1.1.1`
- `slf4j-api`
- `log4j-api`, `log4j-core` (Log4j 2)
- `mssql-jdbc:12.5.0.jre11-preview` (Microsoft SQL Server JDBC)
- `HikariCP:5.1.0`
- `jakarta.jms-api:3.1.0`
- `com.ibm.mq.jakarta.client:9.4.0.0`
- `json:20240303`

## CI/CD Pipeline

No explicit GitHub Actions workflow files were found directly in the repository. The build is likely triggered by a pipeline in a central CI configuration repository (`CONFIG_jenkins-file` or `CONFIG_ci-templates` visible in the broader repo list). The `.mvn/wrapper/settings.xml` configures the Maven repository (Nexus/Artifactory) server credentials.

Dependabot may be active via `.github/dependabot.yml`.

## Version Management

- Root version: `3.1.9-SNAPSHOT`
- All child modules inherit the root version
- The Maven enforcer plugin (`maven-enforcer-plugin`) prevents snapshot dependencies in release builds (with an exclusion for intra-project modules)

## Runtime Deployment

The service is deployed as a WAR to Tomcat 10. The Tomcat `server.xml` (`eCoreWar/config/server.xml`) configures:
- HTTP/1.1 connector on port 80
- JNDI datasource resources (injected from environment)

The `CBASE_HOME_URL` environment variable points to a mounted filesystem directory containing external configuration. In production, this is a volume mount (`/cbase`) containing environment-specific property files.

## IBM MQ Integration

The service integrates with IBM MQ (`com.ibm.mq.jakarta.client:9.4.0.0`) for asynchronous message processing. MQ credentials and queue manager details are expected to be provided via environment variables or `server.xml` JNDI resources. The Dockerfile creates a `PPA_QA_MQ` user in group `NAM` specifically for this integration (following MQ access control patterns used at many financial institutions).

## Dependency Highlights (Security Relevant)

| Dependency | Version | Notes |
|---|---|---|
| Log4j 2 (log4j-api, log4j-core) | Managed by `prepaid-parent` | Replaces Log4j 1.x; must be >= 2.17.1 for Log4Shell mitigation |
| `log4j-1.2-api` | Managed by parent | Bridge for legacy Log4j 1.x API callers |
| `mssql-jdbc` | 12.5.0 (tomcat-lib), 12.8.1 (test, via POM) | Modern Microsoft SQL Server driver |
| `HikariCP:5.1.0` | Tomcat lib | Fast connection pool |
| `spring-security-oauth2-client:6.5.5` | Managed | OAuth2 for Azure AD |
| `springdoc-openapi-starter-webmvc-ui:2.6.0` | Managed | OpenAPI / Swagger UI |
| `guava:33.2.0-jre` | Managed | Google Guava utilities |
| `azure-data-appconfiguration:1.3.0` | Managed | Azure App Configuration client |

## Health Monitoring

`HealthMonitor.xml` indicates a health-monitoring Spring bean is configured. The service likely exposes a health endpoint at `/health` or via Spring Actuator, consumed by load balancers and container orchestration.
