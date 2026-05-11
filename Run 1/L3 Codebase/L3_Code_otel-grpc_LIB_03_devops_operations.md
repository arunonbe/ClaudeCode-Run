# DevOps & Operations — otel-grpc_LIB

## Build
- **Build tool**: Apache Maven (POM 4.1.0 — note: Maven POM 4.1.0 is a future/unreleased schema version as of mid-2026; may indicate forward-looking configuration).
- **Java**: 25 (`maven.compiler.source/target=25`).
- **Artifact**: JAR (`otel-grpc-1.0.0-SNAPSHOT.jar`); `packaging=jar`.
- **Wrapper**: `mvnw` / `mvnw.cmd` present.
- **Lombok**: Annotation processor path configured in `maven-compiler-plugin`.
- **No CI/CD file** found in repository root.
- **Key version pins**:
  - `grpc-bom: 1.79.0`
  - `micrometer-bom: 1.16.4`
  - `opentelemetry-bom: 1.60.1`
  - `spring-boot-dependencies: 4.0.3`
  - `opentelemetry-logback-appender-1.0: 2.26.0-alpha` (alpha dependency in production library)

## Deployment
- This is a library artifact — it is not independently deployed.
- Consuming services include it as a Maven dependency; no Dockerfile, no container.
- It activates automatically in a Spring Boot 4 application via Spring's `@Component` scanning and `ObjectProvider` for `OtlpMetricsSender`.

## Configuration Management
- **Endpoint configuration**: Consuming service sets `management.otlp.metrics.export.url` or `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable.
- **No other configuration** required by this library itself.
- No property files, no `application.yaml` in this library.

## Observability
- This library IS the observability layer — it provides metrics and log export.
- Self-observability: `OtlpGrpcMetricsSender` logs info/warn/error on connection lifecycle events via SLF4J (Lombok `@Slf4j`).
- `InstallOpenTelemetryAppender` logs info messages on startup/successful install.
- No health indicator or Spring Boot Actuator integration.

## Infrastructure Dependencies
| Dependency | Purpose |
|-----------|---------|
| Azure Container Apps OTel Collector | Receives OTLP metrics via gRPC on port 4317 |
| gRPC Netty shaded transport | HTTP/2 connection management |
| Micrometer OTLP registry | Metrics collection and scheduling |
| OpenTelemetry SDK | Trace/log/metric SDK |
| Spring Boot 4 OTel starter | Spring Boot auto-configuration |

## Operational Risks
- **Java 25 / Spring Boot 4**: No existing Onbe service currently runs Java 25 or Spring Boot 4 (as of this analysis). This library cannot be consumed until consuming services are upgraded.
- **Alpha dependency** (`opentelemetry-logback-appender-1.0:2.26.0-alpha`): Alpha versions are not stable and should not be in production library dependencies.
- **SNAPSHOT version**: `1.0.0-SNAPSHOT` — non-reproducible, should not be a transitive dependency in production services.
- **Blocking gRPC call**: `ClientCalls.blockingUnaryCall()` with a 10-second deadline will block the calling thread for up to 10 seconds if the collector is slow — could impact metrics export performance if the collector is under load.
- **No retry logic**: Failed exports are not retried by the library.
- **Channel shutdown timeout**: `@PreDestroy` waits up to 5 seconds (then 5 more after force) — during rapid container shutdown, telemetry in flight may be lost.

## CI/CD
- No CI/CD pipeline definition file found in this repository.
- As a shared library, it should be published to the internal Maven repository with proper versioning before consuming services can adopt it.
