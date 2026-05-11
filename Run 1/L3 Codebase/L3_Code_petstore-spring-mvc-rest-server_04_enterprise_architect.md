# petstore-spring-mvc-rest-server — Enterprise Architect View

## Platform Generation

**Generation**: Gen-3 Reference Implementation

`petstore-spring-mvc-rest-server` is explicitly designed as a Gen-3 pattern showcase. It inherits from `onbe-spring-boot-parent:0.0.22-SNAPSHOT`, uses Java 21 virtual threads, Spring Boot 3.x, Docker/Kubernetes deployment, GitHub Actions CI/CD with DORA metrics, and demonstrates the full suite of Gen-3 infrastructure patterns (Azure Key Vault, Azure Service Bus, Redis, Debezium CDC, Resilience4j, ArchUnit). It is the canonical reference for how a new Gen-3 Onbe service should be structured.

## Business Domain

**Domain**: Engineering Enablement / Platform Reference Architecture

`petstore-spring-mvc-rest-server` has no direct business domain — it manages fictional pet CRUD operations. Its business value is indirect and high: it reduces the time and risk of building new Gen-3 services by providing tested, demonstratable implementations of every major integration pattern Onbe engineers will need.

Target audience: Onbe engineers building new services or migrating Gen-2 services to Gen-3. The repository is also used for code review training (`CopilotReviewDemo.java`) and security control validation (`PetStoreConfig` log injection demo).

## Role in the Platform

### Dependency Relationships
```
onbe-spring-boot-parent (platform BOM + standards)
    └── petstore-spring-mvc-rest-server (reference impl)
            └── onbe-sqlserver (dev/test database container)

Consuming engineers reference patterns from:
    petstore-spring-mvc-rest-server
        ↳ copy to: order_SVC (Gen-3 migration)
        ↳ copy to: new-service_SVC (greenfield)
        ↳ copy to: ecount-core_SVC (migration)
```

### Pattern Coverage

| Pattern | Class | Applicability to Production |
|---|---|---|
| Rate limiter | `PetStoreController` (`@RateLimiter`) | All externally-facing write APIs |
| Circuit breaker | `PetStoreController` (`@CircuitBreaker`) | All database/downstream calls |
| Time limiter | `PetStoreController` (`@TimeLimiter`) | Long-running async operations |
| Virtual thread executor | `PetStoreConfig` | All Gen-3 Spring MVC services |
| Redis caching with silent error handling | `RedisCacheConfig`, `PetServiceImpl` | Services with expensive queries |
| CDC with leader election | `CDCConfig`, `LeaderConfig` | Multi-replica services publishing CDC events |
| Avro + Azure Schema Registry | `MessagingConfig`, `petstore.avdl` | All event-driven service integrations |
| Azure Key Vault property binding | `KeyVaultConfigProperties` | All services with secrets |
| QueryDSL dynamic queries | `QueryDslPetServiceImpl` | Services with complex query predicates |
| ArchUnit architectural tests | `GeneralArchUnitTests` | Recommended for all Gen-3 services |
| HikariCP multi-datasource | `DBConfig` | Services with dedicated SQL Server connections |
| OpenAPI code generation | `petstore-spring-mvc-rest-server-api` | API-first design pattern |

## Integration with Onbe Platform Standards

`petstore-spring-mvc-rest-server` inherits from `onbe-spring-boot-parent:0.0.22-SNAPSHOT`, which provides:
- Centralized dependency version management (Spring Boot 3.x, Debezium, Azure SDK versions).
- `onbe-spring-boot-starter-web` — Onbe-standard HTTP client, logging, and header configurations.
- `onbe-spring-boot-starter-logback` — Onbe-standard log format and sanitization.
- `onbe-spring-boot-starter-test` — Testcontainers + JUnit 5 + WireMock baseline.

This makes the petstore the best current example of what a fully-compliant `onbe-spring-boot-parent` consumer looks like in practice.

## Strategic Status

**Status**: Active Reference Implementation — Maintained alongside platform evolution

As `onbe-spring-boot-parent` evolves (new starters, new platform patterns), `petstore-spring-mvc-rest-server` is expected to be updated in parallel to demonstrate the latest recommended patterns. It should be treated as a living architectural document, not a one-time artifact.

**DORA metrics enabled** (`ENABLE_DORA_METRICS: true` in `deployment.yml`) — this is an indicator that Onbe is tracking deployment frequency and change lead time for this reference implementation, likely to demonstrate platform velocity improvements.

## Migration Blockers

There are no migration blockers for this repository — it is already a Gen-3 service. The relevant concern is ensuring that Gen-2 services migrating to Gen-3 can accurately adopt these patterns without introducing the gaps noted in the solution architect view:

| Risk to Adopters | Detail |
|---|---|
| Security config with all auth disabled | `SecurityConfig.java` disables CORS, CSRF, HTTP Basic, Form Login — this is intentional for a demo but must NOT be copied to production services |
| `encrypt: false` in `application.yaml` datasource | Local dev convenience; production services must use `encrypt: true` |
| `trustServerCertificate: true` in datasource config | Local dev only; production requires CA-signed SQL Server cert |
| `debug: true` in local profile | Must not appear in QA, stage, or prod profiles |
| Log injection demo in `PetStoreConfig` | `CopilotReviewDemo.java` and `PetStoreConfig` log injection lines must not be replicated in production code |
| `surefire.testFailureIgnore=true` | Tests can fail without failing the build — this must be removed in production services |
