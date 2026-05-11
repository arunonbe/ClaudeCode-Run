# Business Analysis — nexpay-mock-processor-svc

## Business Purpose
A development and testing mock server that simulates two external payment-processor APIs — FIS (legacy prepaid) and Thredd (modern card processor) — so that NexPay Gen-3 microservices can be developed and tested without connecting to live processor sandboxes. This service has no production payment-processing role; it is a developer tooling artifact within the NexPay Gen-3 platform.

## Capabilities
- Simulate FIS HTTP/form-POST endpoints: CreatePerson, AssignCard_LoadValue, OTB_ByProxy (balance), StatusAcct (card status).
- Simulate Thredd REST JSON endpoints: create card, load funds, get card balance, update card status.
- Simulate Thredd OAuth2 token endpoint (`/connect/token`).
- Template-driven responses stored in SQLite, editable at runtime without restarting the service.
- Dynamic value generation: random person IDs, card proxies, masked PANs, balances, expiry dates, transaction IDs, OAuth access tokens.
- OpenAPI/Swagger UI exposed at `/swagger-ui.html` (port 8085).
- Spring Boot Actuator health and info endpoints.

## Key Entities
| Entity | Purpose |
|--------|---------|
| `EndpointResponseTemplate` | JPA entity persisted in SQLite; keyed by `endpointKey` string; stores the response template body |

## Business Rules
- Each endpoint's response is driven by a template resolved from the `endpoint_response_templates` SQLite table.
- If no template row exists for an endpoint key, the controller throws `IllegalStateException` (5xx).
- `DataSeeder` inserts default templates idempotently on startup (only if the row does not already exist).
- Input parameters (e.g. `RefNum`, `Proxykey`, `Status`) from the request are injected into the template as `{confirmCode}`, `{proxyKey}`, `{status}` to make responses contextually accurate.
- Log-injection prevention: all user-supplied strings are sanitised (CR/LF/TAB stripped) before logging.

## Data Flow (per request)
1. Client POSTs to FIS or Thredd mock endpoint.
2. Controller looks up the matching template from SQLite via `EndpointResponseTemplateRepository`.
3. `TemplateResolverService` replaces `{token}` placeholders with request-derived or randomly generated values via `MockDataGenerator`.
4. Resolved string is returned as plain text (FIS) or JSON (Thredd).

## Compliance Relevance
- This service is explicitly a **test double**; it must **never** be deployed to production or connected to production networks.
- Templates contain fake PANs starting with `5555-5555` and masked placeholders — no real cardholder data is generated.
- No authentication on any endpoint — access control must be enforced at the network layer in any deployed test environment.

## Risks
- No authentication: if exposed on a reachable network, any caller can invoke mock endpoints.
- SQLite database file (`mock-responses.db`) is local to the container; state is lost on container restart unless a volume is mounted.
- Spring Boot version 4.0.2 / Java 25 at time of analysis — both are pre-release/early-access; may not be production-grade stable.
- No test sources observed in the repository; logic correctness relies entirely on manual inspection.
