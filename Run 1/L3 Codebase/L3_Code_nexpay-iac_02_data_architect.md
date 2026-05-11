# nexpay-iac — Data Architect View

## 1. Persistent Data Infrastructure

The IaC provisions the following persistent data stores for the NexPay platform:

### 1.1 PostgreSQL Flexible Server

**Server**: Single `postgresql` server in QA (region: West US 2)

| Parameter | Value | Source |
|---|---|---|
| Version | 18 | `qa.tfvars` line 224 |
| SKU | `B_Standard_B1ms` (Burstable, 1 vCore) | line 225 |
| Storage | 32GB | line 227 |
| Public network access | Disabled | line 249 |
| VNet integration | Enabled (delegated subnet) | line 250 |
| Backup retention | 7 days | line 255 |
| Geo-redundant backup | Disabled | line 256 |
| SSL required | `require_secure_transport = true` | line 278 |
| Authentication | Both Entra ID + password auth | lines 229–244 |

**Databases on this server**:

| Database | Owner Service | Purpose |
|---|---|---|
| `config` | nexpay-config-svc | Program/country/modality configuration |
| `cardprocessor` | nexpay-cardprocessor-svc | Card transaction processing data |
| `recipientprofile` | nexpay-recipient-profile-svc | Recipient identity and profile data |
| `recipientauth` | nexpay-auth-svc | Authentication data |
| `configtest` | nexpay-config-test-svc | Test configuration data |

**Entra ID Admin Group**: `nexpay-qa-pg-admins` (Object ID: `2d83a86b-bb50-4bec-bc25-03f7e3deec6e`) — this Azure AD group should contain only DBAs and senior engineers who require administrative access to the PostgreSQL server.

### 1.2 Azure Cache for Redis

Redis is referenced in service configurations but not explicitly provisioned in the Terraform code reviewed (it may be provisioned in a separate module or by the shared infrastructure team). The Redis primary access key is stored in Key Vault (`redis-primary-access-key`), confirming that an Azure Cache for Redis instance exists for the NexPay platform.

### 1.3 Azure Key Vault (`kv-nexpay-qa`)

The Key Vault stores 8 secrets (per `kv-secrets.json`). It uses standard SKU with RBAC authorization (`rbac_authorization_enabled = true`), which is the modern, recommended approach over legacy access policies.

**Key Vault network access**: Controlled by `network_acls.default_action` and `allowed_ip_ranges` (from `key-vault/variables.tf`). The actual values for QA are not set explicitly in `qa.tfvars`, meaning the module defaults apply. The Key Vault module (`key-vault/main.tf` line 34–39) configures:
```hcl
network_acls {
  bypass         = "AzureServices"
  default_action = var.network_acls_default_action   # likely "Allow" if not specified
}
```

If `network_acls_default_action` defaults to `"Allow"`, the Key Vault is publicly accessible from any IP. This is a critical finding — Key Vault for a PCI DSS Level 1 processor must restrict access to known IP ranges or use private endpoints. Verify the default value in `key-vault/variables.tf`.

### 1.4 Azure App Configuration (`appcg-nexpay-qa`)

Used as the centralised runtime configuration store for all NexPay microservices. It stores:
- Non-secret configuration values (service endpoints, feature flags, Redis host/port)
- Key Vault references (pointing to secrets in `kv-nexpay-qa`)
- Sentinel key for dynamic refresh triggering

**SKU**: `free` (QA) — the free tier has limitations: 1 request per second, no private endpoint, no geo-replication. For production, `standard` SKU is required.

**Data at rest**: All configuration values (including Key Vault references) are stored in Azure App Configuration. The values themselves are not secrets (Key Vault references are just URIs), but the configuration structure reveals the platform architecture to anyone with access.

## 2. Networking and Data Routing

### 2.1 Virtual Network Topology

```
VNet: vnet-nexpay-qa (10.60.0.0/20 = 4096 IPs)
│
├── snet-container-apps-qa    (10.60.0.0/23 = 512 IPs)  — Container Apps Environment
│                               [delegated to Microsoft.App/environments]
│
├── snet-private-endpoints-qa (10.60.2.0/24 = 256 IPs)  — Private endpoint NICs
│
└── snet-postgresql-qa        (10.60.3.0/24 = 256 IPs)  — PostgreSQL VNet integration
                                [delegated to Microsoft.DBforPostgreSQL/flexibleServers]
```

### 2.2 VNet Peering

```
vnet-nexpay-qa (10.60.0.0/20)
    ↔ (peering) ↔
vnet-az1-qa-ecount-spoke-001 (/subscriptions/8a143b5c.../Microsoft.Network/virtualNetworks/...)
```

This peering provides NexPay Gen-3 services with access to the legacy eCount PostgreSQL/SQL Server databases in the eCount spoke VNet. This confirms that during the transition period, Gen-3 services may read from or write to legacy eCount databases.

### 2.3 Wirecard DNS Records

Three private DNS A records in the `nam.wirecard.sys` zone provide name resolution for legacy Wirecard database servers:
- `q-lis-db01` → 10.91.16.21
- `q-lis-db02` → 10.91.16.28
- `q-lis-db03` → 10.91.16.31

These are private IP addresses in a separate network (likely reachable via the eCount VNet peering or a VPN gateway). This indicates NexPay cardprocessor-svc or auth-svc connects to legacy Wirecard database infrastructure.

## 3. Secret and Data Sensitivity Classification

| Data Category | Storage Location | Classification |
|---|---|---|
| FIS API credentials | Key Vault (`fis-uat-username`, `fis-uat-password`) | Secret — PCI DSS scope |
| FIS mTLS certificate | Key Vault (`fis-cert-base64`) | Secret — PCI DSS scope |
| Thredd OAuth credentials | Key Vault | Secret — PCI DSS scope |
| JWT signing secret | Key Vault | Secret — authentication |
| Redis access key | Key Vault | Secret — infrastructure |
| PostgreSQL admin password | Key Vault (generated by Terraform) | Secret — database admin |
| PostgreSQL readonly password | Key Vault | Secret — read-only access |
| Dynatrace API token | GitHub Secrets only (not in Key Vault) | Secret — monitoring |
| Azure tenant ID | `qa.tfvars` (plaintext) | Sensitive — not a secret, but public exposure undesirable |
| Azure AD object IDs | `qa.tfvars` (plaintext) | Low sensitivity — Azure AD GUIDs |
| ACR subscription ID | `qa.tfvars` (plaintext) | Low sensitivity |

**Finding**: The Dynatrace API token is passed as `TF_VAR_dynatrace_api_token` at Terraform deploy time and written into the Container Apps Environment OTLP headers via the `container_apps_integration.tf` OpenTelemetry configuration block. It is never persisted to Key Vault. If the Terraform state file is accessible (stored in Azure Storage Account `sanexpaytfstorage${ENV}`), the Dynatrace token may be stored in the state file in plaintext. Terraform state must be treated as a sensitive artifact — access to the state storage account should be restricted to the deployment service principal only.

## 4. Backup and Recovery

| Resource | Backup Retention | Geo-Redundancy | RPO |
|---|---|---|---|
| PostgreSQL (QA) | 7 days | Disabled | ~24h (point-in-time recovery) |
| Key Vault | Soft delete 7 days, no purge protection | Not configured | Secret deletion is recoverable within 7 days |
| App Configuration | Soft delete 7 days, no purge protection | Not configured | Not backed up separately |
| Terraform state | Azure Storage (LRS by default) | Not configured | Azure Storage default redundancy |

For production, all of the above must be enhanced: PostgreSQL geo-redundant backup enabled, Key Vault purge protection enabled, Terraform state stored in GRS storage.
