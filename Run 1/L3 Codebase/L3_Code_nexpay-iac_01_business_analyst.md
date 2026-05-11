# nexpay-iac — Business Analyst View

## 1. Purpose and Business Function

`nexpay-iac` is the **Infrastructure as Code (IaC) repository** for the NexPay Gen-3 platform. It defines, provisions, and manages all Azure cloud infrastructure required to run the NexPay microservices. From a business perspective, this repository is the control plane for Onbe's cloud spend, security posture, and operational capability for the NexPay platform.

The repository directly enables:
- **Client program delivery**: Without the provisioned Container Apps, no NexPay service can run, meaning no payment programs can be processed.
- **Cost governance**: The IaC controls which Azure resources exist, in which SKUs, and in which regions — directly driving Azure cloud costs.
- **Compliance posture**: Network isolation, secret management, and RBAC definitions in this repository determine whether NexPay meets PCI DSS, SOC 2, and GLBA infrastructure requirements.
- **Operational resilience**: Backup retention, high availability settings, and VNet architecture defined here determine the platform's disaster recovery capability.

## 2. Business Scope — What is Provisioned

The IaC provisions the complete QA environment for NexPay. The following resources are defined across the Terraform configuration:

| Resource Category | Resources Provisioned | Business Purpose |
|---|---|---|
| Container Apps | 11 apps (config-svc, order-orchestrator, ordervalidator, auth, profile, config-test, recipientweb-bff, claim-code, card-proc, ivr-bff, clientadminweb-bff) | NexPay microservices runtime |
| PostgreSQL Flexible Server | 1 server, 5 databases (config, cardprocessor, recipientprofile, recipientauth, configtest) | Persistent data for NexPay services |
| Azure Key Vault | 1 vault (`kv-nexpay-qa`) | Secrets management (FIS, Thredd, Redis, JWT, SQL credentials) |
| Azure App Configuration | 1 store (`appcg-nexpay-qa`) | Centralised runtime configuration for all services |
| Azure Container Registry | Referenced (external: `acraz1clusterqass.azurecr.io`) | Container image registry |
| Virtual Network | 1 VNet (10.60.0.0/20), 3+ subnets | Network isolation for all services |
| Private DNS Zones | 5 zones (keyvault, appconfig, wirecard, postgresql, postgresql-privatelink) | Private network name resolution |
| VNet Peering | 1 peering to ecount spoke VNet | Connectivity to legacy eCount SQL databases |
| Dynatrace OTel | OTLP sink configuration on ACA Environment | Observability infrastructure |
| Wirecard DNS records | 3 A records (q-lis-db01/02/03) | Legacy Wirecard database connectivity |

## 3. Third-Party Processor Connectivity

A notable business observation: The IaC provisions connectivity to both:

1. **Wirecard/legacy processor** (`nam.wirecard.sys` private DNS zone with A records for `q-lis-db01`, `q-lis-db02`, `q-lis-db03` at private IPs 10.91.16.21/28/31) — indicating that NexPay Gen-3 still maintains connectivity to Wirecard/legacy processor infrastructure in QA.

2. **FIS and Thredd** — credentials for both processors are provisioned in Key Vault (`kv-secrets.json`). FIS is the legacy prepaid card processor for Onbe's US programs. Thredd is the modern card-issuing processor (UK-based) used for newer programs.

This dual-processor connectivity confirms that NexPay Gen-3 is being built for a multi-processor architecture, where programs can route to different card processors based on configuration.

## 4. Business-Critical Security Secrets Managed

The `kv-secrets.json` file catalogues all secrets loaded into Key Vault:

| Secret | Business Significance |
|---|---|
| `fis-uat-username` / `fis-uat-password` | FIS (cardholder processor) authentication credentials |
| `fis-cert-base64` | FIS mTLS client certificate — required for card transactions |
| `thredd-uat-clientid` / `thredd-uat-clientsecret` | Thredd OAuth client credentials for card operations |
| `redis-primary-access-key` | Azure Cache for Redis authentication key |
| `jwt-secret-qa` | JWT signing secret for NexPay API authentication |
| `nexpay-sql-password-qa` | PostgreSQL readonly user password |

The presence of FIS and Thredd UAT credentials indicates that QA is integrated with processor UAT environments, enabling end-to-end payment flow testing.

## 5. Business Risks from IaC Perspective

### 5.1 Single QA Environment

The current IaC supports only one deployed environment (`qa`). There is no `dev` or `staging` environment defined. This means all developers test against the same QA environment, creating coordination challenges and a risk that one team's changes break another's tests.

### 5.2 Key Vault Purge Protection Disabled

`key_vault_purge_protection_enabled = false` in `qa.tfvars` (line 18). This means a Key Vault deletion cannot be undone — accidental or malicious deletion of the vault would immediately destroy all secrets, taking down all NexPay services that depend on them. For a payments platform, this is a business continuity risk that should be remediated before production.

### 5.3 App Configuration Public Network Access

`app_config_public_network_access = "Enabled"` (line 24) means the App Configuration store is reachable from the public internet. While RBAC protects the data, public network exposure creates an attack surface. The private endpoint is disabled (`app_config_enable_private_endpoint = false`, line 26). This should be reviewed for production.

### 5.4 App Configuration Local Auth Enabled

`app_config_local_auth_enabled = true` (line 23) enables connection string access to App Configuration, bypassing Managed Identity RBAC. This is documented as a CI/CD requirement but represents an over-privileged access mode that bypasses audit trails.
