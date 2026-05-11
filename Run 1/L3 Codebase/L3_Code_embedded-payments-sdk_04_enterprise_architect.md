# 04 Enterprise Architect — embedded-payments-sdk

## Platform Generation

`embedded-payments-sdk` is a **Generation 3 (Gen-3)** component — it is the browser-facing layer of the newest Onbe product. Evidence:

| Dimension | Value |
|---|---|
| Language | TypeScript 5.9 (latest) |
| Build | Vite 5 (latest) |
| Framework | Vanilla TypeScript + Web Components (no React/Angular overhead) |
| API protocol | REST via Axios with HttpOnly cookies |
| Auth pattern | Short-lived OTT → OAuth2 cookie session |
| Distribution | CDN + bundled into Spring Boot static resources |
| CI/CD | GitHub Actions with cross-repo artefact deployment |
| Testing | CodeQL static analysis |

Contrast with `emboss-extract_LIB` (Spring 2.0, Java 5, Log4j 1.2) — these two components are at opposite ends of the technology spectrum within the same platform.

## Role in Platform Architecture

The SDK occupies the **partner integration edge** of the platform — the only component that runs in end-user browsers on partner-hosted web pages. Its security posture directly affects:
- The trust boundary between the partner's page and Onbe's payment widget
- The cardholder's experience of Onbe's brand
- The confidentiality of PANs and CVVs displayed in the widget

```
Partner's Web Page (external domain)
    │
    │  includes shim.js from CDN
    ▼
┌─────────────────────────────────────────────────────────┐
│  OnbeWidget.init({ container, accessToken, theme })     │
│  (shim.js — runs on partner domain)                     │
│    │                                                     │
│    │  creates iFrame                                     │
│    ▼                                                     │
│  <iframe sandbox="allow-scripts allow-forms ...">       │
│    │                                                     │
│    │  form POST with accessToken                        │
│    ▼                                                     │
│  https://api.onbe.com/embedded/shim/load-spa            │
│    │  (embedded-payments-api validates OTT,             │
│    │   sets HttpOnly cookies, returns widget HTML)       │
│    ▼                                                     │
│  Widget SPA loads (main.ts → views → components)        │
│    │                                                     │
│    │  postMessage ONBE_WIDGET_READY to shim             │
│    ▼                                                     │
│  Shim sends WidgetConfig to widget                      │
│    │                                                     │
│    │  Widget renders DashboardView, makes API calls     │
│    ▼                                                     │
│  Widget operates (cookies auth all /embedded/widget/* ) │
└─────────────────────────────────────────────────────────┘
```

## Architectural Patterns

### 1. iFrame Isolation
The widget runs in a sandboxed iFrame with `allow-same-origin` to enable cookie-based auth. The `sandbox` attribute's `allow-same-origin` grants the widget origin access to its own cookies (the `X-Onbe-Session-Token` cookie), which is necessary but means XSS in the widget has access to session material.

### 2. postMessage Protocol
The shim and widget communicate via `window.postMessage`. The shim validates message origin via `TARGET_ORIGIN` (derived from `VITE_WIDGET_URL`). This is the correct pattern for cross-origin iFrame communication. The protocol uses typed events (`IFrameEvents` enum):
- `ONBE_WIDGET_READY` — widget ready signal
- `ONBE_WIDGET_INIT` — shim → widget: sends `WidgetConfig`
- `ONBE_WIDGET_LOAD_FAILED` — widget → shim: error propagation
- `ONBE_WIDGET_ERROR` — shim → partner page: error events

### 3. Token Flow (No Token in URL)
The OTT is submitted via a hidden form POST (`method=POST` form targeting the iFrame), not via URL parameters. This prevents the token from appearing in browser history, server logs, or Referer headers. This is the correct pattern for PCI-sensitive token handling.

### 4. No Third-Party Framework
The widget is implemented in vanilla TypeScript with Web Components. This eliminates the framework dependency attack surface (no React/Angular CVEs) but requires more custom code for DOM manipulation and state management.

## Cross-Repo Dependency

The SDK has a CI coupling to `embedded-payments-api`: on every merge to `main`, the widget build is automatically pushed to the backend repo as a PR. This means:
- The SDK version controls what UI the backend serves
- Widget and API deployments are coordinated through the backend's review process
- A breaking API change requires coordinating SDK and API PRs

## Strategic Fit

The SDK represents the partner experience abstraction layer. As the Embedded Payments product matures, this SDK is likely to:
1. Expand to support more modalities and payment methods
2. Add React/Angular wrapper packages for partner developer experience
3. Potentially be published to npm (under a scoped `@onbe/` package)
4. Develop formal API versioning to manage backward compatibility with partner integrations

## PCI DSS Considerations in Architecture

- The iFrame boundary provides domain isolation but `allow-same-origin` within the iFrame weakens the sandbox guarantee
- The `CardDetailsComponent` is the highest-risk UI element — any XSS vulnerability in the widget SPA could exfiltrate PANs/CVVs to an attacker's server
- The `devAccessToken` mechanism (dev mode) must be absolutely unreachable in production builds — a Vite `define` or environment guard must ensure `VITE_DEV_MODE !== 'true'` in production
