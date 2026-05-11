# petstore-spring-mvc-rest-server — Solution Architect View

## Technical Architecture

`petstore-spring-mvc-rest-server` is a three-module Maven project (`-api`, `-impl`, `-boot`) following Onbe's standard API-first module split. It targets Java 21, Spring Boot 3.x on Tomcat (Spring MVC — blocking), and deploys as a Docker container built via Spring Boot's `spring-boot:build-image` Maven plugin.

### Module Architecture
```
petstore-spring-mvc-rest-server (parent pom)
├── petstore-spring-mvc-rest-server-api
│     └── OpenAPI-generated server stub + published client JAR
│           (petstore-expanded-openapi.yaml → generated DefaultApi interface)
│
├── petstore-spring-mvc-rest-server-impl
│     ├── api/           PetStoreController (implements DefaultApi)
│     ├── config/        CDCConfig, DBConfig, LeaderConfig, MessagingConfig,
│     │                  PetStoreConfig, QueryDslConfig, RedisCacheConfig,
│     │                  RestClientConfig, SecurityConfig
│     ├── service/
│     │     ├── jdbc/    PetServiceImpl (JDBC + Spring Cache → Redis)
│     │     ├── querydsl/ QueryDslPetServiceImpl
│     │     └── redis/   Pet (RedisHash), PetRepository
│     ├── exception/     PetStoreException, NotImplementedException
│     └── codereview_test/ CopilotReviewDemo (intentional bugs)
│
└── petstore-spring-mvc-rest-server-boot
      ├── PetstoreSpringMvcRestApplication (Spring Boot entry)
      ├── application.yaml (all profile configs)
      ├── Dockerfile, Dockerfile-ssl, compose.yaml
      └── test/ ArchUnit tests (GeneralArchUnitTests, SpringArchUnitTests, ModularityTests)
```

### Runtime Dependency Stack
```
HTTP :8080 (Tomcat)
    └── PetStoreController (Resilience4j: RateLimiter + CircuitBreaker + TimeLimiter)
          ├── Virtual thread executor (SimpleAsyncTaskExecutor.setVirtualThreads=true)
          ├── QueryDslPetServiceImpl (@Qualifier("querydsl")) — primary service impl
          │     └── SQL Server via QueryDSL + JPAQueryFactory
          ├── PetServiceImpl (JDBC + Redis cache)
          │     ├── Spring Data JDBC → SQL Server (HikariCP, pool=10)
          │     └── Spring Cache annotations → Redis (TTL=2h, Lettuce)
          ├── RedisRepository (Redis as primary store)
          │     └── @RedisHash → Redis (Lettuce)
          └── PetStoreMessageService (Spring Cloud Stream StreamBridge)
                └── Avro PetEvent → Azure Service Bus (QA/prod) / RabbitMQ (local)

CDC Engine (leader-elected, separate thread pool):
    CDCConfig → DebeziumEngine (SqlServerConnector)
      ├── Only active when this instance holds Spring Integration leader lock
      ├── Reads from SQL Server transaction log → cdc.dbo_pet_CT
      └── Publishes PetEvent as Spring application event → StreamBridge

Azure Key Vault (startup, via Spring Cloud Azure):
    mypaymentvaultapi-cbaseappdb-username → petstore.kv-secret
    mysecret → available as Spring property
```

## API Surface

### REST Endpoints (OpenAPI-generated interface)
The API is defined in `petstore-expanded-openapi.yaml` and published to APIM (`PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`, suffix `petstoremvc/v2`):

| Method | Path | Resilience4j Guard | Description |
|---|---|---|---|
| `POST` | `/pets` | `@RateLimiter` (1 req/min) | Add a new pet; publishes `CREATED` event |
| `DELETE` | `/pets/{id}` | `@CircuitBreaker` (50% failure threshold) | Delete pet; parallel: publish `DELETED` event + delete |
| `GET` | `/pets` | `@TimeLimiter` (30s) | Find pets by optional tag filter |
| `GET` | `/pets/{id}` | — | Get pet by ID (Redis cache hit or DB miss) |

All methods use `CompletableFuture` execution on the virtual thread executor.

### Published Client JAR
`petstore-spring-mvc-rest-server-api` is published as a reusable client JAR to GitHub Packages, enabling other Onbe services to consume the petstore API as a typed client — the pattern used for inter-service REST calls across the Gen-3 platform.

## Security Posture

### Security Controls Present
- Azure Key Vault property binding — secrets never in `application.yaml`.
- `com.onbe.text.TextUtils.mask()` applied before logging Key Vault secret values.
- `onbe-spring-boot-starter-logback` — Onbe log sanitization (strips log injection payloads).
- CodeQL SAST (`codeql.yml`) with `CODEQL_QUALITY: true`.
- Resilience4j circuit breaker prevents downstream overload during failures.
- CDC leader election prevents duplicate event publication from multiple replicas.
- Container built with Spring Boot build image (layered Docker image — principle of least privilege).

### Security Gaps (Demo Artifacts — Must Not Be Replicated)

| Finding | Location | Action Required for Production |
|---|---|---|
| All authentication disabled | `SecurityConfig.java` | Enable appropriate auth (OAuth2/JWT, mTLS) |
| `encrypt: false` in datasource | `application.yaml` (local/default profile) | Set `encrypt=true` for all non-local profiles |
| `trustServerCertificate: true` | `application.yaml` | Use CA-signed cert in QA/stage/prod |
| Log injection demo | `PetStoreConfig.java` line 74 | Remove from production copies |
| `CopilotReviewDemo.java` (intentional bugs) | `codereview_test/` | Never copy to production; package is clearly labelled |
| `surefire.testFailureIgnore=true` | `pom.xml` | Remove for production services |
| `debug: true` in local profile | `application.yaml` | Never include in non-local profiles |
| Container scan disabled | `deployment.yml` | Re-enable for production services |

### `wirecard.pem` Certificate in Bindings
`petstore-spring-mvc-rest-server-boot/bindings/ca-certificates/wirecard.pem` — a PEM certificate file in the repository. This is a CA certificate (not a private key), used by Cloud Native Buildpacks service binding to trust the Wirecard CA. Its presence is appropriate for a demo that may connect to Wirecard-signed endpoints. Verify that no private keys are committed alongside it.

## Technical Debt

| Item | Severity | Detail |
|---|---|---|
| `onbe-spring-boot-parent:0.0.22-SNAPSHOT` | Medium | SNAPSHOT parent — production services must use a release version |
| `surefire.testFailureIgnore=true` | Medium | Tests can fail silently in CI — masks real regressions |
| Container scan disabled | Medium | Must be enabled for production pattern compliance |
| `MAVEN_ARGS: '-Dmaven.test.skip=true'` in CI | Medium | Tests not run in CI pipeline despite being present in the repo |
| QueryDSL `QSystranschemas` system table query | Low | Querying `sys.schemas` via QueryDSL is a demo curiosity; not a production pattern |
| `CopilotReviewDemo.java` in production package | Low | Demo code in main source tree; should be in a `demo/` submodule |

## Code-Level Risks for Production Adoption

### Pattern 1: CDC + Leader Election
The `CDCConfig` uses `@EventListener(OnGrantedEvent.class)` to start Debezium and `@EventListener(OnRevokedEvent.class)` to stop it. The graceful shutdown path calls `engine.close()` — if this blocks, the Spring context shutdown sequence will also block. Production implementations should use `engine.close()` with a timeout:
```java
engine.close();
engine.await(30, TimeUnit.SECONDS);
```

### Pattern 2: Redis Silent Error Handler
`SilentCacheErrorHandler` silently logs and continues on all Redis errors. This is correct for availability (Redis outage must not break the API), but it means cache misses caused by Redis errors are indistinguishable from legitimate cache misses in metrics. Production services should emit a metric counter for cache error events to distinguish "cache miss" from "cache error".

### Pattern 3: Avro Schema in Local File
The `petstore.avdl` file defines the event schema. In production, this schema must be registered with Azure Schema Registry before the application starts. The current `MessagingConfig` registers the converter but does not validate schema registration at startup — a schema mismatch between producer and consumer would only be discovered at runtime when the first event is published.

### Pattern 4: `application.yaml` Key Vault Secret Listing
The `secret-keys` list in `application.yaml` must be kept in sync with actual Azure Key Vault secrets. If a secret is added to the list but not present in Key Vault, Spring Cloud Azure will throw an exception at startup. Production deployments should use a startup readiness check that validates all required secrets are resolvable.
