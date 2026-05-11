# Business Analyst — otel-grpc_LIB

## Business Purpose
A shared Java library that provides OpenTelemetry observability integration for Onbe's Spring Boot 4 microservices targeting Azure Container Apps. It solves a specific gap: Micrometer's built-in OTLP metrics exporter only supports HTTP transport, but the Azure Container Apps OpenTelemetry collector requires gRPC on port 4317. This library provides the gRPC transport bridge and also wires OpenTelemetry into the Logback logging pipeline so that logs, traces, and metrics are all exported together to the same collector.

## Capabilities
- **gRPC metrics export**: `OtlpGrpcMetricsSender` implements Micrometer's `OtlpMetricsSender` interface to send pre-serialized OTLP protobuf metrics over a gRPC managed channel to the Azure OTLP collector.
- **Logback → OpenTelemetry bridge**: `InstallOpenTelemetryAppender` programmatically installs the OpenTelemetry Logback appender at Spring context startup, ensuring all Logback log records are exported to the OTLP collector alongside traces and metrics.
- **Spring Boot 4 auto-configuration**: Both components are Spring `@Component` beans that integrate automatically with Spring Boot's auto-configuration (`OtlpMetricsExportAutoConfiguration` picks up the custom sender via `ObjectProvider`).

## Key Entities
- **`OtlpGrpcMetricsSender`**: Spring `@Component`; reads `management.otlp.metrics.export.url` or `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable for the collector endpoint; creates a gRPC `ManagedChannel`; implements `send(Request)` with a 10-second deadline.
- **`InstallOpenTelemetryAppender`**: Spring `@Component` implementing `InitializingBean`; receives `OpenTelemetry` bean via constructor injection; calls `OpenTelemetryAppender.install(openTelemetry)` in `afterPropertiesSet()`.

## Business Rules
- Library targets **Spring Boot 4** and Java 25 (`maven.compiler.source=25`) — not yet compatible with the current Spring Boot 3 / Java 21 services.
- Endpoint defaults: `http://localhost:4317` if no configuration property is present.
- TLS: if endpoint scheme is `https`, `useTransportSecurity()` is set on the gRPC channel builder; otherwise plaintext.
- The library uses the OkHttp gRPC sender exclusion pattern to avoid `Multiple GrpcSenderProvider found` warnings.
- Graceful shutdown: `@PreDestroy` method waits up to 5 seconds for channel termination, then forces shutdown.

## Key Flows
1. **Metrics export**: Spring Boot `OtlpMetricsExportAutoConfiguration` calls `OtlpGrpcMetricsSender.send(request)` on the configured export interval → `ClientCalls.blockingUnaryCall()` sends protobuf bytes over gRPC to the Azure collector.
2. **Log bridging**: On Spring context startup, `InstallOpenTelemetryAppender.afterPropertiesSet()` → `OpenTelemetryAppender.install(openTelemetry)` → all subsequent Logback log events are routed to the OTLP collector.

## Compliance Relevance
- Observability infrastructure — indirectly supports PCI DSS Req 10 (logging and monitoring) by providing the transport mechanism for centralized log and metric collection.
- If services use this library to export security-relevant logs to a SIEM, it is part of the audit trail.
- The library itself processes no cardholder data; it transmits telemetry metadata (log messages, metric values, trace spans).

## Risks
- **Java 25 / Spring Boot 4 requirement**: No current Onbe service is on Java 25 or Spring Boot 4; this library cannot be used by any of the other five analyzed repos without a major upgrade.
- **SNAPSHOT version** (`1.0.0-SNAPSHOT`): Not suitable for production dependency resolution.
- **Plaintext gRPC by default**: If `OTEL_EXPORTER_OTLP_ENDPOINT` is not explicitly set to `https://...`, all telemetry is sent in plaintext.
- **No retry on export failure**: `send()` throws on error; Micrometer's retry behavior (if any) is upstream; the library itself has no retry logic.
