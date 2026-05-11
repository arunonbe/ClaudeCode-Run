# Data Architect View — wirecard_issuing-s2s-token-service_LIB

## Data Models

**OAuth 2.0 domain** (`ext/spring/`):
- `IssClientDetails` — OAuth 2.0 client registration (client ID, client secret hash, scopes, grant types, brand claims)
- `IssUserDetails` — technical user (service account) authentication details
- `IssOAuth2AccessToken` — custom JWT access token with brand claim extension
- `IssOAuth2Request` — custom OAuth 2.0 request carrying brand context
- `IssOAuth2RequestFactory` — request factory that injects brand context into OAuth 2.0 requests

**Key management domain** (`keys/`):
- `AbstractSigningKeyRecord` — base class for signing key records
- `ActiveSigningKeyRecord` — currently active JWT signing key (RSA or EC key material)
- `InactiveSigningKeyRecord` — retired/rotated signing key retained for token validation
- `InMemorySigningKeyRepository` (builder pattern) — in-memory repository of all signing keys
- `KeysConfiguration` — Spring configuration loading signing keys from application configuration
- `HashingKeyIdGenerator` — generates key IDs (JWK `kid` parameter) via hashing of public key material
- `KeyIdAwareJwtAccessTokenConverter` — converts between JWT strings and OAuth 2.0 token objects, aware of key ID for multi-key selection
- `KeyIdAwareSigner` / `KeyIdAwareSignerDecorator` — JWT signing with key ID embedding

## Sensitive Data Handled

| Data Category | Presence | Protection Status |
|---|---|---|
| RSA/EC private keys | In `ActiveSigningKeyRecord` | In-memory only; must be loaded from secure storage (key store or HSM) |
| Client secrets (OAuth 2.0) | In `IssClientDetails` | Should be hashed (BCrypt or similar) in Oracle database |
| JWT access tokens | Issued and validated | Short-lived; RSA/EC signed; not stored (stateless) |
| Service account credentials | Via `IssUserDetails` | Technical user passwords; database-managed |
| Brand context in tokens | JWT claims | Non-sensitive routing context |
| No cardholder PAN/PII | Not present | Correct; S2S auth service handles no cardholder data |

**Critical finding**: The RSA/EC private signing key(s) are loaded into memory from application configuration. If private key material is stored in plaintext configuration files (application.yml or properties files), this is a PCI DSS Requirement 3.6 violation (cryptographic key protection). Keys must be stored in a hardware security module (HSM) or at minimum in an encrypted key store with access controls.

The BouncyCastle provider (`bcprov-jdk15on`, `bcpkix-jdk15on`) is used for cryptographic operations. BouncyCastle version 1.56 (substituted via dependency substitution in `build.gradle`) must be verified for any known CVEs.

## Encryption and Protection Status

- **JWT signing**: RSA or EC asymmetric signing via BouncyCastle; signature algorithm configurable per `KeysConfiguration`
- **Horus crypto**: `com.wirecard.horus:horus-crypto:8.35.0.RC3` — Wirecard proprietary cryptography library; algorithm details unknown without source access
- **Database connection**: Oracle via DBCP2 connection pool; TLS depends on Oracle JDBC driver configuration (`ojdbc8:12.2.0.1.0`)
- **Transport**: Spring Boot `starter-web` over HTTPS (TLS enforced at load balancer or application server level)
- **Client secrets in Oracle**: Should be hashed (not stored plaintext); implementation details in `IssClientDetailsService` (compiled `.class` files available but source not observed)
- **Key rotation**: In-memory key repository supports multiple key versions; ensures tokens signed with retired keys remain valid during rotation window

## Database Schemas

**Oracle database** (confirmed by `validationQuery: select 1 from dual`):

Tables (inferred from Spring Security OAuth 2.0 standard schema + custom extensions):

| Table | Description |
|---|---|
| `oauth_client_details` (or custom) | Client registrations (IssClientDetails) |
| `oauth_access_token` | Token store (if using JDBC token store) |
| `users` / `authorities` | Technical user accounts (IssUserDetails) |
| Custom brand/scope tables | Brand-scoped access control |

Spring Security OAuth 2.0 uses DBCP2 connection pool with Oracle JDBC driver. Auto-commit is disabled (`defaultAutoCommit: false`), suggesting transactional token operations.

## Data Flows

```
Gen-2 Microservice (client)
  → POST /oauth/token (client_credentials grant)
    → IssWebServerSecurityConfiguration (authentication filter)
      → IssClientDetailsService (Oracle DB — client lookup)
      → IssAuthorizationServerConfiguration (token issuance)
        → KeyIdAwareJwtAccessTokenConverter (JWT signing with RSA/EC)
          → BouncyCastle / Horus crypto
      → JWT access token (HTTP response)

Gen-2 Microservice (resource)
  → Bearer JWT in Authorization header
    → JWT signature validation (public key lookup by kid)
      → In-memory signing key repository
        → Token accepted/rejected
```

Monitoring:
```
Health check (Actuator)
  → /actuator/health
    → issuing-boot-actuator-utils health contributor
```

## Retention Concerns

- JWT access tokens are stateless (not stored in database unless JDBC token store is enabled); no retention concern for token content
- Oracle client credentials database: retained as long as the service is active; must have a deprovisioning process for retired service accounts
- Signing key material: private keys must be destroyed per PCI DSS Requirement 3.7 when retired; the `InactiveSigningKeyRecord` retains public key material only (private key should be purged on deactivation)

## PCI DSS Data Storage Compliance

- **PCI DSS Requirement 3.6**: Cryptographic signing keys must be stored securely. If private key material is in plaintext configuration files, this is a compliance violation. Keys should be in an HSM or encrypted key store with restricted access.
- **PCI DSS Requirement 8.3**: Service accounts (OAuth 2.0 clients) must use strong authentication. Client secrets must be complex and regularly rotated.
- **PCI DSS Requirement 8.6.2**: Application/service accounts must not be used for interactive user sessions.
- **No PAN/SAD**: The S2S token service does not store or process cardholder data — it is not a CDE component but is a security control component that protects CDE access.
