# Business Analyst View — exemplar-customer-service_WAPP

## Business Purpose
This repository is Onbe's reference architecture exemplar web application for a microservice. It demonstrates the canonical patterns, tooling choices, and structural conventions that development teams should follow when building new Gen-3 Spring Boot services at Onbe. It is explicitly a demo/template project, not a production business service.

## Capabilities
- Create, retrieve, and update customer records via a RESTful JSON/XML API.
- Publishes domain events (TheaterCreatedEvent) to a Dapr pub/sub topic, demonstrating event-driven messaging.
- Exposes Swagger/OpenAPI documentation through springdoc-openapi.
- Provides acceptance-test scaffolding using Cucumber BDD scenarios.
- Provides contract-test scaffolding using Pact (consumer-driven contract testing via PactFlow broker).
- Manages schema via Liquibase changesets.

## Entities
| Entity | Key Fields |
|--------|-----------|
| Customer | customerId (UUID), firstName, lastName, inserted/updated audit columns |

## Business Rules
- customerId is assigned server-side as a UUID on creation; callers may not supply their own.
- Customer records are unique by CUSTOMER_ID (unique index UDX_CUSTOMER_ID on the CUSTOMER table).
- All API endpoints require JSON or XML content negotiation (application/vnd.onbe.v1+json or XML equivalents).
- Liquibase ddl-auto is set to `none`; schema changes must go through Liquibase changesets only.

## Process Flows
1. **Create Customer**: POST /customers → CustomerController → CustomerServiceImpl → CustomerRepository (JPA, SQL Server) → 201 Created with Location header.
2. **Get Customer**: GET /customers/{customerId} → CustomerController → CustomerServiceImpl → CustomerRepository → 200 or 404.
3. **Update Customer**: PUT /customers → CustomerController → CustomerServiceImpl → CustomerRepository (flush) → 200.
4. **Event Publish**: POST /pubsub/{topic} → PublishController → Dapr client → pub/sub broker (MQTT or equivalent).

## Compliance Considerations
- The application.yml committed to source contains hardcoded credentials (`credentials.username`, `credentials.password`) and database passwords (`password: B00t1ful`). These must not appear in production configuration and represent a secrets-in-code violation under PCI DSS Requirement 8.
- H2 console is enabled in the committed config (`spring.h2.console.enabled: true`); this must be disabled or removed before any production-adjacent deployment.
- TLS for the SQL Server data source is configurable and present in code (DataSourceConfiguration.java).
- The Pact broker token (`emSbllw1wbfH-ZAFB-cD-Q`) is hardcoded in pom.xml; treat as a leaked secret.

## Risks
- Hardcoded credentials and tokens in committed source files (pom.xml, application.yml).
- H2 console enabled by default.
- Spring Boot 2.4.5 is end-of-life; dependency CVE exposure is expected.
- No authentication/authorisation mechanism is implemented in the exemplar; downstream teams may copy the pattern without adding security.
