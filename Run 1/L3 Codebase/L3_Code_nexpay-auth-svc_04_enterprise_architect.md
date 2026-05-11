# Enterprise Architect Report — nexpay-auth-svc

## 1. Position in the Gen-3 Architecture

`nexpay-auth-svc` is the **identity foundation service** of the NexPay Gen-3 platform. It occupies the Identity and Access Management (IAM) layer:

```
NexPay Gen-3 Platform
├── Identity Layer
│   └── nexpay-auth-svc  ←── THIS SERVICE
│           │  Microsoft Graph API (OAuth2 client_credentials)
│           ▼
│       Microsoft Entra External ID (CIAM tenant)
│           │  OIDC/OAuth2
│           ▼
│       Cardholder browsers / MPV SPA
│
├── API Gateway (Azure APIM — Internal)
│   └── Routes /auth/** to nexpay-auth-svc
│
├── Application Layer
│   ├── nexpay-cardprocessor-svc
│   ├── nexpay-claim-code-svc
│   └── nexpay-order-orchestrator
│
└── Front-End
    └── mpv (cardholder portal)
```

The service is exclusively internal (`INTERNAL_APIM: true, EXTERNAL_APIM: false`). Cardholders do not authenticate directly against this service — they authenticate against Entra External ID directly (via OIDC flows initiated by MPV), and `nexpay-auth-svc` handles the back-channel user management operations.

## 2. OIDC/OAuth2 Architecture Analysis

The current implementation uses the Microsoft Graph API for user management but does not directly issue tokens to clients. The token issuance responsibility belongs to **Entra External ID itself** (which is an OIDC/OAuth2 authorization server). This is the correct architectural separation:

- **Entra External ID**: Token issuer, OIDC provider, credential storage, MFA enforcement
- **nexpay-auth-svc**: User lifecycle management (create, query) via Graph API; does not store passwords

**Critical gap — PKCE**: The `README.md` describes this as an "Authentication service," but the implementation only handles user provisioning (create/query). The actual PKCE-based authorization code flow for cardholder authentication is handled entirely by Entra External ID. If MPV uses a public client (SPA without a client secret), it must use PKCE (`code_challenge` / `code_verifier`). There is no evidence in this repository that PKCE enforcement is configured in the Entra tenant — this is an external configuration concern, not a code concern, but it should be verified.

**Token rotation**: Refresh token rotation should be enforced at the Entra External ID tenant level. The service does not directly handle refresh token storage or rotation — this is also an external Entra configuration concern.

## 3. Client Secret Management

The service authenticates to Graph API using `client_credentials` grant with `ENTRA_CLIENT_ID` and `ENTRA_CLIENT_SECRET` environment variables (`application.yaml` lines 29-30). This has several enterprise architecture implications:

| Concern | Current State | Recommended State |
|---|---|---|
| Secret rotation | Manual (or automated via Key Vault rotation policy) | Automated via Azure Key Vault with rotation trigger |
| Secret leakage risk | Medium (env var in ACA) | Low (Managed Identity eliminates secret) |
| Multi-region resilience | Single client secret | Federated identity/Managed Identity works regionally |
| Audit trail | Key Vault access logs | Key Vault access logs |

The enterprise architecture recommendation is to migrate from `client_secret` to **Azure Managed Identity** for Graph API authentication. ACA supports both system-assigned and user-assigned managed identities. With a managed identity, no `client_secret` is needed — the ACA runtime automatically obtains tokens from Entra without any secret to manage or rotate.

## 4. Gen-3 Assessment

| Criterion | Assessment |
|---|---|
| Java version | Java 25 — ahead of NexPay standard (most services target 21-25) |
| Spring Boot | Spring Boot 4.x (via nexpay-parent) — current Gen-3 standard |
| Container runtime | Azure Container Apps (ACA) — Gen-3 standard |
| Configuration | Azure App Configuration + Key Vault — Gen-3 standard |
| Observability | OpenTelemetry via `otel.java.global-autoconfigure` — Gen-3 standard (note: not seen in cardprocessor but implied by nexpay-parent) |
| Database | None (Entra only) — appropriate for current scope |
| API-first | OpenAPI code generation (nexpay-auth-api module) — Gen-3 standard |
| Auth protocol | OAuth2 client_credentials to Graph API — acceptable; Managed Identity preferred |

## 5. Cross-Service Dependencies

`nexpay-auth-svc` is consumed by:
- **MPV / nexpay-recipientweb-bff**: Calls `POST /users/check-username` during registration and `POST /users` for user creation
- Potentially **nexpay-order-orchestrator** or **nexpay-recipient-profile-svc**: May call `GET /users/{externalId}` for identity verification

The service depends on:
- **Microsoft Entra External ID**: Hard dependency — all operations fail if Entra is unreachable
- **Azure App Configuration**: Soft dependency (startup degrades gracefully due to `optional:` prefix)
- **Azure Key Vault**: Implicit — secrets referenced in App Configuration are resolved from Key Vault

## 6. Security Architecture Summary

The OAuth2 security design is sound for a service-to-service identity management API:
- No PAN or financial data flows through this service
- Credentials are environment-variable injected from Key Vault
- Entra External ID handles all cardholder credential security
- The service is not internet-exposed

Primary residual risks:
1. `client_secret` rotation burden — mitigated by migrating to Managed Identity
2. Email logging at INFO level — GDPR data minimization concern
3. SNAPSHOT parent POM — build non-determinism risk
