# SprintCrushers_Automation — DevOps / Operations View

## Build System
- **Runtime**: Node.js ≥16.0 (v24 recommended per LOCAL_SETUP.md)
- **Package manager**: npm
- **Entry point**: `run-with-report.js` (invoked via `npm test`)
- **Dependencies** (`package.json`):
  - `newman ^6.0.0` (devDependency — used for CLI collection execution via `npx`)
  - No production runtime dependencies

## CI/CD Pipeline
The `LOCAL_SETUP.md` references a GitHub Actions workflow at `.github/workflows/postman-tests.yml` but this file was not present in the repository at analysis time. The `run-with-report.js` script contains detection logic for:
- GitHub Actions environment variables (`GITHUB_ACTIONS`, `GITHUB_RUN_ID`, `GITHUB_REPOSITORY`)
- Azure DevOps environment variables (`BUILD_BUILDID`, `TF_BUILD`, `SYSTEM_TEAMPROJECT`, `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI`)

This indicates the suite is designed to run in either CI environment with appropriate URL generation for Teams notifications.

**Trigger**: Per LOCAL_SETUP.md — any push to `main` or pull request triggers the GitHub Actions workflow.

## Deployment
This is not a deployed application. The test runner produces artifacts:
1. `detailed-responses.json` — raw results
2. `newman-detailed-table-report.html` — HTML report
3. `gh-pages/index.html` — GitHub Pages copy

The `gh-pages/index.html` is the public-facing artifact published to GitHub Pages.

## Configuration Management
All sensitive configuration is passed via environment variables (none committed):

| Variable | Purpose | Required |
|---|---|---|
| `HTTP_TIMEOUT_MS` | HTTP request timeout in ms (default 30000) | Optional |
| `TEAMS_WEBHOOK_URL` | Teams Incoming Webhook URL | Optional |
| `REPORT_URL` | Public URL for hosted HTML report | Optional |
| `TEAMS_TENANT_ID` | Azure AD tenant ID for Graph API auth | Optional (file upload) |
| `TEAMS_APP_ID` | Azure AD app (client) ID | Optional (file upload) |
| `TEAMS_APP_SECRET` | Azure AD app client secret | Optional (file upload) |
| `TEAMS_TEAM_ID` | Teams team ID | Optional (file upload) |
| `TEAMS_CHANNEL_ID` | Teams channel ID | Optional (file upload) |
| `GITHUB_TOKEN` | Implicitly available in GitHub Actions | CI |

The API endpoint URL is hardcoded in `collection.json`: `https://webservice-uat.mypaymentadmin.com:4005/accountmanagementapiws/services/AccountManagementApiWebServices?wsdl`.

## Observability
- Console output provides step-by-step progress with labelled stages.
- HTML report provides per-iteration success/failure/incomplete breakdown.
- Teams Adaptive Card notification provides summary stats on completion.
- No structured logging, no metrics export, no alerting beyond Teams webhook.

## Infra Dependencies
| Dependency | Type | Notes |
|---|---|---|
| `webservice-uat.mypaymentadmin.com:4005` | External API (UAT) | Account Management SOAP API — must be reachable from CI runner |
| `graph.microsoft.com` | External API | Teams file upload (optional) |
| `login.microsoftonline.com` | External API | Azure AD token acquisition (optional) |
| `*.webhook.office.com` | External API | Teams Incoming Webhook (optional) |
| GitHub Pages | Hosting | HTML report publishing |

## Operational Risks
| Risk | Severity | Notes |
|---|---|---|
| Missing GitHub Actions workflow file | High | `.github/workflows/postman-tests.yml` referenced in README but not present — CI pipeline does not exist |
| Hardcoded UAT endpoint | Medium | Tests always hit UAT; cannot target prod without modifying `collection.json` |
| `npm test` exits 0 even with test failures | Medium | Newman exits non-zero on assertion failures but `run-with-report.js` continues; pipeline may show green with failed tests |
| HTML report published with financial data | High | `gh-pages/index.html` with account/card numbers could be publicly visible |
| No test isolation | Low | Tests create real accounts in UAT on each run; no cleanup/teardown |
| `collectionnew.json` vs `collection.json` | Low | Two collection files present; README references `collectionnew.json` but `run-with-report.js` defaults to `collection.json` — ambiguity |
