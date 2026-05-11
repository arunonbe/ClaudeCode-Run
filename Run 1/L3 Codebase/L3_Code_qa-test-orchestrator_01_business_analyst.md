# 01 Business Analyst — qa-test-orchestrator

## Business Purpose
Centralised GitHub Actions orchestration layer for Onbe East QA automation. Provides a single entry point to trigger smoke test suites across all East-region APIs from either a QA or production environment, replacing per-repo manual test execution.

## Capabilities
- On-demand, manually triggered API smoke-test execution via `workflow_dispatch`
- Selective or bulk execution: run all applications or a single named application
- Environment selection (qa / prod) at trigger time
- Reuse of test workflow definitions stored in the `qa-api-test-automation` repository via reusable workflow calls

## Entities
- **Application**: one of ten named East APIs (accept-prechecks, account-management-api, card-notification-restful, clientapi, cs-api-v1, cs-api-v3, customer-service-rest-api, debit-api, ivr-ws, manage-payment-rest-api)
- **Environment**: qa | prod
- **PAT_TOKEN**: GitHub Personal Access Token secret enabling cross-repo workflow invocation

## Business Rules
- Tests may only be triggered manually; no automated schedule or push triggers exist
- Environment type defaults to `qa`; explicit selection required to target production
- All individual API jobs share the same PAT_TOKEN secret
- Each API job is conditional on the `application` input matching its name or being `all`

## Flows
1. Operator selects environment and application in the Actions UI
2. Dispatcher workflow fans out to matching per-API reusable workflow(s) in `qa-api-test-automation`
3. Each child workflow runs its Postman / Playwright smoke collection
4. Results appear in the GitHub Actions run summary

## Compliance
- No cardholder data processed; repo contains no source code, only workflow YAML
- PAT_TOKEN should be scoped to the minimum required repo/workflow permissions (least-privilege principle)
- Production environment smoke tests carry UDAAP risk if they trigger state-changing operations; confirm tests are read-only before enabling prod runs

## Risks
- No automated gating: production can be targeted any time by any workflow-dispatch actor with repo write access
- No artifact retention or test-result archiving configured
- Single workflow file; adding new APIs requires manual YAML edits with no automated registration
- No CODEOWNERS enforcement on who may trigger production smoke runs
