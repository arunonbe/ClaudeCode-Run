# Solution Architect Analysis: rubens-playground-ms

## Technical Architecture
- **Framework**: Spring Boot (via `nexpay-parent:0.1.10-SNAPSHOT`); Spring MVC (WebMVC, not reactive)
- **Language**: Java (JDK 25 in Docker; version from parent POM for compilation)
- **API Layer**: OpenAPI-generated Spring delegate pattern from `ordersapi.yml` via `openapi-generator-maven-plugin:7.18.0`
- **Persistence**: Spring Data JPA + Hibernate; PostgreSQL (prod) / H2 (dev/test)
- **Schema Migration**: Liquibase (`spring-boot-starter-liquibase`)
- **Email**: SendGrid Java SDK `4.10.3` + FreeMarker templates
- **Validation**: Jakarta Bean Validation (`@NotBlank`, `@Pattern`, `@Valid`)
- **Mapping**: `OrderMapper` (likely MapStruct or manual; class in `util/mapper/`)
- **Containerisation**: Multi-stage Dockerfile (JDK 25 build → JRE 25 runtime)
- **Logging**: SLF4J + Lombok `@Slf4j`

### Application Structure
```
src/main/java/com/onbe/stablerails/orderapims/
  OrderapimsApplication.java                  — Spring Boot entry point
  config/
    EmailConfiguration.java                   — SendGrid email config bean
    HttpClientConfiguration.java              — HttpClient bean
    OpenApiConfiguration.java                 — Springdoc config
    properties/AppProperties.java             — @ConfigurationProperties for app.* properties
  domain/entity/
    Order.java                                — JPA entity; orders table mapping
  exception/
    GlobalExceptionHandler.java               — @ControllerAdvice error handling
    EmailException.java, OrderCreationException.java, OrderValidationException.java
  model/email/
    EmailRequest.java, EmailResponse.java     — Email model
  repository/
    OrderRepository.java                      — JpaRepository<Order, Long> with custom finders
  service/
    email/EmailService.java + SendGridEmailServiceImpl.java — Email service
    ordersapi/OrdersApiDelegateImpl.java       — API delegate implementation
    template/TemplateService.java             — FreeMarker template rendering
  util/mapper/
    OrderMapper.java                          — CreateOrderRequest <-> Order <-> CreateOrderResponse
```

Generated (target/generated-sources):
```
  api/ordersapi/OrdersApiDelegate.java        — Generated interface (delegate pattern)
  model/ordersapi/CreateOrderRequest.java     — Generated request model
  model/ordersapi/CreateOrderResponse.java    — Generated response model
  model/ordersapi/Error.java                  — Generated error model
  (+ supporting generated models)
```

## API Surface
Defined in `ordersapi.yml` (OpenAPI 3.1.1):

| Method | Path | Operation | Auth |
|---|---|---|---|
| POST | `/orders` | `createOrder` | Bearer JWT (spec only) |
| GET | `/orders` | `lookupOrder` | Bearer JWT (spec only) |
| GET | `/orders/{orderId}` | `getOrder` | Bearer JWT (spec only) |

**Security**: `bearerAuth` (Bearer JWT) defined in `ordersapi.yml` components. **Auth enforcement is NOT implemented in the code** — no Spring Security configuration visible.

## Security Posture

### Authentication & Authorisation
- **No authentication enforcement**: Bearer JWT is defined in the OpenAPI spec (`securitySchemes.bearerAuth`) but no Spring Security configuration is present in the codebase. The API is effectively unauthenticated.
- `GlobalExceptionHandler` handles validation and runtime errors but provides no auth challenge.

### Sensitive Data in Logs
- `Order.toString()` (line 43-74 in `Order.java`) returns a string containing `firstName`, `lastName`, `dateOfBirth`, `address1`, `address2`, `city`, `state`, `postalCode`, `primaryPhone`, `mobilePhone`, `email`.
- `log.debug("order: {}", order)` at `OrdersApiDelegateImpl.java:123` and `log.debug("savedOrder: {}", savedOrder)` at line 127 will log all PII fields if DEBUG level is active.
- `log.debug("createOrderRequest: {}", createOrderRequest)` at line 119 logs the full request including all account data.

### Secrets Management
- `SENDGRID_API_KEY` is injected via environment variable — correct pattern.
- `DB_PASSWORD` via environment variable — correct pattern.
- docker-compose default values (`DB_PASSWORD=postgres`) are insecure defaults for non-local environments.

### Input Validation
- Bean validation on `CreateOrderRequest` via `@Valid` and Jakarta constraint annotations.
- `orderId` pattern `^ORD_\d{6}$` validated in OpenAPI spec; enforced by generated code.
- `smartLinkGuid` UUID pattern validated in spec.
- Currency code pattern `^[A-Z]{3}$` validated.
- Country code pattern `^[A-Z]{2}$` validated.

### Known CVEs / Vulnerable Dependencies
| Library | Version | Risk |
|---|---|---|
| `springdoc-openapi-starter-webmvc-ui` | 3.0.0 | Version 3.0.0 is non-standard (springdoc current is 2.x); verify this is a valid release |
| `spring-boot-devtools` | (parent-managed) | Must be excluded from production builds — provides remote restart and classpath reload capabilities |
| `h2` | (parent-managed) | H2 console must be disabled in non-dev profiles (CVE-2022-45868 if console enabled) |
| SendGrid Java SDK | 4.10.3 | Check for current CVEs |
| `swagger-models` | 2.2.40 | Check — appears very new; verify release validity |
| `openapi-generator-maven-plugin` | 7.18.0 | Build-time only; no runtime risk |

## Technical Debt
1. **No authentication enforcement** despite bearer auth in spec — must be implemented before any production use.
2. **`spring-boot-devtools` in runtime scope** (`pom.xml:103-107`): Devtools should be `optional=true` and excluded from production builds; it enables hot-reload and exposes a remote restart endpoint.
3. **Java 25 (pre-release JDK)**: Should use Java 21 LTS.
4. **SNAPSHOT versioning**: Both parent (`nexpay-parent:0.1.10-SNAPSHOT`) and artifact (`orders-api-ms:0.0.1-SNAPSHOT`).
5. **PII in DEBUG logs** (`Order.toString()`): All entity fields including DOB, phone, email logged at DEBUG.
6. **No DOB encryption** in `Order.java`: `dateOfBirth` is a plain `LocalDate` column.
7. **`springdoc-openapi-starter-webmvc-ui:3.0.0`**: Non-standard version number for springdoc.
8. **`db/` directory not read**: Liquibase changelogs in `db/` were not analysed; SQL DDL may contain additional sensitive column definitions or missing indexes.
9. **`docker-compose.yml` default credentials**: `DB_PASSWORD=postgres` as a default in compose file.
10. **`network_mode: host`** in docker-compose: Not suitable for production.

## Gen-3 Promotion Requirements (Sandbox to Production)
1. Implement Spring Security with JWT bearer token validation (Onbe IDP / Azure Entra).
2. Replace Java 25 with Java 21 LTS in Dockerfile.
3. Release `nexpay-parent` and this artifact with proper semver release versions.
4. Mask PII in `Order.toString()` (or remove `@Data` and write custom `toString()` that omits sensitive fields).
5. Encrypt `date_of_birth` at application layer (e.g., JPA `AttributeConverter` with AES-256).
6. Set `spring-boot-devtools` to `optional=true`.
7. Disable H2 console in non-dev Spring profiles.
8. Add Azure Pipelines / GitHub Actions CI/CD pipeline committed to repo.
9. Integrate SendGrid API key with StrongBox / Azure Key Vault (not env var alone).
10. Add rate limiting (Spring `@RateLimiter` or Azure APIM).
11. Add OpenTelemetry for distributed tracing.

## Code-Level Risks (File:Line References)
- `Order.java:43-74` — `toString()` includes `dateOfBirth`, `firstName`, `lastName`, `email`, `primaryPhone`, `mobilePhone`, `address1`, `address2`, `postalCode`; all will appear in DEBUG logs.
- `OrdersApiDelegateImpl.java:119,123,127` — `log.debug("createOrderRequest:", ...)`, `log.debug("order:", ...)`, `log.debug("savedOrder:", ...)` — PII in debug.
- `AppProperties.java:29-31` — `@DefaultValue` exposes the Azure Container Apps URL in compiled code — acceptable for non-secret URLs.
- `docker-compose.yml:18` — `SENDGRID_API_KEY=${SENDGRID_API_KEY}` — no default (good); but `DB_PASSWORD=postgres` default on line 28 is insecure.
- `pom.xml:103-107` — `spring-boot-devtools` with `scope=runtime` — must be made `optional=true` to prevent inclusion in production JAR.
- `OrdersApiDelegateImpl.java:138-145` — `DataIntegrityViolationException` caught and re-thrown (correct behaviour); generic `Exception` caught at line 141 and wrapped as `OrderCreationException` — may mask unexpected errors.
