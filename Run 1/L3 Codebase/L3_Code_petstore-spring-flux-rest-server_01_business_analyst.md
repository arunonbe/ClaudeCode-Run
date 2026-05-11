# Business Analyst Report — petstore-spring-flux-rest-server

## Business Purpose

`petstore-spring-flux-rest-server` is a Gen-3 reference implementation and demonstration application built on Onbe's `onbe-spring-boot` framework. It implements the classic OpenAPI "Petstore" specification as a fully functional Spring WebFlux (reactive) REST server deployed to Azure via containerized workloads. Its primary purpose is to serve as:

1. **A working reference application** demonstrating correct use of `onbe-spring-boot-starter`, reactive R2DBC data access, Azure App Configuration feature flags, Dapr secrets, structured logging, OpenAPI code generation, and the Onbe CI/CD pipeline pattern.
2. **A template for new Gen-3 microservices** — teams creating new OnePlatform services can use this repository as the canonical starting point, copying its multi-module Maven structure, Dockerfile, GitHub Actions workflows, and application configuration patterns.
3. **A testing ground for framework features** — the repository exercises BlockHound reactive testing, log correlation, Testcontainers integration, WireMock contract testing, Pact contract testing, and Azure App Configuration refresh.

Although it implements a fictional "pet store" domain (pets, not payments), every infrastructure pattern it demonstrates maps directly to patterns used in production payment services. The actual business value is in the reference implementation, not the pet domain.

## Capabilities

- **CRUD REST API (reactive):** Create, read, update, and delete "Pet" resources via a Spring WebFlux controller implementing the OpenAPI-generated `DefaultApiDelegate` interface.
- **Reactive R2DBC database access:** Connects to Microsoft SQL Server via R2DBC (non-blocking), with a `PetRepository` (Spring Data R2DBC) and a `DatabaseClient` for raw SQL queries. Supports retry on transient exceptions (`@Retryable(retryFor = R2dbcTransientException.class)`).
- **Azure App Configuration / Feature Flags:** `FeatureManager` is injected into the controller for runtime feature flag evaluation (e.g., `featureManager.isEnabled("streaming")`). Configuration refresh is implemented via a scheduled task that polls `AppConfigurationRefresh.refreshConfigurations()`.
- **Dapr secrets integration:** At startup, Dapr loads `SPRING_R2DBC_USERNAME` and `MERCHANTENRICHMENT_TRIPLE_APITOKEN` from the local (dev) or production secret store.
- **Streaming support:** `findAll()` returns a `Flux<Pet>` with `delayElements(500ms)` — demonstrating Server-Sent Events or reactive streaming patterns.
- **OpenAPI contract:** Published to Azure API Management (`PUBLISH_TO_APIM: true`, internal APIM, not external).
- **Pact contract testing:** The deployment pipeline includes `PACT_PACTICIPANT` and `VERIFY_PROVIDER_PACT` configuration, indicating consumer-driven contract testing integration.

## Client/Cardholder Impact

The Petstore service itself has no production cardholder impact — it is a reference/demo application. However, the patterns it establishes are directly adopted by payment services. If this reference application demonstrates incorrect security, configuration, or data access patterns, those patterns will propagate into production payment services built by Onbe engineers.

## Business Rules in Code

- `deletePet()` is not implemented — throws `NotImplementedException` (a deliberate stub demonstrating the delegate pattern).
- `findPets()` ignores the `tags` and `limit` parameters and delegates to `findAll()` (commented-out code with a note about demonstrating streaming). This is intentional for demonstration purposes but would be a business logic error in production.
- Retry behavior is configured at both the service layer (`@Retryable` on `getPetById`) and the controller layer (`@Retryable` on the entire `PetStoreControllerDelegate` class), creating double-retry behavior.
- Feature flag evaluation for `streaming` is logged but does not affect behavior (the `deletePet()` method that checks the flag throws `NotImplementedException` regardless).

## Regulatory Obligations

As a reference/demo application with no production CHD: no direct PCI DSS, NACHA, Reg E, or OFAC obligations. Indirectly, by being the template for production services, it must demonstrate compliance-aligned patterns:
- Dapr secrets (not hardcoded credentials) — aligned with PCI DSS Req 8.
- Structured logging (Logstash format) — aligned with PCI DSS Req 10.
- APIM publication — aligned with API governance for PCI DSS Req 6.

## Key Business Risks

- Teams adopting this as a template may inherit the double-retry anti-pattern if not caught in code review.
- The `findAll()` streaming demonstration with `delayElements(500ms)` in a production API would create severe performance issues under load — this pattern must not be copied into production services without modification.
- The Dapr secret list in `application.yaml` includes `MERCHANTENRICHMENT_TRIPLE_APITOKEN` — this reveals a real integration service name (merchant enrichment) that should not appear in a public-facing or widely-accessible repository, even as a placeholder.
