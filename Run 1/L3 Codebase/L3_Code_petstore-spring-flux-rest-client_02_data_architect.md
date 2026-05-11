# Data Architect Report — petstore-spring-flux-rest-client

## Data Models

### API Client Models (OpenAPI-generated)
The `-api` module contains OpenAPI-generated client models mirroring the Petstore server contract:
- `Pet` — API response model with `id`, `name`, `tag`
- `NewPet` — API request model with `name`, `tag`

These are DTOs for HTTP JSON serialization/deserialization. No sensitive data fields.

### Configuration Models
`WebClientConfigProperties` — configuration properties for the WebClient:
- `petstore.webclient.base-url` — target API base URL
- `petstore.webclient.timeout` — request timeout (30s in local/dev profile)

### Test Data
File: `petstore-spring-flux-rest-client-boot/src/test/resources/postman/collections/QA_LB.postman_environment.json`
Contains Postman environment configuration for QA load balancer testing. This file may contain base URLs or environment-specific settings for the QA environment. No credentials should be in this file.

File: `petstore-spring-flux-rest-client-boot/src/test/resources/db/mssql/schema.sql` and `init.sql`
Test database schema for integration tests that use a Testcontainers SQL Server instance. The schema is likely the same Petstore `pet` table used in the server's tests. No CHD fields.

File: `petstore-spring-flux-rest-client-boot/src/test/resources/components/dapr-secrets.json`
Local Dapr secrets file for test execution. Should contain only test placeholder values, not real credentials.

## Sensitive Data Handling

The client application processes HTTP request/response pairs for the Petstore API. The Petstore domain data (`Pet` objects) contains no sensitive payment data.

### WebClient Observation Risk
`WebClientCustomizer` registers the `ObservationRegistry` with the `WebClient.Builder`:
```java
builder.observationRegistry(this.observationRegistry);
```
Micrometer Observation for WebClient automatically records HTTP client span attributes including: URL template, HTTP method, HTTP status, and optionally full URI. In a production payment API client that processes requests containing PAN, authorization tokens, or account identifiers in URLs or headers, Micrometer observation must be configured to **exclude** sensitive URL parameters and headers from trace spans. The reference implementation does not demonstrate this configuration, which could lead teams to inadvertently expose CHD in distributed traces.

### Retry Filter Data Flow
The `retryFilter` in `WebClientCustomizer` intercepts HTTP responses. In a payment API context, if the response body contains CHD (e.g., a card authorization response with a masked PAN), the response is held in memory during retry evaluation. The current implementation uses `ExchangeFilterFunction.ofResponseProcessor`, which buffers the response status code but not necessarily the body — the body stream is passed through. Body buffering risk is low, but should be confirmed in production usage.

## Data Flows

```
[Application code] --> [PetStoreClient (blocking facade)]
    --> [DefaultApi (generated)] --> [WebClient]
        --> [WebClientCustomizer: ObservationRegistry + retryFilter]
            --> [HTTP/HTTPS: petstore.webclient.base-url/v2]
                --> [petstore-spring-flux-rest-server (or mock)]
                    --> [JSON response] --> [DefaultApi model deserialization]
                        --> [Caller]

[Test execution] --> [PetStoreAcrImageTestContainerTests]
    --> [Docker (ACR image pull)] --> [Testcontainers petstore server container]
        --> [WebClient (localhost)]
```

## Encryption Status

- **HTTP transport:** `application.yaml` dev profile base URL is `http://localhost:8080/v2` — HTTP (not HTTPS). For local development this is acceptable. In QA/stage/prod profiles, the base URL must use `https://`. The current YAML has empty QA/stage/prod profile sections with no base URL configured — this must be filled in before any environment deployment.
- **R2DBC (test only):** Test resources include MS SQL Server schema for Testcontainers-based integration tests. No production database connectivity in the client.
- **Dapr test secrets:** Local Dapr test secret file (`dapr-secrets.json`) should contain only placeholder values.

## PCI DSS Compliance Assessment

As a reference/demo client application with no production CHD:
- No direct PCI DSS obligations for the Petstore data.
- As a template for production payment API clients:
  - Gap: Missing Micrometer Observation configuration to exclude sensitive headers/parameters from traces — production payment clients must add this.
  - Gap: QA/stage/prod `base-url` configurations are empty — teams must configure HTTPS URLs for all non-local environments.
  - Gap: No TLS client certificate configuration shown — mTLS for API authentication is not demonstrated.
  - Gap: Retry filter bug (see 05_solution_architect.md) means rate-limit handling does not function as intended.
