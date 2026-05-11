# DevOps & Operations — oneplatform-rediscache-adminservice

## Build
- **Build tool**: Apache Maven with Spring Boot Maven Plugin (Spring Boot 3.2.4 parent).
- **Java version**: Java 21 (virtual threads enabled via `spring.threads.virtual.enabled=true`).
- **Artifact**: Executable JAR (`adminservice-0.0.5.jar`).
- **Wrapper**: `mvnw` / `mvnw.cmd` bundled; no Maven installation required.
- **No CI/CD file found** in the repository root (no `.gitlab-ci.yml`, `.github/workflows/`, or `Jenkinsfile` present).

## Deployment
- No Dockerfile present in this repository — deployment mechanism not defined within source.
- Spring profiles: `dev`, `qa`, `stage`, `prod` (property files present for all four).
- Server port: `8081` (dev), default port in base `application.properties` is unset (Spring default 8080).
- The application is a standalone Spring Boot JAR; Tomcat is embedded.
- Azure Key Vault integration requires the deployment identity to have the `Key Vault Secrets User` role on the target vault; vault name injected via `KEY_VAULT_NAME` environment variable.

## Configuration Management
- Profile-specific `application-{profile}.properties` files control all environment differences.
- Secrets injected at runtime via Azure Key Vault using Spring Cloud Azure Key Vault Secret property source (`spring.cloud.azure.keyvault.secret.property-source-enabled=true`).
- Key Vault name resolved from environment variable `KEY_VAULT_NAME`.
- Azure subscription ID and tenant ID are hardcoded in `application.properties` (dev values visible; production values should override via profile or environment variables).
- Redis host, AFD resource group/name/endpoint all vary per profile.

## Observability
- **Logging**: SLF4J (`@Slf4j` via Lombok) throughout; log level not explicitly configured in observed property files (defaults to Spring Boot default INFO).
- **Health endpoint**: Not explicitly configured — Spring Boot Actuator dependency not present in `pom.xml`. No `/hc` endpoint defined.
- **Metrics**: No Micrometer or Actuator dependency observed.
- **Tracing**: No OpenTelemetry or distributed tracing dependency observed.
- `log.error(...)` calls exist but use `e.printStackTrace()` in several catch blocks — may produce duplicate stack trace output to stdout vs. log appender.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| Azure Redis Cache | Managed Redis | Port 6380, TLS, password from Key Vault |
| Azure Blob Storage | Object storage | Connection string from Key Vault, container `data` |
| SQL Server `cbaseapp` | Relational DB | HikariCP pool; `q-lis-db01` (dev/qa), TLS 1.2 |
| SQL Server `Ecountcore` | Relational DB | HikariCP pool; `q-lis-db02` (dev/qa), TLS 1.2 |
| Azure Key Vault | Secrets management | Managed Identity; vault name from `KEY_VAULT_NAME` env var |
| Azure Front Door / CDN | CDN | Purge operations via Azure Resource Manager SDK |
| Azure Resource Manager | Management plane | `azure-resourcemanager 2.45.0`, `azure-resourcemanager-cdn 2.45.0` |

## Operational Risks
- **No health endpoint / readiness probe**: No way for a load balancer or orchestrator to verify the service is ready without a custom probe.
- **No CI/CD pipeline**: No automated build, test, or deployment pipeline visible in source.
- **Circular references enabled in dev** (`spring.main.allow-circular-references=true`) suggests potential Spring bean configuration issue that has not been resolved.
- **Virtual thread executor shutdown**: `VirtualThreadAsyncConfig.destroy()` waits 60 seconds, then force-shuts; long-running cache warm-up tasks may be interrupted during rolling restarts.
- **Jedis pool exhaustion**: Max active connections is 50 (default profile); bulk affiliate caching uses up to 20 parallel threads — pool sizing may be adequate but should be monitored.
- **No retry or circuit breaker** on Redis or SQL connections beyond HikariCP timeout settings.
- **`AsyncConfig.javaold` and `ExecutorServiceConfig.javaold`** in source tree — dead code that could cause confusion or accidental reactivation.

## CI/CD
- No pipeline definition file found in this repository.
- Downstream usage (how and where the JAR is deployed) is not defined within source.
