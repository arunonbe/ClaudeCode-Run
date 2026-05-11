# Enterprise Architect View — nexpay-iac

## Platform Generation

**Generation 3 — NexPay Platform Infrastructure Control Plane**

`nexpay-iac` is the infrastructure control plane for the entire NexPay Gen-3 platform. It is not an application — it is the foundation upon which all Gen-3 services run. Its strategic significance is equal to any individual Gen-3 service because without it, no Gen-3 service can be deployed or operate.

## Business Domain

**Platform Infrastructure / Cloud Operations**

`nexpay-iac` is in the Platform Engineering / Cloud Infrastructure domain. Its primary consumers are:
- **DevOps/SRE teams** — provision and manage the NexPay cloud environment
- **Application teams** — depend on the provisioned resources (Container Apps, databases, secrets, config) to deploy their services
- **Security/Compliance teams** — the network architecture, KV RBAC, and logging configs defined here directly determine PCI DSS compliance posture

## Position in the Architecture

```
[Azure Subscription: nexpay-{qa,prod}-rg]
│
├── Azure Container Apps Environment (cae-nexpay-qa)
│   ├── ca-nexpay-config-svc-qa
│   ├── ca-nexpay-order-orchestrator-qa
│   ├── ca-nexpay-ordervalidator-svc-qa
│   ├── ca-nexpay-recipient-auth-svc-qa
│   ├── ca-nexpay-recipient-profile-svc-qa
│   ├── ca-nexpay-config-test-svc-qa
│   ├── ca-nexpay-recipientweb-bff-qa      ← External-facing
│   ├── ca-nexpay-claim-code-svc-qa
│   ├── ca-nexpay-card-proc-svc-qa
│   ├── ca-nexpay-ivr-bff-qa               ← External-facing
│   └── ca-nexpay-clientadminweb-bff-qa    ← External-facing
│
├── Azure PostgreSQL Flexible Server (PostgreSQL 18, B1ms, West US 2)
│   ├── config DB
│   ├── cardprocessor DB
│   ├── recipientprofile DB
│   ├── recipientauth DB
│   └── configtest DB
│
├── Azure Key Vault (kv-nexpay-qa)
├── Azure App Configuration (appcg-nexpay-qa, free tier)
├── VNet (10.60.0.0/20) + 3 subnets
│   └── VNet Peering → eCount legacy spoke (10.x.x.x, SQL Server databases)
│
└── Private DNS Zone (nam.wirecard.sys)
    ├── q-lis-db01 → 10.91.16.21
    ├── q-lis-db02 → 10.91.16.28
    └── q-lis-db03 → 10.91.16.31
```

## Dependencies

### Managed by this Repo
All Gen-3 NexPay services (`nexpay-cardprocessor-svc`, `nexpay-recipientorchestrator-svc`, `nexpay-order-orchestrator`, etc.) depend on resources provisioned here.

### External Dependencies
| Resource | Owner | Purpose |
|---|---|---|
| ACR (`acraz1clusterqass.azurecr.io`) | Shared infrastructure team | Container image registry |
| eCount spoke VNet | eCount team | Legacy SQL Server connectivity via peering |
| Wirecard DB servers (10.91.16.21/28/31) | Legacy infrastructure | NexPay connectivity to legacy processor DBs |
| Dynatrace SaaS | Platform/SRE | OTel observability sink |
| GitHub Actions | GitHub | CI/CD execution |
| Azure AD tenant (`2d652670-5422-4688-a20e-c2d32cc46751`) | Identity team | Managed Identity, RBAC |

## Integration Patterns

- **GitOps (partial)**: Infrastructure changes require a manual plan → confirmation → apply sequence. Not fully automated on push — a human must type "deploy" to confirm.
- **Shared workflow templates**: `java-build-deploy-aca.yml` acts as a reusable CI/CD template consumed by all NexPay application repos via `uses: OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`. This centralises CI/CD governance in the IaC repo.
- **Managed Identity as credential alternative**: All container apps use user-assigned managed identities for database and Key Vault access — no stored database passwords.
- **VNet-integrated deployment**: Container Apps, PostgreSQL, and private endpoints are all within a single VNet with delegated subnets — no public-internet database exposure.

## Strategic Status

**Active Development — Foundation for Gen-3 Platform**

`nexpay-iac` is the foundation layer being actively built alongside the Gen-3 services. Its key strategic gaps:

1. **No production environment defined**: The most critical gap. There are no `prod.tfvars` or a production Terraform workspace. Production infrastructure is either provisioned manually or managed by a separate mechanism — this is a significant operational and compliance risk.

2. **Single environment bottleneck**: All 11+ Container Apps share one QA environment. Developer and QA testing activity competes for the same infrastructure.

3. **VNet peering to eCount speaks**: The peering to the legacy eCount VNet (`vnet-az1-qa-ecount-spoke-001`) is the physical embodiment of Gen-3 / Gen-2 integration dependency. This peering must be maintained as long as any Gen-3 service reads from legacy SQL Server databases.

## Migration Blockers

| Blocker | Impact | Path |
|---|---|---|
| No production IaC | Critical | Define `prod.tfvars` and test full prod provisioning before go-live |
| Key Vault purge protection disabled | High | Enable before any production deployment |
| App Config public network access | High | Enable private endpoint before production deployment |
| PostgreSQL 18 (pre-GA) | Medium | Wait for PostgreSQL 18 GA or pin to 17 for production |
| Free App Config tier | Medium | Upgrade to Standard tier for production (private endpoint, geo-replication) |
| eCount VNet peering | Low-ongoing | Required as long as Gen-3 services connect to legacy databases |

## Compliance Architecture

- **PCI DSS Req 1 (Network controls)**: VNet isolation, internal load balancer, private endpoints for Key Vault and PostgreSQL, delegated subnets — strong network segmentation.
- **PCI DSS Req 3 (Data protection)**: Key Vault RBAC for all secrets. `kv-purge_soft_delete_on_destroy = true` in the provider block means accidental KV deletion is recoverable only if soft-delete retention window (7 days) hasn't expired.
- **PCI DSS Req 7 (Access control)**: Managed Identity with RBAC authorization for Key Vault (`rbac_authorization_enabled = true`) — no legacy access policies.
- **PCI DSS Req 10 (Audit logging)**: PostgreSQL `log_connections`/`log_disconnections` enabled. Container App OTel to Dynatrace for application-level audit. No Azure Monitor / Log Analytics workspace defined in this repo — SIEM integration may be handled externally.
- **SOC 2**: Infrastructure tags (`ManagedBy=Terraform`, `Owner=DevOps Team`) support asset inventory. Terraform state provides infrastructure configuration history.
