# DevOps / Operations View — nexpay-recipientorchestrator-svc

## Build System

| Attribute | Value |
|---|---|
| Build tool | Maven 4 (via nexpay-parent) |
| Java | 25 |
| Submodules | `-api`, `-boot`, `-client`, `-data-entity`, `-data-repository`, `-impl` |
| Test infrastructure | JUnit 5, Testcontainers (PostgreSQL) |

The service has a richer module structure than the orchestrator, reflecting its data access layer: `-data-entity` (JPA entities + Flyway migrations) and `-data-repository` (Spring Data repositories) are separate modules, enabling cleaner layering and reuse.

## Containerization

**`nexpay-recipientorchestrator-boot/Dockerfile`**:

```dockerfile
FROM bellsoft/liberica-openjre-alpine:25
```

Like other NexPay services, this uses BellSoft Liberica JRE 25 on Alpine. The same concerns apply: no `USER` instruction (runs as root), no maximum heap configured.

**`docker-compose.yml`** at the repo root and in the boot module provides local development with a PostgreSQL container. This is the correct approach for local development testing with realistic database behaviour.

## CI/CD Pipeline

The service has only a `codeql.yml` GitHub Actions workflow visible in the repository. Unlike the order orchestrator and ordervalidator, there is no `deployment.yml` visible. This may mean:
1. The deployment workflow has not yet been added (service is earlier in development).
2. Deployment is managed from the `nexpay-iac` repository directly.
3. The workflow file was not included in the repository scan.

**Gap**: Without a CI/CD deployment pipeline in the repository, the deployment process for this service is opaque. Given its critical role in recipient onboarding, a documented, automated deployment pipeline is essential.

## Configuration Management

### Application Profiles

| Profile | App Config | Database |
|---|---|---|
| `test` | Disabled | None (unit tests) |
| `local` | Azure App Config (managed identity optional) | PostgreSQL (localhost:5432) |
| `docker` | Disabled | PostgreSQL (postgres:5432) |
| `qa`, `prod` | Azure App Config (managed identity) | Azure PostgreSQL (passwordless) |

In QA/Prod, database connectivity uses Azure AD passwordless authentication:
```yaml
datasource:
    username: ${AZURE_POSTGRESQL_AD_NON_ADMIN_USERNAME}
    azure:
        passwordless-enabled: true
```

This is the correct approach for PCI DSS compliance — no database passwords in configuration, using managed identity for credential-free authentication.

### Swagger UI in All Environments

**Important finding**: The Swagger UI is enabled in all environments including QA and Prod:
```yaml
springdoc:
  swagger-ui:
    enabled: true
    try-it-out-enabled: true
```

This is a security concern. Swagger UI in production:
- Exposes the complete API surface to any authenticated user.
- With `try-it-out-enabled: true`, allows interactive API calls directly from the browser.
- Could be exploited to trigger saga creation for arbitrary claim codes if authentication is not strict.

**Recommendation**: Disable Swagger UI in production (`swagger-ui.enabled: false`). Keep it enabled only for `local` and `docker` profiles.

## Observability

### Logging Configuration

The default logging level is `ERROR` for all application components:
```yaml
com.onbe.nexpay: ERROR
org.flywaydb: ERROR
```

This is extremely restrictive and may prevent useful diagnostic information from appearing in logs during incident response. The QA/Prod profile overrides this to `INFO` for application code and `DEBUG` for Azure/database components, but the base level of `ERROR` means any misconfigured profile activation would result in silent failures.

**Recommendation**: Set base level to `WARN` rather than `ERROR` to ensure warnings are captured even in default profile.

### Connection Pool Logging

In the default profile, `com.zaxxer.hikari: TRACE` is set. This is highly verbose and will produce a large volume of log output for every database connection lifecycle event. This level is appropriate for debugging connection pool issues but should not be the default.

### OpenTelemetry

OTel is enabled in QA/Prod with OTLP export. The Dynatrace API token integration:
```yaml
otel:
  exporter:
    otlp:
      headers:
        Authorization: "Api-Token ${DYNATRACE_API_TOKEN:your-dynatrace-api-token}"
```

The default value `your-dynatrace-api-token` indicates the environment variable `DYNATRACE_API_TOKEN` must be set in QA/Prod container runtime. If not set, OTel export will fail silently with an invalid auth header, creating an observability gap.

## Operational Health

### Health Endpoints

| Endpoint | Port |
|---|---|
| `GET /actuator/health` | 8081 |
| `GET /actuator/health/liveness` | 8081 |
| `GET /actuator/health/readiness` | 8081 |
| `GET /actuator/startup` | 8081 (UNRESTRICTED access) |

The `startup` endpoint is set to `UNRESTRICTED` access in the base profile. This may expose startup diagnostics without authentication. Combined with the `nexpay.diagnostics.environment-printer.enabled: true` setting, startup information including environment variable names could be visible.

### Database Connection Leak Detection

```yaml
hikari:
  leak-detection-threshold: ${DB_LEAK_DETECTION_THRESHOLD:60000}
```

Connection leak detection is enabled with a 60-second threshold. This will log warnings for any database connections held open for more than 60 seconds, which is useful for detecting slow saga processing that holds database transactions open.

## Runbook Notes

### Stuck Sagas

Sagas in `FAILED` state have not been compensated (stubs only). Monitoring queries:
```sql
SELECT current_state, COUNT(*) FROM saga 
GROUP BY current_state 
ORDER BY current_state;
```

Alert if `FAILED` count exceeds threshold or if any saga has been in `FAILED` state for more than 1 hour.

### Outbox Event Backlog

```sql
SELECT COUNT(*) FROM outbox_event WHERE published = FALSE;
```

Alert if unpublished event count exceeds threshold, indicating the outbox relay process has stopped or fallen behind.

### Flyway Migration Status

On startup, Flyway migration status is logged (`nexpay.flyway.log-status-on-startup: true`). Review startup logs after deployments to confirm migrations ran successfully.
