# Business Analyst View — oneplatform-react_WAPP

## Business Purpose

oneplatform-react_WAPP is the cardholder-facing single-page application (SPA) branded as "My Payment Vault" (npm package name `om-mypaymentvault-spa`). It is the Gen-3 React-based replacement for the older OnePlatform JSP/servlet web application. The app gives prepaid cardholders a self-service portal to manage their Onbe-issued payment instruments across multiple product lines (prepaid cards, digital wallets, rewards).

## Capabilities Provided

- Card activation flow with identification banner (T-Mobile and generic variants visible in public assets)
- Dashboard showing balance, recent transactions, and brand-accelerator promotions
- Digital wallet provisioning — Apple Pay, Google Pay, Samsung Pay (wallet images present in public assets)
- ATM locator
- Account management: personal profile updates, secondary card additions, request plastic reissue
- Check request and ACH/wire transfer initiation
- Rewards and refer-a-friend integration
- Transaction history with infinite scroll
- i18n support via `react-i18next` and `i18next` (multi-locale cardholder UI)
- Help and support, disclosure management, logout
- Mixpanel analytics integration (`mixpanel-browser`)
- PDF export of statements (`html2pdf.js`)
- reCAPTCHA integration (`react-google-recaptcha`) for bot protection

## Client/Cardholder Impact

This is a direct consumer-facing application. Downtime or security failures directly affect cardholders' ability to access funds, activate cards, or initiate disbursements. The wallet provisioning feature has PCI DSS implications (card data must not be exposed in the SPA layer — PAN must remain masked). Any defect in the activation flow blocks cardholder access to funds, triggering Reg E dispute obligations. The app's T-Mobile brand-specific activation banner indicates multi-program support for named enterprise clients.

## Business Rules Found in Code

- Multi-environment configuration enforced via `.env`, `.env.qa`, `.env.stage`, `.env.prod` — environment-specific API base URLs must not allow cross-environment data access
- Build-time environment injection (webpack, env-cmd) means secrets must not be embedded in bundles shipped to browsers
- Mock server (`mock-server/server-mocker.js`) provides card activation GET/POST stubs — indicates strict API contract testing required before release
- reCAPTCHA on public-facing forms enforces CAPTCHA as a fraud deterrent consistent with UDAAP expectations for cardholder self-service portals
- Mixpanel event tracking is present; data minimization obligations under CCPA and GDPR require that PII not be sent to third-party analytics platforms without consent

## Regulatory Obligations

- **PCI DSS**: SPA must not receive, render, or log full PAN or CVV; any card data display must be masked (first 6 / last 4). Wallet provisioning flows must use tokenization endpoints only.
- **Reg E**: Activation failures must provide clear error messaging; fund-access features require error resolution paths.
- **GDPR/CCPA**: Mixpanel integration and i18n cookie preferences require a privacy notice and opt-out mechanism for EU/CA cardholders.
- **GLBA**: Cardholder data transmitted over the network must use TLS 1.2+; the application must not store sensitive financial data in localStorage or sessionStorage.

## Key Business Risks Found in Code

- **Third-party analytics risk**: Mixpanel receives browser telemetry. If event payloads inadvertently include PII (name, account number fragments), CCPA and GDPR obligations are triggered. No evidence of a data-scrubbing layer was found in available source.
- **Mock server in repository**: `mock-server/` containing card activation POST stubs is checked into the repo. Misuse in a production deployment (or accidental exposure) could simulate card activation responses without backend validation.
- **Environment variable exposure**: Webpack bundles environment variables at build time. Any secrets placed in `.env.prod` are embedded in the static bundle and visible to any user who inspects the JavaScript.
- **Dependency currency**: React 18, Redux Toolkit 2.x, and Axios 1.x are current. `react-scripts` 5.x has known CRA deprecation; migration to a supported bundler (Vite) should be evaluated.
- **No server-side rendering**: All rendering is client-side; SEO and initial load security headers depend entirely on the hosting layer (AKS ingress), not the application itself.
