# 05 Solution Architect — embedded-payments-api

## Key Services and Components

### `com.onbe.embedded.payments.service` package (from CLAUDE.md)

| Service | Purpose |
|---|---|
| `WidgetService` | Core widget embedding and session logic — loads SPA, validates OTT, establishes session cookies |
| `ClaimablePaymentsService` | Manages the claimable payment lifecycle: listing disbursements, querying modalities, executing disbursement via EcountCore |
| `ECountCoreService` | Adapter to EcountCore — wraps SOAP/REST calls; handles circuit-breaker protection |
| `DomainWhitelistService` | Validates that the `Origin` or `Referer` header of widget requests matches the client's registered domains |
| `ShimService` | OTT validation, domain check, SPA HTML response construction, secure cookie issuance |
| `ClientService` | Client/merchant CRUD and lookup |
| `CacheService` | Ehcache cache management; caches client configurations and frequently-accessed data |
| `CleanupTask` | Scheduled Spring `@Scheduled` task — deletes expired `one_time_tokens` and `revoked_sessions` records |

### `com.onbe.embedded.payments.client` package

| Client | Purpose |
|---|---|
| `CMSClient` | REST client for XContent CMS (localised strings, T&C documents) |
| `ECountCoreRestClient` | REST client for EcountCore REST API |
| `OAuthTokenClient` | MSAL4J-based OAuth2 token acquisition for Azure AD service auth |

### `com.onbe.embedded.payments.db` package

Five JPA EntityManager contexts, one per datasource (`primary`, `jobservice`, `ecountcore`, `cbase`, `cbaseapp`). Each has its own `@Repository` interfaces backed by Hibernate with SQL Server dialect.

### `com.onbe.embedded.payments.config` package

Spring `@Configuration` classes for datasource wiring, security (Spring Security OAuth2), Ehcache, Resilience4j, truststore, and CORS.

### `com.onbe.embedded.payments.context` package

Request/security context utilities — likely holds the current session's member ID, claim code, and authentication context across the request lifecycle.

### `com.onbe.embedded.payments.exception` package

Exception types and a `@ControllerAdvice` global exception handler producing RFC 7807 `ErrorResponse` (`openapi.yaml` lines 651–677).

### `com.onbe.embedded.payments.models` package

DTOs and domain models mapped to the OpenAPI schemas — MapStruct mappers convert between JPA entities and API DTOs.

## OpenAPI Surface — Complete Endpoint Inventory

| Method | Path | Operation | Auth | Tags |
|---|---|---|---|---|
| POST | `/embedded/client/authenticate` | `authenticate` | Client credentials | Client |
| POST | `/embedded/shim/load-spa` | `loadSpa` | OTT (form POST) | Shim |
| GET | `/embedded/assets/{fileName}` | `getStaticAsset` | None (public) | Shim |
| POST | `/embedded/widget/list-disbursements` | `listDisbursements` | Session cookie | Widget |
| POST | `/embedded/widget/accept-terms` | `acceptTerms` | Session cookie | Widget |
| POST | `/embedded/widget/disburse` | `executeDisbursement` | Session cookie | Widget |
| POST | `/embedded/widget/disbursement-info` | `getDisbursementInfo` | Session cookie | Widget |
| POST | `/embedded/widget/masked-disbursement-info` | `getMaskedDisbursementInfo` | Session cookie | Widget |
| POST | `/embedded/widget/modalities` | `getModalities` | Session cookie | Widget |
| POST | `/embedded/widget/logout` | `logout` | Session cookie | Widget |
| POST | `/embedded/widget/transactions` | `getTransactions` | Session cookie | Widget |
| POST | `/embedded/widget/contact-info` | `getInfo` | Session cookie | Widget |
| POST | `/embedded/widget/enabled-wallets` | `getEnabledWallets` | Session cookie | Widget |
| POST | `/embedded/widget/provision-wallet` | `provisionWallet` | Session cookie | Widget |
| GET | `/hc` | Health check | None | Actuator |
| GET | `/info` | App info | None | Actuator |

## Security Vulnerabilities and Technical Debt

### 1. CSP `allowed-ancestors: "*"` (P1 — High)
`application.yaml` line 122: `allowed-ancestors: "*"` means the widget SPA can be embedded in **any domain**. The `DomainWhitelistService` provides per-client domain validation at the API level, but the Content-Security-Policy `frame-ancestors` directive is set to `*`. This allows any site to attempt to iframe the widget. The CSP directive should be set to the specific client domains or restricted to the API's own origin.

### 2. CORS `shim-allowed-origins: "*"` (P1 — High)
`application.yaml` line 123: The shim endpoint accepts CORS requests from any origin. The shim's purpose is to load the SPA via form POST, but an overly permissive CORS policy could allow CSRF-adjacent attacks. Should be restricted to known partner domains.

### 3. `client_secret` Storage Verification Needed (P1 — High)
`dbo.clients.client_secret VARCHAR(255)` — the column stores the partner's client secret. The initial migration (`V001.001`) does not explicitly show hashing. If stored in plaintext, this is a PCI DSS Req 8 violation. Must be verified to use bcrypt/PBKDF2 hashing.

### 4. OTT Hashing Algorithm Verification (P2 — Medium)
V001.005 adds a hash column to `one_time_tokens` but the migration SQL was not fully analysed. The hashing algorithm must be SHA-256 or better (not MD5/SHA-1) per PCI DSS Req 8.

### 5. `health` Endpoint `show-details: always` (P3 — Medium)
If `/hc` is publicly accessible (e.g., via Azure APIM with no auth on the health path), `show-details: always` exposes database connectivity status, datasource names, and potentially host information to unauthenticated callers. Should be `when-authorized` for public exposure.

### 6. `truststore_qa.jks` Committed to Source (P2 — Medium)
A TLS truststore is bundled in `src/main/resources/keystore/`. If this contains only CA certificates for QA, the risk is low. If it contains any private keys or client certificates, it is a critical security issue. Must be verified.

### 7. `0.0.1-SNAPSHOT` Version (P3 — Medium)
Version number has never been incremented from the project template. This makes release traceability difficult.

### 8. Wallet IDI SDK `passthruFromIdiSdk` (P2 — Medium)
The `provisionWallet` endpoint accepts `passthruFromIdiSdk` — an opaque string from the IDI (Issuer Digital Integration) SDK in the browser. This data is passed through to the wallet provisioning APIM. If not validated/sanitised, it could be a vector for injection or replay attacks. Input validation must be confirmed.

### 9. JWE `app-secret` (P1 — High)
`application.yaml` line 88: `embed.jwe.app-secret: ${secrets.jwe.app-secret}` — a JWE (JSON Web Encryption) secret is used. This secret's length, algorithm, and rotation policy must be verified to meet NIST SP 800-57 requirements (minimum 128-bit for AES-based JWE).

## Remediation Priority Summary

| Issue | Priority | Action |
|---|---|---|
| CSP `frame-ancestors: *` | P1 — High | Restrict to registered client domains via DomainWhitelistService output |
| CORS `shim-allowed-origins: *` | P1 — High | Restrict to known partner domains |
| `client_secret` storage | P1 — High | Verify bcrypt/PBKDF2 hashing is applied |
| JWE app-secret strength | P1 — High | Verify >= 256-bit key; document rotation policy |
| OTT hash algorithm | P2 — Medium | Verify SHA-256 or better |
| `truststore_qa.jks` in source | P2 — Medium | Audit for private key content; move to Key Vault |
| Health endpoint details | P3 — Medium | Set `when-authorized` for production |
| Version management | P3 — Medium | Implement semantic versioning and release pipeline |
| `passthruFromIdiSdk` validation | P2 — Medium | Add input validation/sanitisation |
