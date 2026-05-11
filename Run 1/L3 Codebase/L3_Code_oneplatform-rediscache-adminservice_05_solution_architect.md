# Solution Architect — oneplatform-rediscache-adminservice

## Technical Architecture
- **Framework**: Spring Boot 3.2.4, Java 21, Maven multi-module (single module).
- **Packaging**: Executable JAR via `spring-boot-maven-plugin`.
- **Concurrency**: Java 21 virtual threads (`Executors.newVirtualThreadPerTaskExecutor()`), Spring `@Async` backed by virtual-thread executor.
- **Persistence layer**: Spring Data JPA (Hibernate, SQL Server dialect) for `cbaseapp`, manual `DataSourceBuilder` for `Ecountcore` (no JPA repositories on secondary DB).
- **Caching layer**: Direct Jedis client to Azure Redis Cache; no Spring Cache abstraction used.
- **Azure integrations**: Spring Cloud Azure 5.11.0 (Key Vault, Blob Storage), Azure Resource Manager 2.45.0 (CDN/Front Door).

## API Surface
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/adminservice/programs` | Trigger full xContent blob → Redis warm-up (async) |
| GET | `/adminservice/programfromstorage/{programName}` | Read blob tags directly from Blob Storage |
| GET | `/adminservice/programfromcache/{programName}` | Read program content from Redis |
| POST | `/adminservice/program/{programName}` | Update single program in Redis from Blob Storage |
| POST | `/adminservice/affiliates` | Trigger full affiliate cache warm-up (async) |
| POST | `/adminservice/affiliate/{affiliateName}` | Cache single affiliate by name or numeric ID |
| GET | `/adminservice/affiliate/{affiliateName}` | Read affiliate data from Redis |
| GET | `/adminservice/keys/{pattern}` | List Redis keys matching pattern |
| DELETE | `/adminservice/keys/{pattern}` | Delete Redis keys matching pattern |
| POST | `/adminservice/cacheProgramSetup/{affiliateId}/{labelName}` | Cache program setup label |
| GET | `/adminservice/programSetup/{programId}/{labelName}` | Read program setup from Redis |
| POST | `/adminservice/cacheIntlCountries` | Cache all international countries |
| GET | `/adminservice/intlCountries[/{search}]` | Read countries from Redis |
| POST | `/adminservice/programSetting` | Cache full program setting response |
| POST | `/adminservice/fdcache/purge` | Purge Azure Front Door / CDN cache paths |

**No authentication or authorization** is applied to any of these endpoints. The `SecurityConfig` is not present in this service's source — protection must be enforced at the network layer.

## Security Posture

### Authentication and Authorization
- **None** — no Spring Security, no JWT, no API key. All endpoints are openly accessible to any client that can reach the service.
- **Risk**: Any actor with network access can trigger full cache warm-up, delete all Redis keys, or purge CDN content.

### Cryptography
- TLS 1.2 enforced on all SQL Server connections (`sslProtocol=TLSv1.2; encrypt=true`).
- Redis TLS on port 6380 in non-dev environments.
- Azure SDK connections use HTTPS by default.
- No application-layer encryption of cached values.

### Secrets Management
- **Production**: All credentials (DB username/password, Redis password, Blob connection string) resolved from Azure Key Vault via Managed Identity. No secrets in production property files.
- **Development** (`application-dev.properties`): Plaintext credentials `b2cstage/b2cstage` committed to source (lines 52-55). This violates PCI DSS Req 6.3 and represents a direct finding.
- Azure subscription ID (`a0acd97f-3bf3-4fa5-9a8e-dcfcc1e5b996`) and tenant ID (`2d652670-5422-4688-a20e-c2d32cc46751`) are hardcoded in `application.properties` (line 43-44) and `application-dev.properties` (lines 43-44). These are infrastructure identifiers and should be externalized.

### CVE / Dependency Risks
- `spring-boot-devtools` included as a runtime dependency (pom.xml line 74-78) — this should be `scope=test` or removed entirely from a production artifact; devtools can expose remote restart and class-reload features.
- `org.json:json:20240303` — no known critical CVEs at time of analysis but this artifact has a history of CVEs; validate in SCA scan.
- `azure-resourcemanager-frontdoor:1.0.0` — older version; check against current Azure SDK releases for security patches.

## Technical Debt
- `AsyncConfig.javaold` and `ExecutorServiceConfig.javaold` — old async config files left in the source tree with `.javaold` extension instead of being removed (`src/main/java/.../config/`).
- `// @PostMapping("/affiliates")` dead-code comment block in `AdminServiceController.java` (lines 62-66).
- `e.printStackTrace()` in catch blocks throughout `CacheAdminService` — should use structured logging.
- Large commented-out code blocks in `CacheAdminService.storeBlobsToCache()` (lines 357-413) — indicate multiple iterations of concurrency design not yet cleaned up.
- `@Autowired` on constructor in `CacheAdminService` is unnecessary when there is a single constructor (Spring Boot 3 injects automatically).
- `spring.main.allow-circular-references=true` in dev profile is a code smell.
- `CachePurgeService` imports `@RestController`, `@PostMapping`, `@RequestBody`, `@RequestMapping` (lines 14-17) — servlet-layer annotations in a service class (not a controller), unused but misleading.

## Gen-3 Migration Requirements
This service is already Gen-3. Remaining gaps to reach full production readiness:
1. Add Spring Security to restrict all admin endpoints to authorized internal callers (e.g., service account JWT or mutual TLS).
2. Add Spring Boot Actuator with health and readiness endpoints.
3. Add structured logging (JSON / Logstash) and remove all `e.printStackTrace()` calls.
4. Add Micrometer metrics for cache operation counts and latencies.
5. Remove `spring-boot-devtools` from the production artifact.
6. Remove `application-dev.properties` plaintext credentials or replace with placeholder values.
7. Externalize Azure subscription/tenant IDs to Key Vault or environment variables.
8. Add Dockerfile for containerized deployment.
9. Add CI/CD pipeline definition.
10. Remove `.javaold` files and commented-out code.

## Code-Level Risks (File:Line References)
| Risk | File | Line(s) |
|------|------|---------|
| Plaintext dev credentials in source | `src/main/resources/application-dev.properties` | 52-55 |
| Azure subscription ID hardcoded | `src/main/resources/application.properties` | 43-44 |
| `e.printStackTrace()` in catch | `CacheAdminService.java` | 252, 303 |
| `spring-boot-devtools` in runtime scope | `pom.xml` | 74-78 |
| No auth on admin endpoints | `AdminServiceController.java`, `CachePurgeController.java` | entire |
| Servlet annotations in service class | `CachePurgeService.java` | 14-17 |
| `allow-circular-references=true` | `application-dev.properties` | 17 |
| Dead `.javaold` files in source tree | `config/AsyncConfig.javaold`, `config/ExecutorServiceConfig.javaold` | N/A |
