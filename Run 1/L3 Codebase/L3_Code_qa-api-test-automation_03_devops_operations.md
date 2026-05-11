# DevOps / Operations — qa-api-test-automation

## Build System
No traditional build system. The repository contains Postman collections (JSON), Postman environments (JSON), GitHub Actions workflows (YAML), and one Node.js script. No Maven, Gradle, or npm build is present at the root level.

The `scripts/generate-encrypted-token.mjs` is a standalone ES module executed via `node` (Node.js 18+, ES modules).

## Deployment
This repo does not deploy a service. It triggers API test executions via GitHub Actions workflows and the Postman/Newman/Pynt CLI tools.

## CI/CD Workflows

The repository contains ~80 GitHub Actions workflow files in `.github/workflows/`. Key patterns:

### Smoke Test Workflows (per-service)
Each service has a dedicated smoke test workflow that calls one of the reusable jobs:

| Reusable Job | File | Purpose |
|---|---|---|
| `postman-smoke-test.yml` | Central reusable workflow | Runs Newman against a Postman collection + environment |
| `postman-smoke-test-with-certs.yml` | Reusable workflow | Same with mTLS certificates |
| `postman-reusable-job.yml` | Alternate reusable | Postman CLI-based execution |

### Security Test Workflows
| Workflow | File | Tool |
|---|---|---|
| Pynt security scan | `pynt-security-scan.yml`, `pynt-*.yml` | Pynt DAST security scanner |
| Certificate Pynt | `pynt-security-test-with-certs.yml` | Pynt with mTLS |
| Account Management security | `account-management-api-security.yml` | Pynt |

### Trigger Patterns
- `workflow_dispatch` — manual trigger with environment selection
- `push` to `main` — auto-trigger on collection updates
- `schedule` — some workflows have cron schedules (not visible in files read)

### Environment Selection
Workflows accept environment inputs (`qa`, `stg`, `prod`) and pass the corresponding environment file to Newman/Postman.

## Configuration Management

| Parameter | Source | Notes |
|---|---|---|
| API endpoint base URLs | Postman environment files | Per-environment JSON |
| Authentication tokens/keys | Postman environment files or GitHub Secrets | Secrets preferred for sensitive values |
| Encryption key (Decagon) | `DECAGON_ENCRYPTION_KEY_BASE64` GitHub Secret | 32-byte base64 |
| mTLS certificates | GitHub Secrets | Injected at runtime |
| Postman CLI / Newman version | Managed by reusable workflow in `om-ci-setup` | Not visible in this repo |

## Observability

| Signal | Mechanism |
|---|---|
| Test execution results | Newman/Postman CLI output in GitHub Actions logs |
| Test report artefacts | HTML/JSON reports uploaded as GitHub Actions artefacts |
| Failure notifications | Workflow failure emails via GitHub Actions |
| No centralised test dashboard | Results are per-run in GitHub Actions; no Allure, TestRail, or similar integration visible |

## Infrastructure Dependencies

| Dependency | Purpose |
|---|---|
| GitHub Actions (hosted runners) | Workflow execution environment |
| Newman CLI / Postman CLI | Postman collection runner |
| Pynt | DAST API security scanner |
| Target API environments | QA, STG, PROD API endpoints under test |
| GitHub Secrets | Sensitive credential storage |
| `om-ci-setup` reusable workflows | Shared CI job definitions |
| Node.js | For `generate-encrypted-token.mjs` script |

## CODEOWNERS
`.github/CODEOWNERS` exists — PR review assignments configured. Specific ownership not read but ensures change control on test collections.

## Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| PROD environment files in version control — tests running against production | High | Collections with PROD environments may inadvertently mutate production data |
| ~80 workflow files with limited cross-referencing — maintenance burden | Medium | Each service manages its own workflow; duplication and drift likely |
| No centralised test result storage | Medium | Test history limited to GitHub Actions 90-day artefact retention |
| Wirecard-domain environment files — legacy systems may no longer exist | Medium | `webservice.wirecard.com.json`, `p-app01.nam.wirecard.sys.json` |
| `generate-encrypted-token.mjs` requires exact 32-byte key | Medium | Misconfigured key will throw at runtime; clear error message present |
| Security scan workflows (Pynt) — no SLA on findings remediation visible | Medium | DAST findings must feed into a remediation process |
| No secrets scanning workflow in this repo | High | Should add `trufflehog` or similar to detect committed credentials |

## CI/CD Pipeline Summary (representative)

```
Service change deployed
  --> {service}-smoke.yml triggered (workflow_dispatch or push)
      --> postman-smoke-test.yml (reusable)
          Newman run: collection={service}.json env={environment}.json
          --> Pass/Fail in GitHub Actions log
          --> HTML report uploaded as artefact

Security scan (manual or scheduled)
  --> pynt-{service}.yml
      --> Pynt DAST scan against deployed endpoint
          --> Security findings in GitHub Actions log
```
