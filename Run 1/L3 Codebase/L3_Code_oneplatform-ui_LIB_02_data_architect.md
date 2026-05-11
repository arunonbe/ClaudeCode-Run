# Data Architect — oneplatform-ui_LIB

## Data Stores
This is a pure frontend static asset library. It does not directly connect to any data store at build or runtime.

- **No databases**: No JDBC, JPA, or any persistence layer.
- **No external APIs**: No HTTP client calls from this library.
- **Mock data mode**: `config.js` sets `datasource: 'MOCKJSON'` indicating the application can operate against mocked JSON responses; actual API backend is `oneplatform-rest_API`.

## Schema / Data Structures
Not applicable — this is a static asset library. Data structures are defined by the JSON API responses from `oneplatform-rest_API` that the JavaScript modules consume.

## Sensitive Data Classification
- **No sensitive data stored** in this library.
- **Risk**: The UI renders cardholder PII (name, address, card last 4, transaction history) received from the API — the client-side code that processes and displays this data lives within the JavaScript modules in `src/client/`. PAN data display (if any) uses OCRAStd font suggesting card number rendering. Full PAN should never be present in UI responses per PCI DSS Req 3.
- `config.js` `debug: true` could cause verbose client-side logging that may inadvertently expose data in browser console.

## Encryption
- No encryption performed by this library.
- HTTPS transport is enforced at the web server / load balancer layer (not managed here).
- No Content Security Policy (CSP) headers set in this HTML (`index.html`) — CSP is responsibility of the serving web application.

## Data Flow
```
Browser
  └─ Loads static assets (CSS, JS, fonts) from WAR deployer
  └─ JS modules make XHR/AJAX calls to oneplatform-rest_API
  └─ Renders API response data in UI components
```

## Data Quality and Retention
Not applicable — static assets; no data storage or retention concerns.

## Compliance Gaps
- **PCI DSS Req 6.4.3**: No evidence of Subresource Integrity (SRI) hashes on script/style includes — SRI would verify integrity of loaded resources.
- **PCI DSS Req 6.4.4**: No X-Frame-Options or CSP `frame-ancestors` visible in `index.html` (though `.antiClickJack` CSS class may accompany JavaScript frame-busting — requires JS review).
- **Flash asset** (`rsa_fso.swf`): Flash is end-of-life; use of any Flash component in a PCI-scoped application is a finding.
- **`debug: true` in config.js**: May expose sensitive request/response data in browser developer tools.
- **No CSP `meta` tag** visible in `index.html` — CSP should be set via HTTP header or meta tag for all cardholder-facing pages.
