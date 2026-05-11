# Enterprise Architect — petstore-spring-cloud-azure-functions

## Platform Generation
**Gen-3 / POC** — Spring Boot (via `onbe-spring-boot-parent`), Java 21, Azure Functions v4, Spring Cloud Function adapter, Avro schema registry, Elastic Premium hosting. This is an architectural reference for event-driven microservices on Azure, demonstrating patterns that Gen-3 production services would adopt.

## Business Domain
**Platform Infrastructure — Event-Driven Patterns / Azure Functions Reference**
Not a business domain service. This is a technology proof-of-concept demonstrating Azure Service Bus + Avro + Spring Cloud Function integration.

## Architectural Role
- **Reference architecture**: Demonstrates how to write Azure Functions using Spring Cloud Function (`spring-cloud-function-adapter-azure`), enabling Spring DI, auto-configuration, and testing within the Azure Functions serverless model.
- **Avro event pattern**: Shows binary Avro deserialization from Service Bus binary message payloads — a pattern applicable to real payment event streams.
- **Observability pattern**: Demonstrates dual logging (Azure Functions logger + SLF4J Logback) and structured JSON logging for qa/prod profiles.
- **Keep-alive pattern**: Timer trigger prevents cold start latency for Service Bus consumers — important for payment event processing SLA.
- **Health check pattern**: Anonymous HTTP health endpoint for Azure Functions, backed by Spring Actuator.

## System Dependencies
| System | Direction | Notes |
|--------|-----------|-------|
| Azure Service Bus | Upstream message source | Topic/subscription pattern; binary Avro payload |
| Azure Functions runtime | Hosting environment | v4, EP1, extension bundle 4.x |
| Azure Storage Account | Infrastructure dependency | Required by Functions runtime |
| Spring Cloud Stream Schema Registry | Optional upstream | Client dependency present; not fully configured |
| `onbe-spring-boot-parent` | Build-time parent | SNAPSHOT version |

## Integration Patterns
- **Spring Cloud Function adapter for Azure**: Maps Azure Functions triggers to Spring Cloud Function `Function<>` and `Consumer<>` beans — enables standard Spring testing and DI.
- **Avro binary deserialization**: `SpecificDatumReader` with binary decoder for Service Bus binary message format — not the JSON envelope format common in REST-based systems.
- **Record type for context wrapping**: `WithContext<T>` Java record cleanly bundles payload and execution context — a reusable pattern for any Azure Functions trigger handler.
- **Profile-based structured logging**: Different log configurations per environment (`local` vs `qa,stage,prod`) — demonstrates Onbe's structured logging convention.
- **AtomicBoolean first-run flag**: Used for one-time initialization on cold start — a pattern for Azure Functions cold start initialization work.

## Strategic Status
- **POC / pre-production**: SNAPSHOT version, dev resource group (`rg-app-dev`), no CI/CD pipeline.
- **Strategically valuable**: If Onbe adopts Azure Functions for event-driven payment flows (e.g., payout status event processing, notification triggers), this POC's patterns would be the foundation.
- The Avro schema approach (`petstore.avsc`, `petstore.avdl`) demonstrates Onbe's intent to use schema-first event design with a schema registry — an important governance capability for a payments platform.
- Compared to the other repos, this is the most "cloud-native" and event-driven pattern explored.

## Migration Blockers (for production adoption)
1. **Remove environment variable dump**: `onTimer()` first-run env dump must be removed before any production use.
2. **Implement real event handler**: `petEventHandler` currently only logs; must implement real business logic.
3. **Add authentication/authorization**: Service Bus connection secured via managed identity in production; no other auth gaps visible.
4. **Schema registry configuration**: `spring-cloud-stream-schema-registry-client` dependency needs a configured schema registry endpoint.
5. **Dead-letter handling**: Must add error handling and dead-letter queue processing for failed Avro deserialization.
6. **Promote parent POM to release**: `onbe-spring-boot-parent:0.0.21-SNAPSHOT` → stable release.
7. **Add CI/CD pipeline**.
8. **Production resource sizing**: `rg-app-dev` and `functionAppRegion=westus2` must be updated to production resource group and region.
