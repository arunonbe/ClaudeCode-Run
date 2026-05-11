# Enterprise Architect — otel-grpc_LIB

## Platform Generation
**Gen-3 / Forward-looking** — Spring Boot 4, Java 25, OpenTelemetry SDK 1.60.1, gRPC 1.79.0, Micrometer 1.16.4. This is the most technologically advanced library in the six-repo set. It is designed for the next generation of Onbe microservices, not current production services (which run Spring Boot 3 / Java 21).

## Business Domain
**Platform Infrastructure — Observability**
Cross-cutting library providing unified telemetry (metrics, logs, traces) export to Azure's OpenTelemetry collector. Addresses the operational monitoring requirements of Onbe's Azure Container Apps microservice deployments.

## Architectural Role
- **Shared observability foundation**: Drop-in library for any Spring Boot 4 service; provides gRPC metrics sender and Logback log bridge with zero configuration beyond endpoint URL.
- **Azure Container Apps integration**: Specifically designed for the Azure Container Apps OTel collector sidecar pattern where gRPC port 4317 is the standard endpoint.
- **Micrometer gap-filler**: Bridges the Micrometer OTLP registry (HTTP-only) to gRPC transport, enabling native gRPC observability in Azure environments.

## System Dependencies
| System | Direction | Notes |
|--------|-----------|-------|
| Azure Container Apps OTel Collector | Upstream receiver | gRPC port 4317; HTTPS in production |
| Consuming Spring Boot 4 services | Consumer | Includes library as Maven dependency |
| Maven repository (internal) | Distribution | SNAPSHOT; must be promoted to release |

## Integration Patterns
- **Spring Boot Auto-configuration**: Uses `ObjectProvider<OtlpMetricsSender>` injection — Spring Boot's metrics auto-configuration automatically discovers the custom sender bean.
- **`InitializingBean` pattern**: Log bridge installation uses `afterPropertiesSet()` lifecycle callback for guaranteed installation before first log event.
- **gRPC unary blocking**: Synchronous blocking gRPC call pattern for metrics export; trade-off between simplicity and throughput.
- **OkHttp exclusion**: Explicitly excludes `opentelemetry-exporter-sender-okhttp` to avoid dual GrpcSenderProvider conflict — required for correct OpenTelemetry gRPC sender resolution.

## Strategic Status
- **Pre-production / in development** (SNAPSHOT version, alpha logback dependency, targets Java 25 / Spring Boot 4 which has no current consumers).
- **Strategic direction**: Represents Onbe's intent to adopt OpenTelemetry as the standard observability framework for Gen-3/4 services.
- Once stabilized and promoted to a release version, this library would be the foundational observability component for all new microservices.
- The README file references this as a library "created to be used with Spring Boot 4 applications" — intentionally forward-looking.

## Migration Blockers
1. **No Spring Boot 4 services yet**: All current Onbe services observed run Spring Boot 3 / Java 21. This library requires Java 25 and Spring Boot 4.
2. **Alpha dependency**: `opentelemetry-logback-appender-1.0:2.26.0-alpha` must be stabilized to a GA release before production use.
3. **SNAPSHOT**: Must be promoted to a release version before inclusion in production service dependencies.
4. **Maven POM 4.1.0**: If this schema version requires a Maven version not yet deployed in Onbe's build infrastructure, the library cannot be built.
5. **No GA test coverage**: Only 2 test files exist (`InstallOpenTelemetryAppenderTest.java`, `OtlpGrpcMetricsSenderTest.java`); must achieve adequate coverage before production adoption.
