# 02 Data Architect — embedded-payments-api

## Multi-Datasource Architecture

The service connects to **5 SQL Server databases** via separate Spring DataSource configurations (`application.yaml` lines 17–38):

| DataSource Key | Spring Bean | Database | Purpose |
|---|---|---|---|
| `primary` | Primary DataSource | `${app.db.primary.url}` | Embedded Payments own tables (themes, clients, OTTs, sessions) |
| `jobservice` | Jobservice DataSource | `${app.db.jobservice.url}` | Job service read/write |
| `ecountcore` | EcountCore DataSource | `${app.db.ecountcore.url}` | EcountCore DB read access (members, cards, transactions) |
| `cbase` | CBASE DataSource | `${app.db.cbase.url}` | CBASE application database |
| `cbaseapp` | CBASEAPP DataSource | (see CLAUDE.md) | CBASE application extended data |

All use `com.microsoft.sqlserver.jdbc.SQLServerDriver`. Credentials come from Azure App Configuration secrets (`secrets.db.*.username/password`).

## Primary Database Schema (Flyway-Managed)

### `dbo.themes`
| Column | Type | Purpose |
|---|---|---|
| `id` | BIGINT IDENTITY PK | Theme ID |
| `primary_color` | VARCHAR(10) | Widget primary colour |
| `secondary_color` | VARCHAR(10) | Widget secondary colour |
| `display_name` | VARCHAR(255) | Client display name |
| `display_logo` | VARBINARY(MAX) | Client logo binary |
| `terms_and_conditions` | NVARCHAR(MAX) | T&C text |
| `created_at` | DATETIME2 | Creation timestamp |

### `dbo.clients`
| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT IDENTITY PK | — |
| `client_id` | VARCHAR(50) UNIQUE | Partner's client ID |
| `program_id` | VARCHAR(50) | Onbe program ID |
| `access_level` | VARCHAR(20) | Access tier |
| `domains` | NVARCHAR(MAX) | Allowed embedding domains (JSON array) |
| `theme_id` | BIGINT FK → `themes.id` | Client branding |
| `client_secret` | VARCHAR(255) | Hashed client secret (PCI Req 8 — must not be stored in plaintext) |
| `created_at` | DATETIME2 | — |

**Note**: `client_secret` storage requires verification — if stored as a bcrypt/PBKDF2 hash, this is acceptable. If plaintext, it is a PCI Req 8.6.3 violation.

### `dbo.one_time_tokens`
| Column | Type | Purpose |
|---|---|---|
| `token` | UNIQUEIDENTIFIER PK | The OTT value (hashed as of V001.005) |
| `program_id` | VARCHAR(50) | Associated program |
| `expires_at` | DATETIME2 | Expiry — TTL is 30 seconds (`application.yaml` line 119) |
| `created_at` | DATETIME2 | — |
| `dda` | (added V001.003) | DDA (direct deposit account) reference |
| `partner_user_id` | (added V001.004) | Partner's user identifier |
| `member_id` | (added V001.006) | Onbe member identifier |

**PCI Note**: Tokens are hashed as of V001.005. The hashing migration must be verified to use a strong algorithm (SHA-256 or better, not MD5/SHA-1).

### `dbo.revoked_sessions`
| Column | Type | Purpose |
|---|---|---|
| `token` | (implied) | Revoked session/OAuth token |
| `expires_at` | DATETIME2 (added V001.008) | Expiry for cleanup by `CleanupTask` |

## Sensitive Data Flows

### PAN / Card Details Flow (PCI Scope)
The `getDisbursementInfo` endpoint (`POST /embedded/widget/disbursement-info`) returns:
```json
{
  "cardNumber": "4111111100000000",  // FULL PAN
  "cvCode": "123",                   // CVV/CVC
  "expiryMonth": "12",
  "expiryYear": "26"
}
```
(`openapi.yaml` lines 483–494, schema `DisbursementInfoResponse`)

This means the API **transmits full PAN and CVV over HTTPS** to the widget SPA. Key security requirements:
- TLS 1.2+ must be enforced (Azure APIM handles this)
- The response must never be cached (no `Cache-Control: public` or localStorage)
- The widget must not log or store the PAN/CVV
- PCI DSS Req 4.2.1 applies to this transmission

The backend retrieves these values from EcountCore via the SOAP/REST integration, which in turn decrypts them from StrongBox.

### OAuth Token / Session Flow
1. Partner server calls `POST /embedded/client/authenticate` with `clientId`, `clientSecret`, `partnerUserId`, `programId`
2. API validates client, creates a `one_time_token` record in the primary DB (30-second TTL)
3. Returns `accessToken` (the OTT value)
4. Partner passes OTT to the widget via `shim.js`
5. Widget submits OTT to `POST /embedded/shim/load-spa` (form POST)
6. API validates OTT, issues two HttpOnly secure cookies: `OAuth-Token` and `X-Onbe-Session-Token`
7. All subsequent widget API calls use these cookies for authentication
8. `POST /embedded/widget/logout` revokes the token and inserts into `revoked_sessions`

### Contact Info / PII Flow
`POST /embedded/widget/contact-info` returns full cardholder PII: name, email, phone, address, city, state, zip, country. This is GDPR/CCPA-sensitive data and must only be displayed to the authenticated cardholder.

## Resilience Configuration

Circuit breakers and retries (Resilience4j, `application.yaml` lines 135–213):

| Circuit Breaker | Failure Rate Threshold | Window | Open Duration |
|---|---|---|---|
| `oauthToken` | 50% | 10 calls | 30s |
| `walletOAuthToken` | 50% | 10 calls | 30s |
| `walletsApim` | 50% | 10 calls | 30s |
| `ecountCore` | 50% | 10 calls | 30s |
| `jobServiceDb` | 70% | 10 calls | 60s |
| `cbaseappDb` | 70% | 10 calls | 60s |
| `ecountCoreDb` | 70% | 10 calls | 60s |

All have retry: 3 attempts, 300–500ms wait, exponential backoff (multiplier 2).

## Configuration Sources

Runtime configuration comes from Azure App Configuration under prefix patterns:
- `embedded-payments-api/app.*` — non-sensitive configuration (URLs, feature flags)
- `embedded-payments-api/secrets.*` — sensitive values (DB passwords, OAuth secrets, JWE secret)

Local development uses `local-secrets.properties` (gitignored) with a `.example` template.
