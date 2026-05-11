# 05 Solution Architect — embedded-payments-sdk

## All Classes, Objects, and Key Functions

### `src/shim.ts` — `OnbeWidget` Export

| Member | Type | Purpose |
|---|---|---|
| `OnbeWidget` | exported const object | Singleton that manages the entire shim lifecycle |
| `OnbeWidget.init(config: WidgetConfig)` | Method | Entry point called by the partner page; validates accessToken, creates iFrame, calls `_loadSpa` |
| `OnbeWidget._loadSpa(accessToken, method)` | Async method | Creates iFrame, submits hidden form POST with token to WIDGET_URL, handles dev-mode GET path |
| `OnbeWidget._renderLoadingState(container)` | Method | Shows animated spinner in container before widget loads |
| `OnbeWidget._renderErrorState(reason?, details?)` | Method | Renders error UI; fires `ONBE_WIDGET_ERROR` postMessage to partner page |
| `OnbeWidget._renderPopupPanel(message, buttonText, src)` | Method | Renders popup fallback panel (not yet enabled — TODO comment at shim.ts line 165) |
| `OnbeWidget._renderSessionActiveState()` | Method | Shows "session active in secure window" state when popup is used |
| `OnbeWidget._openPopup(src)` | Method | Opens popup window; monitors for close |
| `OnbeWidget._onWidgetReady(source)` | Method | Handles successful widget handshake; hides loading state |
| `OnbeWidget._hideStatusPanel()` | Method | Fades out and removes loading/error panel; reveals iFrame |
| `OnbeWidget._makeCenteredWrapper()` | Method | DOM utility; creates centred flex container |
| `OnbeWidget._makeButton(label, accentColor, onClick)` | Method | DOM utility; creates styled button element |
| `handleMessage(event: MessageEvent)` | Function (module scope) | Validates message source; processes WIDGET_READY, LOAD_FAILED, forwards others |

### `src/widget/main.ts`
Entry point for the widget SPA. Mounts the root component to the `<div id="app">` element in `src/widget/index.html`. Likely initialises `WidgetStore` and renders the initial `LoadingView`.

### `src/widget/store/WidgetStore.ts`
Singleton reactive state store for the widget. Holds all in-memory widget state:
- Current screen/view
- Disbursements list
- Selected modality + claim code
- Card details (PAN, CVV, expiry — PCI state)
- Transactions and balance
- Contact information
- Error state

### `src/widget/services/ApiClient.ts`

| Member | Purpose |
|---|---|
| `getApiUrl()` | Resolves `window.appConfig.apiUrl`; falls back to `http://localhost:8080/embedded/widget` |
| `ApiClient` | Axios instance with `baseURL`, `Content-Type: application/json`, `withCredentials: true` |
| Request interceptor | In dev mode, attaches `X-Dev-Access-Token` header from `appConfig.devAccessToken` |

### `src/widget/services/WalletService.ts`

| Method | Purpose |
|---|---|
| `WalletService.fetchEnabledWallets(request, onError?)` | POST `/enabled-wallets`; returns `EnabledWalletsResponse | null` |
| `WalletService.pushProvision(request, onError?)` | POST `/provision-wallet`; returns `PushProvisionResponse | null` |
| `parseError(error)` | Normalises Axios errors to `{ status, message, path }` |

### `src/widget/services/ClaimService.ts`
Handles disbursement-related API calls:
- `listDisbursements()` — `POST /list-disbursements`
- `getModalities(claimCode)` — `POST /modalities`
- `acceptTerms(termsIDs)` — `POST /accept-terms`
- `executeDisbursement(claimCode, modalityId)` — `POST /disburse`
- `getDisbursementInfo()` — `POST /disbursement-info`
- `getMaskedDisbursementInfo()` — `POST /masked-disbursement-info`

### `src/widget/services/WalletService.ts`
Digital wallet provisioning calls (Apple Pay, Google Pay). See method table above.

### UI Components (all in `src/widget/components/`)

| Class | Key Responsibilities |
|---|---|
| `BalanceCardComponent` | Renders available balance from `WidgetStore` |
| `CardDetailsComponent` | **Renders full PAN, CVV, expiry date** — PCI-sensitive display; likely includes a reveal/hide toggle |
| `DateFilterComponent` | Date range selector for transaction filtering |
| `ErrorResolutionComponent` | Shows error type and user-actionable resolution steps |
| `ErrorTooltipComponent` | Inline field-level error tooltip |
| `FooterComponent` | Legal/branding footer |
| `HeaderComponent` | Widget title bar; may include close/logout button |
| `ToastComponent` | Dismissible notification (success/error/info) |
| `TransactionModalComponent` | Detailed overlay for a single transaction |
| `TransactionsComponent` | Scrollable list of `Transaction` items with date/amount/balance |
| `WebWalletComponent` | Apple/Google Pay wallet selection and provisioning UX |

### UI Views (all in `src/widget/views/`)

| Class | Purpose |
|---|---|
| `LoadingView` | Spinner while API calls in progress |
| `DashboardView` | Main screen — balance + disbursement list |
| `ModalitySelectionView` | Payment method selection |
| `ClaimsView` | Claims history |
| `ContactInfoView` | Cardholder PII display |
| `ErrorView` | Terminal error screen |
| `TermsModalView` | T&C acceptance flow |
| `DateSelectorModalView` | Date range picker |

### Utility Classes (`src/widget/utils/`)

| Class | Key Functions | Purpose |
|---|---|---|
| `ColorUtils` | `isDark(hex)`, `lighten/darken` | Compute derived theme colours from `accentColor` |
| `DateUtils` | `formatDate()`, `parseDate()` | Date formatting for transaction display |
| `DeviceDetector` | `isIOS()`, `isAndroid()`, `isMobile()` | Device detection for wallet provisioning eligibility |
| `ErrorHandler` | `handleApiError(error, fatal, onError?)` | Centralised API error handling; triggers error view or toast |
| `FormatterUtils` | `formatCurrency(cents)`, `formatCardNumber(pan)` | Display formatting for amounts and card numbers |
| `TermsUtils` | `buildTermsURL(resourceName)` | Constructs CDN URL for T&C documents |
| `WalletConstants` | Wallet provider ID constants | Apple Pay / Google Pay ID mapping |
| `XContentUtils` | `getAssetUrl(name)` | Constructs XContent/CDN URLs for widget assets |

## Security Vulnerabilities and Technical Debt

### 1. `allow-same-origin` in iFrame Sandbox (P1 — High)
`shim.ts` line 134: `iframe.sandbox.add('allow-scripts', 'allow-forms', 'allow-popups', 'allow-same-origin')`.
`allow-same-origin` combined with `allow-scripts` means the widget SPA can access its own cookies and localStorage. An XSS vulnerability in the widget could exfiltrate the `X-Onbe-Session-Token` cookie. The reason `allow-same-origin` is needed is for the widget's cookie-based API calls. Alternatives:
- Use `SameSite=Strict` cookies and rely on origin checks
- Evaluate whether `allow-same-origin` can be removed with modified auth flow

### 2. `CardDetailsComponent` PAN/CVV Display (P1 — High)
The `CardDetailsComponent` displays full PAN and CVV in the DOM. If an attacker can inject script into the widget iframe (via XSS), or if the iFrame is loaded in a page where the same-origin sandbox is not active, the PAN/CVV can be read from the DOM. Mitigations:
- Ensure no inline event handlers exist (`Content-Security-Policy: script-src 'self'`)
- Auto-clear card details from `WidgetStore` after a timeout (e.g., 30 seconds)
- Implement a `maskOnCopy` feature so the clipboard never receives the raw PAN

### 3. `devAccessToken` in `AppConfig` (P1 — Critical in Production)
`ApiClient.ts` lines 26–32: In dev mode, the `devAccessToken` from `window.appConfig` is sent as `X-Dev-Access-Token`. If `VITE_DEV_MODE` is not correctly set to `false` in production builds, this header could bypass the cookie-auth requirement. Vite's `import.meta.env.VITE_DEV_MODE` will be replaced at build time with the env-var value — this must be verified in the production CI/CD build.

### 4. `_renderErrorState` fires `postMessage` with `targetOrigin: '*'` (P2 — Medium)
`shim.ts` line 207: `window.postMessage({ type: IFrameEvents.ONBE_WIDGET_ERROR, ... }, '*')`.
Firing postMessage with `'*'` as `targetOrigin` means any listening page can receive the error payload. While the error details are non-sensitive (error message, field/issue pairs), best practice is to use the partner's origin as the target.

### 5. Axios `^1.13.5` (Check for CVEs — P3)
Axios is a widely-used HTTP library with an active CVE history. The `^` semver range allows automatic minor/patch updates on `npm install`. The `package-lock.json` should be committed and `npm ci` used in CI to pin the exact version.

### 6. No Content Security Policy Declared in SDK (P2)
The widget HTML (`index.html`) likely does not set a strict CSP. Since the widget displays PANs/CVVs, a strict CSP (`script-src 'self'; object-src 'none'; frame-ancestors 'self' {partner-domains}`) should be enforced.

### 7. `_renderErrorState` Uses Emoji (cosmetic but PCI-notable) (P4 — Low)
`shim.ts` line 229: `icon.textContent = '🔒'`. Emoji rendering is environment-dependent. Not a security issue but may render incorrectly in some operating environments.

## Remediation Priority Summary

| Issue | Priority | Action |
|---|---|---|
| `allow-same-origin` XSS risk for session cookie | P1 — High | Evaluate alternative auth mechanism; strengthen widget CSP |
| PAN/CVV auto-clear in `WidgetStore` | P1 — High | Add timeout-based state clearance; zero out card fields on navigation away |
| `devAccessToken` in production build | P1 — Critical | Add build-time assertion that `VITE_DEV_MODE` is `'false'` in production CI |
| `postMessage` with `'*'` origin | P2 — Medium | Use specific partner origin |
| Widget CSP declaration | P2 — Medium | Add `Content-Security-Policy` meta tag to `index.html` |
| Axios version pinning | P3 — Low | Use `npm ci` in CI; review for CVEs |
