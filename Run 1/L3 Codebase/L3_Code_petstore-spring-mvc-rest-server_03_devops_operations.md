# DevOps / Operations View — petstore-spring-mvc-rest-server

## Build System

- **Build tool**: Maven with Maven Wrapper (`mvnw`, `mvnw.cmd`)
- **Multi-module structure**:
  - `petstore-spring-mvc-rest-server-api` — OpenAPI-generated model/interface module
  - `petstore-spring-mvc-rest-server-impl` — implementation module (controllers, services, config)
  - `petstore-spring-mvc-rest-server-boot` — Spring Boot executable module (fat JAR + container image)
- **Parent POM**: `com.onbe.petstore:petstore-spring-mvc-rest-server:0.0.1-SNAPSHOT`
- **onbe-spring-boot-starter**: Custom Onbe Spring Boot starter provides platform defaults (logging, security, observability)
- **SBOM**: CycloneDX Maven plugin configured in boot module for software bill of materials generation
- **Spring Boot Maven Plugin**: used for OCI image build via Cloud Native Buildpacks
- **Test frameworks**: JUnit 5, ArchUnit, Spring Modulith test, Onbe test starter (`onbe-spring-boot-starter-test`)
- **System Stubs**: `system-stubs-jupiter` for environment variable injection in tests

## CI/CD Pipeline

- **Platform**: GitHub Actions
- **Workflow files**:
  - `.github/workflows/deployment.yml` — main build and deploy pipeline
  - `.github/workflows/codeql.yml` — CodeQL static analysis (Java)
- **Reusable workflow**: references `Onbe/om-ci-setup` (specific ref not shown in available config)
- **Triggers**: push to `main`, pull request to `main`
- **Dependabot**: `.github/dependabot.yml` configures automated dependency update PRs
- **Container scan**: `.github/containerscan/allowedlist.yaml` for Trivy CVE allowlist

## Deployment Model

- **Artifact**: OCI container image built via Spring Boot Maven Plugin (Cloud Native Buildpacks)
- **Runtime**: Containerized Spring Boot fat JAR in AKS
- **Dockerfile**: `petstore-spring-mvc-rest-server-boot/Dockerfile` and `Dockerfile-ssl` (SSL-enabled variant)
- **Compose**: `compose.yaml` for local development with Docker Compose (SQL Server, Redis, RabbitMQ)
- **Buildpacks environment**: timezone (`America/New_York`), locale (`en_US.UTF-8`) set via BPE variables
- **SSL certificates**: `bindings/ca-certificates/wirecard.pem` — Wirecard/Northlane CA certificate bundled for internal TLS trust

## Runtime

- **Java**: 21 (set via Spring Boot parent POM)
- **Spring Boot**: 3.x (inferred from Jakarta namespace, Java 21 requirement, `onbe-spring-boot-starter`)
- **Spring Cloud Azure**: Key Vault Secrets, App Config Feature Management
- **Spring Cloud Stream**: Azure Service Bus and/or RabbitMQ binders
- **Spring Modulith**: module structure enforcement
- **Resilience4j**: circuit breaker, rate limiter, time limiter
- **QueryDSL**: 5.x (Jakarta-compatible)
- **Redis**: Lettuce client with optional SSL

## Secrets Management

- **Azure Key Vault**: primary secret store for production/QA secrets (endpoint: `kv-az1-cluster-qa-ss.vault.azure.net`)
  - Secrets loaded: `mysecret`, `mypaymentvaultapi-cbaseappdb-username`
- **Dapr sidecar**: `local-secret-store` Dapr component for local development secrets
  - Secrets: `SPRING_R2DBC_USERNAME`, `MERCHANTENRICHMENT_TRIPLE_APITOKEN`
- **Environment variables**: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_SSL_ENABLED`, `AZURE_SERVICEBUS_NAMESPACE` injected at runtime
- No secrets in source code or configuration files committed to repository

## Observability

- **Logging**: SLF4J / Logback via `onbe-spring-boot-starter`; `logback-test.xml` in test resources; `debug: true` in local profile (must not be production)
- **Spring Boot Actuator**: included via `onbe-spring-boot-starter` (inferred from platform standard)
- **Resilience4j health indicators**: circuit breaker and rate limiter register health indicators (`register-health-indicator: true`)
- **Spring Cloud Stream metrics**: event consumer buffer and writable stack traces enabled for debugging
- **ArchUnit tests**: enforce architectural correctness at build time — failures block CI

## Known EOL Runtimes and CVEs

- `0.0.1-SNAPSHOT` version — not production-ready; this is the intended status for an exemplar
- `wirecard.pem` CA certificate bundled in `bindings/ca-certificates/` — this is a legacy Wirecard/Northlane CA. Certificate expiry must be monitored; if Wirecard's CA has been rotated, this certificate may already be stale.
- Local profile config has `encrypt: false` and `trustServerCertificate: true` for SQL Server — **must not be present in production builds**. The CI pipeline must validate that production profiles do not inherit these insecure defaults.
- `debug: true` in local profile — must not be present in production; Spring debug logging can expose configuration, request parameters, and bean wirings.
- Rate limiter configured at 1 request/minute for `petstore` backend — this is a demonstration value; production services must configure appropriate limits based on expected load.
