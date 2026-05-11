# Data Architect View — oneplatform-react_WAPP

## Data Models

oneplatform-react_WAPP is a pure SPA and does not own a persistent data store. All domain data is fetched from backend REST APIs at runtime and held transiently in Redux state. The Redux Toolkit store acts as the in-memory model during a browser session.

Key in-memory data domains inferred from UI feature set and mock-server stubs:
- **Card/Account**: card status, masked PAN (last 4), balance, card type, activation state
- **Cardholder Profile**: name, address, phone, email — used for account management views
- **Transaction History**: date, merchant, amount, transaction type — paginated via infinite scroll
- **Affiliate/Program Context**: affiliate ID, branding skin, locale — drives theming and i18n copy
- **Wallet Provisioning**: tokenization request/response payloads for Apple Pay, Google Pay, Samsung Pay

## Sensitive Data Handled

| Data Category | Presence | Protection Status |
|---|---|---|
| Full PAN | Must NOT be present per PCI DSS | Not observed in source; backend must mask |
| Masked PAN (last 4) | Expected in transaction/account display | Rendered only; not persisted client-side |
| CVV/CVC | Must NOT be present | No CVV field observed in SPA layer |
| Cardholder Name | Present in profile view | In Redux state only; not persisted to browser storage |
| Address/Phone/Email | Present in account management | In Redux state only |
| SSN / Government ID | Not observed | Not expected in cardholder self-service SPA |
| Bank Account / Routing | Possible in ACH transfer flow | Must be masked; backend-owned |

## Encryption and Protection Status

- All API communication must use TLS (enforced at AKS ingress level; not visible in SPA code)
- No client-side encryption libraries observed in `package.json`; the SPA does not encrypt data at rest
- Browser storage (localStorage, sessionStorage) usage is not directly observable from available source; this must be audited to confirm no sensitive tokens are persisted
- reCAPTCHA tokens are short-lived and transmitted to backend; not stored
- Redux state is in-memory only; cleared on tab close assuming no persistence middleware

## Data Flows

```
Cardholder Browser
  -> AKS Ingress (TLS termination)
    -> oneplatform-rest_API (REST calls via Axios)
      -> Backend microservices (card data, transactions, profile)
        -> Core databases (ecountcore, cbaseapp, nexpay)
```

Analytics side-channel:
```
Cardholder Browser
  -> Mixpanel CDN (event telemetry)
```

## Retention Concerns

- The SPA itself retains no data beyond the browser session
- Mixpanel events are retained per Mixpanel's data retention policy (configurable by Onbe's account settings); events may contain user-agent, IP, session metadata, and any custom event properties set by the application
- Browser caching of static assets (JS bundles) containing build-time configuration values warrants review under GLBA's safeguard rules if any non-public configuration is embedded

## PCI DSS Data Storage Compliance

- The SPA does not store SAD (Sensitive Authentication Data) — PAN, CVV, track data — in any persistent browser store. This is the correct posture.
- PCI DSS Requirement 4.2.1 (strong cryptography for data in transit) compliance depends on TLS enforcement at the AKS ingress layer; the SPA cannot enforce this independently.
- PCI DSS Requirement 6.4.3 requires that all payment page scripts be managed with integrity protection (e.g., Subresource Integrity for CDN-loaded scripts). The Mixpanel browser SDK loaded from CDN should be assessed for SRI compliance.
- The mock server files checked into the repository must not be deployed to any CDE-adjacent environment; they simulate card activation without real authorization.
