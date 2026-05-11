# SprintCrushers_Automation — Solution Architect View

## Technical Architecture
Single-process Node.js test runner with no framework abstraction. Architecture:

```
npm test
    |
    v
run-with-report.js
    ├── File validation (collection.json, countries.csv)
    ├── child_process.exec → npx newman run (JSON reporter)
    ├── fs.readFileSync → parse detailed-responses.json
    ├── HTML generation → newman-detailed-table-report.html + gh-pages/index.html
    └── Async Teams integration (optional)
            ├── uploadReportToTeams() → Azure AD OAuth2 → Graph API PUT (file upload)
            └── sendTeamsNotification() → Teams Incoming Webhook POST
```

Test collection: Postman Collection v2.1.0 JSON (`collection.json`). Single test item: `createAccount` SOAP request with pre-request script (random partner_user_id generation) and test script (HTTP status assertion).

## API Surface
The runner itself exposes no API. It calls:
- `POST https://webservice-uat.mypaymentadmin.com:4005/accountmanagementapiws/services/AccountManagementApiWebServices?wsdl` — Account Management SOAP API
- `POST https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token` — Azure AD (optional)
- `GET/PUT https://graph.microsoft.com/v1.0/...` — Microsoft Graph API (optional)
- `POST https://*.webhook.office.com/...` — Teams webhook (optional)

## Security Posture

### Authentication to External APIs
- Teams Graph API: OAuth2 client-credentials flow using `TEAMS_APP_ID` + `TEAMS_APP_SECRET` → bearer token. Correctly sourced from environment variables.
- Teams webhook: URL-based authentication (webhook URL contains embedded token). Must be kept secret.
- Account Management API: No authentication header observed in `collection.json` — the UAT endpoint appears to accept requests without explicit auth (SOAPAction header only).

### Cryptography
- All HTTP requests in `httpRequest()` are enforced to use HTTPS (`url.protocol !== 'https:'` check at `run-with-report.js:867`).
- Port must be default HTTPS (443); non-standard ports blocked at `run-with-report.js:888`.
- Exception: Newman itself makes the SOAP call via `child_process.exec` — the `httpRequest` security wrapper does not apply to Newman's requests. The SOAP endpoint uses port 4005 (non-standard).

### Host Allowlist
`run-with-report.js` implements a strict host allowlist for its own HTTP calls (lines 827–855):
- `graph.microsoft.com`
- `login.microsoftonline.com`
- `*.webhook.office.com` (suffix match, subdomain required)
- `*.cf.environment.api.powerplatform.com` (suffix match)

This prevents SSRF in the Teams integration code. Newman's external calls are not subject to this allowlist.

### Secrets Management
- All credentials sourced from environment variables — correct.
- No secrets in committed files.

### Known CVE Concerns
- `newman ^6.0.0` — Check for known vulnerabilities in current npm audit; Newman depends on `postman-runtime` which has had CVEs.
- `node:https` built-in — no known CVEs; used correctly.
- `child_process.exec` with user-controlled input: the Newman command is constructed from `config.collection` and `config.dataFile` which are fixed constants (`collection.json`, `countries.csv`) — not user-controlled at runtime. Low risk.

## Technical Debt
| Item | File | Line | Notes |
|---|---|---|---|
| Missing CI workflow | `.github/workflows/postman-tests.yml` | — | Referenced in README, not present |
| Hardcoded endpoint | `collection.json` | 79 | UAT URL; port 4005 non-standard |
| Card number rendered in report | `run-with-report.js` | 189, 244 | `cardNumber` from response included in HTML table — PCI risk |
| Account number in report | `run-with-report.js` | 179, 244 | `accountNumber` rendered plaintext |
| Hardcoded test email | `collection.json` | 71 | `Jeraldin.Gerard@onbe.com` — likely synthetic but committed |
| Hardcoded program ID | `collection.json` | 72 | `04012535` — specific production program |
| Ambiguous collection file | `run-with-report.js:22` vs README | — | Script uses `collection.json`, README says `collectionnew.json` |
| Commented-out channel message POST | `run-with-report.js` | 805–809 | Teams channel message posting is disabled; SharePoint upload occurs but no follow-up message is sent |
| No teardown / account cleanup | — | — | Each test run creates real UAT accounts with no cleanup |

## Gen-3 Migration Requirements
1. If Account Management API migrates to REST, replace SOAP collection with REST Postman requests.
2. Add PAN masking to HTML report: replace card number display with first 6 / last 4 format.
3. Add account number masking or removal from HTML report artifacts.
4. Implement the missing GitHub Actions workflow.
5. Consider moving to a more structured test framework (e.g., Playwright API testing, k6, or REST Assured) for better assertion granularity.

## Code-Level Risks
| Risk | File | Line | Notes |
|---|---|---|---|
| Card PAN in report | `run-with-report.js` | 189 | `cardMatch[1]` written to `cardNumber` variable, rendered at line 244 in HTML `<td>` |
| Account number in report | `run-with-report.js` | 179 | `accountMatch[1]` written to `accountNumber`, rendered at line 244 |
| Newman exit code swallowed | `run-with-report.js` | 132–135 | Non-zero exit from Newman (test failures) logged as warning but does not fail pipeline — HTML generation continues |
| Port 4005 (non-standard HTTPS) | `collection.json` | 84 | Newman allowed to connect; the `httpRequest` wrapper would block this port, but Newman is called via `exec` outside that wrapper |
