# DevOps / Operations View — nexpay-ordervalidator-svc

## Build System

| Attribute | Value |
|-----------|-------|
| Build tool | Maven 4.0.0-rc-5 (minimum enforced by parent) |
| Java | 25 |
| Parent POM | `nexpay-parent 0.2.8-SNAPSHOT` |
| Submodules | `-api`, `-address` (address client), `-impl`, `-boot` |
| Test separation | `*IT.java` files → Failsafe; `*Test.java` → Surefire |
| Code coverage | JaCoCo (inherited from parent) |

## CI/CD Pipeline

### GitHub Actions Workflows

The service has four GitHub Actions workflows:

| Workflow | Purpose |
|----------|---------|
| `deployment.yml` | Build and deploy to Azure Container App on PR/push to main |
| `app-config.yml` | Sync `app-config/qa/appsettings.json` to Azure App Configuration |
| `codeql.yml` | Static analysis (SAST) |
| `redeploy.yml` | Manual or automated redeployment without code changes |

The deployment workflow pattern mirrors the orchestrator's — it delegates to the reusable `nexpay-iac` workflow. The critical difference is that the ordervalidator has a `redeploy.yml` workflow (which the orchestrator does not), suggesting the validation service is deployed more frequently or requires zero-downtime redeployment capability.

## Containerization

The `nexpay-ordervalidator-boot` module contains a `Dockerfile` and `compose.yaml` for local development. The `compose-with-client.yaml` allows running the validator alongside a client service for integration testing. The `COMPOSE-NETWORK-EXAMPLES.md` and `DOCKER-CONNECTIVITY.md` files provide developer guidance for local service mesh configuration.

## Configuration Management

### Bootstrap Configuration

Like all NexPay services, the ordervalidator uses Azure App Configuration for runtime config in QA/Prod (`bootstrap.yml`). The `app-config/qa/appsettings.json` file defines the values that are pushed to Azure App Configuration. The key filter `nexpay-ordervalidator-svc/` with label `qa` scopes the configuration.

### CRITICAL: Credentials in Source Code

**File**: `nexpay-ordervalidator-boot/src/main/resources/application.yaml`, lines 126–179

The `dev-test` profile contains a full Azure App Configuration connection string with credentials:
```
connection-string: Endpoint=https://as-app-configuration.azconfig.io;Id=eSca;Secret=AknWtgoJsE4...
```

The `integration` profile also contains an OAuth2 client secret:
```
secret: [REDACTED — rotate immediately]
```

These credentials are committed to the Git repository. Even if they belong to non-production environments, this violates:
- **PCI DSS Requirement 8.2.1**: No shared group credentials
- **PCI DSS Requirement 12.3.3**: Cryptographic key management
- **GitHub Secret Scanning**: Should have been caught by GitHub's secret scanning feature

**Immediate remediation steps**:
1. Rotate both credentials immediately.
2. Remove them from `application.yaml` and replace with `${ENV_VAR}` references or Azure Key Vault references.
3. Enable GitHub secret scanning push protection on the repository.
4. Audit git history to determine if these secrets were ever pushed to external forks or used in production.

## Runtime Profiles

| Profile | App Config Source | Database | OTel |
|---------|-------------------|----------|------|
| `local` | Disabled | None (stateless) | Disabled |
| `dev-test` | Azure App Config (connection string) | None | Disabled |
| `test` | Disabled | None | Disabled |
| `integration` | Disabled | R2DBC MSSQL (localhost) | Disabled |
| `qa` | Azure App Config (managed identity) | None | Enabled |

Note: the `qa` profile has two separate YAML sections (lines 58–96 and lines 181–209 in `application.yaml`), which is unusual. The second `qa` section overrides the first. This should be consolidated to avoid confusion.

## Observability

### Logging

- Default level: `com.onbe.nexpay: INFO` — appropriate for production.
- Azure App Configuration and identity: `WARN` — minimal noise.
- Structured Logstash format for log aggregation.

The application log level is lower than the orchestrator's DEBUG default, which is better for production. However, the integration profile sets verbose logging that may inadvertently reveal validation request details if that profile is ever activated in a shared environment.

### Metrics

Spring Actuator exposes standard endpoints on port 8081. OpenTelemetry OTLP export to `${OTEL_EXPORTER_OTLP_ENDPOINT}` is active in QA.

### Integration Tests

`RUNNING-INTEGRATION-TESTS.md` provides developer documentation for running integration tests. The `application-integration.yaml` test resource file suggests tests use WireMock or Testcontainers to mock the address verification service.

## Operational Considerations

### Service is Stateless

The validator does not maintain state between requests. This means:
- Horizontal scaling is straightforward — any instance can handle any request.
- There is no session affinity requirement.
- Restart is zero-impact (no in-flight state to recover).

### Health Endpoints

Standard Actuator health endpoints at port 8081. Given the service is stateless, the only meaningful health indicator is application startup state and downstream service connectivity (address verification service, if used).

### Deployment Frequency

The existence of `redeploy.yml` suggests this service is deployed frequently for configuration-only changes. The `app-config.yml` workflow allows configuration updates without a full build.

### Runbook: Hardcoded Amount Limit

If a business decision is made to change the $1,000 transaction limit, this currently requires:
1. Modify `FundsValidationService.java` line 16.
2. Build and test.
3. Deploy via CI/CD.

Until the limit is externalised to Azure App Configuration, any limit change is a deployment event. Teams should be aware that a fraud response requiring an emergency limit reduction cannot be executed without a code deployment.
