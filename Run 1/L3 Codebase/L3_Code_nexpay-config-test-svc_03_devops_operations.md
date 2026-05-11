# nexpay-config-test-svc — DevOps & Operations View

## 1. Repository State

The `nexpay-config-test-svc` repository currently contains only two files:
- `README.md` — one-line description: "A playground/test service used in the International Payment project for testing purposes only."
- `.gitignore` — standard Git ignore rules.

There is no application code, no `pom.xml`, no Dockerfile, no GitHub Actions workflows, and no Spring Boot configuration. This is a **repository placeholder** — the service has been registered in the platform infrastructure (IaC) before its code has been developed, which is a valid "infrastructure-first" development practice within the NexPay Gen-3 approach.

## 2. Provisioned Infrastructure

Despite the empty repository, the IaC (`nexpay-iac/terraform/environments/qa.tfvars`) fully provisions this service's Azure resources:

### 2.1 Container App

```hcl
config-test-svc = {
  image                 = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
  cpu                   = 0.25
  memory                = "0.5Gi"
  min_replicas          = 1
  max_replicas          = 2
  target_port           = 8080
  external_enabled      = false   # Internal service
  ingress_enabled       = true
  workload_profile_name = "Consumption"
}
```

The Container App is running the Microsoft demo `helloworld` image. This image returns a simple "Welcome to Azure Container Apps!" HTML page on any HTTP request. It does not connect to the PostgreSQL database or perform any NexPay logic.

**Operational concern**: Min replicas is 1, meaning the demo image is always running and consuming Azure Consumption quota. If the Container App Environment is shared with production (which it is not — this is QA-only based on the environment variable `qa`), this would be a concern. In QA it is an unnecessary cost.

### 2.2 PostgreSQL Database

The `configtest` database is created on the shared `postgresql` Flexible Server. The database credentials (Managed Identity) are provisioned by the `ca-nexpay-pg-setup-qa` Container App Job. The database is empty — no application has run Flyway migrations.

### 2.3 Azure App Configuration

A key namespace `nexpay-config-test-svc/` with label `qa` may exist in `appcg-nexpay-qa.azconfig.io`. Without application code to confirm, this is speculative.

## 3. CI/CD Pipeline — Current State

There are no GitHub Actions workflows in this repository. When application code is added, the standard NexPay pattern will require:

| Workflow | Expected |
|---|---|
| `deployment.yml` | `uses: OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main` with `APP_NAME: ca-nexpay-config-test-svc` |
| `app-config.yml` | Push test-specific settings to App Configuration |
| `codeql.yml` | CodeQL SAST scanning |
| `dependabot.yml` | Dependency vulnerability scanning |

The `deployment.yml` should specify `PUBLISH_TO_APIM: false` since this is an internal test service that should never appear in the APIM catalogue.

## 4. Expected Container and Build Structure

When code is committed, the expected project structure (based on NexPay conventions from other services) is:

```
nexpay-config-test-svc/
├── pom.xml                          (parent — inherits from nexpay-parent)
├── nexpay-config-test-api/          (OpenAPI server stubs, if applicable)
├── nexpay-config-test-boot/
│   ├── Dockerfile
│   ├── src/main/resources/
│   │   ├── application.yaml
│   │   ├── application-qa.yaml     (Azure App Config + Managed Identity DB auth)
│   │   └── application-local.yaml
│   └── src/test/                   (Testcontainers integration tests)
└── nexpay-config-test-data/        (if it has its own schema)
    └── db/migration/*.sql          (Flyway migrations)
```

## 5. Operational Risks of Current State

### 5.1 Demo Image Security Risk

The `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest` image:
- Is a publicly distributed, well-known image — its behavior is predictable by any attacker who knows it's running.
- Has no authentication requirements — any caller inside the ACA network can receive an HTTP 200 response from this service.
- Could be mistaken for a working service by monitoring dashboards (health check passes on the demo image's `/` endpoint).

**Recommendation**: Replace the placeholder image with a "service not ready" image that returns HTTP 503, or scale min_replicas to 0 until code is developed.

### 5.2 Misleading Health Checks

The Container Apps liveness probe will succeed on the demo image (the HTTP endpoint returns 200), causing the service to appear healthy in monitoring dashboards even though no real application is running. This can mask the fact that the service has not been implemented.

### 5.3 Cost Without Utility

The Container App (min 1 replica) and the `configtest` database (PostgreSQL storage billed even when empty) incur ongoing Azure costs. For a test-only service that has not yet been implemented:
- Set `min_replicas = 0` in `qa.tfvars` (Container Apps Consumption supports scale-to-zero)
- Consider whether the PostgreSQL database needs to be provisioned before the application code exists

## 6. Recommended Development Readiness Checklist

Before committing application code to this repository, the following should be in place:

- [ ] `pom.xml` created, inheriting from `nexpay-parent`
- [ ] `Dockerfile` following the NexPay pattern (bellsoft/liberica JRE, non-root user)
- [ ] `application.yaml` and `application-qa.yaml` following `nexpay-config-svc` pattern
- [ ] `.github/workflows/deployment.yml` using the shared IaC workflow
- [ ] `.github/workflows/codeql.yml` for SAST scanning
- [ ] `.github/dependabot.yml` for dependency scanning
- [ ] Flyway migrations defined (either reusing nexpay-config-svc migrations or custom)
- [ ] Testcontainers integration tests
- [ ] App Configuration keys populated for `nexpay-config-test-svc/qa`
- [ ] README updated with architecture description, dependencies, and test instructions
