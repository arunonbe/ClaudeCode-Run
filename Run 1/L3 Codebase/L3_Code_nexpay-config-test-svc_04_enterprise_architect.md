# nexpay-config-test-svc — Enterprise Architect View

## 1. Strategic Role

`nexpay-config-test-svc` represents an **infrastructure-first**, code-second provisioning approach: the Azure resources (Container App, database, managed identity) are fully provisioned before the application exists. This is a deliberate practice in the NexPay platform — it allows infrastructure changes to be reviewed and deployed on their own cycle, decoupled from application development.

From an enterprise architecture standpoint, this service sits in the **Quality Assurance Support Services** layer — it exists solely to enable testing of the International Payment capability without contaminating shared QA data. It has no production footprint and no end-user-facing function.

## 2. Fit Within the NexPay Platform

The service's role in the enterprise is:

```
International Payments Feature Development
    → nexpay-config-test-svc  (test/staging environment for config changes)
    → nexpay-config-svc       (QA/production configuration)
```

This mirrors a common pattern in large-scale platform engineering: a "shadow" or "canary" service that runs ahead of the production service, receiving experimental features or data before they are promoted. The pattern is beneficial for:

1. **Reducing QA environmental coupling**: Other QA services (`nexpay-order-orchestrator`, `nexpay-cardprocessor-svc`) can continue testing against the stable `nexpay-config-svc` while international payment development tests against `nexpay-config-test-svc`.
2. **Migration dry-runs**: New Flyway migrations can be validated against `configtest` before being applied to the `config` database, reducing the risk of migration failures in QA.
3. **API versioning experiments**: Breaking API changes can be tested in `config-test-svc` before being implemented in `config-svc`.

## 3. Governance and Lifecycle Concerns

### 3.1 No Formal Owner Assignment

The repository has no `CODEOWNERS` file, no team assignment, and only a one-line README. Without a formal owner:
- Security vulnerabilities in the dependency tree will not be actioned (no Dependabot workflows)
- The service may remain in placeholder state indefinitely, incurring costs
- Changes to the shared infrastructure (e.g., PostgreSQL server migration) may break this service without anyone noticing

**Recommendation**: Assign a product owner and engineering team to this service within the International Payments project governance structure.

### 3.2 Relationship to nexpay-config-svc Schema

The two services (`config-svc` and `config-test-svc`) will likely maintain near-identical schemas, creating a schema drift risk over time. As `nexpay-config-svc` evolves (V11, V12 migrations), `nexpay-config-test-svc` must apply the same migrations at the same pace. Without automation:
- The schemas will diverge
- Tests run against `config-test-svc` will not reflect the production schema
- International payment features validated in `config-test-svc` may fail when deployed to `config-svc`

**Recommendation**: Establish a shared Flyway migration library that both services depend on, ensuring schema parity by construction.

## 4. Security Architecture Assessment

### 4.1 Network Isolation

The service is correctly configured as `external_enabled: false` — not reachable from the internet or APIM. It is only accessible from within the ACA Container Apps Environment (`snet-container-apps-qa` subnet, 10.60.0.0/23).

### 4.2 Placeholder Image Attack Surface

The running `containerapps-helloworld:latest` image presents a non-zero attack surface:
- It has no authentication
- It accepts any HTTP request and returns a static HTML page
- It could be used as a pivot point if the ACA network is compromised (the image is benign but occupies a Container App slot with granted Azure RBAC permissions)

The Container App has the `msi-nexpay-qa` managed identity assigned with `Key Vault Secrets User` role. An attacker who can exec into this container could use the Managed Identity to read all secrets from Key Vault (`kv-nexpay-qa`). This is the most significant security risk: **a placeholder container with full production secret access**.

**Immediate recommendation**: Either remove the managed identity assignment from this Container App until real application code is deployed, or restrict its Key Vault access to no secrets until needed.

### 4.3 PCI DSS Scope

The `configtest` database is on the same PostgreSQL Flexible Server as `config`, `cardprocessor`, `recipientprofile`, and `recipientauth`. If any of these databases store cardholder data (PANs, CVVs — which they should not per the microservices CDE design), the `configtest` database would be within PCI DSS scope by network proximity. The QSA should assess whether the shared server constitutes CDE scope expansion.

## 5. Architecture Principles Evaluation

| Principle | Status | Notes |
|---|---|---|
| Infrastructure-as-code | Achieved | Fully provisioned via Terraform IaC |
| Service isolation | Achieved | Dedicated database, internal-only ingress |
| Managed Identity authentication | Configured | But no application to use it |
| Code repository exists | Achieved | Repository exists in source control |
| No production footprint | Achieved | QA-only |
| Formal ownership | Not achieved | No CODEOWNERS, no team assignment |
| Schema parity with config-svc | Not achieved | No code, no migrations |
| Least-privilege secret access | Not achieved | Full vault access via msi-nexpay-qa |

## 6. Recommendations to Enterprise Architecture

1. **Gate infrastructure costs on code readiness**: Do not provision Azure resources (Container App, database) for a service until its first application artifact has been built and committed to the repository.
2. **Define lifecycle policy for placeholder services**: Establish an organisational policy that placeholder repositories must be resolved (code committed or infrastructure decommissioned) within 60 days of provisioning.
3. **Formalise the International Payments track**: Create a product epic/initiative in the project management tool (Asana/Jira) that owns this service, with defined deliverables and timelines.
4. **Schema parity automation**: Invest in a shared Flyway library or a CI/CD rule that verifies `configtest` schema is in sync with `config` schema before any test run.
