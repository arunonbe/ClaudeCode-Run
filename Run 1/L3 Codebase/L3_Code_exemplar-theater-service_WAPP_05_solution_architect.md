# Solution Architect View — exemplar-theater-service_WAPP

## Complete Class/Method Inventory

### Package: `com.onbe.service.theaterservice` (config module)

**`TheaterServiceApplication.java`**
- `main(String[] args)`: Entry point. Parses `-p <port>` CLI argument, starts Spring Boot on the specified port. Uses Apache Commons CLI for argument parsing.

**`DataSourceConfiguration.java`**
- Spring `@Configuration` class for HikariCP datasource wiring. Configures connection pool using `DataSourceTruststoreProperties`.

**`DataSourceTruststoreProperties.java`**
- `@ConfigurationProperties` binding for `global.datasource.truststore.*` properties (location, password, content, type). Supports TLS truststore configuration for encrypted database connections.

**`AppConfigContext.java`** (package `appconfig`)
- Spring `@Configuration` context for Azure App Configuration integration.

**`PersistenceContext.java`** (package `persistence`)
- Spring `@Configuration` that imports JPA and transaction management.

**`RestControllerContext.java`** (package `restcontroller`)
- Spring `@Configuration` enabling REST controller component scan.

**`ServiceContext.java`** (package `service`)
- Spring `@Configuration` enabling service layer component scan.

---

### Package: `com.onbe.service.theaterservice.data` (data module)

**`TheaterInfo.java`**
- DTO: `theaterId`, `customSiteId`, `customSiteCode`, `creatorSubjectId`, `creatorIssuerId`, `status`. Used as both request body and response body. Lombok `@Builder`, `@Data`.

**`TheaterStatus.java`** (enum, package `common`)
- Values: `PENDING`, `CREATED`. Method `value()` returns the string representation.

**`ErrorResponse.java`** (package `error`)
- Error response DTO with HTTP status code and message.

**`ErrorType.java`** (enum, package `error`)
- Enumerates error categories (NOT_FOUND, BAD_REQUEST, INTERNAL_SERVER_ERROR, BAD_GATEWAY).

**`TheaterCreatedEvent.java`** (package `event`)
- Event payload: `theaterId` (String). Deserialized from Dapr CloudEvent data.

**`NotFoundException.java`** (package `exception`)
- Custom `RuntimeException` thrown when a theater ID is not found in the database.

---

### Package: `com.onbe.service.theaterservice.persistence` (persistence module)

**`BaseEntity.java`** (package `entity`)
- Abstract JPA base entity with `id` (UUID, auto-generated), `version` (optimistic locking), `insertedAt`, `insertedBy`, `updatedAt`, `updatedBy` audit columns.

**`CustomSite.java`** (entity)
- JPA entity mapping to `CUSTOM_SITE` table. Fields: `customSiteId`, `customSiteCode`. Extends `BaseEntity`.

**`Theater.java`** (entity)
- JPA entity mapping to `THEATER` table. Fields: `theaterId`, `customSite` (one-to-one), `creatorSubjectId`, `creatorIssuerId`, `status` (enum). Extends `BaseEntity`.

**`TheaterHistory.java`** (entity)
- JPA entity mapping to `THEATER_HISTORY` table. Fields: `theater` (many-to-one), `status` (enum). Extends `BaseEntity`.

**`CustomSiteRepository.java`** (interface)
- Extends `JpaRepository<CustomSite, String>`. Standard CRUD for custom sites.

**`TheaterRepository.java`** (interface)
- Extends `JpaRepository<Theater, String>`. Custom method: `Optional<Theater> findByTheaterId(String theaterId)`.

**`TheaterHistoryRepository.java`** (interface)
- Extends `JpaRepository<TheaterHistory, String>`. Custom method: `List<TheaterHistory> findByTheaterOrderByInsertedAtDesc(Theater theater)` — returns history sorted newest-first.

---

### Package: `com.onbe.service.theaterservice.service`

**`TheaterService.java`** (interface)
- `TheaterInfo saveTheater(TheaterInfo theaterInfo, TheaterStatus theaterStatus)`: Persist a new theater.
- `TheaterInfo getTheater(String theaterId)`: Retrieve theater by ID.
- `List<TheaterInfo> getTheaterHistory(String theaterId)`: Retrieve status history.
- `void consumeTheaterCreatedEvent(TheaterCreatedEvent event)`: Handle event consumption.

**`TheaterServiceImpl.java`** (implementation)
- `saveTheater(...)`: Creates `CustomSite`, `Theater`, and initial `TheaterHistory` record atomically. Generates UUID if not provided.
- `getTheater(String theaterId)`: Fetches `Theater` entity, maps to `TheaterInfo` DTO.
- `getTheaterHistory(String theaterId)`: Fetches ordered `TheaterHistory` list, maps to `List<TheaterInfo>`.
- `consumeTheaterCreatedEvent(TheaterCreatedEvent)`: If theater exists and status != CREATED, updates to CREATED and creates history record. If theater does not exist, creates it directly in CREATED state (lines 119–128).

---

### Package: `com.onbe.service.theaterservice.restcontroller`

**`TheaterController.java`**
- `createTheater(@Valid TheaterInfo, UriComponentsBuilder)`: `POST /theaters` → 201 Created with `Location` header.
- `getTheater(@PathVariable String theaterId)`: `GET /theaters/{theaterId}` → 200 OK.
- `getTheaterHistory(@PathVariable String theaterId)`: `GET /theaters/history/{theaterId}` → 200 OK with list.

**`SubscriberController.java`**
- `consumeEvent(@RequestBody CloudEvent)`: `POST /dii.integration.customerservice.theaterv1` — Dapr pub/sub endpoint. Deserializes `TheaterCreatedEvent` and calls `theaterService.consumeTheaterCreatedEvent(...)`.

**`SwaggerConfiguration.java`**
- SpringDoc OpenAPI configuration. Excluded from JaCoCo coverage (`pom.xml` line 314).

**`ApiVersion.java`**
- Constants for `Accept` and `Content-Type` headers (`application/json`).

**`GeneralExceptionControllerAdvice.java`** (package `advice`)
- `@ControllerAdvice` that maps `NotFoundException` → 404, general exceptions → 500. Returns `ErrorResponse` JSON.

---

## Security Vulnerabilities

### VULN-1: Hardcoded Credentials in application.yml (CRITICAL)
**File**: `theater-service-config/src/main/resources/application.yml` lines 11–14 and 44  
**Detail**: Plaintext credentials: `credentials.username`, `credentials.password`, `datasource.password: [REDACTED — rotate immediately]`. These are committed to version control.  
**Remediation**: Replace with Spring Cloud Config Server external properties or Azure Key Vault references.  
**Priority**: P1.

### VULN-2: show-sql: true (HIGH — PII/Data Exposure)
**File**: `application.yml` line 66  
**Detail**: JPA SQL logging enabled. In any service handling real data, this logs parameterized query values to application logs, potentially exposing PII or payment data.  
**Remediation**: Set `show-sql: false` in all non-local profiles.  
**Priority**: P1 for any payment-data service derived from this pattern.

### VULN-3: Spring Boot 2.5.1 (HIGH — Multiple CVEs)
**File**: `pom.xml` line 9  
**Detail**: Spring Boot 2.5.1 is over 3 years old and has numerous known CVEs (Spring Framework, Spring Security, Netty, etc.). OWASP dependency check is configured but the version is old.  
**Remediation**: Upgrade to Spring Boot 3.3.x (Java 17 minimum).  
**Priority**: P2.

### VULN-4: PactFlow Token in pom.xml (MEDIUM)
**File**: `pom.xml` line 404: `<pactBrokerToken>emSbllw1wbfH-ZAFB-cD-Q</pactBrokerToken>`  
**Detail**: The PactFlow authentication token is committed in the pom.xml. This token grants access to the contract test broker.  
**Remediation**: Move to a CI/CD secret variable. Use `${env.PACT_BROKER_TOKEN}` Maven property.  
**Priority**: P2.

### VULN-5: Actuator Full Exposure (MEDIUM)
**File**: `application.yml` lines 82–84: `exposure.include: '*'`  
**Detail**: All actuator endpoints exposed, including `/heapdump`, `/env`, `/configprops`. In a production deployment without authentication, these endpoints leak configuration data.  
**Remediation**: Restrict to `health,info,metrics` or add Spring Security to protect actuator endpoints.  
**Priority**: P2.

### VULN-6: H2 Console Enabled (LOW)
**File**: `application.yml` lines 18–20: `h2.console.enabled: true`  
**Detail**: H2 web console enabled. If this property carries over to an environment using H2, it exposes a database console endpoint.  
**Remediation**: Disable H2 console in all non-local profiles.  
**Priority**: P3.

## Technical Debt

| Item | Description |
|------|-------------|
| Dapr SDK 1.1.0 | Old version; current is 1.12+. Breaking API changes may require updates. |
| Wiremock 2.8.0 | Very old WireMock version; 3.x is current. |
| H2 1.4.200 | H2 1.x is EOL; 2.x is current. |
| Fake truststore path | `truststore.location: /tmp/ora.jks` is a placeholder; TLS is not actually configured. |
| `RuntimeException` wrapping in SubscriberController | `consumeEvent` catches Exception and rethrows as `RuntimeException` (line 47) — loses stack context. Should rethrow typed exception. |
| `logger.info(...)` with string concatenation | Several log statements use `+` concatenation instead of parameterized logging, which has minor performance implications. |

## Remediation Priority Summary

| Priority | Item |
|----------|------|
| P1 | Remove hardcoded credentials from application.yml |
| P1 | Disable show-sql in production profiles |
| P2 | Upgrade Spring Boot to 3.x |
| P2 | Move PactFlow token to CI secret |
| P2 | Restrict Actuator endpoint exposure |
| P3 | Upgrade Dapr SDK, WireMock, H2 to current versions |
| P3 | Implement real TLS truststore configuration |
