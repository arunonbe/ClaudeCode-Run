# Data Architect Report — nexpay-auth-svc

## 1. Data Architecture Overview

`nexpay-auth-svc` is architecturally notable for what it **does not own**: it maintains no local database, no JPA entities, and no Flyway schema at the time of this inspection. User identity data is stored exclusively in Microsoft Entra External ID. The service is a **stateless API facade** that proxies identity operations to the Graph API.

The `application.yaml` (lines 15-19) explicitly excludes database auto-configuration:
```yaml
autoconfigure:
  exclude:
    - org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration
    - org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration
    - org.springframework.boot.autoconfigure.flyway.FlywayAutoConfiguration
```

However, the `README.md` (lines 21-36) documents a planned module structure that includes `nexpay-auth-data-entity` (JPA entities with `UserIdentity`, `AuthProvider`, `ProviderType`) and `nexpay-auth-data-repository`. These modules are referenced in the README but **not present in the actual file system**, indicating the data persistence layer is planned but not yet implemented. The current codebase represents an early-phase implementation where Entra is the sole identity store.

## 2. Data Model (Entra External ID)

User data stored in Entra External ID, as modeled by `GraphUser.java` (inferred from usage in `EntraGraphClient.java`):

| Entra Field | Usage in Service | Notes |
|---|---|---|
| `id` (object ID) | `UserResponse.externalId`, `UserResponse.userIdentityId` | Primary identity reference |
| `displayName` | `UserResponse.displayName` | Cardholder display name |
| `mail` | `UserResponse.email` (via `resolveEmail()`) | Primary email address |
| `accountEnabled` | `UserResponse.isActive` | Account active/disabled flag |
| `createdDateTime` | `UserResponse.createdAt` | ISO 8601 timestamp |
| `identities[signInType=emailAddress].issuerAssignedId` | `UserResponse.email` | Email sign-in identity |
| `userPrincipalName` | Fallback for email resolution | UPN format |

## 3. Token Cache Data

`EntraGraphTokenProvider.java` maintains an in-memory token cache:

```java
private volatile String cachedToken;        // access token string
private volatile Instant tokenExpiry;       // expiry timestamp
private final ReentrantLock lock;          // thread-safety guard
```

This is **process-local in-memory state** with a 60-second pre-expiry refresh margin (line 26: `TOKEN_REFRESH_MARGIN_SECONDS = 60`). Implications:
- Token is not shared across horizontal scaling instances — each pod independently fetches tokens from Entra
- On pod restart, the first request will incur a token fetch latency (typically < 500ms to Entra)
- If the service is scaled to multiple ACA replicas, each maintains its own cached token — this is acceptable for the `client_credentials` grant which is designed for service-to-service use
- **No token persistence**: tokens are not written to any store, minimizing credential leakage risk

The `ReentrantLock` with double-checked locking (lines 43-58 in `EntraGraphTokenProvider.java`) ensures thread-safe token refresh under concurrent virtual thread load (Project Loom is enabled in `application.yaml` line 9-10).

## 4. OData Query Safety

`EntraGraphClient.buildMailFilterUri()` (lines 177-183) constructs an OData `$filter` query against the Entra users endpoint. The implementation:
1. Sanitizes single quotes by doubling them: `email.replace("'", "''"` ) — OData injection prevention (line 179)
2. URL-encodes the sanitized value: `URLEncoder.encode(sanitizedEmail, StandardCharsets.UTF_8)` (line 180)
3. Constructs the URI with `URI.create()` to bypass Spring's template parameter encoding (line 181)

This is a correct implementation of OData filter query construction. The comment explains why Spring's URI template variables cannot be used (they would break OData syntax), and the manual sanitization adequately prevents OData injection attacks.

## 5. Secret and Credential Data

`application.yaml` (lines 29-30) shows:
```yaml
client-id: ${ENTRA_CLIENT_ID:your-client-id}
client-secret: ${ENTRA_CLIENT_SECRET:your-client-secret}
```

These placeholders indicate that `client_id` and `client_secret` for the Graph API service principal are injected via environment variables. In Azure Container Apps, these would be sourced from Azure Key Vault via the Key Vault reference mechanism (`app-config/qa/appsettings.json` pattern used in other NexPay services). No secrets are hard-coded in the repository.

**Critical observation**: The `client_secret` approach is a shared-secret authentication pattern. Azure recommends migrating to Managed Identity or certificate-based authentication for production service principals to eliminate the `client_secret` rotation burden and eliminate the risk of secret leakage. Since this service runs in ACA, it could use a system-assigned or user-assigned managed identity to authenticate to Graph API without a `client_secret` at all.

## 6. Planned vs. Implemented Data Architecture

| Layer | README Documented | Actual Implementation |
|---|---|---|
| Entra External ID (Graph API) | Yes | Yes — fully implemented |
| Local PostgreSQL (`UserIdentity` entity) | Yes | Not implemented |
| Flyway migrations (`V1__initial_schema.sql`) | Yes | Not implemented |
| Spring Data JPA repositories | Yes | Not implemented |

The planned local database would likely serve as a **local mirror** of Entra identities, allowing faster queries without Graph API round-trips and supporting local caching or enrichment of identity data. This is a common pattern for CIAM-integrated services. The current stateless architecture is simpler but means every user lookup goes to Entra.

## 7. Data Risks

1. **No local persistence**: If Entra External ID is unavailable, all identity operations fail. The service has no fallback.
2. **`client_secret` in environment variable**: If an ACA environment variable is leaked (e.g., through a misconfigured `env` actuator endpoint), the Graph API service principal is compromised.
3. **`management.endpoint.health.show-details: always`** in local profile (line 97-98 of `application.yaml`): In production, this should be `when_authorized` (already set for non-local profiles at line 49).
4. **Email in log statements**: `AuthService.java` line 33 logs `username` at INFO level. If email addresses are considered PII (GDPR), logging them at INFO may violate the principle of data minimization in log storage.
