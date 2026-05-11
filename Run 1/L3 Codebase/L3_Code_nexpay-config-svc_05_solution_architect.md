# nexpay-config-svc — Solution Architect View

## 1. Technical Stack Summary

| Layer | Technology | Details |
|---|---|---|
| Language | Java | (version from nexpay-parent, likely 21+) |
| Framework | Spring Boot | Inherited from nexpay-parent 0.2.8-SNAPSHOT |
| Persistence | Spring Data JPA + Hibernate | `ddl-auto: none` (Flyway-managed) |
| Schema migration | Flyway | V1–V10 migrations, `baseline-on-migrate: true` |
| Audit | Hibernate Envers | Full entity revision history with source/reason |
| Database | PostgreSQL 18 (Flexible Server) | VNet-integrated, Managed Identity auth |
| DB connection pool | HikariCP | Max 20, min idle 5, keepalive 60s |
| DB authentication | Azure AD passwordless | `AzurePostgresqlAuthenticationPlugin` |
| Caching/Idempotency | Redis (Azure Cache for Redis) | Lettuce pool, TLS port 6380 |
| Config | Azure App Configuration + Key Vault refs | Spring Cloud Azure |
| Observability | OpenTelemetry → Dynatrace (OTLP HTTP) | 100% sampling, structured JSON logs |
| Testing | Testcontainers + JUnit 5 | Real PostgreSQL in integration tests |
| Container | Azure Container Apps (Consumption, internal) | `ca-nexpay-config-svc-qa` |
| CI/CD | GitHub Actions (shared nexpay-iac workflow) | |

## 2. Module Architecture

```
nexpay-config-svc/
│
├── nexpay-config-api/
│     └── OpenAPI-generated server stubs (controllers, request/response DTOs)
│         Endpoints: /programs, /countries, /currencies, /promotions,
│                    /programs/{id}/modality-detail,
│                    /programs/{id}/registration-settings,
│                    /programs/{id}/countries,
│                    /countries/{id}/address-config
│
├── nexpay-config-boot/
│     ├── NexpayConfigApplication.java          — Spring Boot main
│     ├── config/
│     │     ├── DatabaseConfigProperties.java   — DB config properties
│     │     ├── JpaConfig.java                  — JPA/Hibernate configuration
│     │     └── OpenTelemetryAppenderInitializer.java — OTEL log appender init
│     ├── exception/ErrorExceptionHandlers.java  — RFC 7807 error handling
│     └── init.db/init.sql                      — Local dev DB init
│
└── nexpay-config-data/
      ├── nexpay-config-data-entity/
      │     ├── entities/  — Program, Promotion, Country, Currency, ProgramModality,
      │     │                 ProgramRegistration, AddressDetail, CountryAddressConfig,
      │     │                 ProgramCountryConfig (all @Audited)
      │     └── db/migration/V1–V10__*.sql      — Flyway migrations
      └── nexpay-config-data-repository/
            └── repositories/ — Spring Data JPA repositories for all entities
```

## 3. Key Design Decisions

### 3.1 Physical Naming Strategy

```java
// JpaConfig inferred from application.yaml
naming:
  physical-strategy: PhysicalNamingStrategyStandardImpl
  implicit-strategy: ImplicitNamingStrategyLegacyJpaImpl
```

Using `PhysicalNamingStrategyStandardImpl` means JPA entity field names map directly to column names without camelCase-to-snake-case conversion. This requires explicit `@Column(name=...)` annotations on all entities — which is observable in `Program.java` (e.g., `@Column(name = "program_id")`). This is a deliberate, explicit design that avoids name resolution surprises.

### 3.2 Audit Trail Architecture

The Hibernate Envers `@Audited` annotation on all domain entities creates a complete, immutable change history in the database. The `REVINFO` table extension (V6, V10) adds:
- `application`/`source`: which service made the change (sourced from OTel baggage `source` field propagated from the BFF's `AuditFilter`)
- `trace_id`: correlates the database change to a distributed trace
- `reason`: free-text reason for the change

This is a sophisticated audit pattern that satisfies:
- PCI DSS Requirement 10.2 (audit log entries)
- SOC 2 Change Management controls
- GDPR Article 5(2) accountability principle

### 3.3 OpenAPI-First Development

The `nexpay-config-api` module contains the server stubs generated from an OpenAPI spec. This means the API contract is the primary artifact, not the implementation. Changes to the API require updating the OpenAPI spec first, which is reviewed through the PR process.

The generated client stubs consumed by `nexpay-clientadminweb-bff` are built from the same spec, ensuring client-server contract alignment at compile time.

## 4. Database Passwordless Authentication Flow

```
1. ACA Container App starts
2. Spring Boot loads application-qa.yaml profile
3. Hikari pool initialises with username = "msi-nexpay-qa"
4. AzurePostgresqlAuthenticationPlugin calls Azure IMDS endpoint
5. IMDS returns an Entra ID access token for the managed identity
6. Plugin exchanges token for PostgreSQL connection credential
7. PostgreSQL validates token against Entra ID (tenant: 2d652670-...)
8. Connection established
```

Token refresh is handled transparently by the plugin on each connection creation/revalidation. This eliminates password rotation risk for the application service account.

## 5. Security Analysis

### 5.1 SQL Injection Prevention

The repository layer uses Spring Data JPA's generated queries and `@Query` annotations with named parameters. No raw `JdbcTemplate` string concatenation was observed. This provides parametrised query protection against SQL injection.

### 5.2 `V5__Seed_test_data.sql` Risk

This migration is in the production migration path at `src/main/resources/db/migration/`. If it has not yet run in production (i.e., it is added after the baseline), it will execute on the first production deployment, inserting test programs with IDs like synthetic test values. This creates phantom records in the production program registry.

**Immediate action**: Move `V5__Seed_test_data.sql` to a separate `src/test/resources/db/migration/` path used only for Testcontainers integration tests. Alternatively, add a conditional block that skips insertion if `ENVIRONMENT = prod`.

### 5.3 Actuator `startup: UNRESTRICTED`

```yaml
# application.yaml line 53-54
endpoint:
  startup:
    access: UNRESTRICTED
```

`UNRESTRICTED` allows the startup endpoint to be triggered (POST to reset startup info) by any caller — not just read-only probed. This should be `read-only`. Flag for correction.

### 5.4 Missing Authentication on REST Endpoints

Config-svc has no Spring Security configuration in the observed codebase. All REST endpoints are publicly accessible to any caller within the ACA network. For a service that manages payment program configurations (which could be used to enable/disable payment rails for clients), this is a significant risk.

## 6. Recommendations Summary

| Priority | Item | File/Location |
|---|---|---|
| P1 | Remove V5 test data migration from main migration path | `db/migration/V5__Seed_test_data.sql` |
| P1 | Add Spring Security to protect config endpoints | New `SecurityConfig.java` |
| P1 | Remove `env` from actuator exposure | `application.yaml` line 48 |
| P1 | Change `startup.access` from UNRESTRICTED to read-only | `application.yaml` line 54 |
| P2 | Disable `app_config_local_auth_enabled` in QA/prod | `qa.tfvars` line 23 |
| P2 | Scope Key Vault RBAC to per-service identities | IaC `container-apps/main.tf` |
| P2 | Add circuit breaker in consuming services | BFF, orchestrator |
| P3 | Enable feature flags for progressive rollout | `AZURE_APP_CONFIG_FEATURE_FLAGS_ENABLED` |
