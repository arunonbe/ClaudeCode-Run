# Solution Architect View — exemplar-customer-service_WAPP

## Technical Architecture

**Stack**: Java 11, Spring Boot 2.4.5, Spring Data JPA (Hibernate), SQL Server (HikariCP), Liquibase, Dapr 1.1.0, springdoc-openapi 1.5.8, Lombok, Docker, Kubernetes.

**Module structure**:
| Module | Role |
|--------|------|
| customer-service-data | Domain model (Customer DTO, events, exceptions) |
| customer-service-persistence | JPA entities and repository |
| customer-service-service | Business logic (CustomerServiceImpl) |
| customer-service-config | Spring Boot application entry point, DataSource config, AppConfig |
| customer-service-rest-controller | REST controllers (CustomerController, PublishController), Swagger config, Dockerfile |
| customer-service-db-app | Database migration runner (Liquibase Docker entry point) |
| customer-service-db-scripts | Liquibase changelog XMLs |
| customer-service-qa | Cucumber acceptance tests |

**Context loading**: The application uses explicit `@Import` of context classes (AppConfigContext, PersistenceContext, ServiceContext, RestControllerContext) rather than `@ComponentScan` — this is a deliberate modularity pattern.

## API Surface

**REST endpoints** (base path `/`, port 9500):

| Method | Path | Description |
|--------|------|-------------|
| POST | /customers | Create customer (JSON/XML request, 201 response) |
| GET | /customers/{customerId} | Get customer by ID (200/404) |
| PUT | /customers | Update customer (200) |
| POST | /pubsub/{topic} | Publish event to Dapr pub/sub topic |
| GET | /monitoring/* | Actuator endpoints (all exposed) |

Content types: `application/vnd.onbe.v1+json`, `application/vnd.onbe.v1+xml` (defined in ApiVersion constants).

**Swagger UI**: Available via springdoc-openapi at `/swagger-ui.html` (standard SpringDoc path).

## Security Posture

### Authentication / Authorisation
- **No authentication implemented** in this exemplar. All endpoints are publicly accessible as deployed.
- The `credentials` block in `application.yml` (username/password/role) is defined but no Spring Security configuration is observed — these credentials are not enforced.
- H2 console enabled — `spring.h2.console.enabled: true`.

### Cryptography
- TLS for database: configurable via `DataSourceConfiguration` — truststore loaded from Base64-encoded content injected at runtime (`global.datasource.truststore.content`). This is a correct pattern when credentials are properly externalised.
- No application-layer encryption of data fields.

### Secrets
- **CRITICAL — Hardcoded secrets in source**:
  - `application.yml` line 8: `password: "[REDACTED — rotate immediately]"` — plaintext credential.
  - `application.yml` line 40: `password: [REDACTED — rotate immediately]` — database password.
  - `application.yml` line 43-44: `username: SA` — SQL Server SA account.
  - `pom.xml` line 271: `<pactBrokerToken>emSbllw1wbfH-ZAFB-cD-Q</pactBrokerToken>` — PactFlow API token.
  - `application.yml` line 37 (commented): `password=[REDACTED — rotate immediately]` in commented Azure SQL connection string.

### CVEs / Dependency Risks
- **Spring Boot 2.4.5** (EOL March 2023): Multiple known CVEs in Spring Framework and related components since this version.
- **H2 1.4.200**: CVE-2021-42392 (critical) — remote code execution via JNDI. H2 console must be disabled.
- **WireMock 2.8.0** (test scope): Multiple CVEs in older WireMock releases.
- **OkHttp 4.9.0**: CVE-2023-0833 and others in older OkHttp versions.
- **commons-codec 1.12**: Older version; check for known CVEs.

## Technical Debt
1. Spring Boot 2.4.5 → must upgrade to 3.x LTS.
2. Java 11 → must upgrade to Java 17 or 21.
3. Hardcoded credentials in `application.yml` and `pom.xml` — blocked exemplar use as a production template.
4. H2 console enabled — security misconfiguration.
5. No Spring Security — exemplar is incomplete.
6. `SA` database user — SQL Server SA should never be used in application configurations.
7. Nexus URL `d-na-stk01.nam.wirecard.sys` — Wirecard-era hostname requiring update.
8. `dapr.version: 1.1.0` — Dapr SDK is outdated; latest is substantially newer.
9. No structured logging (JSON log format) for Kubernetes log aggregation.
10. `PublishController` pub/sub topic name `dii-integration` is hardcoded as a constant — should be configurable.

## Gen-3 Migration Requirements
This IS the Gen-3 exemplar. Remaining gaps before it can be used as a production template:
1. Externalise all secrets to Azure Key Vault / Azure App Configuration.
2. Add Spring Security with OAuth2/JWT bearer token validation.
3. Upgrade to Spring Boot 3.x and Java 17+.
4. Disable H2 console in all non-local profiles.
5. Add structured logging (logstash-logback-encoder or equivalent).
6. Update Nexus and PactFlow references to current Onbe infrastructure.
7. Replace SA database user with a least-privilege application account.

## Code-Level Risks

| File | Line | Risk |
|------|------|------|
| `customer-service-config/src/main/resources/application.yml` | 8 | Hardcoded credentials password |
| `customer-service-config/src/main/resources/application.yml` | 40 | Hardcoded DB password `[REDACTED — rotate immediately]` |
| `customer-service-config/src/main/resources/application.yml` | 43 | SA username for SQL Server |
| `customer-service-config/src/main/resources/application.yml` | 13-15 | H2 console enabled |
| `pom.xml` | 271 | PactFlow API token hardcoded |
| `customer-service-service/src/main/java/.../CustomerServiceImpl.java` | 60-62 | `BeanUtils.copyProperties` on JPA entity without refresh — stale state risk |
| `deploy/customer-service.yaml` | 10 | No image digest pinning |
| `deploy/customer-service.yaml` | 1 | Single replica only |
