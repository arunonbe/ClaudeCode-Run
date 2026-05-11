# Enterprise Architect — platform-system-utilities

## Platform Generation
**Gen-3** — New build, cloud-native patterns, Spring Boot 4.0.5, Java 25, OpenTelemetry, Micrometer, Redis-backed distributed coordination. No legacy technology present.

## Business Domain
**Cross-cutting Platform Infrastructure** — Not aligned to a single business capability; this is a horizontal library layer consumed by multiple domains (payments, account management, card services, etc.).

## Role in the Architecture
This repo acts as a **shared platform library layer** (inner-source utility monorepo). It provides:
- **Idempotency infrastructure** for all services that handle mutation operations (payment creation, fund transfers, account updates)
- **Audit infrastructure** for all services that need PCI DSS-compliant change history

It is a compile-time dependency for consuming services, not a runtime deployment.

## Module Dependency Map

```
platform-dependencies-bom
  (version pinning consumed by all other modules)

platform-idempotency
├── platform-idempotency-core       <-- consumed by Spring Boot services
│     depends on: Spring Boot 4.x, spring-aop, spring-web, micrometer, opentelemetry
└── platform-idempotency-redis      <-- auto-configured when spring-data-redis present
      depends on: platform-idempotency-core, spring-data-redis

platform-envers-db-audit            <-- consumed by services with JPA entities
      depends on: hibernate-envers, opentelemetry
```

## Key Dependencies (from pom.xml / README)

| Dependency | Version | Notes |
|---|---|---|
| Spring Boot | 4.0.5 | Very recent; Spring Boot 4.x requires Spring Framework 7.x and Java 25 |
| Testcontainers | 1.21.0 | Integration test infrastructure |
| Lombok | 1.18.38 | Compile-time annotation processing |
| JUnit | 5.12.2 | Test framework |
| Mockito | 5.17.0 | Mocking |
| AssertJ | 3.27.3 | Assertions |

## Integration Patterns

| Pattern | Implementation |
|---|---|
| Annotation-driven AOP | `@Idempotent` on Spring-managed methods; `IdempotencyAspect` intercepts via `@Around` |
| Spring Boot Auto-configuration | `AutoConfiguration.imports` for zero-config activation in consumer services |
| SPI/Strategy | `IdempotencyStore` SPI allows non-Redis implementations without core changes |
| OpenTelemetry Baggage propagation | Key resolution fallback and audit context extraction use OTel Baggage API — supports HTTP and non-HTTP entry points |
| Distributed lock (SETNX) | Redis-backed advisory lock for concurrent request coordination |

## Strategic Status
**Active investment — Gen-3 platform capability.** This library is establishing the standard patterns for idempotency and audit across Onbe's newer microservices. It is being published to GitHub Packages indicating active adoption intent.

## Dependencies on Other Onbe Systems
- `Onbe/om-ci-setup` — CI/CD reusable workflow library (required for build and publish pipelines)
- Consumer services supply: Redis connection, relational DB connection, Spring `application.name`, OTel agent/SDK

## Migration Considerations
- No Gen-1/Gen-2 code present; this is a greenfield Gen-3 library
- Consumer services migrating from legacy Spring Boot 2.x / Java 11 cannot adopt this library until they upgrade to Spring Boot 4.x / Java 25
- The `platform-dependencies-bom` provides a migration path for version alignment

## Risks to Enterprise Architecture

| Risk | Impact |
|---|---|
| Spring Boot 4.x / Java 25 constraint limits immediate adoption | Services on Spring Boot 2.x or Java 17/21 cannot use this library yet |
| `IdempotencyProperties.ttl` not wired creates operational inconsistency | Operators may configure TTL expecting effect but observe none |
| No versioning strategy beyond SNAPSHOT | `0.0.1-SNAPSHOT` — no stable release published; consumers depend on mutable snapshot artifacts |
| Single Redis implementation; no fallback store | If organisation moves away from Redis, entire SPI must be re-implemented |
