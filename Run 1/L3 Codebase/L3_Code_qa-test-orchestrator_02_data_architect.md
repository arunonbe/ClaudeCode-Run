# 02 Data Architect — qa-test-orchestrator

## Data Stores
None. The repository contains only GitHub Actions YAML workflow files and a README. No application code, no databases, no file system I/O.

## Schema / Tables
Not applicable.

## Sensitive Data
- **PAT_TOKEN** GitHub secret is the only sensitive artefact. It is referenced in the workflow as `${{ secrets.PAT_TOKEN }}` and passed to child workflows; it is never logged or written to files.
- Test payloads used by the downstream `qa-api-test-automation` workflows may contain synthetic account numbers or API credentials — those are out of scope for this repository.

## Encryption
- GitHub-managed encrypted secrets for PAT_TOKEN storage
- HTTPS transport enforced for all GitHub API calls implicitly by the Actions runner

## Data Flow
```
Operator (GitHub UI)
  --> workflow_dispatch (environment_type, application)
  --> east-api-smoke-test.yml (this repo)
      --> OnbeEast/qa-api-test-automation/<app>-smoke.yml@main (reusable workflow, cross-repo)
          --> API under test (QA or Prod endpoint)
          --> Test results (GitHub Actions job summary only — not persisted)
```

## Quality / Retention
- No test result artefacts are stored or archived; run history is subject to GitHub's default retention (90 days for public, configurable for private repos)
- No data quality controls; entirely dependent on downstream test definitions

## Compliance Gaps
- No explicit test-result archiving for audit evidence (SOC 2 control gap)
- No separation between who can trigger QA vs. production runs; RBAC gap
- No record of production smoke-test executions beyond ephemeral GitHub Actions logs
