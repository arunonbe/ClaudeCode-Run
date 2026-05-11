# Solution Architect — poc_elasticsearch

## Technical Architecture

No software architecture in the traditional sense. The repository is a collection of static web files:

```
poc_elasticsearch/
├── CustomerService.html     -- Single-page agent search UI
├── customerservice.css      -- Stylesheet
├── style.css                -- Additional styles
├── images/                  -- UI screenshots (FIS CSA mockups, nav icons)
├── xContent/
│   └── recipient/
│       ├── op/              -- Activation component CSS + images
│       └── TMO_4848/        -- T-Mobile program activation banners
└── test.txt                 -- Git sync test file
```

### Runtime Architecture (as designed for POC)
```
Browser
  --> loads CustomerService.html (static file host or directly)
      --> CDN: Bootstrap 5, azsearch.js 0.0.21, React 15, Redux 3
      --> azsearch.js initialises AzSearch.Automagic
          --> HTTPS API calls to csapoc1.search.windows.net
              using hard-coded query key
              index: azureblob-index
          --> Results rendered into DOM divs: #searchBox, #results, #pager
          --> Facets rendered into: #sortBy, #platformFilter, #amountFacet, #clientFacet, #programFacet
      --> Modals: Advance Search, FIS CSA detail view
```

## API Surface
No Onbe-owned API. The only external call is:
- `GET https://csapoc1.search.windows.net/indexes/azureblob-index/docs` (azsearch.js SDK call)

## Security Posture

### CRITICAL FINDING — Hard-coded API Key
**File:** `CustomerService.html` **Line:** ~349

```javascript
var automagic = new AzSearch.Automagic({
  index: "azureblob-index",
  queryKey: "[REDACTED — rotate immediately]",
  service: "csapoc1",
  dnsSuffix: "search.windows.net",
});
```

This key grants read access to the Azure Cognitive Search index `azureblob-index` on service `csapoc1`. If this index contains real cardholder data, it represents a live PCI DSS breach vector. **Rotate immediately.**

### Authentication
None. The HTML page is served without any authentication. There is no OAuth, session management, or access control.

### Cryptography
None at the application level. Azure Cognitive Search uses TLS for transport. No application-layer encryption.

### Secrets Management
No secrets management. API key is plaintext in version-controlled HTML.

### CVE / Dependency Risk

| Dependency | Version | Status |
|---|---|---|
| React | 15.5.4 (CDN) | End-of-life 2017; numerous known CVEs |
| Redux | 3.6.0 (CDN) | Outdated |
| azsearch.js | 0.0.21 (CDN, no SRI) | Unmaintained since ~2018; no integrity hash |
| Bootstrap | 5.3.0-alpha3 (CDN) | Alpha release; not recommended for production |
| Popper.js | 1.16.0 (CDN) | Outdated |
| FontAwesome kit | `3c6a1f2f0f` (CDN) | Kit ID in URL; kit-based delivery can be updated remotely |

### SRI (Subresource Integrity)
Bootstrap CSS has an `integrity` attribute. azsearch.js, React, Redux, and Popper.js do NOT have SRI hashes — supply chain compromise at CDN would execute in the browser context.

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| Hard-coded Azure search API key | `CustomerService.html:349` | Critical |
| No authentication | Entire repo | Critical |
| End-of-life React 15 loaded | `CustomerService.html:338` | High |
| azsearch.js 0.0.21 (unmaintained, no SRI) | `CustomerService.html:346` | High |
| Advance search card number input uses `type="email"` | `CustomerService.html:189` | Medium — wrong input type for card number field |
| Mixed content — POC search UI + recipient activation assets in same repo | `xContent/` | Medium |
| `test.txt` committed — cleanup artefact | `test.txt` | Low |

## Gen-3 Migration Requirements
This repository should not be migrated — it should be retired. If the business capability (unified cardholder search) is required in production:

1. Design a Gen-3 search service (Spring Boot microservice) acting as authenticated proxy to Azure Cognitive Search
2. Implement OIDC/OAuth2 authentication
3. Mask CHD fields server-side before returning results to the browser
4. Move recipient `xContent/` assets to the appropriate content delivery repository
5. Use `react-component_LIB` and the Onbe design system for the frontend

## Code-Level Risks (file:line references)

| Risk | File | Line (approx.) | Detail |
|---|---|---|---|
| Hard-coded Azure Cognitive Search query API key | `CustomerService.html` | 349 | `queryKey: "[REDACTED — rotate immediately]"` |
| Full card value in search index — only last-4 masked in display | `CustomerService.html` | 372 | `result.cardlast4 = result.card.substr(result.card.length - 4)` — `result.card` is full value in memory |
| Card number input field uses `type="email"` | `CustomerService.html` | 189 | `<input type="email" ... placeholder="Card Number">` — wrong semantic type |
| No SRI on azsearch.js CDN script | `CustomerService.html` | 346 | `<script src="https://cdn.jsdelivr.net/npm/azsearch.js@0.0.21/dist/AzSearch.bundle.js">` |
