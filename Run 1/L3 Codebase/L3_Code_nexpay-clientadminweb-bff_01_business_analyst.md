# nexpay-clientadminweb-bff — Business Analyst View

## 1. Service Purpose and Business Context

`nexpay-clientadminweb-bff` is the Backend-for-Frontend (BFF) layer that backs the NexPay Client Administration Web portal. The portal is used by Onbe's internal client-facing operations staff (program managers, client success managers, and administrators) to configure and monitor payment programs, promotions, and country/modality settings for B2C disbursement clients.

The service acts as an orchestration and translation layer: it aggregates data from multiple downstream microservices (currently `nexpay-claim-code-svc` and `nexpay-config-svc`) and presents a coherent, web-friendly API surface that the React/Angular front end consumes. By keeping all service-to-service communication inside the Azure Container Apps internal network, the BFF prevents the browser from directly calling back-end services with sensitive credentials.

## 2. Key Business Capabilities Observed

| Capability | Evidence |
|---|---|
| Program modality enquiry | `ConfigSvcClient.getModalityDetail()` — `GET /programs/{programId}/modality-detail` |
| Program registration settings | `ConfigSvcClient.getRegistrationSettings()` — `GET /programs/{programId}/registration-settings` |
| Country configuration (address validation) | `ConfigSvcClient.getCountriesWithAddressConfig()` — `GET /programs/{programId}/countries?withAddressConfig=true` |
| Claim code management | `ClaimCodeSvcClient` — delegates to `nexpay-claim-code-svc` |
| API published to external APIM | `deployment.yml` lines 28–31 — `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` |

The service is explicitly annotated in the IaC configuration (`qa.tfvars` line 199) as `external_enabled: true`, confirming that it is reachable through Azure API Management (APIM) from the internet-facing admin portal SPA.

## 3. User Personas and Workflows

**Client Program Manager**: Queries available payment modalities (ACH, prepaid card, push-to-card, virtual card) available for a specific program, so they can advise clients on which disbursement rails are active.

**Onbe Operations / Client Admin**: Retrieves registration settings (self-registration toggles, OTP requirements, address verification strictness) to support client onboarding configuration.

**System Integration Owner**: Uses claim code APIs to provision or retrieve unique claim codes that recipients use to activate their disbursement.

## 4. Integration with Other NexPay Services

```
Client Admin Web SPA (browser)
    → Azure APIM (External)
        → nexpay-clientadminweb-bff  (Azure Container App, external ingress)
            → nexpay-claim-code-svc  (internal, http://ca-nexpay-claim-code-svc-qa)
            → nexpay-config-svc      (internal, http://ca-nexpay-config-svc-qa)
```

Service URLs are injected at container startup via Azure App Configuration (`appcg-nexpay-qa.azconfig.io`) using the key filter `nexpay-clientadminweb-bff/` with label `qa` (`application-qa.yaml` lines 17–24). No URL is hardcoded in the source code beyond environment-variable defaults for local development.

## 5. Business Rules and Constraints

- **Idempotency**: The `AuditFilter` captures an `Idempotency-Key` header and propagates it through OpenTelemetry baggage for end-to-end deduplication (`AuditFilter.java` line 91–103). This is relevant for claim code issuance, which must not be duplicated.
- **Actor attribution**: Every request records an `actor.id` (sourced from JWT `email`, `preferred_username`, or `sub` claims) in OTEL baggage. This is the audit trail required for PCI DSS Requirement 10.2 (individual accountability).
- **Swagger/OpenAPI disabled in QA/prod**: Lines 43–46 of `application-qa.yaml` confirm that the API docs endpoint is disabled in non-local environments, reducing the attack surface.
- **Program-scoped access**: All config queries are scoped to a `programId` path parameter, enforcing per-program data isolation at the API contract level.

## 6. Outstanding Business Risks

1. **No authorisation check on `programId`**: The current implementation delegates authorisation to downstream services. If `nexpay-config-svc` does not enforce that the requesting user's JWT is authorised for the requested `programId`, any authenticated admin user could query any program's config. This is an access-control gap that must be addressed before production.
2. **Claim code API scope**: The file tree includes `nexpay-clientadminweb-claimcode-client-api` and `nexpay-clientadminweb-config-client-api` modules (`nexpay-clientadminweb-client/`) but the actual controller implementing these endpoints was not present at analysis time, suggesting development is still in progress. Business requirements for claim code CRUD in the admin portal should be confirmed.
3. **Actuator management port exposed**: The management actuator (`/actuator/health`, `/actuator/env`, `/actuator/metrics`) is exposed on port 8081 (`application.yaml` lines 36–51). The `env` endpoint can reveal configuration values. It must be restricted to the Container Apps internal subnet and not fronted by APIM.

## 7. Regulatory Relevance

The admin portal configures programs that in turn determine cardholder experience (modality availability, registration, country coverage). Configuration errors (e.g., enabling the wrong modality for a program) could result in regulatory exposure under Reg E (error resolution obligations) or UDAAP (unfair/deceptive acts). The audit trail via `AuditFilter` is the primary control for demonstrating that configuration changes are attributable to named individuals.
