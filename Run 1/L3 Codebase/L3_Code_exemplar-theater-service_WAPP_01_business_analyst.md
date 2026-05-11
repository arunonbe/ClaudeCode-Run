# Business Analyst View — exemplar-theater-service_WAPP

## Repository Overview

**exemplar-theater-service_WAPP** is a Gen-3 reference (exemplar) implementation of a Spring Boot microservice built to demonstrate Onbe's approved patterns for:
1. RESTful microservice design
2. Event-driven architecture using Dapr pub/sub
3. CQRS-style state management (create + state transition + audit history)
4. Multi-layered modular Maven project structure
5. Consumer-driven contract testing (Pact)
6. BDD integration testing (Cucumber)

The "theater" domain is deliberately neutral — it has no connection to Onbe's payment business. It is chosen purely as a vehicle to demonstrate the architecture patterns that development teams should apply when building real payment microservices.

## Business Patterns Demonstrated

### Pattern 1: Event-Driven Status Lifecycle

The theater entity demonstrates a status lifecycle pattern that mirrors real payment processing flows:
- A theater is **created** via a REST POST. Initial status = `PENDING` (`TheaterController.java` line 51).
- An external service publishes a `TheaterCreatedEvent` to the pub/sub topic `dii.integration.customerservice.theaterv1`.
- This service **subscribes** to that event and transitions the theater status to `CREATED` (`TheaterServiceImpl.java` lines 111–117).
- All status transitions are recorded in `THEATER_HISTORY` (audit trail).

This pattern is directly applicable to Onbe's payment use cases: a disbursement request starts in `PENDING`, transitions to `PROCESSING` or `COMPLETED` as downstream card processor events arrive.

### Pattern 2: Dapr Pub/Sub Integration

The service uses [Dapr](https://dapr.io/) as the pub/sub sidecar. The `SubscriberController.java` subscribes to topic `dii.integration.customerservice.theaterv1` on pub/sub component `dii-integration` (line 38). This demonstrates how Java Spring Boot services can decouple from specific message brokers (the underlying broker — MQTT or Redis — can be swapped by changing only the Dapr component configuration in `theater-service-dapr-components/`).

### Pattern 3: CRUD plus Audit History

Three business operations are exposed:
1. `POST /theaters` — Create a theater in PENDING status.
2. `GET /theaters/{theaterId}` — Retrieve current theater state.
3. `GET /theaters/history/{theaterId}` — Retrieve full status history (immutable audit log).

The audit history pattern (`THEATER_HISTORY` table, `TheaterHistoryRepository`) demonstrates how to maintain an immutable event log alongside a current-state record — a pattern directly applicable to Onbe's transaction and card event audit requirements.

### Pattern 4: Custom Site Relationship

Theaters are associated with a `CustomSite` entity (custom site code + ID). This models the Onbe concept of a program/client site, demonstrating how microservices should model client-scoped entities and their UUID-based identity management.

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | Spring Boot 2.5.1 |
| Language | Java 11 |
| Database | Microsoft SQL Server (via mssql-jdbc 9.2.1.jre11) |
| Schema Migration | Liquibase 4.3.5 |
| Pub/Sub Sidecar | Dapr 1.1.0 |
| API Documentation | SpringDoc OpenAPI / Swagger UI |
| Testing | JUnit 5, JMock, WireMock, Cucumber 6.10.4, Pact 4.2.6 |
| Code Quality | Checkstyle, JaCoCo (90% coverage minimum enforced) |
| Security Scanning | OWASP Dependency Check |

## Module Structure

| Module | Business Purpose |
|--------|-----------------|
| `theater-service-config` | Spring wiring of all contexts (AppConfig, Persistence, Service, REST) |
| `theater-service-data` | Shared domain model (TheaterInfo DTO, TheaterStatus enum, events, errors) |
| `theater-service-db-app` | Standalone Spring Boot app for Liquibase DB migration only |
| `theater-service-db-scripts` | Liquibase changelogs for THEATER, CUSTOM_SITE, THEATER_HISTORY tables |
| `theater-service-persistence` | JPA entities and Spring Data repositories |
| `theater-service-rest-controller` | REST endpoints and Dapr subscriber endpoint |
| `theater-service-service` | Business logic layer |
| `theater-service-qa` | BDD/integration tests using Cucumber and Pact contract tests |

## Compliance Notes for Applying this Pattern

When applying this pattern to real Onbe payment services:
- The `credentials` block in `application.yml` (lines 11–14) with plaintext username/password must be replaced with Azure Key Vault or Spring Cloud Config Server references.
- The `show-sql: true` JPA setting (application.yml line 65) logs all SQL queries to the application log — this must be `false` in production to prevent potential exposure of PII or payment data in log streams.
- The hardcoded database password in `application.yml` line 44 (`[REDACTED — rotate immediately]`) must be replaced with secrets management.
