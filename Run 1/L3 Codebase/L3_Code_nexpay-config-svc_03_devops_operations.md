# nexpay-config-svc — DevOps & Operations View

## 1. Repository and Build Structure

```
nexpay-config-svc/
├── nexpay-config-api/              (OpenAPI server stubs — generated)
├── nexpay-config-boot/             (Spring Boot executable + Dockerfile)
│   ├── init.db/init.sql            (Local dev database initialisation)
│   ├── compose.yaml                (Docker Compose for local dev with PostgreSQL)
│   └── src/test/                   (Integration tests using Testcontainers)
└── nexpay-config-data/
    ├── nexpay-config-data-entity/  (JPA entities + Flyway migrations)
    └── nexpay-config-data-repository/ (Spring Data JPA repositories)
```

**Java version**: Inherits from `nexpay-parent:0.2.8-SNAPSHOT`. Likely Java 21+ (virtual threads, Jakarta EE 10).

**Testing**: `TestContainerConfig.java` in both the boot and repository test modules confirms that integration tests use Testcontainers to spin up a real PostgreSQL instance. This makes the test suite environment-independent and reduces "works on my machine" test failures.

## 2. Docker and Container

### 2.1 Dockerfile

Located at `nexpay-config-boot/Dockerfile`. The exact content was not scanned but follows the same pattern as the other NexPay services (bellsoft/liberica-openjre-alpine base, Java JAR deployment).

### 2.2 Local Development Compose

`nexpay-config-boot/compose.yaml` spins up a PostgreSQL container for local development. The `init.db/init.sql` pre-creates the database schema for local use. This is separate from the production Flyway migration path.

## 3. CI/CD Pipeline

### 3.1 Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `deployment.yml` | PR / push to main | Build, test, ACR push, ACA deploy |
| `app-config.yml` | Separate | Push app settings to Azure App Configuration |
| `codeql.yml` | Push/PR | CodeQL SAST scanning |
| `redeploy.yml` | Manual | Re-deploy without code change |
| `dependabot.yml` | Scheduled | Dependency vulnerability scanning |

The `deployment.yml` delegates to the same shared reusable workflow as all other NexPay services (`OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`), ensuring consistent build standards across the platform.

### 3.2 Container App Name

The deployed Container App is named `ca-nexpay-config-svc-qa` (inferred from `application-qa.yaml` line 59 of the BFF: `base-url: "http://ca-nexpay-config-svc-qa"`). The internal ingress is not publicly accessible (`external_enabled: false` in `qa.tfvars` line 65).

### 3.3 Database Deployment Automation

The PostgreSQL `config` database is created by Terraform (`qa.tfvars` line 285–287). The Managed Identity database role (`msi-nexpay-qa`) is provisioned by the `ca-nexpay-pg-setup-qa` Container App Job, which runs `pgaadauth_create_principal()` inside the VNet after each Terraform apply (`terraform-qa-deploy.yml` lines 177–193). Application schema is then applied by Flyway at service startup.

## 4. Environment Configuration

### 4.1 Azure App Configuration Key Filter

```yaml
# application-qa.yaml
selects:
  - key-filter: "nexpay-config-svc/"
    label-filter: "qa"
trim-key-prefix: "nexpay-config-svc/"
```

All app-specific configuration keys in Azure App Configuration are prefixed with `nexpay-config-svc/` and labelled `qa`. The `trim-key-prefix` setting strips the prefix so that application code sees clean key names.

### 4.2 The Sentinel Pattern

The `sync-secrets-to-kv.yml` workflow bumps a `sentinel` key in Azure App Configuration after updating secrets. This triggers the `spring-cloud-azure-appconfiguration-config` library's refresh mechanism, causing all running config-svc instances to pull updated configuration values without restart. The sentinel key approach is documented in the Spring Cloud Azure documentation and is the correct pattern for dynamic secret rotation.

**Current risk**: `app_config_local_auth_enabled = true` in `qa.tfvars` (line 23) allows access to the App Configuration store via connection strings, bypassing Managed Identity RBAC. The comment says this is required for the CI/CD workflow to store secrets. This is a security gap — the CI/CD service principal should use RBAC (`App Configuration Data Owner` role assignment, which is already present at line 35 of `qa.tfvars`) rather than connection string access. Disable `local_auth_enabled` once verified.

## 5. Observability

### 5.1 OpenTelemetry (Dynatrace OTLP/HTTP)

Config-svc uses OTLP over **HTTP** (not gRPC as in the BFF) for traces, logs, and metrics. This is configured in `application-qa.yaml` lines 111–139.

```yaml
management:
  tracing:
    sampling:
      probability: 1.0   # 100% sampling — appropriate for a config service with low traffic
  opentelemetry:
    tracing:
      export:
        otlp:
          transport: http
          endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces
          headers:
            Authorization: ${DT_OTLP_AUTH_HEADER}
```

The `DT_OTLP_AUTH_HEADER` is sourced from Azure App Configuration as a Key Vault reference to the Dynatrace API token.

### 5.2 Log Format

```yaml
logging:
  structured:
    format:
      file: logstash
```

Structured JSON logging in Logstash format (`application-qa.yaml` line 159–161) enables log aggregation in Dynatrace without custom parsers. This is a best practice.

### 5.3 Actuator Endpoints

```yaml
endpoints:
  web:
    exposure:
      include: health,info,env   ← env is exposed
```

The `env` endpoint is included (`application.yaml` line 48). Same risk as the BFF — this can expose resolved configuration values including those loaded from Key Vault references if the actuator port is reachable. The management server should be restricted to an internal subnet or the `env` endpoint removed from the exposure list.

Additionally, the startup endpoint is configured with `access: UNRESTRICTED` (`application.yaml` line 54), which is more permissive than `read-only`. This means the startup endpoint can be triggered by any caller, not just read. Confirm whether this is intentional (it appears to be a misconfiguration — the typical setting is `read-only`).

## 6. Integration Testing Strategy

The `nexpay-config-boot/src/test` directory contains 11 integration test classes. Each test uses the `TestContainerConfig` to start a real PostgreSQL container and runs the Flyway migrations before executing tests. This provides:

- Full schema validation (Flyway runs migrations as in production)
- Real SQL execution (not mocked JPA)
- Idempotency test coverage (`CountriesIdempotencyIntegrationTest`)
- Envers audit trail test coverage (`EnversRevisionIntegrationTest` in repository module)

The `copilot-instructions.md` in `.github/instructions/` suggests GitHub Copilot integration for developer assistance, which is a Gen-3 practice.

## 7. Operational Runbook Notes

**Schema migration rollback**: Flyway does not support automatic rollback of applied migrations. If a migration introduces a breaking change, a rollback migration (`V11__rollback_something.sql`) must be written and deployed. Ensure a tested rollback migration exists for all schema changes before deploying to production.

**Connection pool sizing**: The pool is sized at 20 max connections (`hikari.maximum-pool-size: 20`). Azure PostgreSQL Flexible Server `B_Standard_B1ms` (QA SKU) supports approximately 50 connections maximum at the server level. With multiple container replicas (max 2 in QA), total connections can reach 40 — within budget but leaving little headroom for administrative connections.

**Sentinel-driven refresh**: If the App Configuration sentinel is bumped without updating the associated secret in Key Vault, services will attempt to reload configuration and may fail if the Key Vault reference cannot be resolved. Test the full secret rotation pipeline in a non-production environment before applying to production.
