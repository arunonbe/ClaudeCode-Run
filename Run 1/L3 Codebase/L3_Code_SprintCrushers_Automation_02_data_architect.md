# SprintCrushers_Automation — Data Architect View

## Data Stores
| Store | Type | Purpose | Retention |
|---|---|---|---|
| `countries.csv` | Flat file (CSV) | Test input data — country, city, state, postal, phone per row | In-repo; version-controlled |
| `detailed-responses.json` | Flat file (JSON) | Raw Newman execution output including full API request/response bodies | Generated at runtime; not committed |
| `newman-detailed-table-report.html` | Flat file (HTML) | Rendered test results including account numbers and card numbers extracted from responses | Generated at runtime; published to GitHub Pages |
| `gh-pages/index.html` | Flat file (HTML) | Copy of HTML report for GitHub Pages hosting | Generated at runtime |

## Schema / Tables
### countries.csv (inferred from collection template)
| Column | Type | Notes |
|---|---|---|
| country | String | ISO country name or code |
| city | String | City name |
| state | String | State/province |
| postal | String | Postal/ZIP code |
| phone | String | Phone number |

### detailed-responses.json (Newman JSON export structure)
Contains full Newman run metadata: `run.executions[]` each with `request` (method, headers, body) and `response` (code, responseTime, stream.data with raw SOAP XML).

## Sensitive Data

| Data Element | Location | Sensitivity | PCI DSS Classification |
|---|---|---|---|
| `accountNumber` | HTML report, JSON report | High | Account data — restricted under PCI DSS and GLBA |
| `cardNumber` | HTML report, JSON report | Critical | Primary Account Number (PAN) — PCI DSS Req 3.3 |
| `partner_user_id` | HTML report | Low | Synthetic random value in test runs |
| `homeEmail` (Jeraldin.Gerard@onbe.com) | `collection.json:71` | Low | Hardcoded test email address |
| `TEAMS_APP_SECRET` | Environment variable | Critical | Azure AD client secret — must never be committed |
| SOAP response body | `detailed-responses.json` | High | Full raw response including all extracted fields |

## Encryption
- API call to `webservice-uat.mypaymentadmin.com:4005` uses HTTPS (port 4005 over TLS).
- Teams/Graph API calls use HTTPS enforced by `httpRequest()` with protocol validation (`url.protocol !== 'https:'` check).
- Reports are written to local filesystem — no encryption at rest.
- GitHub Pages hosting of the HTML report means it is publicly accessible if the GitHub repository is public (or accessible to org members if private). The report contains account numbers.

## Data Flow
```
countries.csv (test input)
       |
       v
Newman collection runner
       |
       v
Account Mgmt SOAP API (UAT) ← HTTPS → SOAP response (accountNumber, cardNumber, etc.)
       |
       v
detailed-responses.json (raw response log)
       |
       v
run-with-report.js (HTML generator)
       |
       +─→ newman-detailed-table-report.html (account/card data rendered)
       +─→ gh-pages/index.html
       +─→ Teams SharePoint upload (optional) ← Microsoft Graph API over HTTPS
       +─→ Teams webhook notification ← HTTPS
```

## Data Quality
- No schema validation on `countries.csv` beyond row count check.
- No validation that API-returned account numbers are valid or match expected patterns.
- Success logic checks for "processed successfully" substring in description — brittle if API response wording changes.

## Compliance Gaps
| Gap | Standard | Notes |
|---|---|---|
| Card numbers in HTML report | PCI DSS Req 3.3, 3.4 | `cardNumber` rendered in plain text in report table (`run-with-report.js:189,244`) — if UAT returns real PANs, masking is required (first 6 / last 4 only) |
| Account numbers in HTML report | PCI DSS Req 3 | Account numbers rendered in plain text |
| Full SOAP response bodies in JSON report | PCI DSS Req 3 | `detailed-responses.json` contains unredacted response bodies |
| Report hosted on GitHub Pages | PCI DSS Req 7 | Restricted financial data accessible to anyone with repository access (or publicly if repo is public) |
| No data retention policy | SOC 2 | Generated reports accumulate without defined purge schedule |
