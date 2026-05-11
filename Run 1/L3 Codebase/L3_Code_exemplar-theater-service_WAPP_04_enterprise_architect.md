# Enterprise Architect View — exemplar-theater-service_WAPP

## Platform Generation and Role

**Platform Generation**: Gen-3 (Onbe's cloud-native microservices platform)  
**Architectural Role**: Reference implementation (exemplar) for all new Gen-3 microservices

This is the canonical reference microservice at Onbe. Every new microservice team is expected to use this repository as their starting point. It demonstrates the full Gen-3 stack: Spring Boot + Dapr + SQL Server + Liquibase + OpenAPI + JaCoCo + Checkstyle + OWASP + Pact + Cucumber.

## Gen-3 Architecture Patterns Demonstrated

### 1. Layered Modular Maven Structure

The project is structured as a multi-module Maven project with clear separation of concerns:
```
theater-service (root pom)
├── theater-service-data          ← Shared domain model (DTOs, events, enums, exceptions)
├── theater-service-persistence   ← JPA entities + Spring Data repositories
├── theater-service-service       ← Business logic (interface + implementation)
├── theater-service-config        ← Spring context wiring (imports all contexts)
├── theater-service-rest-controller ← REST API + Dapr subscriber
├── theater-service-db-scripts    ← Liquibase changesets only
├── theater-service-db-app        ← Standalone migration runner
└── theater-service-qa            ← BDD + contract tests
```

This layered structure enforces dependency direction: controllers depend on services, services depend on persistence, nothing depends on controllers.

### 2. Dapr-Based Event-Driven Integration

Dapr is the middleware abstraction for pub/sub. The `SubscriberController.java` uses the `@Topic` annotation (line 38) to subscribe to events. This decouples the service from any specific message broker. In development, EMQ X MQTT is used; in production, this could be Azure Service Bus or Redis without changing application code.

The topic naming convention `dii.integration.customerservice.theaterv1` (`v1` suffix) demonstrates versioned event topics, enabling backward-compatible evolution of event contracts.

### 3. CQRS-Style Command and Query Separation

The service maintains two data paths:
- **Command path**: `POST /theaters` → creates theater in PENDING state.
- **Event consumption**: `TheaterCreatedEvent` → transitions to CREATED state.
- **Query path**: `GET /theaters/{id}` and `GET /theaters/history/{id}`.

The `THEATER_HISTORY` table acts as an event store within the SQL database, enabling temporal queries of entity state.

### 4. Consumer-Driven Contract Testing (Pact)

Pact integration with `https://northlane.pactflow.io/` demonstrates the contract-first approach for API integration. Consumer services publish their expectations; this service verifies them. This is the approved pattern for preventing integration regressions in Onbe's microservices ecosystem.

### 5. BDD Integration Tests (Cucumber)

The `theater-service-qa` module contains Cucumber feature files (`theater.feature`) and step definitions (`TheaterSteps.java`). This demonstrates end-to-end behavioral testing that can be run against a deployed environment, not just in-memory mocks.

## Dependencies

### Internal Onbe Dependencies

| Dependency | Type | Source |
|-----------|------|--------|
| `automated-database-migration` (`com.wirecard.issuing`) | Library | Wirecard-origin DB migration library |

This dependency (`database-migration.version=1.0.0.7+b2f00c`) pulls from the Onbe artifact repository and has a Wirecard origin — signaling that this is a legacy dependency from the Wirecard acquisition era. This warrants review for active maintenance.

### External Dependencies

| Dependency | Version | Notes |
|-----------|---------|-------|
| Spring Boot | 2.5.1 | Multiple known CVEs in this version (see solution architect view) |
| Dapr SDK | 1.1.0 | Relatively old Dapr SDK version |
| H2 | 1.4.200 | In-memory DB for tests only |
| Pact | 4.2.6 | Contract testing |
| Cucumber | 6.10.4 | BDD testing |

## Ecosystem Position

```
[External Event Producer]
    (e.g., customer-service publishes TheaterCreatedEvent)
           |
           | MQTT / Redis (via Dapr)
           v
[exemplar-theater-service_WAPP] ← This service
    |
    | JDBC
    v
[Theater DB] (provisioned by exemplar-database_WAPP)
```

This service is both a REST API provider (for consumers of the theater domain) and a Dapr event consumer (for events published by the customer-service exemplar). This dual role demonstrates the typical microservice integration pattern at Onbe.

## Platform Compliance

For adapting this pattern to production payment services:

1. **Authentication/Authorization**: The exemplar has a placeholder credential block in `application.yml` (lines 11–14) but no actual Spring Security or OAuth2 integration. Production services must implement JWT validation against Onbe's identity provider.

2. **TLS**: `tlsEnabled: true` appears in the datasource config (line 57) but the actual truststore configuration (`global.datasource.truststore.location`) is set to a fake value (`/tmp/ora.jks`). Production services must configure real TLS certificates for database connectivity.

3. **PCI DSS Logging**: `show-sql: true` must be disabled. Actuator endpoints must be secured (not exposed publicly).

4. **Spring Boot Version**: 2.5.1 is significantly outdated. Production services should target Spring Boot 3.x with Java 17+ for active LTS support and Spring Security 6.x.
