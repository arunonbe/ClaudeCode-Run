# Solution Architect View — nexpay-iac

## Technical Architecture

`nexpay-iac` is a **Terraform monorepo** using a modular architecture. All modules are local (not from Terraform Registry), enabling tight version control.

### Repository Structure

```
nexpay-iac/
├── terraform/
│   ├── main.tf                         ← Provider config, Key Vault, App Config modules
│   ├── locals.tf                       ← Derived locals (resource names, tags)
│   ├── variables.tf                    ← Variable declarations
│   ├── outputs.tf                      ← Outputs (resource IDs, endpoints)
│   ├── networking.tf                   ← VNet, subnets, peering, private DNS
│   ├── container_apps_integration.tf   ← ACA Environment + Apps + role assignments
│   ├── container_app_jobs.tf           ← Container App Jobs (currently disabled)
│   ├── postgresql_integration.tf       ← PostgreSQL server, databases, users, role setup job
│   ├── environments/
│   │   └── qa.tfvars                   ← QA environment values
│   └── modules/
│       ├── app-config/                 ← Azure App Configuration
│       ├── container-app-job/          ← Container App Job
│       ├── container-apps/             ← Container Apps (multiple, from map)
│       ├── container-apps-environment/ ← ACA Environment with OTel
│       ├── key-vault/                  ← Key Vault + RBAC
│       ├── postgresql-database/        ← PostgreSQL + monitoring + security
│       └── storage-account/            ← Terraform state storage
├── scripts/
│   ├── terraform-apply.ps1
│   ├── terraform-destroy.ps1
│   └── terraform-plan.ps1             ← PowerShell scripts for local execution
└── .github/workflows/
    ├── java-build-deploy-aca.yml       ← Shared ACA deployment template (consumed by all services)
    ├── terraform-qa-orchestrator.yml   ← IaC orchestration workflow
    ├── terraform-qa-validate-plan.yml
    ├── terraform-qa-deploy.yml
    ├── terraform-qa-destroy.yml
    ├── app-config-*.yml                ← App Configuration management
    ├── sync-secrets-to-kv.yml          ← KV secret synchronisation
    └── redeploy-aca.yml                ← ACA redeployment
```

## Key Design Decisions

### 1. Internal Load Balancer Only

```hcl
internal_load_balancer_enabled = true
```

The Container Apps Environment uses an internal load balancer — no Container App has a public IP. External access is controlled via ingress rules (`external_enabled`) on individual Container Apps, routed through APIM. This is the correct architecture for a PCI DSS environment.

Three Container Apps are external-facing: `recipientweb-bff`, `ivr-bff`, `clientadminweb-bff`. All others are internal-only.

### 2. PostgreSQL VNet Integration (Not Private Endpoint)

```hcl
enable_vnet_integration = true
enable_private_endpoint = false
```

PostgreSQL uses VNet integration (delegated subnet `10.60.3.0/24`) rather than a private endpoint. VNet integration is simpler (no NIC required) but provides equivalent network isolation for a Flexible Server.

### 3. Managed Identity for All Database Access

Every Container App that uses PostgreSQL is mapped to a managed identity user (`msi-nexpay-{env}`). The PostgreSQL role setup job (`ca-nexpay-pg-setup-qa`) runs within the VNet after Terraform apply to call `pgaadauth_create_principal` — creating the Entra ID managed identity user in each database.

### 4. Terraform State Security

State is stored in Azure Blob Storage (`sanexpaytfstorage{env}`). The Terraform state file will contain:
- Resource IDs and FQDNs
- `Dynatrace_api_token` (if not properly excluded)
- PostgreSQL admin password (Terraform-generated, stored in Key Vault — but also in state)
- Azure AD object IDs

**Finding**: Terraform state must be treated as a sensitive artifact. Access to `sanexpaytfstoragetf` storage account must be restricted to the deployment service principal only (ARM_CLIENT_ID in the workflow secrets).

## Security Posture

### Network Security
- VNet: 10.60.0.0/20 with three delegated subnets — no subnet security groups visible in the reviewed code (may be in modules).
- No public IP on Container Apps Environment.
- PostgreSQL not accessible from internet (`public_network_access_enabled = false`).
- Key Vault: RBAC authorization, `bypassAzureServices` — potentially accessible from public network depending on `network_acls_default_action` default value.

### Identity and Access
- Azure AD RBAC for Key Vault (not legacy access policies) — correct modern pattern.
- Managed Identity for all service-to-database and service-to-KeyVault access.
- Deployment service principal (`980a2f07-...`) has `App Configuration Data Owner` — broad permission; consider restricting to `Data Contributor` for CI/CD.

### Secrets in Repository
- `kv-secrets.json` lists secret names and metadata but NOT values — values come from GitHub Secrets at sync time. This is correct.
- `qa.tfvars` contains tenant IDs and Azure AD object IDs (not secrets, but Azure-specific identifiers).

## Technical Debt

| Item | Severity | Description |
|---|---|---|
| No production IaC | Critical | `prod.tfvars` does not exist; production environment not managed by this repo |
| Key Vault purge protection disabled | High | Must enable before production |
| App Config public network access | High | Must enable private endpoint and disable public access for production |
| PostgreSQL 18 pre-GA | Medium | Non-GA database engine in production pipeline |
| Free App Config tier | Medium | 1 req/sec limit; upgrade to Standard for production |
| Container App Jobs disabled | Medium | VNet timeout issue prevents running operational jobs (e.g., DB admin tasks) |
| Dynatrace token in Terraform state | Medium | Injected via TF_VAR; ends up in state file and workflow artifact |
| No staging environment | Medium | Single QA → prod path; no pre-production isolation |
| `purge_soft_delete_on_destroy = true` | Medium | KV soft-deleted resources are immediately purged on destroy — no recovery window for accidents |
| Module versions not pinned | Low | Local modules have no version constraints; changes to a module affect all environments simultaneously |

## Code-Level Architecture

### Dynamic Container App Creation

The `container_apps` map in `qa.tfvars` drives the creation of all 11 Container Apps via a single `module "container_apps"` call with `for_each`. This pattern correctly treats infrastructure as data and avoids duplicating module calls.

### PostgreSQL Role Setup via Container App Job

The post-apply PostgreSQL role setup is clever: a Container App Job is triggered by the Terraform deployment workflow after `terraform apply`. The job runs within the VNet (where PostgreSQL is accessible) and creates the Entra ID managed identity users. This solves the "bootstrap problem" of needing to run database commands that require network access unavailable from the CI runner.

**Risk**: Container App Jobs in a VNet-integrated ACA environment have timeout issues (noted in `qa.tfvars` comments). If the setup job times out, services will fail to authenticate to PostgreSQL on startup.

### OTel at Environment Level

The `container_apps_environment` module configures OpenTelemetry at the ACA environment level using the `azapi` provider (Azure API directly, not azurerm, as this feature was not available in azurerm at the time of implementation). The Dynatrace OTLP endpoint and auth header are injected here, ensuring all Container Apps in the environment inherit the OTel sink configuration without any per-app configuration.
