# om-east-deploy — Solution Architect View

## Solution Design

`om-east-deploy` implements a minimal, composable deployment pipeline. The solution design follows the principle of least logic in the orchestrator: the repo contains only configuration and orchestration glue, delegating implementation details to `om-ci-setup` composite actions and `yq` for config parsing.

## Component Architecture

```
om-east-deploy/
├── .github/workflows/deploy.yml     ← Pipeline definition; only business logic
├── services/
│   └── <name>.yml                   ← Deployment topology declarations (data, not code)
└── README.md                        ← Operational documentation

External Dependencies:
├── Onbe/om-ci-setup (composite action @main)  ← Deployment mechanics
├── maven.pkg.github.com/onbe/onbe_maven_releases  ← Artifact registry
└── mikefarah/yq (v4.44.3)           ← YAML processing tool
```

## Workflow Sequence Design

### Step Composition Analysis

| Step | Tool | Input | Output | Failure Mode |
|---|---|---|---|---|
| Install yq | curl + chmod | yq version | /usr/local/bin/yq | Network unreachable → hard fail |
| Parse service config | yq | services/<name>.yml + env | GITHUB_OUTPUT key-value pairs | Missing file/key → hard fail |
| Set up Java | actions/setup-java | version=21 | JDK + mvn in PATH | Rare; cached |
| Fetch WAR | mvn dependency:copy | Maven coords + settings.xml | ./war-download/<id>.war | Artifact not published → hard fail |
| Deploy WAR | om-ci-setup/windows-war | WAR path + all config | Changed state on server | Windows connectivity issues |
| Deploy summary | bash | GITHUB_OUTPUT + job.status | Step summary markdown | Never fails (if: always()) |

### Data Flow Between Steps

The workflow uses `$GITHUB_OUTPUT` for inter-step data passing. All values extracted by the `Parse service config` step (group_id, artifact_id, packaging, servers, deploy_user, deploy_path, service_name, backup_path, clean_targets, delete_targets, war_name) are accessed downstream as `${{ steps.config.outputs.<field> }}`. This is a clean pattern that avoids environment variable pollution and makes data dependencies explicit.

The WAR path from the `Fetch WAR` step is passed as `${{ steps.fetch.outputs.war_path }}` to the deploy step — a single value thread that links artifact retrieval to artifact deployment.

## Security Design Analysis

### Authentication Architecture

```
GitHub Actions Runner
  ├── GITHUB_TOKEN → Maven settings.xml (read:packages on onbe_maven_releases)
  ├── QA_EAST_DEPLOY_PASSWORD → om-ci-setup composite (Windows DOMAIN\user auth)
  └── PROD_EAST_DEPLOY_PASSWORD → om-ci-setup composite (conditional on env=prod)
```

The Maven `settings.xml` is generated inline at runtime using a `<<'EOF'` heredoc (lines 117-143). The password reference `${env.GITHUB_TOKEN}` uses Maven property interpolation, not shell variable injection — this is secure as Maven reads the environment variable at runtime without it appearing in the XML that might be logged.

However, the step explicitly prints parsed config values to the log (lines 75-85):
```bash
echo "deploy_user=$DEPLOY_USER"
```
`DEPLOY_USER` is `NAM\qa_east_deploy` — not a secret. But if any future config field included sensitive values, this debug logging pattern would expose them. The print block should be reviewed when Phase 2 adds Azure credentials to config parsing.

### Environment Isolation
The conditional credential selection at line 177:
```yaml
DEPLOY_PASSWORD: ${{ inputs.environment == 'prod' && secrets.PROD_EAST_DEPLOY_PASSWORD || secrets.QA_EAST_DEPLOY_PASSWORD }}
```
This GitHub Expressions ternary is evaluated server-side before the workflow run, ensuring the prod secret is only materialized when `environment == 'prod'`.

### Supply Chain Security Gap
The `windows-war` composite action is referenced as `Onbe/om-ci-setup/composite-actions/deploy/windows-war@main`. This is an unpinned reference. If `om-ci-setup` is compromised or accidentally modified, all deployments through this orchestrator are affected. The correct pattern is to pin to a specific commit SHA:
```yaml
uses: Onbe/om-ci-setup/composite-actions/deploy/windows-war@<SHA>
```
This is the single highest-priority supply-chain security improvement for this repo.

## WAR Naming Strategy

At line 162-165, the downloaded WAR is renamed to `<artifact_id>.war`:
```bash
TARGET="./war-download/${{ steps.config.outputs.war_name }}.war"
if [[ "$WAR_FILE" != "$TARGET" ]]; then
  mv "$WAR_FILE" "$TARGET"
fi
```
This is important for Tomcat context path management: Tomcat derives the web application context path from the WAR filename. By normalizing to `<artifact_id>.war`, the solution ensures the context path is always predictable regardless of the version suffix in the downloaded filename.

## Service Config Schema Design Assessment

The YAML schema is well-designed for its Phase 1 scope:

**Strengths:**
- Separation of artifact coordinates from environment-specific topology.
- Optional fields (`backup_path`, `clean_targets`, `delete_targets`) default gracefully via `yq`'s `// ""` and `// []` operators.
- The `rolling:` block is a future extension point that doesn't affect current behavior.

**Weaknesses:**
- No schema validation tooling (JSON Schema, yamllint) is applied to service configs in CI.
- Multi-server deployments list servers as a flat space-separated string after `yq join` (line 67: `SERVERS=$(yq eval "... | join(\" \")" "$CONFIG")`). The consuming composite action must parse this string — if server names contained spaces (unlikely but possible for FQDN aliases), this would break.
- No versioning of the schema itself. If the schema changes incompatibly in the future, older service configs would silently misparse.

## Rolling Deploy Architecture (Phase 2 Design Preview)

The commented config at `services/test-east-deploy.yml` lines 23-35 outlines a rolling deploy:

1. Remove server from Azure App Gateway backend pool (drain existing connections with `drain_timeout_seconds: 60`).
2. Deploy WAR to the drained server.
3. Health-check the server at `/test-east-deploy/health:8080` up to 10 times with 5-second intervals.
4. Re-add server to App Gateway backend pool if health passes.
5. Repeat for next server (subject to `min_healthy_servers: 1` guard).

This is a standard **blue-green within a pool** rolling strategy. The key constraint is that `drain_timeout_seconds` must match the App Gateway Backend HTTP Setting value — this is an operational coupling between infrastructure configuration (Azure App Gateway) and deployment configuration (service YAML), creating a synchronization risk.

## Observations and Recommended Improvements

| Priority | Issue | Recommendation |
|---|---|---|
| Critical | `@main` reference to `om-ci-setup` | Pin to commit SHA; add SHA rotation procedure |
| High | No schema validation for `services/*.yml` | Add yamllint + JSON Schema check in a pre-merge CI workflow |
| High | Debug logging prints deploy_user | Review print block before adding any sensitive config fields |
| Medium | yq downloaded at runtime | Install yq in self-hosted runner image |
| Medium | No deployment notification | Add Teams/Slack notification on deploy success/failure |
| Medium | 90-day default log retention | Export deployment summaries to SIEM for 12-month retention |
| Low | Single environment (uat) in workflow options | Add qa and prod with approval gates |
