# DevOps & Operations — petstore-spring-cloud-azure-functions

## Build
- **Build tool**: Apache Maven (parent `onbe-spring-boot-parent:0.0.21-SNAPSHOT`).
- **Java**: 21.
- **Artifact**: JAR (`petstore-spring-cloud-azure-functions.jar`); Spring Boot repackage skipped (`spring-boot.repackage.skip=true`) — standard JAR for Azure Functions adapter.
- **Wrapper**: `mvnw` / `mvnw.cmd` present.
- **Key build plugins**:
  - `azure-functions-maven-plugin` (Microsoft): Packages and deploys Azure Functions; reads `local.settings.json` and `host.json`.
  - `spring-boot-maven-plugin`: Provides dependency management but repackage is skipped.
  - `avro-maven-plugin`: Compiles `.avdl`/`.avsc` schema files to Java POJOs.
  - `license-maven-plugin`: License header management.
  - `docker-maven-plugin` (Fabric8): Docker image build capability.
- **No CI/CD file** found in repository root.

## Deployment
- **Target**: Azure Functions (Consumption plan or Elastic Premium — `functionPricingTier=EP1`, Elastic Premium 1).
- **Azure region**: `westus2`.
- **Resource group**: `rg-app-dev`.
- **App Service Plan**: `asp-app-dev`.
- **Function App name**: `petstore-spring-cloud-azure-functions`.
- **Dockerfile** present — container-based deployment option available alongside Azure Functions native deployment.
- **Docker**: `bellsoft/liberica-openjre-alpine:21` base (inferred from Dockerfile pattern visible in this group).
- **host.json**: Azure Functions v2 runtime; extension bundle `Microsoft.Azure.Functions.ExtensionBundle [4.*, 5.0.0)` for Service Bus trigger; function timeout 2 minutes; dynamic concurrency enabled.

## Configuration Management
- **Azure Functions app settings**: Service Bus connection (`ServiceBusConnection`), topic name (`ServiceBusTopic`), subscription (`ServiceBusTopicSubscription`), timer schedule (`TimerTriggerSchedule`) — all injected as `%VariableName%` app setting references at runtime.
- **`local.settings.json`**: Referenced in `azure-functions-maven-plugin` configuration but not present in repository source (correctly excluded from source control).
- **`pig.template`**: Present (likely pipeline template marker).
- **Spring profiles**: `local`, `qa,stage,prod` — profile-specific logging config in `application.yaml`.
  - `local`: standard Logback (`logback-spring.xml`).
  - `qa,stage,prod`: Structured Logstash JSON logging (`logback-structured-spring.xml`; `logging.structured.format.console: logstash`).

## Observability
- **Health endpoint**: HTTP `/health` (anonymous) returns Spring Actuator health status; liveness and readiness probes enabled.
- **Logging**: Profile-aware Logback configuration; structured JSON (Logstash format) in non-local environments.
- **host.json logging**: Spring logs at Debug level (`org.springframework: Debug`); all others at Information.
- **Azure Functions runtime logging**: `context.getLogger()` for Azure-native structured logging.
- **Dual logging** in `petEventHandler`: Both `context.getLogger().info()` and `log.info()` (SLF4J Logback) — demonstrates the logging bridge pattern.
- **No Micrometer/OTel metrics**: No metrics instrumentation in this POC.

## Infrastructure Dependencies
| Dependency | Details |
|-----------|---------|
| Azure Functions runtime (v4) | Hosting environment; extension bundle 4.x |
| Azure Service Bus | Topic/subscription messaging; EP1 plan for trigger |
| Azure Storage Account | Required by Azure Functions runtime |
| Azure App Service Plan (EP1) | Elastic Premium 1; prevents cold start for timer trigger |

## Operational Risks
- **Cold start**: Azure Functions with Spring Boot may have significant cold start latency (several seconds); the timer trigger (keep-alive) mitigates this for the Service Bus trigger.
- **Environment variable dump on first run**: `onTimer()` first-run code dumps all environment variables — security risk if any environment variable contains secrets (Service Bus connection strings, API keys).
- **No dead-letter handling**: No `deadLetterExchange` or error handler configured for Service Bus messages that fail deserialization.
- **SNAPSHOT parent**: `onbe-spring-boot-parent:0.0.21-SNAPSHOT` — non-reproducible builds.
- **2-minute function timeout** (`host.json`): Long-running event processing would time out.
- **`local.settings.json` missing from source**: Correct for security but means local development setup requires manual configuration; no README instructions visible.
- **No CI/CD pipeline**: Deployment must be done manually via `mvn azure-functions:deploy` or Docker.

## CI/CD
- No CI/CD pipeline definition file found in this repository.
- Deployment is via `azure-functions-maven-plugin` (`mvn azure-functions:deploy`) or Docker push to Azure Container Registry.
