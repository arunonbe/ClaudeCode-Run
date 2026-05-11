# Data Architect — qa-api-test-automation

## Data Stores

This repository contains no persistent application data stores. Data artefacts are:

| Artefact Type | Storage | Description |
|---|---|---|
| Postman Collections | Version-controlled JSON files in `collections/` | API request definitions, test assertions, pre-request scripts |
| Postman Environments | Version-controlled JSON files in `environments/` | Environment-specific variables (URLs, credentials, tokens) |
| Test execution results | GitHub Actions artefacts (ephemeral) | Per-run test reports, not persisted beyond GitHub retention |

## Schema / Structure

### Postman Environment Variables (sensitive field analysis)

Postman environment files follow the standard Postman schema:
```json
{
  "values": [
    { "key": "baseUrl", "value": "https://...", "enabled": true },
    { "key": "token", "value": "...", "enabled": true },
    ...
  ]
}
```

Variables commonly present in environment files across Onbe's pattern include:
- `baseUrl` / `host` — API endpoint base URL
- `token` / `access_token` / `bearer_token` — authentication tokens
- `apiKey` — API key values
- `client_id` / `client_secret` — OAuth client credentials

## Sensitive Data

| Data Class | Location | Risk |
|---|---|---|
| API authentication tokens | Postman environment files (if populated with real values) | Critical if real tokens committed |
| OAuth client credentials | Postman environment files | High if real values committed |
| Test card numbers / account numbers | Postman collection request bodies | CHD if real PANs used in test data |
| Encryption key (DECAGON) | `scripts/generate-encrypted-token.mjs` reads from `DECAGON_ENCRYPTION_KEY_BASE64` env var | Key managed via env var / GitHub Secrets — correct pattern |
| Wirecard/legacy endpoint credentials | `environments/webservice.wirecard.com.json`, `environments/p-app01.nam.wirecard.sys.json` | May contain legacy system credentials |

Note: Actual values in environment files were not read as part of this analysis. A secrets-scanning pass (e.g., `git-secrets`, `trufflehog`) should be run against the full commit history.

## Encryption

| Usage | Algorithm | Implementation |
|---|---|---|
| Decagon API token generation | AES-256-GCM | `scripts/generate-encrypted-token.mjs` — 12-byte random nonce, 16-byte auth tag, base64 output |
| Environment variable storage in CI | GitHub Secrets | `AZURE_VAULT_URL`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` referenced in workflows |
| mTLS certificate handling | TLS (infrastructure) | Certificate secrets injected via GitHub Secrets |

The AES-256-GCM implementation in `generate-encrypted-token.mjs` is cryptographically correct:
- 32-byte key (enforced with explicit length check)
- 12-byte random nonce (`crypto.randomBytes(12)`)
- 16-byte authentication tag
- Output: base64(nonce + ciphertext + tag)

## Data Flow

```
GitHub Actions Workflow trigger
  --> Postman collection + environment files checked out
      --> Newman CLI (or Postman CLI) executes collection
          --> HTTP requests sent to target API (QA/STG/PROD)
          --> Responses validated against assertions in collection
  --> Test results uploaded as GitHub Actions artefact

For Decagon tests:
  GitHub Secrets (DECAGON_ENCRYPTION_KEY_BASE64)
    --> generate-encrypted-token.mjs
        --> AES-256-GCM encrypted token
            --> Used as Bearer token in Postman pre-request script / env var
```

## Data Quality / Retention

| Concern | Detail |
|---|---|
| Environment file values may be stale | Real-valued environments can have expired tokens or rotated credentials — test failures indicate stale credentials |
| No test data management strategy visible | Collections use hardcoded or environment-variable test data; no test data generation framework |
| Historical environments for decommissioned systems | Wirecard-named environments suggest legacy test data that may need cleanup |
| GitHub Actions artefact retention | Default 90 days; test reports not persistently stored |

## Compliance Gaps

| Gap | Standard | Impact |
|---|---|---|
| Postman environment files may contain plaintext credentials | PCI DSS Req 8.3 | All environment files should be audited for committed secrets |
| PROD environment files in version control | PCI DSS Req 6 | Production credentials must not be stored in version-controlled files |
| No documented test data classification | PCI DSS Req 3 | Test collections may use real account/card data — must use synthetic/masked data |
| Legacy environment files (Wirecard) not cleaned up | Operational | Decommissioned system references create confusion and potential credential exposure |
