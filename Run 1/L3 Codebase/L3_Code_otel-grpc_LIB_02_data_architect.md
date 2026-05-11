# Data Architect — otel-grpc_LIB

## Data Stores
This library has no data stores. It is a pure telemetry transport library.

- **No databases, no caches, no file storage**.
- **Output**: Telemetry data (metrics in OTLP protobuf format, log records) sent over gRPC to the Azure Container Apps OpenTelemetry collector.

## Schema / Data Structures
- **Input**: `OtlpMetricsSender.Request` — contains `byte[] metricsData` which is pre-serialized OTLP protobuf (`ExportMetricsServiceRequest` proto format).
- **Transport**: gRPC unary call to `opentelemetry.proto.collector.metrics.v1.MetricsService/Export` method.
- **Byte passthrough**: `ByteArrayMarshaller` passes raw protobuf bytes to gRPC without re-serialization — the library is deliberately transparent to the OTLP wire format.
- **Logback AppenderEvent**: Standard Logback `ILoggingEvent` objects are bridged to `OpenTelemetryAppender` which converts them to OTLP log records.

## Sensitive Data Classification
- **Telemetry risk**: Log messages exported to the collector may contain PII or sensitive data depending on what the consuming application logs. The library itself does not filter or redact log content.
- **Metric names and values**: Typically non-sensitive (JVM heap, HTTP request counts, etc.).
- **Trace spans**: May contain HTTP path parameters, request metadata — could contain PII if APIs log path variables with PII in them.
- **No cardholder data** is processed by this library directly.

## Encryption
- **gRPC channel**: TLS if endpoint URL scheme is `https`; plaintext otherwise.
- **No application-level encryption** of telemetry payloads.
- **Default is plaintext** (`http://localhost:4317`) — consuming services must explicitly configure `https://` endpoint for encrypted transport to the collector.

## Data Flow
```
Spring Boot Application (consuming service)
  ├── Micrometer metrics scrape interval
  │     └── OtlpGrpcMetricsSender.send() → gRPC → Azure OTel Collector (port 4317)
  └── Logback log event
        └── OpenTelemetryAppender → OTLP logs → Azure OTel Collector
```

## Data Quality and Retention
- No buffering or persistence in this library; telemetry is fire-and-forget (blocking unary gRPC call with 10-second deadline).
- If the collector is unreachable, the `send()` call throws an exception — Micrometer handles the retry policy at the registry level.
- Log records are not buffered; if the gRPC channel is unavailable at log time, `OpenTelemetryAppender` may drop log records silently (standard OpenTelemetry SDK behavior).

## Compliance Gaps
- **PCI DSS Req 10.3 (log integrity)**: The library provides the transport but does not sign or hash log records for tamper evidence.
- **Plaintext transport default**: If consuming services do not configure HTTPS endpoints, telemetry (including log messages) travels in plaintext — a network-level eavesdropping risk.
- **No PII filtering**: If log messages from consuming services include PII (e.g., email addresses, card last 4, account numbers), those will be exported verbatim to the collector.
