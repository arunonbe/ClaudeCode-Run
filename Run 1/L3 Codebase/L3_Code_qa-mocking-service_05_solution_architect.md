# Solution Architect View — qa-mocking-service

## API Surface

The service exposes a single WireMock HTTP server on port 8082. The stub endpoints mirror Fiserv's REST API surface, including:

- `POST /customer/v4/cardholder` — cardholder balance/status inquiry
- Fiserv card-management endpoints for activation, embossing, PIN operations, DDA management, authorization control, and account creation (exact URL patterns defined per mapping file)

All endpoints are unauthenticated. WireMock accepts any request and evaluates it against stub matchers. There is no OAuth, API key, mTLS, or other authentication mechanism.

## Security Posture

The security posture of this service is intentionally minimal because it is a local test tool. Key characteristics:

- **No authentication**: Any client on the Docker host network can call any stub endpoint.
- **No TLS**: All communication is plain HTTP on port 8082.
- **No network isolation controls**: The docker-compose.yml defines no Docker network restrictions; the service is accessible to any process on the host.
- **Verbose logging**: Full request and response payloads are written to stdout with `--verbose`.

These characteristics are acceptable only in a fully isolated local development environment. If this service is ever deployed on a shared QA server or cloud environment, all four of the above must be addressed before deployment.

## Critical Vulnerability: Unversioned Base Image

**Finding**: `docker-compose.yml` line 4 — `image: wiremock/wiremock:latest`

Using an unversioned `latest` tag means the pulled image is non-deterministic across environments and time. A WireMock release introducing breaking changes to request-matching semantics (which has occurred across major versions, e.g., 2.x to 3.x) would silently corrupt test results. Additionally, a stale cached `latest` image may contain CVEs in its embedded JVM.

**Remediation**: Pin to a specific digest or semver tag; add Trivy scanning to a CI step.

## Critical Vulnerability: Sensitive Field Schema in Stub Responses

**Finding**: `mappings/fiserv/cardholder-balance-status/cardholder-balance-status-200.json` — fields `primaryCustomerSocialSecurityNumber`, `secondaryCustomerSocialSecurityNumber`, `primaryPinNumber`, `secondaryPinNumber`

These fields are currently set to the literal value `"string"`. However, the stub schema demonstrates the complete Fiserv cardholder response shape, including SAD fields (PIN) and PII fields (SSN, DOB). There is no technical control preventing a developer from replacing `"string"` with an actual value sourced from a test account or, worse, a production account. This represents a latent PCI DSS Req 3.2 (do not store SAD) and Req 3.3 (do not use real PANs in test) risk.

**Remediation**: Implement a pre-commit hook or CI step using a regex scanner (e.g., `detect-secrets` or `git-secrets`) configured to reject PAN-format strings (Luhn-valid 13–19 digit sequences) and SSN patterns from all JSON mapping files.

## Technical Debt

1. **No CI pipeline**: The repository has no GitHub Actions workflow, meaning no JSON syntax validation, no contract drift detection, and no image scanning occur on pull requests.
2. **No contract linkage**: Stub mappings are not derived from or validated against an OpenAPI specification for the Fiserv API, making drift invisible until integration tests fail unexpectedly.
3. **No shared mapping strategy**: Individual service repositories that consume Fiserv APIs each maintain their own test setup, creating duplication and inconsistency risk. A centralized mapping library with versioned releases would reduce drift.
4. **README quality**: The README provides minimal operational guidance. There is no documentation of which Onbe services consume this mock, which Fiserv API version the stubs correspond to, or how to add new mappings.

## Code-Level Findings

| Finding | Location | Severity |
|---|---|---|
| `latest` image tag (non-deterministic runtime) | `docker-compose.yml:4` | High |
| PIN fields (`primaryPinNumber`, `secondaryPinNumber`) in stub schema | `mappings/fiserv/cardholder-balance-status/cardholder-balance-status-200.json` | Medium |
| SSN fields in stub schema without access controls | Same file | Medium |
| No CI pipeline, no automated JSON validation | Repository-wide | Medium |
| `--verbose` flag logs full payloads | `docker-compose.yml:11` | Low (test-env only) |
| No Docker health check defined | `docker-compose.yml` | Low |
