# Data Architect View — petstore-spring-mvc-rest-server

## Data Models

The data model is the classic OpenAPI Petstore schema, with two implementation variants:

**JDBC implementation** (`service/jdbc/`):
- `Pet` — entity with `id` (Long), `name` (String), `tag` (String, optional); maps to `pets` table
- `PetMapper` — row mapper from SQL result set to Pet domain object
- `PetRepository` — JDBC-based repository (Spring JdbcClient)

**QueryDSL implementation** (`service/querydsl/`):
- `Pet` — QueryDSL-annotated entity (`@QueryEntity`)
- `QPet` — generated QueryDSL predicate type for type-safe queries
- `Systranschemas` / `QSystranschemas` — SQL Server system schema introspection entity (used for schema validation/CDC)

**Redis implementation** (`service/redis/`):
- `Pet` — Redis-serializable entity with Spring Data Redis repository
- `PetRepository` — Redis repository for caching pet records

**Avro schema** (`src/main/avro/petstore.avdl`):
- `PetEvent` — event record with fields: `PetEventType` (CREATED, DELETED enum), `id` (Long)
- Published to Azure Service Bus / RabbitMQ on pet create/delete operations

**Database schema** (`petstore-spring-mvc-rest-server-boot/src/main/resources/schema.sql`):
- Creates `pets` table in SQL Server with columns: `id` (BIGINT IDENTITY), `name` (VARCHAR), `tag` (VARCHAR, nullable)

## Sensitive Data Handled

This is a demo application with no real sensitive data. The `Pet` entity contains only synthetic data (name, tag). However, the infrastructure configuration demonstrates handling of actual secrets:

| Data Category | Presence | Notes |
|---|---|---|
| Real PAN/CVV/PII | None | Petstore is synthetic domain |
| Database credentials | Via Azure Key Vault | `mypaymentvaultapi-cbaseappdb-username` loaded from Key Vault |
| API tokens | Via Dapr secrets | `MERCHANTENRICHMENT_TRIPLE_APITOKEN` — real token name suggests production integration |
| Redis password | Environment variable | `REDIS_PASSWORD` injected at runtime |

## Encryption and Protection Status

- **Database TLS**: `encrypt=false` in local dev config (`application.yaml`) — **not encrypted in local mode**. Production must override to `encrypt=true`.
- **Redis TLS**: `ssl.enabled: ${REDIS_SSL_ENABLED:false}` — disabled by default; must be enabled in all non-local environments.
- **Key Vault**: Azure Key Vault integration via Spring Cloud Azure provides encrypted-at-rest secret management. Secrets are fetched over HTTPS at application startup.
- **Dapr sidecar**: Dapr secret store provides an additional secrets abstraction layer; communication between application and Dapr sidecar is local (localhost), which is acceptable.
- **Event data**: Avro-encoded events published to Service Bus are not separately encrypted beyond TLS transport — event payload (`PetEventType`, `id`) is non-sensitive in this exemplar.

## Database Schemas

```sql
-- schema.sql (inferred location: petstore-spring-mvc-rest-server-boot/src/main/resources/schema.sql)
CREATE TABLE pets (
    id   BIGINT IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tag  VARCHAR(255)
);

-- Systranschemas referenced via QueryDSL - SQL Server system table for schema introspection
```

HikariCP configuration:
- Pool size: 10 connections maximum
- Connection timeout: 30 seconds
- Idle timeout: 600 seconds (10 minutes)
- Max lifetime: 1800 seconds (30 minutes)
- Leak detection: 120 seconds

## Data Flows

```
REST Client
  → PetStoreController (/v2/pets, /v2/pets/{id})
    → PetService (JDBC or QueryDSL implementation)
      → SQL Server (petstore database, HikariCP pool)
    → Redis cache (read-through; 2-hour TTL)
    → PetStoreMessageService
      → Azure Service Bus topic (production) / RabbitMQ (local)
        → event consumers (downstream services subscribing to petstore topic)
```

Leader election:
```
Application startup
  → Redis SETNX on "leader-lock" key (5-minute expiry)
    → elected leader runs scheduled tasks
```

## Retention Concerns

- `pets` table has no explicit retention policy — this is appropriate for an exemplar
- Redis cache TTL is 2 hours — synthetic data only
- Service Bus event retention follows Azure default (7 days for Premium tier topics)
- No audit logging of data access beyond Spring DEBUG level logging (which must be disabled in production)

## PCI DSS Data Storage Compliance

Not directly applicable as a demo service. However, this repo serves as the reference template for production services. The following must be addressed before any production adaptation:

- Remove `encrypt=false` and `trustServerCertificate=true` from all non-local profiles
- Enable Redis SSL for all non-local environments
- Ensure Avro event schemas for production services do not include SAD fields
- Implement field-level masking (using the demonstrated `TextUtils.mask()` pattern) for any PII/financial fields logged in production adaptations
- The `init()` method in `PetStoreController` logs `KeyVaultConfigProperties` at INFO level — in production adaptations, confirm masked fields are truly masked before promoting this pattern
