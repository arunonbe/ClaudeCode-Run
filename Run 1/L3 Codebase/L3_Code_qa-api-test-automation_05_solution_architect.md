# Solution Architect — qa-api-test-automation

## Technical Architecture

```
qa-api-test-automation/
├── collections/             -- Postman collection JSON files (one per service)
├── environments/            -- Postman environment JSON files (QA/STG/PROD per service)
├── scripts/
│   └── generate-encrypted-token.mjs  -- AES-256-GCM token generator (Node.js ESM)
└── .github/
    ├── CODEOWNERS           -- PR review assignments
    ├── copilot-instructions.md
    └── workflows/           -- ~80 GitHub Actions workflow files
        ├── postman-smoke-test.yml          -- reusable: Newman smoke execution
        ├── postman-smoke-test-with-certs.yml -- reusable: Newman + mTLS
        ├── postman-reusable-job.yml        -- reusable: Postman CLI execution
        ├── pynt-security-scan.yml          -- reusable: Pynt DAST
        ├── pynt-security-test-with-certs.yml -- reusable: Pynt + mTLS
        └── {service}-smoke.yml (many)      -- per-service callers
```

## API Surface
This repo invokes APIs; it does not expose any. All outbound calls are to Onbe service endpoints defined in Postman environment files.

## Security Posture

### Authentication Patterns in Tests
Tests authenticate against services using credentials stored in:
1. **GitHub Secrets** — referenced as `${{ secrets.* }}` in workflow files (correct practice)
2. **Postman environment files** — variable values in JSON (risk: may contain real credentials if not templated)

### Encrypted Token Script (`scripts/generate-encrypted-token.mjs`)
This script is cryptographically sound:

```javascript
// AES-256-GCM with 12-byte nonce, 16-byte tag
const nonce = crypto.randomBytes(12);
const cipher = crypto.createCipheriv("aes-256-gcm", key, nonce);
const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
const tag = cipher.getAuthTag(); // 16 bytes
const tokenBytes = Buffer.concat([nonce, ciphertext, tag]);
```

- Uses Node.js built-in `node:crypto` (not a third-party library)
- 32-byte key enforced at line 31: `if (key.length !== 32) { throw new Error(...) }`
- Random nonce per invocation
- Full AEAD integrity via GCM auth tag

### mTLS Support
`postman-smoke-test-with-certs.yml` and `pynt-security-test-with-certs.yml` inject TLS certificates from GitHub Secrets — no certificates committed to version control.

### Secrets in Environment Files
Environment files in `environments/` were not individually read in this analysis. However:
- Files named `*PROD*` and `*.prod*` should be treated as potentially containing production credentials
- PCI DSS requires secrets scanning (`git-secrets`, `trufflehog`) on all commits to this repo

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| ~80 per-service workflow files with potential duplication | `.github/workflows/` | Medium — maintenance burden; pattern is correct (reusable workflows) but individual callers may drift |
| Legacy Wirecard environment files not cleaned up | `environments/p-app01.nam.wirecard.sys.json`, `environments/webservice.wirecard.com.json`, etc. | Medium |
| No secrets scanning workflow | `.github/workflows/` | High — no automated detection of committed credentials |
| PROD environment files in version control | `environments/*PROD*`, `environments/*prod*` | High — should be removed and injected via CI secrets |
| `README.md` references `viktor.potok@onbe.com` as contact — personal email in VCS | `README.md:17` | Low |
| No test result persistence beyond GitHub artefacts | All workflows | Medium |

## Gen-3 Migration Requirements
This repo does not need a Gen-3 migration per se — Postman/Newman is tooling-agnostic. However, as services migrate to Gen-3:
1. Update collection request schemas to match Gen-3 REST API contracts
2. Add OAuth2/OIDC authentication flows to replace legacy auth patterns
3. Consider migrating to OpenAPI-based contract testing (supplementing Postman with Pact or Schemathesis)
4. Implement persistent test reporting (Allure, ReportPortal) instead of ephemeral GitHub artefacts

## Code-Level Risks (file:line references)

| Risk | File | Line | Detail |
|---|---|---|---|
| Potential PROD credentials in committed environment files | `environments/` directory | Multiple files | Not read individually — secrets scan required |
| `generate-encrypted-token.mjs` warns on missing userId and digitalToken but does not fail | `scripts/generate-encrypted-token.mjs` | 26–28 | `console.warn("WARN: both userId and digitalToken are missing/null")` — silent continuation may produce unusable tokens |
| `DECAGON_ENCRYPTION_KEY_BASE64` must be exactly 32 decoded bytes — no padding tolerance | `scripts/generate-encrypted-token.mjs` | 30–32 | Correct enforcement but brittle if key is base64url-encoded vs base64-standard |
| No SRI or version pinning on Pynt tool | Various `pynt-*.yml` workflows | — | Pynt version not pinned in visible workflow content |
