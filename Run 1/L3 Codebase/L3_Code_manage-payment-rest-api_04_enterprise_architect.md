# Enterprise Architect View — manage-payment-rest-api

## Platform Generation

**Generation 2.5 — Modern API Facade over Legacy Platform**

`manage-payment-rest-api` occupies a strategic position as a **modernisation bridge**: it exposes a clean, OpenAPI-documented, JWT-authenticated REST API to enterprise clients, while internally delegating all business logic to Gen-1/2 legacy services (Account Management API, Director Service, Banker Service) through SOAP, Spring Remoting, and Apache Axis protocols.

Key indicators:
- Spring Boot 3.4.5 (modern, Jakarta EE 10)
- Java 21, Docker container, Azure Container Apps deployment
- Depends on `accountmanagementapi-impl:3.1.8` and `debitapi-impl:3.1.2` — legacy service wrappers that call legacy SOAP/XmlRPC backends
- Depends on `jakarta-spring-remoting` and `jakarta-axis-*` — migrated legacy SOAP libraries
- Connects to the same `cbaseapp`, `jobsvc`, `ecountcore` SQL Server databases as the legacy prepaid platform

## Business Domain

**External Payment Management API — Client-Facing Payment Disbursement**

This service is the primary **external-facing API surface** for enterprise clients to interact with Onbe's payment platform programmatically. It serves the same business purpose as the legacy `clientapi_API` (batch file import + SOAP) but offers a REST/JSON interface with fine-grained JWT-based access control. It is published to Azure APIM as an externally accessible API (`EXTERNAL_APIM: true`).

## Position in the Architecture

```
[Enterprise Client (external)]
         │ HTTPS + JWT
         ▼
[Azure APIM] (apim-az1-cluster-{env}-ss)
         │ route: /managepayments
         ▼
[manage-payment-rest-api] (ACA: ca-ManagePaymentAPI-{env})
  │
  ├──→ [accountmanagementapi-impl]
  │       ├──→ [Director Service] (nam.wirecard.sys:8080 SOAP)
  │       └──→ [cbaseapp DB] (stored procedures)
  │
  ├──→ [debitapi-impl]
  │       ├──→ [Banker Service SOAP] (nam.wirecard.sys:9009)
  │       └──→ [Redis Cache]
  │
  ├──→ [jobsvc DB] (job action queue)
  ├──→ [ordersvc DB] (order management)
  ├──→ [ecountcore DB] (core platform)
  └──→ [Redis Cache] (international program flags)
```

## Dependencies

### Upstream (Clients)
| Consumer | Channel | Operations |
|---|---|---|
| Enterprise clients | Azure APIM (external) | Account creation, fund loads, withdrawals, card inquiries, debit operations |
| Internal systems | Azure APIM (internal path) | Programmatic payment management |

### Downstream
| Service | Type | Criticality |
|---|---|---|
| Director Service (`prod.nam.wirecard.sys:8080`) | SOAP via Spring Remoting | Critical — account management |
| Banker Service (`prod.nam.wirecard.sys:9009`) | SOAP WSDL | Critical — debit operations |
| cbaseapp DB | SQL Server (JDBC) | Critical — cardholder data |
| jobsvc DB | SQL Server (JDBC) | High — job queue |
| ordersvc DB | SQL Server (JDBC) | High — order management |
| ecountcore DB | SQL Server (JDBC) | High — core platform |
| Redis Cache (`redis-az1-recipientweb-prod-ss`) | Azure Redis TLS | Medium — country/program flags |

## Integration Patterns

- **Facade pattern**: Thin REST layer over legacy SOAP/XmlRPC backends.
- **Two-phase commit for debit**: `begin → commit/cancel` implemented at REST API level, backed by legacy debit service.
- **JWT + APIM gateway**: External clients authenticate via Azure AD OAuth, receive JWTs validated by the `JwtSecurityValidator` at the API layer.
- **Feature-level authorization**: JWT claims control not just which endpoints a client can call but which response fields they receive (e.g., a client may call `cardInquiry` but not receive the PAN if the `Return-Card-Number` feature is not granted).
- **Dapr (partially implemented)**: `dapr-components/` directory and dependencies suggest Dapr was considered or is being piloted for secret management, but the service does not appear to use Dapr sidecars in production (no Dapr sidecar annotations in deployment config).

## Strategic Status

**Active / Strategically Important — Primary External API**

This service is the designated path for **API-based client integration** with Onbe's payment platform. Its latest release tag (`20260430.203650`) confirms it is actively deployed and updated. It is the modernisation path for clients currently using the legacy `clientapi_API` batch SOAP interface.

However, it is architecturally a **stopgap**, not a final state:
- The legacy SOAP/Spring Remoting backends it depends on (`Director Service`, `Banker Service`) must eventually be replaced with Gen-3 NexPay services.
- The `trustServerCertificate=true` and `javax.*` → `jakarta.*` dependencies indicate the legacy platform integration has not been fully modernised.

The long-term target is for the card issuance and fund load operations to be served by `nexpay-cardprocessor-svc` and the NexPay order/recipient orchestrators, with `manage-payment-rest-api` either retired or refactored as a thin adapter to those services.

## Migration Blockers

| Blocker | Severity | Resolution Path |
|---|---|---|
| `accountmanagementapi-impl` dependency | High | Replace with direct calls to `nexpay-cardprocessor-svc` when feature parity exists |
| `debitapi-impl` / Banker SOAP dependency | High | Replace with Gen-3 debit capability when available |
| SQL Server legacy databases (cbaseapp, ecountcore) | High | Requires migration to PostgreSQL (NexPay databases) — large scope |
| `dapr-secrets.json` credentials in repo | Critical | Immediate rotation and file removal from repository |
| `trustServerCertificate=true` | High | Replace with proper cert validation |

## Compliance Architecture

- **PCI DSS CDE**: In scope. `cardInquiry` and `cvvInquiry` return SAD. Service must be within a CDE-compliant network segment.
- **APIM as CDE boundary**: Azure APIM acts as the external-facing boundary. End-to-end TLS from APIM to ACA to backend services is required.
- **Reg E**: `addFunds` and `withdraw` operations constitute electronic fund transfers. The service must retain transaction records accessible for error resolution.
- **GDPR/CCPA**: Cardholder PII (name, address, email, phone) flows through `CreateAccountRequest`. Logbook masking covers `ssn`, `cardNumber`, `cvv` but not address or phone fields in logs.
