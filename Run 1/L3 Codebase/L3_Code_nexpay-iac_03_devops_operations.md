# DevOps / Operations View — nexpay-iac

## Build System

`nexpay-iac` is an **Infrastructure as Code repository** — it does not produce application artifacts. The "build" is a Terraform plan/apply cycle.

| Attribute | Value |
|---|---|
| IaC tool | Terraform >= 1.0 (pinned to `1.14.3` in deployment workflow) |
| Providers | `azurerm ~> 4.0`, `azurecaf ~> 1.2`, `azapi ~> 2.0` |
| Backend | Azure Blob Storage (remote state) |
| State storage | `sanexpaytfstorage{env}` storage account, `tfstate-{env}` container |
| Environments | QA only (no `dev`, `staging`, or `prod` tfvars defined) |
| Modules | `app-config`, `container-app-job`, `container-apps`, `container-apps-environment`, `key-vault`, `postgresql-database`, `storage-account` |

## CI/CD Pipelines

### Workflow Architecture (Four-Workflow Pattern)

| Workflow | Trigger | Purpose |
|---|---|---|
| `terraform-qa-orchestrator.yml` | Manual dispatch | Orchestrates the full plan → confirm → deploy sequence |
| `terraform-qa-validate-plan.yml` | Called by orchestrator | Runs `terraform init` + `terraform plan` + posts plan summary to GitHub |
| `terraform-qa-deploy.yml` | Called by orchestrator with `confirm_deploy == "deploy"` | Runs `terraform apply`, triggers PostgreSQL role setup job |
| `terraform-qa-destroy.yml` | Manual dispatch | Destroys QA infrastructure (`terraform destroy`) |

**Safety gate**: The deploy workflow requires `confirm_deploy == "deploy"` input to proceed. This prevents accidental applies from partial workflow triggers.

### Service Deployment Workflow (`java-build-deploy-aca.yml`)

This workflow is the **shared CI/CD template** consumed by all NexPay application services:
- Reads Java version from `pom.xml`
- Runs `mvn clean verify`
- CodeQL analysis
- Docker build + push to ACR
- Deploys to ACA (QA then prod, sequential)
- Optionally publishes OpenAPI spec to APIM

It resolves `AZURE_CLIENT_ID` and `AZURE_APP_CONFIG_ENDPOINT` at deploy time via `az containerapp show` and `az appconfig show` — the Container App must already exist (provisioned by Terraform) before this workflow runs.

### Supporting Workflows

| Workflow | Purpose |
|---|---|
| `app-config-update.yml` | Update App Configuration values (non-Terraform) |
| `app-config-call.yml` | Called variant of app-config-update |
| `appconfig-apply.yml` | Applies App Configuration changes |
| `redeploy-aca.yml` | Redeploy an existing Container App image (no rebuild) |
| `sync-secrets-to-kv.yml` | Syncs secrets from `kv-secrets.json` to Azure Key Vault |

## Configuration Management

### Terraform Variable Strategy

Environment-specific configuration is entirely in `terraform/environments/qa.tfvars`. There is no `prod.tfvars` — production is not yet defined in IaC.

### Secret Synchronisation

`kv-secrets.json` (`infra/kv-secrets.json`) lists all secrets to be loaded into Key Vault. The `sync-secrets-to-kv.yml` workflow reads this file and upserts secrets. The actual secret values are stored as GitHub Secrets (`secrets.DYNATRACE_API_TOKEN`, etc.) and resolved at workflow runtime — they are never committed to the repository.

**Note**: The Dynatrace API token follows a different path — it is injected as `TF_VAR_dynatrace_api_token` at Terraform apply time and written directly into the Container Apps Environment OTel header configuration. This means it may be stored in the Terraform state file (`terraform_outputs.json` artifact uploaded to GitHub Actions for 15 days).

### Container App Configuration Pattern

Each service receives the following environment variables from the deploy workflow:
- `ENVIRONMENT` — `qa` or `prod`
- `APP_NAME` — container app name
- `AZURE_CLIENT_ID` — managed identity client ID (resolved from Container App identity)
- `AZURE_APP_CONFIG_ENDPOINT` — App Configuration endpoint
- `AZURE_APP_CONFIG_ENABLED=true`
- `SPRING_CLOUD_BOOTSTRAP_ENABLED=true`

Service-specific configuration is loaded from Azure App Configuration using the service's `spring.application.name` as the key prefix.

## Observability Infrastructure

### OpenTelemetry at ACA Environment Level

OTel is configured at the Container Apps Environment level (not per-app):
```hcl
open_telemetry_configuration = {
  enabled = true
  otlp_configurations = [{
    name     = "dynatrace"
    endpoint = "https://dpv87776.live.dynatrace.com/api/v2/otlp"
    headers  = [{ key = "Authorization", value = "Api-Token ${dynatrace_api_token}" }]
  }]
  logs_destinations    = ["dynatrace"]
  metrics_destinations = ["dynatrace"]
  traces_destinations  = ["dynatrace"]
}
```

All 11 Container Apps inherit this OTel configuration from the environment. Individual services configure their own OTel SDK settings in application YAML, but the environment-level OTLP sink ensures even services without SDK-level OTel send sidecar-level telemetry to Dynatrace.

### PostgreSQL Monitoring

The PostgreSQL module (`postgresql_monitoring.tf`) provisions monitoring configuration. `log_connections` and `log_disconnections` are enabled as PostgreSQL server parameters — connections are logged at the database level.

## Infrastructure Dependencies

| Resource | Provider | Purpose |
|---|---|---|
| Azure Container Registry (`acraz1clusterqass.azurecr.io`) | External (shared, not managed by this repo) | Container image storage |
| Azure Container Apps Environment | This repo | NexPay service runtime |
| Azure PostgreSQL Flexible Server | This repo | Service databases |
| Azure Key Vault (`kv-nexpay-qa`) | This repo | Secrets store |
| Azure App Configuration (`appcg-nexpay-qa`) | This repo | Runtime config store |
| Azure VNet (10.60.0.0/20) | This repo | Network isolation |
| eCount spoke VNet | External (eCount team) | Legacy DB connectivity via peering |
| Dynatrace SaaS | External | Observability backend |
| GitHub Actions (ubuntu-latest) | GitHub | CI/CD runners |

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| No prod environment defined in IaC | Critical | Production infrastructure is not managed by this Terraform repo — unknown state |
| Key Vault purge protection disabled | High | `key_vault_purge_protection_enabled = false` — accidental KV deletion is irreversible |
| App Config public network access | High | `app_config_public_network_access = "Enabled"` — accessible from internet |
| Terraform state in `terraform_apply.log` artifact | Medium | 15-day retention, includes `DYNATRACE_API_TOKEN` via TF_VAR |
| Single QA environment | Medium | All developers use same environment; coordination required |
| Container App Jobs timeout in VNet | Medium | Jobs disabled due to VNet timeout issues — admins cannot run one-off operational tasks |
| Free tier App Config in QA | Low | 1 req/sec limit; private endpoint not available |
| PostgreSQL 18 beta risk | Low | PostgreSQL 18 is not yet GA — QA uses a pre-release database engine |
