# Solution Architect — otel-grpc_LIB

## Technical Architecture
- **Language**: Java 25.
- **Framework**: Spring Boot 4.0.3 (`spring-boot-dependencies` BOM).
- **Observability stack**: OpenTelemetry SDK 1.60.1 + Micrometer 1.16.4 + gRPC 1.79.0.
- **Transport**: gRPC (Netty shaded transport); `ManagedChannelBuilder` for connection management.
- **Logging bridge**: `opentelemetry-logback-appender-1.0:2.26.0-alpha`.
- **Source files**: 2 main classes, 2 test classes (minimal footprint by design).

## API Surface
This is a library with no REST or gRPC server endpoints.

### Exported Beans (for consuming Spring Boot applications)
| Bean Class | Type | Auto-discovered via |
|-----------|------|---------------------|
| `OtlpGrpcMetricsSender` | `OtlpMetricsSender` | `ObjectProvider<OtlpMetricsSender>` in `OtlpMetricsExportAutoConfiguration` |
| `InstallOpenTelemetryAppender` | `InitializingBean` | Spring component scan |

### Configuration Properties Consumed
| Property | Default | Purpose |
|---------|---------|---------|
| `management.otlp.metrics.export.url` | `${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4317}` | OTLP collector endpoint |

## Security Posture

### Transport Security
- **TLS**: Enabled if endpoint scheme is `https`; `builder.useTransportSecurity()` called. [OtlpGrpcMetricsSender.java:68]
- **Plaintext**: Default if `http://` scheme; `builder.usePlaintext()` called. [OtlpGrpcMetricsSender.java:72]
- **Risk**: Production deployments must explicitly configure `https://` or telemetry data (including log messages) will travel unencrypted over the network.

### Authentication
- **No authentication** on the gRPC channel: No mTLS, no bearer token, no API key. The library assumes the Azure Container Apps network security (VNet isolation) provides sufficient protection.
- If the collector endpoint is exposed beyond the VNet boundary, this is a significant gap.

### Data Privacy
- Log messages are exported verbatim. Consuming services must ensure their log output does not contain PII, PAN data, or other sensitive information. This library provides no redaction.

### CVE / Dependency Risks
- `opentelemetry-logback-appender-1.0:2.26.0-alpha`: Alpha dependency — stability and security posture uncertain.
- `grpc-bom:1.79.0`, `opentelemetry-bom:1.60.1`: Current major versions; SCA scan should validate no known CVEs.
- `grpc-netty-shaded`: Shaded Netty — may hide CVEs that tooling would otherwise detect; requires explicit version scanning.

## Technical Debt
- **SNAPSHOT version** (`1.0.0-SNAPSHOT`): Cannot be used in production dependency chain.
- **Alpha logback appender**: Must reach GA before production use.
- **Blocking gRPC call**: `ClientCalls.blockingUnaryCall()` in `send()` — blocks the Micrometer export thread for up to 10 seconds on timeout. Consider async pattern if metrics export frequency is high. [OtlpGrpcMetricsSender.java:82-86]
- **No retry logic**: Transient collector unavailability causes immediate export failure with no retry.
- **Maven POM model version 4.1.0**: Requires validation that Onbe's Maven infrastructure supports this schema version.
- **Java 25**: No other Onbe service observed is on Java 25; this creates a version isolation problem.
- **POM comment**: "ATTENTION: This library was created to be used with Spring Boot 4 applications" — the comment is in the POM's `<!--` block, confirming intentional Spring Boot 4 targeting.

## Gen-3 / Production Readiness Requirements
1. Promote from SNAPSHOT to a release version.
2. Replace `opentelemetry-logback-appender-1.0:2.26.0-alpha` with a GA release.
3. Add mTLS or token-based authentication to the gRPC channel for production environments.
4. Add PII-safe log filtering guidance or an optional redaction filter.
5. Consider async/non-blocking gRPC export to avoid blocking Micrometer's export thread.
6. Add CI/CD pipeline.
7. Add integration test with an embedded OTLP collector (e.g., `testcontainers-opentelemetry`).
8. Validate Maven POM 4.1.0 support in Onbe build infrastructure.
9. Confirm Java 25 readiness in Onbe build and runtime infrastructure.

## Code-Level Risks (File:Line References)
| Risk | File | Line(s) |
|------|------|---------|
| Plaintext gRPC transport by default | `src/main/java/.../OtlpGrpcMetricsSender.java` | 67-75 |
| Blocking 10-second deadline call | `src/main/java/.../OtlpGrpcMetricsSender.java` | 82-86 |
| No auth on gRPC channel | `src/main/java/.../OtlpGrpcMetricsSender.java` | 66-76 |
| Alpha dependency in POM | `pom.xml` | 31 |
| SNAPSHOT version | `pom.xml` | 14 |
| Maven POM 4.1.0 schema | `pom.xml` | 2 |
