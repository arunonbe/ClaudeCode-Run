# Enterprise Architect Report — demoaccessibilitytesting

## 1. Platform Generation Classification

| Attribute | Value |
|---|---|
| Generation | Gen-3 frontend patterns (React 18, Redux Toolkit, Azure integration) |
| Runtime | Browser SPA; CI on GitHub Actions ubuntu-latest |
| Framework | Create React App 5 / React 18 |
| State management | Redux Toolkit + redux-thunk |
| Routing | React Router 6 |
| i18n | i18next + react-i18next |
| API integration | Axios (REST/JSON) |
| Accessibility testing | Axe-core CLI (WCAG 2.x) |

---

## 2. Domain Context

**Domain**: Cardholder Experience / Digital Banking  
**Sub-domain**: Payment Vault — Cardholder self-service portal  
**Application**: `mypaymentvault` — the recipient-facing web application for Onbe prepaid card management

This repository contains:
1. The **source code** for the mypaymentvault frontend (or a test variant of it)
2. The **accessibility CI pipeline** targeting that application

The application supports **T-Mobile** and **Onbe default** (`op`) affiliate programs, with distinct branding per affiliate.

---

## 3. Role in Platform

```
Cardholder Browser
  │ HTTPS
  ▼
mypaymentvault SPA (React)
  │
  ├─ REST → /mypaymentvaultapi (BFF / backend-for-frontend)
  │           [card activation, account data, transaction history]
  │
  ├─ Azure Blob → xContent
  │           [disclosures, branded content]
  │
  └─ Google reCAPTCHA
           [bot prevention on activation/registration]

[CI: GitHub Actions]
  └─ axe-core → mypaymentvault.qa.onbe.dev
           [WCAG accessibility scanning]
```

---

## 4. Dependencies

| Direction | System | Interface | Notes |
|---|---|---|---|
| External | mypaymentvaultapi (BFF) | REST/JSON over HTTPS | `external.{env}.onbe.dev/mypaymentvaultapi` |
| External | Azure Blob Storage | HTTPS | xContent static assets |
| External | Google reCAPTCHA | HTTPS | `react-google-recaptcha` v2 |
| External | MSAL / Azure AD | HTTPS | Auth credentials in CI secrets (`REACT_APP_AUTH_CLIENT_ID`, `_AUTHORITY`, `_REDIRECT_URI`) |
| Internal | GitHub Actions | CI workflow | Axe scan pipeline |

---

## 5. Architectural Patterns

| Pattern | Implementation | Quality |
|---|---|---|
| Component-based UI | React 18 functional components | Modern |
| Flux/Redux state | `@reduxjs/toolkit` + `react-redux` | Good |
| Environment-based config | `env-cmd` + `.env.*` files | Poor — files committed to repo |
| Mock server for dev | `connect-api-mocker` + Express | Good — clean separation |
| i18n | `i18next` | Good |
| Infinite scroll | `react-infinite-scroll-component` | Used for transaction history |
| Multi-wallet support | Images for Apple Pay, Google Pay, Samsung Pay present | Partial — UI assets only visible |

---

## 6. Current Status

| Aspect | Status |
|---|---|
| Branch | `main` |
| React version | 18.2.0 (current) |
| Accessibility CI | Present but manual trigger only |
| Test coverage | Unknown — `src/` React source files not found in repo glob (likely excluded or in different structure) |
| Affiliate support | `op` (Onbe default) + `tmobile` (branded) |

---

## 7. Blockers

| Blocker | Detail |
|---|---|
| `.env*` files in repo | Must be removed and gitignored before any production readiness review |
| Axe CI not triggered on PRs | Accessibility regressions can reach main without detection |
| xContent URL env mismatch | Prod `.env.prod` points to staging blob storage URL |
| Source files not in repo | React `src/` directory appears empty/excluded — limits analysis depth |
| Auth secrets approach | MSAL auth config injected via CI secrets but local `.env` has no equivalent, suggesting dev builds may not have auth |
