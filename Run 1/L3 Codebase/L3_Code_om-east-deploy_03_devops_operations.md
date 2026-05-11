# om-east-deploy — DevOps / Operations View

## Infrastructure Overview

`om-east-deploy` targets a traditional Windows-hosted Tomcat deployment estate. Services are deployed as WAR files to Apache Tomcat instances running on Windows servers in the `nam.wirecard.sys` domain. The deployment orchestrator is GitHub Actions hosted on `ubuntu-docker` runners, which reach Windows targets through the `om-ci-setup` composite actions.

## Workflow Architecture

### Trigger Model
The workflow (`.github/workflows/deploy.yml`) is triggered exclusively via `workflow_dispatch` — manual human initiation. This is intentional Phase 1 design (README.md line 93). Future phases will add `workflow_run` for automatic SNAPSHOT-to-QA promotion (Phase 4).

### Concurrency Control
The workflow implements concurrency locking at line 21-24:
```yaml
concurrency:
  group: deploy-${{ inputs.service }}-${{ inputs.environment }}
  cancel-in-progress: false
```
`cancel-in-progress: false` means a second deployment of the same service+environment combination will queue rather than cancel the running deploy. This is the correct behavior for deployment workflows — cancelling mid-flight deployments risks leaving servers in inconsistent states.

### Runner Requirements
`runs-on: ubuntu-docker` (line 28) — this is a self-hosted or org-registered runner, not the standard `ubuntu-latest` GitHub-hosted runner. This implies a self-hosted runner pool is maintained, which requires patching and lifecycle management.

## Deployment Pipeline Steps

1. **Checkout** (`actions/checkout@v4`) — checks out the orchestrator repo.
2. **Install yq** — downloads `yq` v4.44.3 binary from GitHub releases at runtime (lines 38-43). This is a network dependency; if GitHub is unreachable, deploys fail. Pinning to a specific version is good practice.
3. **Parse Service Config** — reads `services/<name>.yml` and extracts all deployment parameters into step outputs.
4. **Set up Java 21** (`actions/setup-java@v4` with Temurin distribution) — required for Maven dependency resolution only, not for runtime.
5. **Fetch WAR** — uses `maven-dependency-plugin:3.6.1:copy` to pull the artifact from GitHub Packages. The settings.xml is generated inline using a heredoc (lines 117-143); the `GITHUB_TOKEN` is injected via environment variable, not written to disk in cleartext.
6. **Deploy WAR to Windows** — delegates to `Onbe/om-ci-setup/composite-actions/deploy/windows-war@main`. The reference to `@main` means the composite action is not pinned by commit SHA, creating a supply-chain risk: a change to `om-ci-setup` main branch takes effect on the next deploy without any review in this repo.
7. **Deploy Summary** — always runs (`if: always()`) and writes a markdown summary to `$GITHUB_STEP_SUMMARY`.

## Target Server Configuration (from `test-east-deploy.yml`)

| Parameter | Value |
|---|---|
| UAT Server 1 | `u-app01.nam.wirecard.sys` |
| UAT Server 2 | `u-app02.nam.wirecard.sys` |
| Deploy User | `NAM\qa_east_deploy` |
| Deploy Path | `D:\c-base\opt\tomcat\servers\TestEastDeploy\webapps` |
| Service Name | `Apache Tomcat - TestEastDeploy` |
| Backup Path | `D:\c-base\backup` |
| Clean Targets | webapps and work directories |

Servers follow `u-` (UAT) prefix naming convention, suggesting production servers would follow `p-` or similar convention. All servers are in the `nam.wirecard.sys` domain — a legacy Wirecard domain, indicating the infrastructure predates the Onbe rebranding.

## Health Check Model (Phase 2 Preview)

The commented-out `rolling:` block defines a health check pattern:
```yaml
health_check:
  path: /test-east-deploy/health
  port: 8080
  expected_status: 200
  retries: 10
  retry_interval_seconds: 5
```
This provides up to 50 seconds of retry budget post-deployment. The `drain_timeout_seconds: 60` must match the App Gateway Backend HTTP Setting connection-draining timeout — a misconfiguration here would cause in-flight requests to be dropped.

`min_healthy_servers: 1` means the rolling deploy will abort if draining a node would leave fewer than 1 healthy server in the backend pool — protecting against total outage during deploy.

## Secrets and Credential Management

### Secret Hierarchy
- **Org-level secrets**: `QA_EAST_DEPLOY_PASSWORD`, `PROD_EAST_DEPLOY_PASSWORD` — centrally managed, available to this repo via the conditional grant.
- **Repo-level secrets**: `PAT_TOKEN_PACKAGE`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

### Credential Separation by Environment
```yaml
DEPLOY_PASSWORD: ${{ inputs.environment == 'prod' && secrets.PROD_EAST_DEPLOY_PASSWORD || secrets.QA_EAST_DEPLOY_PASSWORD }}
```
This ternary ensures production credentials are never used in non-production deployments. The pattern is correct.

## Operational Runbook Notes

### Normal Deployment Flow
1. Navigate to the `om-east-deploy` repo Actions tab.
2. Select the "Deploy" workflow.
3. Click "Run workflow", supply `service` (e.g., `test-east-deploy`), `version` (e.g., `1.0.0`), `environment` (`uat`).
4. Approve the environment deployment if prompted (requires East Deploy Team membership).
5. Monitor workflow steps; check Deploy Summary on completion.

### Break-Glass Procedure
If `om-east-deploy` is unavailable:
- Locate the deprecated `cicd-deployment.yml` workflow in the service repo (if still present).
- Trigger directly from the service repo's Actions tab.
- Document the manual deployment in the change management system.

### Failure Modes

| Failure | Symptom | Resolution |
|---|---|---|
| Service config not found | Step 2 exits with `::error::Service config not found` | Create `services/<name>.yml` |
| Environment not in config | Step 2 exits with `::error::Environment '<env>' not defined` | Add environment block to service YAML |
| No WAR in GitHub Packages | Step 4 exits: `No WAR file downloaded` | Trigger build in service repo first |
| Windows deploy failure | Step 5 fails (composite action error) | Check Windows service status, disk space, server connectivity |
| yq download fails | Step 1 fails with network error | Retry; or pre-install yq on self-hosted runner image |

## Supply Chain Risk Assessment

1. **`@main` reference to `om-ci-setup`**: The composite action is pinned to the `main` branch HEAD, not a commit SHA. Any push to `om-ci-setup/main` immediately affects all future deployments. This is a supply-chain vulnerability — a compromised or inadvertent change to `om-ci-setup` could alter deployment behavior without review in `om-east-deploy`. **Recommendation**: pin to a commit SHA or a signed tag.
2. **yq downloaded from internet at runtime**: `curl` fetches `yq_linux_amd64` from GitHub releases each time (lines 38-43). This introduces latency and a network dependency. Embedding `yq` in the runner image would be more robust.
3. **Maven settings.xml generated inline**: The settings.xml is created in `.m2/settings.xml` within the workspace and references `${env.GITHUB_TOKEN}`. This is correct Maven property substitution. The file is not committed to the repo and exists only for the duration of the workflow run.

## Monitoring and Alerting Gaps

- There is no post-deployment smoke test beyond the Phase 2 health-check model.
- There is no notification mechanism (Slack, Teams, email) on deployment success or failure — operators must monitor GitHub Actions UI directly.
- No metrics are emitted to an observability platform from the deployment workflow itself.
