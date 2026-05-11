# Solution Architect View — nexpay-parent

## Technical Role

The nexpay-parent is a Maven 4 POM artifact that provides dependency management (`<dependencyManagement>`), plugin management (`<pluginManagement>`), and plugin execution configuration for all NexPay Gen-3 services. It inherits from `spring-boot-starter-parent:4.0.5`, which itself inherits from `spring-boot-dependencies` (the official Spring Boot BOM).

## Dependency Management Details

### Managed Dependencies (nexpay-parent-specific)

These are dependencies managed by nexpay-parent but not by the Spring Boot BOM:

| Dependency | Version | Scope |
|---|---|---|
| `com.onbe.api.utils:rest-errors` | 1.0.4 | compile |
| `io.swagger.core.v3:swagger-annotations-jakarta` | 2.2.48 | compile |
| `uk.org.webcompere:system-stubs-jupiter` | 2.1.8 | test |
| `com.azure.spring:spring-cloud-azure-dependencies` | 7.1.0 | pom import |
| `org.springframework.retry:spring-retry` | 2.0.12 | compile |
| `com.fasterxml.jackson.datatype:jackson-datatype-jsr310` | 2.21.2 | compile |
| `org.mapstruct:mapstruct` | 1.6.3 | compile |
| `org.mapstruct:mapstruct-processor` | 1.6.3 | compile |
| `org.projectlombok:lombok-mapstruct-binding` | 0.2.0 | compile |
| `org.springdoc:springdoc-openapi-starter-webmvc-ui` | 3.0.3 | compile |

### Universal Dependencies (applied to all services)

These are in the `<dependencies>` (not `<dependencyManagement>`) section and therefore added to every service:

| Dependency | Scope |
|---|---|
| `org.projectlombok:lombok` | provided |
| `org.springframework.boot:spring-boot-starter-test` | test |
| `org.springframework.boot:spring-boot-starter-opentelemetry` | compile |
| `org.springframework.boot:spring-boot-testcontainers` | test |

The universal inclusion of `spring-boot-starter-opentelemetry` and `spring-boot-testcontainers` means these are not optional in any NexPay service — they are always present in the classpath.

## Annotation Processor Ordering

The compiler plugin configuration establishes a critical ordering:

```xml
<annotationProcessorPaths>
    <path> mapstruct-processor </path>
    <path> lombok </path>
    <path> lombok-mapstruct-binding </path>
</annotationProcessorPaths>
<showWarnings>true</showWarnings>
<compilerArgs>
    <arg>-Amapstruct.verbose=true</arg>
</compilerArgs>
```

The `-Amapstruct.verbose=true` flag causes MapStruct to log detailed mapping decisions during compilation. This is useful for debugging mapper issues but adds compilation log noise. For production CI builds, this could be conditionally disabled.

## Jackson 2.x/3.x Compatibility Layer

The parent POM manages `jackson-datatype-jsr310` at version 2.21.2. However, Spring Boot 4 brings Jackson 3.x. The coexistence of both Jackson versions creates a potential classpath conflict.

The architectural design decision here is to maintain Jackson 2.x for OpenAPI-generated client code (which uses `com.fasterxml.jackson.databind.ObjectMapper` from Jackson 2.x APIs) while Spring Boot 4's autoconfiguration uses Jackson 3.x for the application's own serialisation. This works because the OpenAPI generator creates standalone HTTP clients with their own ObjectMapper configuration, isolated from Spring Boot's main application context ObjectMapper.

However, this design is fragile. If an OpenAPI-generated client is used in a context where Spring Boot's Jackson 3.x ObjectMapper is injected, type serialisation conflicts may occur. Teams must ensure that generated client ObjectMappers are configured independently.

The orchestrator's POM overrides `jackson-datatype-jsr310.version` to `2.18.3` (slightly older than the parent's `2.21.2`), creating a further version divergence. This suggests the version was pinned during development to resolve a specific issue and should be reviewed for alignment.

## OpenAPI Code Generation

The `openapi-generator-maven-plugin` version `7.21.0` is the standard generator across all services. Individual services configure execution goals (generate Spring interfaces for servers, generate RestClient/WebClient for clients). The consistency of the generator version ensures that all generated code has the same structure and import paths, making cross-service code review easier.

## Spring Cloud Azure 7.1.0

Spring Cloud Azure 7.1.0 is imported as a BOM (`pom` scope import in `<dependencyManagement>`). This provides consistent versions for:
- `spring-cloud-azure-starter-appconfiguration-config` — Azure App Configuration
- `spring-cloud-azure-starter-keyvault-secrets` — Azure Key Vault
- `spring-cloud-azure-starter-servicebus` — Azure Service Bus
- `spring-cloud-azure-starter-data-redis` — Azure Cache for Redis

All of these are used across NexPay services. The BOM import ensures they are all compatible with each other and with Spring Boot 4.

## Security Implications of Universal Dependencies

### OpenTelemetry Auto-instrumentation

`spring-boot-starter-opentelemetry` enables OpenTelemetry Java auto-instrumentation. By default, this instruments HTTP clients, JDBC, and other libraries. Auto-instrumentation may capture request/response bodies or SQL query parameters in trace spans depending on the OTel SDK configuration. Teams must verify that OTel span data does not include PII or sensitive payment data, especially given the `BODY_AND_HEADERS` logging level used in some environments.

### Testcontainers in Test Scope

`spring-boot-testcontainers` is test scope, so it does not appear in production artifacts. However, it requires Docker daemon access on CI agents. CI agents should be hardened to prevent container escape vulnerabilities.

### `rest-errors` Internal Library

`com.onbe.api.utils:rest-errors:1.0.4` is an internal Onbe library for standardised error responses. This library is in `compile` scope, meaning it is included in all NexPay service JARs. Any vulnerability or API change in this library requires a parent POM update and re-deployment of all services.

## Recommendations

1. **Release parent to stable version** (0.2.8) before production go-live to ensure reproducible builds.
2. **Define coverage thresholds** in the parent POM's JaCoCo configuration (e.g., `<minimum>0.80</minimum>` for line coverage).
3. **Remove `-Amapstruct.verbose=true`** or make it conditional on a profile to reduce build log noise.
4. **Document Jackson versioning strategy** and create a migration plan to move fully to Jackson 3.x.
5. **Audit OTel configuration** to ensure sensitive data (claim codes, recipient PII) is not captured in trace spans.
6. **Add OWASP Dependency Check plugin** to the parent POM to fail builds on known CVEs in managed dependencies.
