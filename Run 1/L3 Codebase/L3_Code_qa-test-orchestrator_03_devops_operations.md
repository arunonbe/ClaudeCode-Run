# 03 DevOps / Operations — qa-test-orchestrator

## Build
No build process. The repository is a pure GitHub Actions orchestration layer. There is no compiled artefact, no Maven/Gradle/npm build, and no Dockerfile.

## Deployment
Not applicable as a standalone deployable. The workflow YAML is consumed directly by the GitHub Actions runtime on manual trigger.

## Config Management
- Single workflow file: `.github/workflows/east-api-smoke-test.yml`
- CODEOWNERS file present at `.github/workflows/CODEOWNERS`; controls who must review changes to the workflow
- Configuration is entirely declarative in YAML; no external config files or environment-specific settings files

## Observability
- Observability is limited to the GitHub Actions UI (per-job logs, step output, pass/fail status)
- No structured log export, no metrics, no alerting configured within this repository
- Child workflow results are reported in the parent run summary but not forwarded to any APM or monitoring platform

## Infrastructure Dependencies
- GitHub Actions SaaS (runner provisioning, secrets management, cross-repo workflow invocation)
- `OnbeEast/qa-api-test-automation` repository (must exist at `@main` and contain matching named workflow files)
- PAT_TOKEN GitHub secret provisioned at the repository or organisation level
- Network connectivity from GitHub-hosted runner to QA/Prod API endpoints

## Operational Risks
- If `qa-api-test-automation@main` workflows are renamed or removed, all jobs in this dispatcher will silently fail to resolve
- No retry logic or timeout configuration; a hanging child workflow will block the run until GitHub's default job timeout
- No notifications on failure; teams must check the Actions tab manually
- Production API calls can be triggered by any user with `write` access to the repository without additional approval gates

## CI/CD
- No CI pipeline for the repo itself (no unit tests, no linting of the YAML)
- Dependabot configuration is absent (`.github/dependabot.yml` not detected in tree)
- All changes to the dispatcher workflow should be reviewed via CODEOWNERS before merge to main
