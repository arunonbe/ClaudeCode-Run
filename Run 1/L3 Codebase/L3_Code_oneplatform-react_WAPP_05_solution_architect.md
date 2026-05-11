# oneplatform-react_WAPP — Solution Architect View

## Technical Architecture

`oneplatform-react_WAPP` is a Single Page Application (SPA) built with React 18, Redux Toolkit, React Router v6, and Webpack 5. It uses a monorepo-within-monorepo layout: the root `package.json` orchestrates scripts that delegate to `project/` which contains the actual React application.

### Build Architecture
```
Root package.json (orchestration)
    └── project/ (actual React app)
          ├── webpack.config.common.js   (shared base config)
          ├── webpack.config.dev.js      (dev server — react-scripts)
          ├── webpack.config.qa.js       (QA build → default 'build' script)
          ├── webpack.config.stage.js    (staging build)
          └── webpack.config.prod.js     (production build)
```

Three environments (QA, Stage, Prod) each have separate Webpack configs injecting environment-specific variables via `dotenv-webpack`. The dev server uses `react-scripts` (Create React App), while all non-dev builds use direct Webpack 5.

### Runtime Architecture
```
Browser
  ├── SPA bundle (served from Azure CDN / Static Web Apps)
  │     ├── React 18 root (main.js)
  │     ├── Redux store (auth, dashboard, transaction, transfer slices)
  │     └── React Router (client-side routing)
  │
  ├── External scripts (loaded at runtime)
  │     ├── BioCatch SDK (fraud detection)
  │     └── Google reCAPTCHA Enterprise
  │
  └── localStorage
        ├── authToken (JWT access token)  ← SECURITY RISK
        ├── refreshToken                  ← SECURITY RISK
        └── cardToken                     ← SECURITY RISK
```

## API Surface

The SPA consumes 80+ REST endpoints from `oneplatform-rest_API` (base: `https://external.{env}.onbe.dev/mypaymentvaultapi`). All calls are made via Axios through `networkCall.js` and `callApi.js`. Key groupings:

| Domain | Endpoint Count | PCI Sensitivity |
|---|---|---|
| Authentication / tokens | 11 | High — credentials, session management |
| Registration / card activation | 7 | Critical — card number, CVV, PIN, DOB, SSN |
| Dashboard / account | 12 | High — balance, card status |
| ACH / bank transfer | 7 | High — routing + account numbers (GLBA) |
| International FX transfer | 12 | High — IBAN, BIC, beneficiary data (GDPR) |
| Push-to-debit | 7 | High — debit card number, expiry |
| PayPal / Venmo | 8 | Medium — OAuth tokens |
| Choice / Payment Hub | 7 | Medium — payment method selection |
| Claimable Choice | 8 | Medium — claim codes |
| Orders (cards / checks) | 5 | Medium — mailing address |
| MFA / OTP | 3 | High — authentication factor |
| Generic / disclosures | 7 | Low |

## Security Posture

### Critical Findings

#### 1. JWT Stored in `localStorage`
`networkCall.js` and `callApi.js` store `authToken`, `refreshToken`, and `cardToken` in `localStorage`. This is vulnerable to XSS attacks — any injected script can exfiltrate tokens. For a payments application handling card activation, PIN change, and ACH transfers, this is a critical risk.

**Recommendation**: Migrate to `httpOnly` cookies for `authToken` and `refreshToken`. Use short-lived access tokens (5-15 minutes) with server-side refresh via a `httpOnly` cookie-backed refresh flow.

#### 2. `console.log(res)` in Production Code
`networkCall.js` line 22 logs the full Axios response object: `console.log(res)`. This logs API responses — which include balance data, transaction history, card status, and potentially PAN fragments — to the browser developer console in production. Accessible to any user who opens DevTools or any browser extension with console access.

**Recommendation**: Remove all `console.log` calls or use Terser `drop_console: true` in `webpack.config.prod.js`.

#### 3. reCAPTCHA Bypass via Environment Variables
`REACT_APP_SKIP_RECAPTCHA` and `REACT_APP_CODE` enable a code path that sends an affiliate-specific bypass code instead of a real reCAPTCHA token. If these variables are inadvertently included in a production build, reCAPTCHA protection is effectively disabled for that affiliate.

**Recommendation**: Audit all production Webpack builds to confirm these variables are not set. Consider removing the bypass mechanism entirely and using reCAPTCHA v3 score thresholds for testing.

### Security Controls Present
- HTTPS enforced via Azure Front Door / CDN.
- BioCatch behavioural analytics for fraud detection.
- Google reCAPTCHA v3 Enterprise for bot protection on login.
- JWT Bearer token authentication on all protected endpoints.
- MFA / OTP for high-value operations (PIN change, bank add, international transfer, debit card add).
- `x-client-ip` forwarding for backend GeoIP restriction.

## Technical Debt

| Item | Severity | Detail |
|---|---|---|
| JWT in `localStorage` | Critical | XSS-exploitable token storage |
| `console.log(res)` in networkCall.js | High | Financial data in browser console |
| No source map suppression confirmed in prod | High | Client-side reverse engineering risk |
| Missing test coverage: 4+ financial flows | High | Venmo, WebToWallet, ClaimableChoice, Transaction untested |
| No TypeScript | Medium | Large codebase with no type safety on API contracts |
| `react-google-recaptcha@3.1.0` (v2 widget) vs reCAPTCHA Enterprise v3 | Medium | Version mismatch between frontend widget and backend expected token format |
| `mock-server/json/cardActivation/test.json` (283 KB) | Medium | Large test fixture — must be audited for real PAN/SSN/DOB data |
| Webpack dual-config (CRA dev / Webpack prod) | Low | Different bundler behaviour in dev vs prod; hot module replacement in CRA not aligned with Webpack 5 prod output |
| No Pact consumer contract tests | Low | API contract between SPA and `oneplatform-rest_API` is not formally tested |

## Gen-3 Migration Path

| Phase | Action | Priority |
|---|---|---|
| Immediate | Fix JWT storage (httpOnly cookies) | Critical |
| Immediate | Remove/gate `console.log` calls in prod | Critical |
| Short-term | Audit `mock-server/json/cardActivation/test.json` for real cardholder data | High |
| Short-term | Add TypeScript for new components; enable strict null checks incrementally | High |
| Short-term | Add test coverage for 4 untested financial transaction flows | High |
| Medium-term | Migrate dev build from CRA to Vite (faster HMR, aligned with Webpack 5 prod) | Medium |
| Medium-term | Implement Pact consumer contracts for all `oneplatform-rest_API` endpoints | Medium |
| Long-term | Evaluate Next.js App Router for SSR/ISR if SEO or performance requirements emerge | Low |

## Code-Level Risks

### `project/src/config/networkCall.js` — Token Refresh Race Condition
If multiple concurrent API calls are made when the access token is expired, each call may independently attempt a token refresh, resulting in multiple concurrent `POST /getToken` calls. The server may invalidate the refresh token after the first use, causing subsequent refresh attempts to fail with 401. A refresh token mutex (lock while refresh is in flight, queue other calls) should be implemented in `callApi.js`.

### `project/src/config/urls.js` — Hardcoded QA URL as Default
```javascript
export const BASE_URL = "https://external.qa.onbe.dev/mypaymentvaultapi";
```
This hardcoded URL is overridden by `REACT_APP_API_BASE_URL` at build time. However, if a production build is created without this env var set (e.g., a misconfigured pipeline), the SPA would silently point to the QA environment in production — a serious data routing error.

**Recommendation**: Add a build-time assertion that `REACT_APP_API_BASE_URL` is set for non-dev builds.

### `project/src/Components/` — Missing Test Directories
The following high-risk components lack test coverage directories, confirmed by the existing DevOps analysis:
- `src/test/Components/Venmo/` — absent
- `src/test/Components/WebToWallet/` — absent
- `src/test/Components/ClaimableChoice/` — absent
- `src/test/Components/Transaction/` — absent

Given that these components handle financial transfers and are PCI DSS in-scope (card number handling in Transaction, digital wallet provisioning in WebToWallet), the absence of tests is both a quality risk and a PCI DSS Req 6.2 (secure SDLC) gap.
