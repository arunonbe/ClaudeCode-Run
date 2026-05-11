# Data Architecture — nexpay-recipientweb-bff

## Data Stores
| Store | Technology | Purpose |
|-------|-----------|---------|
| Redis | Spring Data Redis / Lettuce | Affiliate cache lookup by `customUrl` |
| Azure App Configuration | Azure SDK | Externalised configuration |
| Azure Key Vault | Via App Config KV provider | Secrets (jwt.secret-token, service URLs) |

This is a stateless BFF — it has no primary relational database. All persistent state lives in downstream services.

## Data Managed by This Service
- **JWE Card Token** (in-flight, not stored): encrypted payload carrying `memberId`, `affiliateId`, `claimCode`, optionally `cardNumber`, `userName`, `password`.
- **Affiliate records** (read-only from Redis): affiliate ID, custom URL, program configuration.
- **Country/State list** (bundled static data in `nexpay-recipientweb-country-state-list` sub-module): `CountryDto`, `StateDto` — read from classpath JSON resource.

## Sensitive Data
- JWE token payload contains: `memberId` (UUID), `affiliateId` (integer), `claimCode` (string), `cardNumber` (optional), `userName` (optional), `password` (optional credential).
- `password` is encrypted inside the JWE — key strength and rotation are critical.
- No raw PAN or SAD fields transit through this service's code paths.
- Recipient name, email, phone, address are passed through from claim-code-svc to UI — PII in transit.

## Encryption
- JWE algorithm: `JWEAlgorithm.DIR` + `EncryptionMethod.A256GCM` (256-bit symmetric, direct key encryption, AES-GCM mode).
- Key source: `jwt.secret-token` property — must be exactly 32 UTF-8 bytes.
- Key injection: Spring `@Value("${jwt.secret-token}")` — sourced from Azure Key Vault via App Config at runtime.
- Base64Helper: wraps Jackson serialization + `java.util.Base64.getEncoder().encodeToString()` — encoding only, not encryption.

## Data Flow (Redis)
- `AffiliateServiceImpl` reads from Redis cache using `customUrl` as the key.
- Redis connection: `localhost:6379` by default; overridden per profile.
- `nexpay-recipientweb-boot/redis/affiliates.json` + `seed.sh` — development Redis seed data.
- Lettuce connection pool: max-active 10, max-idle/min-idle 4.

## Data Quality / Retention
- BFF is stateless — no data retention applicable.
- Country/state list is bundled static JSON; updates require code deployment.
- Redis cache TTL for affiliate data not directly observable in this repo — governed by the Azure Function that updates it.

## Compliance Gaps
- `password` encrypted in JWE registration token — if the symmetric key is reused across environments or not rotated, cross-environment token forgery is possible.
- Base64-encoded response payloads are not signed or integrity-protected — a MITM could decode and read response content (mitigated by HTTPS at transport layer).
- No audit logging of who called which claim code flow — actor identity relies on OTEL baggage (`AuditFilter`) which is extracted from `X-Actor-Id` header or JWT subject — caller-supplied, not verified by this BFF.
- `jwt.secret-token` is a symmetric key shared with any service decrypting the token — key rotation requires coordinated deployment.
