# Solution Architect Report — demoaccessibilitytesting

## 1. Architecture Overview

demoaccessibilitytesting is a **React 18 SPA** (`project/`) with an **Express mock server** (`mock-server/`) and a **GitHub Actions accessibility testing pipeline**. The repository appears to be a copy of (or closely related to) the production `mypaymentvault` cardholder portal, used specifically for accessibility (WCAG) validation.

```
Repository Structure:
├── project/               — React 18 SPA (Create React App)
│   ├── public/            — Static assets (images, SVGs, favicon)
│   ├── src/               — React source (not found in glob — possibly gitignored)
│   ├── package.json       — Dependencies and scripts
│   └── .env*              — Environment configs (committed — risk)
│
├── mock-server/           — Local dev API mock
│   ├── server-mocker.js   — Express server on port 8080
│   └── json/              — Static JSON responses
│       ├── cardActivation/GET.json
│       ├── cardActivation/POST.json
│       ├── cardActivation/test.json
│       └── affiliate/GET.json
│
└── .github/workflows/
    └── axe.yml            — Accessibility CI pipeline
```

---

## 2. API Surface

The application consumes the following external APIs (inferred from mock structure and env files):

| Endpoint | Method | Mock Available | Purpose |
|---|---|---|---|
| `/api/cardActivation` | GET | Yes | Fetch auth requirements for card activation |
| `/api/cardActivation` | POST | Yes | Submit card activation |
| `/api/affiliate` | GET | Yes | Fetch affiliate branding/config |
| `mypaymentvaultapi/*` | Various | No | Full backend BFF (all other operations) |

---

## 3. Security Architecture

| Control | Status | Detail |
|---|---|---|
| HTTPS | Active | All production URLs use HTTPS |
| reCAPTCHA v2 | Active | `react-google-recaptcha` protects activation/registration |
| MSAL / Azure AD authentication | Present in CI secrets | `REACT_APP_AUTH_CLIENT_ID`, `REACT_APP_AUTH_AUTHORITY`, `REACT_APP_AUTH_REDIRECT_URI` — auth strategy for the portal |
| Environment file secrets | **Critical Gap** | `.env*` files committed to repository |
| Content Security Policy | Not observed | No CSP headers configured in React or Express mock |
| Subresource Integrity | Not observed | No SRI on CDN assets |
| Log sanitization | Not applicable | SPA; no server-side logging |

---

## 4. Technical Debt

| Item | Location | Severity |
|---|---|---|
| `.env*` files committed to repo | `project/.env`, `.env.qa`, `.env.stage`, `.env.prod` | Critical — secrets hygiene failure |
| No `.gitignore` for `.env*` files | Root of `project/` | Critical |
| React source (`src/`) not in repo | `project/src/` appears empty | High — analysis incomplete; may be in `.gitignore` |
| xContent URL mismatch (prod env points to staging) | `project/.env.prod` line 4 | High |
| `CI: false` in axe workflow | `axe.yml` line 12 | Medium — suppresses CRA warning-as-errors |
| Axe scan targets live QA, not built artefact | `axe.yml` lines 52–58 | Medium — build step disconnected from scan |
| Manual-only accessibility CI trigger | `axe.yml` line 3 | Medium |
| T-Mobile branded assets in public repo | `public/TMO_4848/` and `public/images/` | Low — client brand assets in version control |

---

## 5. Gen-3 Status

This application is **already Gen-3** in frontend technology (React 18, Redux Toolkit, i18next, MSAL). Key modernization gaps:

1. **Environment configuration**: Replace `.env` file approach with Azure App Configuration / runtime injection at deploy time
2. **Auth flow**: Confirm MSAL integration is complete end-to-end (secrets only in CI currently)
3. **Accessibility CI**: Move from manual `workflow_dispatch` to automatic trigger on PRs to `main`
4. **CSP headers**: Implement strict Content-Security-Policy in the hosting layer or SPA config
5. **Source code presence**: Ensure React `src/` is in repo (not gitignored) for proper auditability

---

## 6. Code Quality Risks

| Risk | Detail |
|---|---|
| React `src/` absent from glob | Cannot audit component-level code, state management, or API call patterns |
| reCAPTCHA site key identical across all envs | Same key used for default/QA/staging/prod — should be env-specific to limit abuse scope |
| xContent prod URL points to staging storage | Cardholder-facing content may serve wrong documents in production |
| No automated PR accessibility gate | WCAG regressions can be merged and deployed |
| Bootstrap 5 + react-bootstrap both in deps | Potential style conflicts; react-bootstrap should be sufficient |
