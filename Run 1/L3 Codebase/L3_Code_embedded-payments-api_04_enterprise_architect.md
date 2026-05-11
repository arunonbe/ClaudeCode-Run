# 04 Enterprise Architect — embedded-payments-api

## Platform Generation

`embedded-payments-api` is a **Generation 3 (Gen-3) service** — the most modern component in this repository set. Evidence:

| Dimension | Value |
|---|---|
| Java | 21 |
| Spring Boot | 3.4.5 (latest as of mid-2025) |
| Database driver | `mssql-jdbc:13.x` (modern Microsoft driver) |
| Security | Azure AD OAuth2, Spring Security 6.5.5 |
| Config | Azure App Configuration + Azure Key Vault |
| Logging | Logback + logstash JSON encoder (structured logs) |
| Resilience | Resilience4j circuit breakers + retries |
| API contract | OpenAPI 3.0.3 code-first spec |
| ORM | Spring Data JPA / Hibernate |
| API docs | SpringDoc OpenAPI 2.8.4 (Swagger UI) |
| Caching | Ehcache 3.11.0 |
| Build | Maven + OpenAPI generator plugin |

## Role in Platform Architecture

The service is the **white-label embedded payments gateway** — the first Gen-3 product surface that external partners interact with directly. It bridges:

```
Partner's Web Application
        │
   (iFrame embed)
        │
  ┌─────▼─────────────────────────────────────────────────────┐
  │  embedded-payments-sdk (JavaScript shim + widget SPA)     │
  └─────┬─────────────────────────────────────────────────────┘
        │  HTTPS
        ▼
  Azure APIM (API Management)
        │
        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  embedded-payments-api (Spring Boot 3.4, Java 21)           │
  │  - Authentication (OTT, OAuth2 cookies)                     │
  │  - Disbursement orchestration                               │
  │  - Widget asset serving (static resources)                  │
  └─────────────┬───────────────────────┬────────────────────┘
                │                       │
          ┌─────▼────────┐    ┌─────────▼──────────┐
          │ ecount-core  │    │   SQL Server DBs    │
          │ (SOAP/REST)  │    │  (5 datasources)   │
          └──────────────┘    └────────────────────┘
                │
          ┌─────▼────────────────────────┐
          │  Azure Services              │
          │  (App Config, Key Vault,     │
          │   AD OAuth2, Wallets APIM)   │
          └──────────────────────────────┘
```

## Multi-Module Design Rationale

The split between `embedded-payments-api` (runtime) and `embedded-payments-open-api` (contract) enables:
1. **API-first development**: The OpenAPI spec is the source of truth; stubs are generated, not hand-written
2. **Client SDK generation**: The same spec can generate client SDKs for partners
3. **Independent versioning**: The API spec can evolve independently of the implementation

## Key Architectural Patterns

1. **One-time token (OTT) authentication**: Short-lived (30s), single-use tokens bridge the partner server-to-server auth to the browser widget session. Eliminates long-lived client credentials in browser memory.
2. **Cookie-based widget session**: `HttpOnly`, `Secure` cookies prevent XSS token theft in the widget iframe.
3. **Domain whitelist**: `DomainWhitelistService` prevents embedding on unauthorised domains (clickjacking mitigation, PCI DSS Req 6.4.3).
4. **iFrame isolation**: The widget runs in a sandboxed iframe (`allow-scripts allow-forms allow-popups allow-same-origin`); the shim communicates via `postMessage` with origin verification.
5. **Resilience**: Circuit breakers on all external service calls (EcountCore, OAuth token endpoint, wallets APIM, all databases).
6. **Immutable session revocation**: Logout inserts into `revoked_sessions` table rather than mutating a session record, enabling stateless verification.

## Integration Dependencies

| Integration | Protocol | Auth | Notes |
|---|---|---|---|
| EcountCore | SOAP (Apache CXF 4.1.1) + REST | Agent credentials | config: `config/ecount-config.xml`; agent: `secrets.ecount-core.agent` |
| CMS / XContent | REST | — | Widget content / localised strings |
| Azure AD | OAuth2 (MSAL4J 1.21.0) | Client credentials | Service-to-service auth |
| Wallets APIM | REST | OAuth2 (separate wallet OAuth) | Apple/Google Pay provisioning |
| SQL Server (5 DBs) | JDBC (mssql-jdbc 13.x) | Azure Key Vault secrets | |

## PCI DSS Architecture Controls

| PCI Req | Control | Implementation |
|---|---|---|
| Req 2 | Secure defaults | Non-default ports; TLS-only; security headers via APIM |
| Req 3 | PAN protection | PAN retrieved from EcountCore/StrongBox; never stored in primary DB |
| Req 4 | Encrypted transmission | HTTPS enforced; Azure APIM TLS termination; TLS truststore configured |
| Req 6 | Secure development | CVE overrides in POM; CodeQL static analysis; dependency hygiene |
| Req 7 | Least-privilege access | Azure AD service principal; scoped DB users |
| Req 8 | Authentication | OTT (30s TTL), OAuth2 cookies, session revocation table |
| Req 10 | Audit logging | Logback JSON + logstash encoder; structured logs to centralised platform |
| Req 12 | Security policy | CLAUDE.md documents security conventions; `ai-guidelines` repo referenced |
