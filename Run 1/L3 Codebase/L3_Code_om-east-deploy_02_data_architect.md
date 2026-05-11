# om-east-deploy — Data Architect View

## Overview

`om-east-deploy` does not own persistent application data. Its data assets are the declarative YAML configuration files, GitHub Actions workflow state, and deployment audit records captured in GitHub workflow run summaries. From a data architecture perspective this repo is a **configuration-as-data** system: the YAML service definitions are the primary data model, and their schema governs operational behavior.

## Primary Data Model — Service Configuration Schema

### Canonical Schema (from `services/test-east-deploy.yml`)

```
artifact:
  group_id:    String   — Maven groupId; namespaces the artifact in GitHub Packages
  artifact_id: String   — Maven artifactId; identifies the deployable unit
  packaging:   Enum     — war | jar | ear

environments:
  <env_name>:           — free key; maps to a GitHub Environment for approval gating
    servers:  List<FQDN>  — one or more target Windows hostnames
    deploy_user: String   — DOMAIN\account format; Windows impersonation identity
    deploy_path: String   — UNC/local path on target server for WAR drop
    service_name: String  — Windows Service Manager display name
    backup_path: String?  — optional; path for pre-deploy backup copy
    clean_targets: List<String>?  — directories to empty before deployment
    delete_targets: List<String>? — directories/files to remove entirely
    rolling:              — optional Phase 2 block
      subscription_id: UUID
      gateway_resource_group: String
      gateway_name: String
      backend_pool_name: String
      drain_timeout_seconds: Integer
      min_healthy_servers: Integer
      health_check:
        path: String      — HTTP path for health probe
        port: Integer
        expected_status:  Integer
        retries: Integer
        retry_interval_seconds: Integer
```

### Data Flow During a Deployment

1. **Input** — GitHub Actions receives `service`, `version`, and `environment` from `workflow_dispatch` (`.github/workflows/deploy.yml` lines 8-20).
2. **Config Parse** — `yq` (v4.44.3, installed at runtime) reads `services/<service>.yml` and extracts typed values into `$GITHUB_OUTPUT` step outputs (lines 63-99).
3. **Artifact Resolution** — Maven coordinates (group:artifact:version:packaging) are assembled into a dependency copy command. The resulting WAR file is written to `./war-download/<artifact_id>.war` (lines 148-167).
4. **Deploy Action Invocation** — the `windows-war` composite action (`Onbe/om-ci-setup`) consumes the WAR path and all config values. The actual filesystem state change happens on target servers over SMB/WinRM (inferred from Windows deploy_path patterns like `D:\c-base\opt\tomcat\...`).
5. **Audit Record** — a Markdown summary is appended to `$GITHUB_STEP_SUMMARY` (lines 185-198) capturing service, version, environment, servers, deployment path, and final status. This record is immutable in GitHub and satisfies change-management evidence requirements.

## Artifact Data Lineage

```
Service Repo (e.g., om-payment-api)
  └─ Maven build → GitHub Packages (maven.pkg.github.com/onbe/onbe_maven_releases)
       └─ om-east-deploy workflow fetches via PAT_TOKEN_PACKAGE
            └─ WAR copied to target Windows server at deploy_path
                 └─ Apache Tomcat loads WAR → runtime application
```

The artifact registry is `maven.pkg.github.com/onbe/onbe_maven_releases`, which functions as the authoritative binary registry. Deployment immutability is guaranteed by Maven version coordinates — once a release version is published to GitHub Packages it cannot be overwritten (SNAPSHOT versions are mutable and should only target non-production environments).

## Configuration Data Governance

### Schema Validation
There is no explicit schema validation of `services/*.yml` files at commit time. The parse step in `deploy.yml` (lines 53-59) performs existence checks: if `services/<service>.yml` does not exist, or if the requested environment key is absent in the file, the workflow exits with an error. This is reactive validation (at deploy time) rather than proactive validation (at PR merge time).

**Gap**: No pre-commit or CI schema check validates that a new `services/*.yml` conforms to the required schema before the first deployment attempt. A malformed config would only fail at deploy time, potentially during a time-sensitive production change.

### Sensitive Data in Configuration Files
The `test-east-deploy.yml` file (lines 24-35) contains commented-out Azure infrastructure identifiers:
- Subscription ID: `f409c36e-affb-495d-93fd-e2cfab1a7faf`
- Resource group: `rg-az1-uat-ecount-001`
- App Gateway: `agw-az1-uat-ecount-002`

These are infrastructure topology identifiers. While not credentials, they constitute internal network topology metadata. In a PCI DSS environment, such data should not be stored in a Git-tracked file without access controls. The repo should have appropriate visibility restrictions (confirmed private given GitHub Enterprise org context).

### Credential Data Model
Secrets referenced in the workflow:
- `PAT_TOKEN_PACKAGE` — repo-level secret; `read:packages` scope on GitHub Packages.
- `QA_EAST_DEPLOY_PASSWORD` — org-level secret; Windows domain credential for UAT/QA.
- `PROD_EAST_DEPLOY_PASSWORD` — org-level secret; Windows domain credential for production.
- `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` — org-level secrets for Phase 2 Azure API calls.

The conditional in line 177 (`inputs.environment == 'prod' && secrets.PROD_EAST_DEPLOY_PASSWORD || secrets.QA_EAST_DEPLOY_PASSWORD`) ensures credential scoping by environment, which is correct. However, the `||` short-circuit in GitHub Expressions means QA_EAST_DEPLOY_PASSWORD is also passed when environment is not `prod` — this is correct behavior but should be documented clearly.

## Data Retention and Auditability

- GitHub Actions workflow runs are retained per GitHub's retention policy (configurable, default 90 days for logs). The immutable step summary is the primary audit evidence for each deployment.
- For PCI DSS compliance, deployment audit records should be retained for at minimum 12 months. If GitHub's log retention is shorter, an external export mechanism (e.g., shipping workflow summaries to a SIEM) is needed.
- There is no database or persistent store in this repo; all state lives in GitHub.

## Inter-System Data Interfaces

| Interface | Direction | Protocol | Data |
|---|---|---|---|
| GitHub Packages (Maven) | Inbound | HTTPS / Maven | WAR artifact binary |
| GitHub Actions secrets | Inbound | GitHub encrypted secrets | Credentials |
| `om-ci-setup` composite action | Outbound | GitHub Actions calls | WAR path + config values |
| Target Windows servers | Outbound | SMB/WinRM (via composite action) | WAR file + service control commands |
| Azure App Gateway API | Outbound (Phase 2) | HTTPS / Azure REST API | Backend pool drain/restore commands |
