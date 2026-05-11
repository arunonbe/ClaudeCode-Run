# Solution Architect Report — nexpay-auth-svc

## 1. Solution Architecture

```
[MPV BFF / Internal Callers]
        │  REST/JSON  (POST /users, GET /users/{id})
        │  Internal APIM only
        ▼
NexpayAuthApplication  (Spring Boot 4.x, Java 25, Virtual Threads)
        │
        ▼
UsersApiDelegateImpl (nexpay-auth-impl)
        │  delegates to
        ▼
AuthService
        │  delegates to
        ▼
EntraGraphClient (RestClient)
        │  OAuth2 Bearer token
        │  (obtained from EntraGraphTokenProvider, cached in-memory)
        ▼
Microsoft Graph API  (https://graph.microsoft.com/v1.0/users)
        │
        ▼
Microsoft Entra External ID CIAM tenant
```

The architecture is a clean three-layer delegation chain: HTTP delegate → service → Graph API client. Spring Boot's virtual thread executor handles request concurrency.

## 2. OAuth2 Security Deep-Dive

### Client Credentials Grant Flow (`EntraGraphTokenProvider`)

```
nexpay-auth-svc → POST /{tenantId}/oauth2/v2.0/token
    client_id={ENTRA_CLIENT_ID}
    client_secret={ENTRA_CLIENT_SECRET}
    grant_type=client_credentials
    scope=https://graph.microsoft.com/.default
    ← access_token (JWT), expires_in
```

The token is cached in a `volatile String` with a `volatile Instant` expiry, protected by `ReentrantLock` with double-checked locking (lines 42-58 in `EntraGraphTokenProvider.java`). This is thread-safe under both platform threads and virtual threads.

**Token lifetime**: Entra `client_credentials` tokens typically expire in 3600 seconds (1 hour). The 60-second pre-expiry refresh margin (line 26) ensures tokens are refreshed proactively before they expire mid-request.

### Security Findings — OAuth2

| Finding | Severity | Analysis |
|---|---|---|
| `client_secret` in environment variable | Medium | Correct pattern for ACA; mitigated by Key Vault injection. Recommended: migrate to Managed Identity |
| No `client_secret` rotation policy visible | Medium | Key Vault rotation should be configured externally; not verifiable from code |
| Graph API token cached in memory | Low | Correct design; no token persistence reduces leakage risk |
| PKCE enforcement not in codebase | Info | PKCE for cardholder OIDC flows is enforced at Entra tenant level, not this service. Verify tenant config |
| HS256 signing for consumer JWTs | Medium | Auth tokens issued by Entra use RS256 by default; if the `authToken` in MPV mock uses HS256, this may indicate a custom token issuer that should be reviewed |

### OData Injection Defense

`EntraGraphClient.buildMailFilterUri()` (lines 177-183) correctly implements:
1. OData single-quote escaping: `"'", "''"` — prevents OData injection via email filter
2. URL encoding via `URLEncoder.encode()` — prevents URL injection
3. `URI.create()` instead of Spring URI template — prevents double-encoding

This is a well-implemented defense.

## 3. Module Architecture

### nexpay-auth-api
Downloads an OpenAPI specification from a remote source (likely the `nexpay-config-svc` or a package registry) and generates Java interfaces and model classes. This API-first approach ensures the service contract is defined independently of the implementation.

### nexpay-auth-boot
Contains:
- `NexpayAuthApplication.java` — Spring Boot entry point
- `HttpConfig.java` — configures the `RestClient` bean used by `EntraGraphClient`
- `OpenApiConfig.java` — Swagger UI configuration
- `ErrorExceptionHandlers.java` — global exception handler mapping service exceptions to HTTP status codes
- `application.yaml` — all application configuration

### nexpay-auth-impl
Contains all business logic:
- `AuthService.java` — service layer (user availability, creation, lookup)
- `UsersApiDelegateImpl.java` — OpenAPI delegate implementation
- `EntraGraphClient.java` — Graph API HTTP client
- `EntraGraphTokenProvider.java` — OAuth2 client_credentials token cache
- `EntraGraphConfigProperties.java` — configuration properties binding
- `ApplicationHealthIndicator.java` — custom health check

## 4. Error Handling Architecture

`UsersApiDelegateImpl` maps service exceptions to HTTP responses:
- `UserAlreadyExistsException` → HTTP 409 Conflict (line 101-103)
- User not found → HTTP 404 Not Found (line 122-124)
- `HttpClientErrorException.NotFound` from Graph API → propagated as Optional.empty() (line 112-113 in `EntraGraphClient.java`)
- `HttpClientErrorException.Conflict` from Graph API → `UserAlreadyExistsException` (line 163-165 in `EntraGraphClient.java`)

The idempotency implementation in `createUser` (lines 87-90) avoids HTTP 409 for duplicate requests by returning the existing user, which is the correct pattern for RESTful POST endpoints that act as upserts.

## 5. Configuration Architecture

```
Environment Variables (ACA secrets / Key Vault refs)
    ENTRA_TENANT_ID, ENTRA_TENANT_SUBDOMAIN
    ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET
    ENTRA_ISSUER_DOMAIN
        │
        ▼
EntraGraphConfigProperties (Spring @ConfigurationProperties)
    tenantId, tenantSubdomain, clientId, clientSecret
    graphBaseUrl, issuerDomain
        │
        ▼
EntraGraphTokenProvider  →  tokenEndpoint = https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token
EntraGraphClient         →  graphBaseUrl = https://graph.microsoft.com/v1.0
```

## 6. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Entra External ID unavailability | High | Consider circuit breaker around Graph API calls; alert on 5xx from Graph |
| `client_secret` leakage via actuator `env` endpoint | Medium | `env` actuator only enabled in local profile (line 93-94); masked in production |
| Email PII logged at INFO | Low | Review log retention policy; consider masking email in log statements |
| Java 25 early-access JDK | Medium | Monitor BellSoft Liberica 25 stability; plan rollback procedure |
| SNAPSHOT parent POM (`nexpay-parent:0.2.8-SNAPSHOT`) | High | Stabilize parent POM to a release version before production |
| `UserAlreadyExistsException` log at WARN exposes email | Low | `AuthService.java` line 57: logs email in warning. Mask or remove. |
