# SprintCrushers_Automation — Business Analyst View

## Business Purpose
`SprintCrushers_Automation` is a QA automation practice repository owned by the "SprintCrushers" team at Onbe. Its stated purpose is "a playground for Sprint Crushers to practice and improve automation testing skills." In its current form it also delivers practical QA value: it runs a Postman collection against the Account Management API in UAT, iterates over a country dataset, and produces an HTML report plus a Microsoft Teams notification. It is used to verify that the Account Management API (`createAccount` SOAP operation) functions correctly across multi-country scenarios.

## Capabilities
| Capability | Description |
|---|---|
| API smoke / functional testing | Executes a Postman/Newman collection (`collection.json` / `collectionnew.json`) against the Account Management SOAP API in UAT |
| Data-driven iteration | Drives test iterations from `countries.csv` — one API call per country/city/state row |
| HTML reporting | Generates a styled HTML report (`newman-detailed-table-report.html`) summarising success/incomplete/error counts per iteration |
| Teams notification | Posts an Adaptive Card to a Microsoft Teams channel via Incoming Webhook; optionally uploads the HTML report to a Teams channel SharePoint folder via Microsoft Graph API |
| GitHub Pages publishing | Copies the HTML report to `gh-pages/index.html` for hosting |
| CI/CD execution | Designed to run in GitHub Actions on push/PR to main, or Azure DevOps (env var detection logic present) |

## Business Entities
| Entity | Source | Description |
|---|---|---|
| Country | `countries.csv` | Test data rows containing country, city, state, postal, phone fields |
| Account | SOAP response `<accountNumber>` | Prepaid account created via `createAccount` |
| Partner User ID | Request `<partner_user_id>` | Randomly generated 6-char alphanumeric per iteration |
| Card Number | SOAP response `<cardNumber>` | Card assigned at account creation (may be nil) |
| Program ID | Hardcoded `04012535` | Identifies the prepaid program being tested |

## Business Rules
1. Success is defined as: HTTP 200 AND `<accountNumber>` present AND `<description>` contains "processed successfully".
2. HTTP 200 without a populated account number is classified as INCOMPLETE (not SUCCESS).
3. HTTP non-200 responses are classified as ERROR.
4. Success rate is computed as `successCount / totalIterations * 100`.

## Business Flows
1. Validate files → Run Newman collection (one iteration per CSV row) → Parse JSON report → Generate HTML report → Upload to Teams SharePoint (optional) → Post Teams Adaptive Card (optional).
2. Any failure in file validation or HTML generation causes `process.exit(1)` (pipeline fail). Teams notification failures are warnings only.

## Compliance Relevance
- Tests target `webservice-uat.mypaymentadmin.com:4005` — UAT environment (non-production), limiting live data risk.
- The test data file `countries.csv` and generated HTML report may contain account numbers and partial card numbers extracted from API responses. These must not contain real PANs.
- The `run-with-report.js` script extracts `<cardNumber>` from responses and renders it in the HTML report — if UAT returns real card numbers, this is a PCI DSS concern.
- Webhook credentials (`TEAMS_WEBHOOK_URL`, `TEAMS_APP_SECRET`) must be stored as CI/CD secrets, not committed.

## Risks
| Risk | Severity | Notes |
|---|---|---|
| Card numbers rendered in HTML report | High | `cardNumber` extracted from responses and included in report table — if real card data flows through UAT, this violates PCI DSS Req 3.3 |
| Account numbers in report | Medium | `accountNumber` rendered in HTML — classified data in test artifacts |
| Hardcoded program ID and test person name | Low | `04012535`, `Jeraldin Gerard`, `Jeraldin.Gerard@onbe.com` in collection.json — likely synthetic but confirms specific program scope |
| Endpoint hardcoded to UAT URL | Low | Non-portable; collection must be updated for other environments |
| `collection.json` in repo | Medium | Contains SOAP endpoint URL, program ID, and test-person email — should be reviewed before public exposure |
