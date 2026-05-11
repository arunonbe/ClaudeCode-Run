# Solution Architect — petstore-spring-cloud-azure-functions

## Technical Architecture
- **Framework**: Spring Boot (via `onbe-spring-boot-parent`), Java 21.
- **Azure Functions**: `spring-cloud-function-adapter-azure` bridges Spring Cloud Function beans to Azure Functions triggers.
- **Event serialization**: Apache Avro (`avro-maven-plugin` compiles schema to POJOs); binary encoding; `SpecificDatumReader`.
- **Schema registry client**: `spring-cloud-stream-schema-registry-client` present but schema registry endpoint not configured in observed source.
- **Health**: Spring Boot Actuator with liveness/readiness probes; `HealthEndpoint` injected into Functions class.
- **Logging**: SLF4J/Logback with profile-based structured logging (Logstash JSON for qa/prod).
- **Azure Functions runtime**: v4 (host.json); Extension Bundle 4.x for Service Bus; EP1 pricing tier.
- **Concurrency**: Dynamic concurrency enabled in `host.json`; snapshot persistence enabled.

## API Surface

### Azure Function Triggers
| Function Name | Trigger Type | Auth Level | Notes |
|-------------|-------------|-----------|-------|
| `PetEventServiceBusTopicTrigger` | Service Bus Topic | N/A (Azure-managed) | Binary Avro payload; topic/subscription from app settings |
| `PetStoreTimerTrigger` | Timer | N/A (Azure-managed) | Keep-alive; env dump on first run |
| `health` | HTTP GET `/health` | ANONYMOUS | Returns Actuator health status string |

### Spring Beans Registered as Functions
| Bean | Type | Spring Cloud Function definition |
|------|------|----------------------------------|
| `petEventHandler` | `Consumer<WithContext<PetEvent>>` | Defined in `spring.cloud.function.definition` |
| `toPetEvent` | `Function<byte[], PetEvent>` | Avro binary → PetEvent converter |

## Security Posture

### Authentication
- **Service Bus trigger**: Authenticated via `ServiceBusConnection` app setting — should be managed identity in production (not connection string with shared access key).
- **HTTP health endpoint**: `AuthorizationLevel.ANONYMOUS` — appropriate for health checks; no sensitive data returned.
- **No application-level auth**: No Spring Security, no JWT on any endpoint.

### Secrets Management
- Service Bus connection string via `ServiceBusConnection` application setting — value comes from `local.settings.json` (not in source) for local dev; should use Key Vault reference (`@Microsoft.KeyVault(...)`) in Azure portal for production.
- No hardcoded secrets observed in source files.

### Security Risk — Environment Variable Dump
- `Functions.envVariables()` called on first timer run logs ALL environment variables via `context.getLogger()`. [Functions.java:63-67]
- In production, environment variables include connection strings, API keys, and other secrets injected as app settings.
- **This is a CRITICAL security risk if this pattern is used in production without removing the env dump.**
- `System.getenv().entrySet().stream()...` — dumps every key=value pair.

### Transport Security
- Azure Service Bus SDK: TLS 1.2 by default.
- Azure Functions HTTPS: Enforced at the Azure Functions runtime layer.
- No additional application-layer encryption.

### CVE / Dependency Risks
- `spring-cloud-stream-schema-registry-client`: Dependency present without configured endpoint — may cause startup errors or schema registry connection failures.
- `com.google.code.gson:gson`: Pulled in as dependency but `GsonAutoConfiguration` is excluded (`@EnableAutoConfiguration(exclude = GsonAutoConfiguration.class)`) — conflict between Gson and Jackson; indicates a dependency that should be removed rather than excluded.
- Parent POM SNAPSHOT: `onbe-spring-boot-parent:0.0.21-SNAPSHOT`.

## Technical Debt
- **Environment variable dump** on first timer run. [Functions.java:63-67]
- **`petEventHandler` is a no-op** (logs only). [FunctionHandlers.java:54-58]
- **`GsonAutoConfiguration` excluded while Gson is a dependency**: Remove Gson dependency instead of excluding its auto-configuration. [FunctionHandlers.java:14; pom.xml line ~64]
- **Schema registry client unconfigured**: Dependency present but no registry URL configured in `application.yaml`.
- **SNAPSHOT parent POM**: `onbe-spring-boot-parent:0.0.21-SNAPSHOT`.
- **`start-class` in pom.xml properties**: `com.onbe.petstore.functions.FunctionHandlers` — also the `main()` class entry point; this is correct for Spring Cloud Function adapter but should be documented.
- **No dead-letter handling**: Avro deserialization failure throws `RuntimeException`, propagates to Azure Functions runtime, and relies on Service Bus retry/dead-letter policy — no explicit error recovery.
- **`functionAppRegion=westus2`**: Development region hardcoded in POM; should be a Maven profile or CI variable for production.

## Gen-3 Production Readiness Requirements
1. Remove environment variable dump from `onTimer()` first-run logic.
2. Implement real `petEventHandler` business logic (or rename/replace with domain-specific consumer).
3. Remove `gson` dependency and `GsonAutoConfiguration` exclusion.
4. Configure schema registry endpoint (`spring.cloud.schema-registry.client.endpoint`) or remove the dependency.
5. Add dead-letter queue handler for deserialization failures.
6. Use managed identity for Service Bus connection (remove shared access key pattern).
7. Add CI/CD pipeline.
8. Parameterize Azure region and resource group via Maven profiles.
9. Promote `onbe-spring-boot-parent` to release version.
10. Add unit tests for `toPetEvent` converter and `petEventHandler`.

## Code-Level Risks (File:Line References)
| Risk | File | Line(s) |
|------|------|---------|
| Environment variable dump on first timer run | `src/main/java/.../functions/Functions.java` | 63-67 |
| No-op event handler | `src/main/java/.../functions/FunctionHandlers.java` | 54-58 |
| GsonAutoConfiguration excluded (Gson still dependency) | `src/main/java/.../functions/FunctionHandlers.java` | 14 |
| Unconfigured schema registry client | `src/main/resources/application.yaml` | (missing config) |
| RuntimeException on Avro decode failure | `src/main/java/.../functions/FunctionHandlers.java` | 45-47 |
| SNAPSHOT parent | `pom.xml` | 9 |
| Dev resource group/region hardcoded | `pom.xml` | 31-34 |
