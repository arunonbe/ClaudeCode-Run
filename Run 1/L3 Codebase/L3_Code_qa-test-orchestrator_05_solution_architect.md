# 05 Solution Architect — qa-test-orchestrator

## Technical Architecture
Single-file GitHub Actions dispatcher. No application runtime, no build artefacts. The architecture consists of:
- One manually-triggered workflow (`east-api-smoke-test.yml`) with conditional job fan-out
- Ten child jobs, each referencing a named reusable workflow in `OnbeEast/qa-api-test-automation@main`
- Two runtime inputs: `environment_type` (choice: qa | prod) and `application` (choice: all | named API)

## API Surface
None. This repository exposes no HTTP API, library API, or CLI. Its only interface is the GitHub Actions `workflow_dispatch` event.

## Security Posture
- **PAT_TOKEN** is the primary security control; its scope and rotation policy should be audited
- No branch protection rules visible in the repository files; changes to the workflow should require at least one approval via CODEOWNERS
- Production environment is reachable without an additional approval gate — **medium risk** for a payments environment
- No secret scanning or CodeQL workflow configured within this repo (CodeQL absent from `.github/workflows`)

## Technical Debt
- All child workflow references are pinned to `@main` (floating ref); a breaking change upstream will silently fail at runtime rather than being caught at definition time — should be pinned to SHA or version tag
- New API onboarding requires manual YAML edits; no templating or code generation
- No timeout or retry settings on any job
- No test result reporting beyond ephemeral GitHub UI

## Gen-3 Migration
This repository is already Gen-3 compatible (GitHub Actions, cloud-hosted runners, no on-premises dependencies). Recommended improvements:
- Pin child workflow refs to a specific SHA or release tag
- Add a production approval/environment gate using GitHub Environments with required reviewers
- Integrate test result export to a reporting platform (e.g., Allure, Azure Test Plans)
- Add a YAML linting step (e.g., `actionlint`) as a pre-merge check

## Code-Level Risks
- `PAT_TOKEN` passed as a secret to reusable workflows is standard practice, but the token scope should be minimised to `actions:read` and specific repos only
- `secrets: inherit` is not used (explicit `PAT_TOKEN` pass-through is correct); however, if additional secrets are needed for a new API, the dispatcher file must be updated
- No input validation on `application` beyond the choice list; GitHub enforces the enum, mitigating injection risk
