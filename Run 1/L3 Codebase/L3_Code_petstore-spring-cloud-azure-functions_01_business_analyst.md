# Business Analyst — petstore-spring-cloud-azure-functions

## Business Purpose
A proof-of-concept (POC) and reference implementation demonstrating how to build Azure Functions using Spring Cloud Function with Spring Boot, Avro schema-based event messaging via Azure Service Bus topics, and structured logging patterns. Named "petstore" to reflect its reference/demo nature (following the OpenAPI Petstore convention). It is not a business-critical production service; it serves as an architectural exemplar for the Azure Functions + Spring Cloud Function + Avro pattern for Onbe's Gen-3 platform.

## Capabilities
- **Service Bus topic consumer**: Subscribes to an Azure Service Bus topic (`%ServiceBusTopic%` / `%ServiceBusTopicSubscription%`) and processes `PetEvent` Avro messages received as binary payloads.
- **Timer trigger (keep-alive)**: Periodic timer function (`%TimerTriggerSchedule%`, every 5 minutes by default) that prevents Azure Functions cold starts; logs environment variables on first run.
- **Health check endpoint**: HTTP GET `/health` (anonymous auth) returns Spring Boot Actuator health status.
- **Avro deserialization**: Converts binary Avro payloads to `PetEvent` objects using `SpecificDatumReader` with binary decoder.
- **Environment variable dump**: On first timer run, logs all environment variables to the Azure Functions logger.

## Key Entities
- **`PetEvent`**: Avro-generated POJO from `src/main/avro/petstore.avdl` / `src/main/resources/schemas/petstore.avsc`. Represents a pet-related domain event (name, content defined by Avro schema).
- **`WithContext<T>`**: Java record wrapping an event payload with the Azure Functions `ExecutionContext`.

## Business Rules
- This is a POC/demo — no business rules govern payment processing or cardholder data.
- Service Bus topic name, subscription name, connection, and timer schedule are all injected via Azure Functions application settings (environment variables at `%...%` interpolation).
- Authorization level on all triggers: `ANONYMOUS` for HTTP health check; Service Bus and Timer triggers use Azure-managed credentials.
- The `petEventHandler` bean simply logs the received event — no processing logic is implemented.
- `isFirstRun` flag (AtomicBoolean) ensures environment variable dump happens only once per cold start.

## Key Flows
1. **Event consumption**: Service Bus topic receives message → Azure Functions runtime delivers binary payload → `onPetEvent()` → `bytes2PetEvent()` (Avro decode) → `peHandler.accept()` → logs event.
2. **Health check**: HTTP GET `/health` → `healthCheck()` → Spring Boot Actuator `HealthEndpoint` → returns health status string.
3. **Timer keep-alive**: Timer fires every `%TimerTriggerSchedule%` → `onTimer()` → first run logs environment variables.

## Compliance Relevance
- **POC/demo only**: Not in PCI DSS cardholder data environment scope.
- No payment data, no PII, no sensitive data processed.
- The environment variable dump on first run is a **security concern** in any non-demo context: it logs all environment variables (which may include secrets, connection strings, API keys) to the Azure Functions logger output.
- Demonstrates the Service Bus + Avro + Spring Cloud Function pattern that may be adopted by production services; compliance requirements would apply at production adoption.

## Risks
- **Environment variable dump** in `onTimer()` first-run logic logs ALL environment variables — in a production adaptation, this would expose secrets (connection strings, API keys, passwords) to application logs.
- **Avro schema registry client** dependency (`spring-cloud-stream-schema-registry-client`) without a configured schema registry may fail at runtime.
- **SNAPSHOT parent POM** (`onbe-spring-boot-parent:0.0.21-SNAPSHOT`).
- The `petEventHandler` bean does nothing with the event beyond logging — this is intentional for a POC but should be replaced with real logic in any production fork.
- `GsonAutoConfiguration` is excluded (`@EnableAutoConfiguration(exclude = GsonAutoConfiguration.class)`) while Gson is also a dependency — indicates a dependency conflict that was resolved by exclusion rather than removal.
