# Enterprise Architecture — nexpay-mock-processor-svc

## Platform Generation
**Gen-3 (NexPay)** — Developer tooling artifact within the Gen-3 NexPay microservices platform.

## Business Domain
Payment Processing / Developer Tooling. Supports the NexPay Gen-3 card-processing domain by providing test doubles for FIS (legacy prepaid processor) and Thredd (modern card processor) APIs.

## Role in the Platform
| Attribute | Value |
|-----------|-------|
| Type | Mock / Test Double Service |
| Deployed in production | No (intended for dev/test environments only) |
| Replaces | Direct integration with FIS sandbox and Thredd sandbox during development |
| Consumed by | nexpay-cardprocessor-svc, integration test suites |

## Dependencies
### Upstream (callers)
- `nexpay-cardprocessor-svc` — the real card processor service under development uses this mock for isolated testing.
- NexPay integration test suites.

### Downstream (calls made by this service)
- None. This service is a leaf node — it only receives requests and returns mock responses.

## Integration Patterns
- **Synchronous REST** — receives HTTP POST/GET/PUT requests and returns immediate responses.
- **Template-driven response injection** — response content is data-driven from SQLite, allowing test scenarios to be configured without code changes.
- **FIS protocol**: form-urlencoded POST with pipe-delimited plain-text responses (legacy format).
- **Thredd protocol**: JSON REST with OAuth2 bearer token pattern.

## Strategic Status
- **Non-production tooling** — no migration or decommission required at go-live; it runs alongside production deployments only in lower environments.
- As Gen-3 matures, this mock should be extended to cover all processor API surface areas exercised by `nexpay-cardprocessor-svc`.
- Spring Boot 4.0.2 / Java 25 adoption is ahead of current stable releases — represents an early adopter commitment to the Gen-3 technology stack; risk must be re-evaluated when stable versions are released.

## Migration Blockers
- None from an enterprise migration perspective; this is a test tool, not a system-of-record.
- If `nexpay-cardprocessor-svc` requires additional FIS or Thredd endpoints not yet mocked, the `DataSeeder` templates must be extended.
