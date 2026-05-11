# Enterprise Architect View — qa-mocking-service

## Platform Generation

This repository is test infrastructure that spans Gen-1 and Gen-2 concerns. The Fiserv API surface it mocks is the processor integration layer used by Gen-1 and Gen-2 card-management services (eCount/Citi lineage). The WireMock container itself is a modern, generation-agnostic tool. There is no direct Gen-3 (NexPay/Onbe Azure) alignment — Gen-3 services use different processor integrations.

## Integration Patterns

The service implements the **service virtualization** pattern: it acts as a controlled test double for Fiserv's card-management HTTP APIs. The pattern is:

- Consuming QA tests point their HTTP clients at `localhost:8082` instead of the real Fiserv endpoint.
- WireMock matches the incoming request to a pre-authored stub and returns the scripted response.
- Tests remain isolated from Fiserv certification environment availability, rate limits, and test data management requirements.

This is aligned with the broader QA ecosystem that uses `qa-test-automation` for XML-RPC service testing; however, those two repositories test different integration layers and are not directly linked.

## External Dependencies

- **Docker Hub** (`wiremock/wiremock:latest`): External runtime image dependency, unversioned.
- **Fiserv API schemas**: The stub mappings implicitly depend on Fiserv's REST API contracts. There is no formal contract linkage (no OpenAPI spec, no Pact contract).

## Position in the Broader Platform

`qa-mocking-service` occupies the test-infrastructure layer. It is consumed exclusively by:
- QA engineers running integration tests against Gen-1/Gen-2 services that call Fiserv APIs
- Potentially CI pipelines of those services (no evidence of automated wiring found in this repo)

The service has no role in production data flows, operational monitoring, or platform routing.

## Migration Blockers

None in the classical sense. This is test tooling that may need to evolve alongside Gen-1 service decomposition. Specific considerations:
- If Gen-1 Fiserv-connected services are retired as part of Gen-3 migration, this repository's Fiserv mappings become obsolete.
- New Gen-3 processor integrations (e.g., FIS, Galileo) would require new mapping sets under a different URL namespace.
- There is currently no mechanism to share or reuse WireMock mappings across CI pipelines of individual service repos, which is an integration gap.

## Strategic Status

**Maintenance mode, low strategic investment.** This repository should be retained as long as Gen-1/Gen-2 Fiserv-connected services are under active QA, but it requires:
1. A pinned WireMock version and a minimal CI pipeline with JSON validation.
2. A formal data-hygiene policy prohibiting real cardholder data in stubs.
3. A mapping-freshness review process tied to Fiserv API change notifications.

Long-term, as Gen-3 migration matures, this repository should be succeeded by contract-testing tooling (Pact) integrated directly into microservice CI pipelines, which would eliminate the need for a centralized mock server.
