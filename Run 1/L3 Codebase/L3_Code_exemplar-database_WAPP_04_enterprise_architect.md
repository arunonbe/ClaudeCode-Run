# Enterprise Architect View — exemplar-database_WAPP

## Platform Generation and Role

**Platform Generation**: Gen-3 (Onbe's current-generation cloud-native microservices platform).

This repository is a **reference infrastructure component** within the Gen-3 exemplar family. Its role in the enterprise architecture is prescriptive: it defines how all Gen-3 services should provision their SQL Server instances, establishing a repeatable, reviewed, and approved pattern for infrastructure-as-code (IaC) at the database layer.

The exemplar family at Onbe comprises multiple reference repositories (exemplar-database, exemplar-theater-service, exemplar-customer-service, exemplar-cross-border-transfer-service). `exemplar-database_WAPP` is the shared infrastructure foundation that underpins all of them.

## Architectural Decisions Documented

### Decision 1: Schema-per-Service over Database-per-Service

The README explicitly documents that the database-per-service pattern was considered and rejected (README lines 4–6). The rejection rationale is resource constraints in local Docker-based development. The chosen schema-per-service pattern:
- Reduces memory and operational overhead.
- Allows a single SQL Server instance to serve multiple bounded contexts.
- Maintains data isolation at the database (catalog) level rather than at the server level.
- Trade-off: No hard isolation boundary — a misconfigured application could theoretically access another service's database if using the SA account.

### Decision 2: Deployment Independence

By separating database provisioning from application code, Onbe enforces:
- Databases must be deployed before applications (README lines 8–9).
- Infrastructure teams can evolve the provisioning pattern without touching application code.
- Application teams cannot deploy application changes that inadvertently affect DB provisioning.

### Decision 3: Dual-Environment Parity (Docker / AKS)

Providing both local Docker Compose and AKS deployment scripts in the same repository ensures that local development mirrors production topology as closely as possible, reducing "works on my machine" incidents.

## Dependency Map

```
exemplar-database_WAPP (this repo)
    |
    |--- exemplar-theater-service_WAPP  (consumes Theater DB)
    |--- exemplar-customer-service_WAPP (consumes Customer DB)
    |--- [DII administration service]   (consumes diiadministration DB)
```

None of the above consuming services have a hard build-time dependency on this repo. The dependency is purely operational: the databases must exist before Liquibase migrations can run at application startup.

## Platform Architecture Context

Within Onbe's Gen-3 architecture:
- Services communicate via Dapr pub/sub (demonstrated in theater-service).
- Each service manages its own schema via Liquibase.
- Shared infrastructure (SQL Server instance) is provisioned independently.
- Services connect to their dedicated database using connection strings injected via environment variables or Azure App Configuration.

This repository demonstrates the infrastructure provisioning layer of that architecture. It is intentionally simple — no Spring Boot, no Java, no Maven — because its only function is to run `sqlcmd` and `az sql`.

## Integration with Azure Platform

The AKS deployment path uses Azure CLI (`az sql`). This implies:
- The deploying principal must have appropriate Azure RBAC roles (Contributor or SQL DB Contributor on the resource group).
- The Azure SQL server is placed in the `exemplar` resource group.
- The `Basic` tier used here is for demonstration only; production Onbe workloads would require at minimum `Standard` or `Business Critical` tiers with geo-redundancy for PCI DSS compliance.

## Compliance Architecture Implications

For a PCI DSS Level 1 service provider:
- SQL Server databases holding cardholder data must reside within the Cardholder Data Environment (CDE).
- Network segmentation (Requirement 1) must restrict access to the database to only authorized application servers, not the open internet range used in the AKS script.
- The SA account (Requirement 7/8) must not be used for application connectivity.
- This exemplar repo, as a reference pattern, must evolve to demonstrate secure credential injection (Azure Key Vault integration) before teams use it as the basis for CDE-adjacent services.

## Migration Complexity

**From exemplar to production**: Medium complexity.
The pattern is architecturally sound but requires the following hardening before production use:
1. Replace hardcoded credentials with secrets management.
2. Restrict firewall rules to specific CIDR ranges.
3. Switch from SA account to service-specific least-privilege SQL logins.
4. Upgrade Azure SQL tier from Basic to production-grade.
5. Add CI/CD pipeline for infrastructure validation.

**Compatibility with Gen-1/Gen-2**: Not applicable. This repository introduces patterns that are specific to Gen-3's containerized, cloud-native deployment model and has no backward compatibility constraints with legacy ecount-based services.
