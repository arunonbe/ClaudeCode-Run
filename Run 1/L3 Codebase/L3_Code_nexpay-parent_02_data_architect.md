# Data Architect View — nexpay-parent

## Data Architecture Role

The nexpay-parent POM does not directly manage data — it manages the tools and libraries through which data is managed. Its data architecture significance lies in the dependency choices that determine how every NexPay service structures, maps, validates, and serialises its data.

## Object Mapping Layer

### MapStruct 1.6.3

MapStruct is the mandated object mapping library. All NexPay services use MapStruct-generated mappers for converting between:
- API DTOs (generated from OpenAPI specs) and domain objects
- Domain objects and JPA entities

MapStruct generates type-safe mapping code at compile time, avoiding reflection-based runtime mapping (unlike ModelMapper or Dozer). This is important for a payments platform because:
1. Compile-time errors catch data model mismatches before deployment.
2. No runtime reflection means mappers cannot accidentally expose or leak sensitive fields through dynamic property access.
3. The generated code is auditable — reviewers can inspect exactly what fields are mapped and how.

The parent POM configures the MapStruct processor via the annotation processor path in `maven-compiler-plugin`:

```xml
<annotationProcessorPaths>
    <path> mapstruct-processor </path>
    <path> lombok </path>
    <path> lombok-mapstruct-binding </path>
</annotationProcessorPaths>
```

The `lombok-mapstruct-binding` (version 0.2.0) is required to ensure Lombok generates builder methods before MapStruct generates mapping code. Without this binding, MapStruct cannot see Lombok-generated constructors and produces compilation errors.

## Serialisation Layer

### Jackson 3.x (via Spring Boot 4)

Spring Boot 4 ships with Jackson 3.x as its default JSON serialiser/deserialiser. Jackson 3.x has breaking changes from Jackson 2.x, particularly around JSR-310 (Java 8+ date/time) module handling.

The parent POM explicitly manages `jackson-datatype-jsr310` version 2.21.2 for compatibility with OpenAPI-generated client code that was generated against Jackson 2.x APIs. The comment in the POM explains: "needed for OpenAPI generated clients." The orchestrator's own POM overrides this to 2.18.3 for similar reasons.

This dual-version Jackson situation is a data serialisation risk: if a service uses Jackson 3.x for its own serialisation while the OpenAPI client uses Jackson 2.x, date/time fields may be serialised differently across service boundaries. This should be monitored for serialisation divergence, particularly for `OffsetDateTime` fields used in payment timestamps.

## API Contract Generation

### OpenAPI Generator 7.21.0

All NexPay services generate their Spring controller interfaces and REST clients from OpenAPI 3.0 YAML specifications using the OpenAPI Generator Maven plugin. This means:
- The API contract (YAML) is the single source of truth for data models.
- DTOs are generated code — developers do not hand-write them.
- Any change to the API spec requires a regeneration and recompile, making backward-incompatible contract changes immediately visible.

The parent POM defines the plugin version but individual services configure the generator execution (generator name, API package, model package, additional properties). The `merge-yaml-plugin` (version 1.4) is also available for merging multiple YAML spec files, which is useful for composing a service's OpenAPI spec from shared components.

### Swagger/OpenAPI Annotations

`swagger-annotations-jakarta` version 2.2.48 is managed. The switch from `javax` to `jakarta` namespace is complete across the platform (Spring Boot 4 uses Jakarta EE 11).

## Test Data Infrastructure

### Testcontainers

`spring-boot-testcontainers` is included as a test-scope dependency across all services. This means all NexPay services can spin up real containerised database instances (PostgreSQL), message brokers (Redis, Azure Service Bus emulator), or other infrastructure during integration tests without mocking.

The data architecture benefit is significant: tests run against the same database dialect as production (PostgreSQL), avoiding the SQL dialect mismatch that plagues services using H2 in-memory databases for testing.

### System Stubs

`system-stubs-jupiter` version 2.1.8 provides environment variable substitution in tests. This is useful for testing code paths that depend on `System.getenv()` calls without modifying the JVM process environment.

## Observability Data

### OpenTelemetry

`spring-boot-starter-opentelemetry` is a universal dependency (non-test scope) for all NexPay services. This means every service emits:
- **Traces**: Distributed traces propagated via W3C TraceContext headers across service boundaries.
- **Metrics**: JVM metrics, HTTP request metrics, and custom application metrics.
- **Logs**: Correlated logs with trace and span IDs injected.

The observability data from all NexPay services flows to a centralised OTLP collector endpoint (`${OTEL_EXPORTER_OTLP_ENDPOINT}`). This provides the data foundation for distributed tracing of disbursement flows across services — essential for incident investigation and compliance evidence.

## Build Metadata

The parent POM's build produces:
- Source encoding: UTF-8 (explicit, preventing locale-dependent compilation behaviour)
- JaCoCo coverage reports in `target/site/jacoco/` for each module
- Aggregate JaCoCo report (`report-aggregate` goal) for combined coverage across submodules

The aggregate coverage report is the mechanism by which overall test coverage is measured for PCI DSS compliance purposes.

## Data Integrity Controls Built Into the Parent

1. **Enforcer plugin**: Prevents builds with Java < 25 or Maven < 4.0.0-rc-5 — ensures all services use the same security-patched compiler.
2. **Versions plugin**: Manages version reporting and `versions:use-latest-releases` for systematic upgrades.
3. **Failsafe/Surefire separation**: Integration tests (IT) and unit tests run in separate phases, ensuring that integration test failures don't mask unit test results.
