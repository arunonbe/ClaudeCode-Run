# oneplatform-react_WAPP — Enterprise Architect View

## Platform Generation

**Generation**: Gen-2 / Active Evolution toward Gen-3

`oneplatform-react_WAPP` is Onbe's current production cardholder-facing SPA. It is a mature, actively maintained React 18 application deployed at `https://login.mypaymentvault.com/`. It is not a legacy system awaiting retirement; it is the primary digital face of Onbe's disbursement business. Gen-3 migration will involve modernising the build system (Webpack → Vite or Next.js), improving observability, and aligning with evolving platform standards — not replacing the application's core business functionality.

## Business Domain

**Domain**: Cardholder Experience — Disbursement Receipt and Fund Management

This SPA is the exclusive digital channel through which Onbe's B2C recipients access and manage their disbursements. It spans the full disbursement lifecycle:

- Card activation and PIN management
- Balance and transaction viewing
- Fund transfer across 10 payout rails (prepaid, ACH, P2D, PayPal, Venmo, IEFT/FX, check, wallets, RIA, WU)
- MFA / OTP for high-value operations
- Affiliate/program-specific UX customisation

No other Onbe system provides this cardholder-facing capability — this application is unique and load-bearing. Outages directly impact cardholder fund access.

## Role in the Platform

### Position in the C4 Architecture
```
Internet (Browser / Mobile WebView)
    │ HTTPS
    ▼
Azure Front Door / CDN
    │
    ▼
oneplatform-react_WAPP (SPA — served as static assets)
    │ HTTPS + JWT Bearer
    ▼
oneplatform-rest_API (BFF — backend for frontend)
    │
    ├── account-management-api_API
    ├── order_SVC
    ├── payment-service_SVC
    ├── notification-framework_SVC
    └── (other backend services)
```

The SPA is a pure client-side application — all business logic executes in the REST API. The SPA orchestrates user flows, manages local state, and mediates between user intent and API calls.

### Key Architectural Roles
1. **Authentication gateway**: Handles username/password, Virtual Express token, SSO, and claim-code login flows. JWT management (token storage, refresh, expiry handling) is centrally implemented in `networkCall.js` and `callApi.js`.
2. **Multi-rail orchestration UI**: The `ChoicePage` and `ClaimableChoice` components present Onbe's multi-rail payout choice to cardholders — a direct UI representation of Onbe's core product differentiation.
3. **Affiliate/program customisation engine**: The `GET_AFFILATE_DATA` and `GET_COPY_TAG` API calls load program-specific branding, content, and feature flags at runtime, enabling one SPA to serve hundreds of client programs.
4. **Fraud signal emitter**: BioCatch session ID injection (`cdApi.setCustomerSessionId()`) and `x-client-ip` header forwarding enable the backend to perform GeoIP restriction and behavioural fraud analysis.

## Dependencies

### Upstream (what the SPA depends on)
| Dependency | Type | Criticality |
|---|---|---|
| `oneplatform-rest_API` | REST API (BFF) | Critical — all data and operations |
| `@onbeeast/common-framework` | npm library | Medium — validation utilities |
| BioCatch CDN SDK | External JS | Medium — fraud signal collection |
| Google reCAPTCHA Enterprise | External API | High — bot protection for login |
| Azure CDN / Static Web Apps | Hosting | Critical — SPA distribution |

### Downstream (what depends on this SPA)
No other Onbe systems depend on the SPA. It is a leaf node in the dependency graph.

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| REST BFF | All calls through `oneplatform-rest_API` | Correct pattern — no direct service coupling |
| JWT auth | Bearer token in `Authorization` header | Token stored in `localStorage` (security risk — see solution architect view) |
| Affiliate customisation | Runtime API call to load program config | Enables white-label flexibility |
| Multi-locale | `i18next` with `en_US`, `fr_CA`, `sp_US` | Supports GDPR/Quebec Law 25 French language requirement |
| Mock/local development | `server-mocker.js` JSON server | Good developer experience pattern |
| reCAPTCHA v3 | Google reCAPTCHA Enterprise token in login payload | Protects authentication endpoint from bots |

## Strategic Status

**Status**: Production — Mission Critical

This application requires ongoing investment. Near-term priorities:
1. Address JWT storage in `localStorage` (move to `httpOnly` cookie or in-memory with refresh token rotation).
2. Add source map suppression in production Webpack builds.
3. Add test coverage for untested financial transaction flows (Venmo, WebToWallet, ClaimableChoice, Transaction).
4. Align Webpack-to-Vite migration timeline with `oneplatform-rest_API` Gen-3 roadmap.

## Migration Blockers

| Blocker | Impact | Notes |
|---|---|---|
| JWT in `localStorage` | Security — XSS token theft | Must be resolved before any Gen-3 migration introduces new attack surface |
| `console.log(res)` in `networkCall.js` | Data leakage in production builds | Financial API responses logged to browser console |
| No source map suppression confirmed | Reverse-engineering risk | `webpack.config.prod.js` must set `devtool: false` |
| `REACT_APP_SKIP_RECAPTCHA` / `REACT_APP_CODE` | reCAPTCHA bypass risk | If these values leak into prod build, bot protection is defeated |
| Missing test coverage for 4+ financial flows | Quality / compliance risk | PCI DSS Req 6.2 requires secure SDLC; untested flows are a gap |
| No TypeScript | Type safety gap | Adopting TypeScript in a large existing codebase requires phased migration planning |
