# Solution Architect — wirecard_check-agent_LIB

## Technical Architecture

### Module Structure
| Module | Role |
|---|---|
| `check-agent-config` | Spring Boot application entry point; datasource TLS config; app context wiring |
| `check-agent-core` | Business logic (CheckService, EmailService, EventHubProducer) |
| `check-agent-data` | DTOs, events, exceptions, REST API models (S2S, S2C), JAXB index |
| `check-agent-persistence` | JPA entities, Spring Data repositories, converters |
| `check-agent-db-scripts` | Liquibase changelogs (Oracle + H2) |
| `check-agent-db-app` | Standalone Spring Boot app for running DB migrations |
| `check-agent-event-consumer` | EventHub consumer (`CheckStatusUpdatedEventSubscriber`), idempotency AOP |
| `check-agent-batch` | Spring Batch retry job for failed EventHub publications |
| `check-agent-rest-controller` | REST controllers, Swagger/Springfox docs, security config, RPM packaging |
| `check-agent-documentation` | Swagger doc generator (test-scope) |
| `check-agent-performance` | JMeter performance test plans |
| `check-agent-qa` | QA test utilities |

### Runtime Stack
- Spring Boot 1.5.13.RELEASE
- Spring Framework 4.3.x (implicit)
- Spring Security OAuth2 (JWT resource server)
- Spring Data JPA + Hibernate (version from Spring Boot 1.5 BOM)
- HikariCP (connection pool)
- Liquibase (DB migrations)
- ActiveMQ (EventHub messaging)
- EhCache 3 (JCache)
- Springfox Swagger 2 (API documentation)

## API Surface

### REST Endpoints
Base path: `/check-agent` (from `server.servlet.context-path`)

Inferred from module structure and data models:
| Endpoint | Model | Auth |
|---|---|---|
| `POST /callcenter-api/...` (S2S) | `S2SCheck` request/response | JWT (ISS Auth Server) |
| `POST /...` (S2C) | `S2CCheck` request/response | JWT |
| `GET /check-agent/monitoring/*` | Spring Boot Actuator | Exposed with ALWAYS detail |

Full endpoint mapping is in `check-agent-rest-controller` (Java files not read in full; inferred from structure and data models).

### EventHub Topics
- **Produces**: `APP/CHECKAGENT` (topic) — `NewCheckEvent`, `VoidCheckEvent`
- **Consumes**: Inbound topic (name not confirmed from read files) — `CheckStatusUpdatedEvent`

## Security Posture

### Authentication / Authorisation
- JWT resource server using `iss-auth-server` JWK Set endpoint for public key retrieval.
- `spring-security-oauth2` library (deprecated, not receiving security patches since ~2019).
- No explicit `@PreAuthorize` annotations observed in data/core modules — auth enforcement is in `check-agent-rest-controller` (not fully read).
- Management endpoints exposed without authentication (`management.endpoints.web.exposure.include: '*'`).

### Cryptography
- JDBC TLS: Base64-decoded truststore written to filesystem (`DataSourceConfiguration.java:37`). The truststore content is Base64-encoded in application config (environment-specific config). Truststore password is also in config.
- EventHub: ActiveMQ connection — no TLS configured in the committed `application.yml` (dev uses `tcp://`).
- REST calls to upstream services: HTTP in QA config (`http://q-horust-app02.wirecard.sys`). Production config must use HTTPS.

### Secrets
- **`application.yml` QA secrets** (must not reach production): `ccp.client.password: [REDACTED — rotate immediately]`, `iss-auth.client.password: [REDACTED — rotate immediately]`.
- **Truststore password** in `global.datasource.truststore.password` — must be injected from a secrets vault.
- **EventHub credentials**: ActiveMQ `userName: local`, `password: local` in dev config.

### Known CVEs / EOL Risks
- **Spring Boot 1.5.13 (EOL August 2019)**: Hundreds of unpatched CVEs across the Spring ecosystem. This is the single highest risk in the repository.
- **`spring-security-oauth2`**: EOL; known vulnerabilities in JWT processing.
- **`com.oracle:ojdbc8`**: Oracle JDBC driver version managed by Wirecard Nexus parent BOM — version is unknown from this repo. OJDBC versions < 19c have known CVEs.
- **`com.h2database:h2`**: H2 runtime dependency; H2 2.x has had critical CVEs (CVE-2021-42392, CVE-2022-23221). Version from BOM must be checked.
- **Gradle 4.8**: Outdated build tool; not a runtime risk but toolchain CVE exposure.

## Technical Debt
1. **Spring Boot 1.5.13 (EOL)**: Highest priority — requires multi-version upgrade path (1.5 → 2.7 → 3.x).
2. **`compile` scope in Gradle**: `build.gradle` uses deprecated `compile` configuration (removed in Gradle 7+). Must be migrated to `implementation`/`api`.
3. **EventHub failure handling**: `CheckServiceImpl.java:95–99` and `141–145` — exceptions from `NewCheckEventNotifier`/`VoidCheckEventNotifier` are caught and logged as WARN. The check record is persisted but the event is not published. No compensating transaction or retry at the point of failure.
4. **`JAXB` index files**: `jaxb.index` files in `check-agent-data` suggest XML serialisation via JAXB. JAXB is removed from JDK 11+ and requires explicit dependency on `jakarta.xml.bind-api`.
5. **`javax.servlet` in rest-controller** (inferred from Spring Boot 1.5 era): Must be migrated to `jakarta.servlet` for any Spring Boot 3.x migration.
6. **Swagger 1.5/Springfox**: `io.springfox:springfox-swagger2` — Springfox does not support Spring Boot 2.6+ and is no longer maintained. Must migrate to SpringDoc OpenAPI.
7. **JMeter test plans**: `CheckAgent_APIs.jmx` and `CheckAgent_CheckStatusUpdatedEvent.jmx` in `check-agent-performance` — likely reference `wirecard.sys` hostnames; must be updated for any new environment.

## Gen-3 Migration Requirements
1. Upgrade Spring Boot: 1.5.13 → 2.7.x → 3.3.x (multi-step recommended).
2. Replace `spring-security-oauth2` with Spring Security 6.x OAuth2 Resource Server.
3. Replace `javax.*` with `jakarta.*` (at Spring Boot 3.x step).
4. Replace `springfox-swagger2` with `springdoc-openapi`.
5. Migrate `compile` to `implementation`/`api` in Gradle; upgrade Gradle to 8.x.
6. Replace ActiveMQ with Gen-3 event platform (Azure Event Hub, Kafka, or equivalent).
7. Replace RPM packaging with Dockerfile / OCI image.
8. Externalise all credentials from `application.yml` to a secrets vault.
9. Port Liquibase changelogs if database changes (Oracle → Azure SQL or other).
10. Migrate JAXB dependencies to Jakarta XML Bind API.

## Code-Level Risks

| File | Line | Risk |
|---|---|---|
| `check-agent-config/src/main/resources/application.yml` | 91–92 | `ccp.client.password: [REDACTED — rotate immediately]` — QA credential in committed config |
| `check-agent-config/src/main/resources/application.yml` | 107–109 | `iss-auth-server.url` pointing to `wirecard.sys` — Wirecard internal hostname |
| `check-agent-config/src/main/resources/application.yml` | 78 | ActiveMQ `tcp://localhost:61616` — plaintext, no TLS |
| `check-agent-config/src/main/resources/application.yml` | 9 | `management.endpoint.health.show-details: ALWAYS` — overly permissive |
| `check-agent-core/.../CheckServiceImpl.java` | 95–99 | EventHub notification failure silently swallowed — check created, event not published |
| `check-agent-core/.../CheckServiceImpl.java` | 141–145 | Same issue on void — VoidCheckEvent notification silently swallowed |
| `check-agent-config/.../DataSourceConfiguration.java` | 37 | Truststore written to filesystem from Base64 config — if config is compromised, truststore is compromised |
| `build.gradle` | 19 | Wirecard Nexus `http://` (not `https://`) — dependency resolution over plaintext HTTP |
