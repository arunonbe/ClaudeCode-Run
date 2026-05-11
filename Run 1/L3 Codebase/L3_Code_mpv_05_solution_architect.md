# Solution Architect Report — mpv (My Payment Vault)

## 1. Solution Architecture (Inferred)

Based on the available mock data and the broader NexPay repository context, the MPV solution architecture is inferred as follows:

```
Cardholder Browser / Mobile
        │  HTTPS
        ▼
Azure Front Door (CDN + WAF)
        │
        ▼
MPV SPA (React/Angular — static assets on Azure CDN or ACA)
        │  REST/JSON with JWT Bearer tokens
        ▼
nexpay-recipientweb-bff (Backend For Frontend — API gateway for MPV)
        │
        ├── /auth/** → nexpay-auth-svc (Entra External ID)
        ├── /claims/** → nexpay-claim-code-svc
        ├── /cards/** → nexpay-cardprocessor-svc
        ├── /orders/** → nexpay-order-orchestrator
        ├── /profile/** → nexpay-recipient-profile-svc
        └── /messages/** → message-center_SVC (Gen-2 XML-RPC bridge)
```

The BFF pattern insulates the front-end from backend service topology changes. The BFF is responsible for:
- Token validation (verifying JWTs from `nexpay-auth-svc`)
- Request aggregation (combining multiple microservice calls into a single front-end API response)
- Protocol translation (REST/JSON from front-end ↔ XML-RPC to `message-center_SVC`)

## 2. Authentication and Session Management

The login flow produces three tokens (`cardToken`, `authToken`, `refreshToken`). The solution architecture for token handling:

| Token | Storage (best practice) | Lifetime | Use |
|---|---|---|---|
| `authToken` (JWT) | `sessionStorage` or memory | ~10 min | API Bearer token |
| `refreshToken` (JWT) | HttpOnly secure cookie | ~60 min | Silent token refresh |
| `cardToken` (JWE) | Memory only | Session-scoped | Card operation authentication |

The `refreshToken` must not be stored in `localStorage` (XSS accessible). The recommended pattern is HttpOnly cookie with `SameSite=Strict` or `SameSite=Lax`. Storing the `authToken` in `sessionStorage` is acceptable (tab-scoped, survives refresh within tab) but still accessible to JavaScript, making XSS mitigation critical.

## 3. Multi-Rail Choice Architecture

The choice page flow is central to the Claimable Choice business model. The solution pattern:

1. **Claim code entry** → POST to `nexpay-claim-code-svc` → validates code, returns `ClaimablePaymentDetail`
2. **Registration check** → GET to `nexpay-auth-svc` — check if recipient is registered
3. **Choice page load** → GET from order orchestrator — returns available rails for this claim/program
4. **Rail selection** → POST to order orchestrator — initiates payout via selected rail
5. **Confirmation** → returns transaction reference and status

The `choicePage/returningUserChoiceSelection.json` mock indicates different flows for new vs. returning users, with returning users' prior rail preferences pre-populated.

## 4. Virtual Card Display Solution

The `cardDashboard/checkCreditCardDetails.json` and the `displayFullCardNumber: "Y"` flag in `dashboardDetails.json` indicate that MPV can display full virtual card details (PAN, CVV, expiry) for online purchases. The solution for this PCI-sensitive feature:

- Full card details should be served through a **secure reveal** mechanism (e.g., a time-limited, single-use API call that returns the decrypted card details, displayed for 30 seconds maximum).
- The `cardToken` (JWE) in the login response likely serves as the encrypted credential that authorizes card detail retrieval without exposing raw card data in the session.
- The browser should never cache card details (no `localStorage`, no service worker cache for this endpoint).

## 5. PCI DSS Scope Assessment for MPV

MPV is in the **PCI DSS scope** as a system that:
- Receives and transmits cardholder data (PAN, CVV for virtual card display)
- Authenticates cardholders accessing their payment instruments
- Initiates financial transactions (fund loads, transfers)

As a client-facing web application, it is subject to PCI DSS Requirements 6 (secure development), 8 (authentication), 11 (security testing), and potentially Requirement 4 (encryption in transit). The WAF at Azure Front Door should be configured with rules that prevent card data from appearing in logs or being cached.

## 6. Critical Security Findings and Remediation

| Finding | Severity | File | Remediation |
|---|---|---|---|
| Full PAN in mock data | Critical | `dashboard/dashboardDetails.json` line 86 | Replace with masked BIN test value immediately |
| CVV in mock data | Critical | `dashboard/dashboardDetails.json` line 87 | Remove CVV field from mock entirely |
| JWT tokens in mock data | High | `login/login.json` lines 4-6 | Replace with placeholder strings like `MOCK_JWT_TOKEN` |
| `verificationCode` in mock | Medium | `dashboard/dashboardDetails.json` lines 99, 107 | Replace with obviously fake codes |
| HS256 token signing | Medium | Architecture | Migrate to RS256 with JWKS for token validation scalability |
