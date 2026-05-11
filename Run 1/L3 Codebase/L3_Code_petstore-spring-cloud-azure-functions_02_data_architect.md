# Data Architect — petstore-spring-cloud-azure-functions

## Data Stores
This POC has no persistent data stores.

| Store | Type | Notes |
|-------|------|-------|
| Azure Service Bus | Message broker | Receives `PetEvent` Avro messages; connection via `ServiceBusConnection` application setting |
| Azure Functions runtime storage | Azure Storage Account | Required by Azure Functions runtime for state/concurrency metadata (not application data) |

## Schema / Data Structures

### Avro Schema — PetEvent
- Schema defined in `src/main/avro/petstore.avdl` and `src/main/resources/schemas/petstore.avsc`.
- Compiled to `com.onbe.petstore.avro.v1.PetEvent` Java class via `avro-maven-plugin`.
- Schema content not read in detail; the `SpecificDatumReader<PetEvent>` pattern requires the Java class to match the Avro schema exactly.
- Binary encoding (not JSON Avro) used on the Service Bus message payload.

### Spring Cloud Stream Schema Registry
- `spring-cloud-stream-schema-registry-client` dependency present — implies schema registry integration is anticipated but may not be fully configured in this POC.
- `spring.cloud.function.expected-content-type: application/avro` set in `application.yaml`.

## Sensitive Data Classification
- **No sensitive data** in this POC.
- `PetEvent` is a demo domain object — no PAN, no PII, no financial data.
- **Risk in production adaptation**: If this pattern is used for real payment events (e.g., payout events), Avro schemas must be designed to exclude PANs and sensitive fields; all sensitive fields must be referenced by opaque tokens only.

## Encryption
- Azure Service Bus: TLS 1.2 enforced by the Azure Service Bus SDK by default.
- No application-layer encryption of Avro payloads.
- Service Bus connection string injected via `ServiceBusConnection` application setting (Azure Functions app settings, typically stored in Azure Key Vault linked to App Configuration).

## Data Flow
```
Azure Service Bus Topic (PetEvent, binary Avro)
  └── Azure Functions trigger → FunctionHandlers.toPetEvent() → PetEvent POJO
        └── petEventHandler Consumer → log event

Timer trigger (every N minutes)
  └── onTimer() → log environment variables (first run)

HTTP GET /health
  └── HealthEndpoint.health().getStatus() → HTTP 200 string response
```

## Data Quality and Retention
- No data persistence or retention in the POC.
- Azure Service Bus provides dead-letter queuing for unprocessable messages — not configured in this application.
- If Avro deserialization fails (schema mismatch), `RuntimeException` is thrown — the Azure Functions runtime will dead-letter the message after retry exhaustion.

## Compliance Gaps
- **Not in scope** as a POC. If this pattern is promoted to production:
  - Schema registry must be secured with authentication.
  - Avro schemas must be reviewed for sensitive field inclusion.
  - Service Bus connection string must be injected from Azure Key Vault (not hardcoded).
  - The environment variable dump (`onTimer()` first-run) must be removed.
  - Log messages must be reviewed for PII/sensitive data.
