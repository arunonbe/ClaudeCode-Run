# om-payment-api — DevOps / Operations View

## Runtime Environment

`om-payment-api` is a Spring Boot 3.4.4 containerized application packaged as an executable JAR, deployed via Docker. It targets Java 21 (Temurin/BellSoft Liberica JRE) and exposes multiple ports.

## Container Architecture

### Dockerfile Analysis (`Dockerfile`)
```
Base image: bellsoft/liberica-openjre-alpine:21
Ports exposed: 80, 9090, 9091, 50505
JVM: -Xms512m -Xmx2048m
Cert import: certfile_qa.crt imported into JVM truststore (keytool)
Working dir: /usr/local/ompayment/
Entry point: startup.sh → java -jar application.jar
```

**Base Image Risk**: `bellsoft/liberica-openjre-alpine:21` is an Alpine-based image. The tag `:21` is mutable — if BellSoft releases a new patch (e.g., 21.0.7), the tag will resolve to the new version on the next build. For reproducibility and security scanning, the image should be pinned to a specific digest (`@sha256:...`).

**Certificate Import**: The QA certificate (`certfile_qa.crt`) is imported with `keytool -storepass changeit`. The `changeit` password is the default Java truststore password — in production environments this should be changed, though the truststore is inside the container and not externally accessible.

**Port Mapping**:
- 80 — application HTTP (Spring Boot server.port)
- 9090 — actuator management port (inferred from `ACTUATOR_PORT` ARG)
- 9091 — likely secondary management endpoint
- 50505 — Dapr sidecar communication port (Dapr default gRPC is 50001 in docker-compose but 50505 exposed in Dockerfile)

### Docker Compose Architecture (`docker-compose.yml`)

Two-container local deployment:
1. `om-payment-api` — the application container
2. `ompaymentapi-dapr` — Dapr sidecar (`daprio/daprd:latest`)

**Dapr Integration**: The application is configured to use Dapr:
- `DAPR_API_PROTOCOL: grpc`
- `DAPR_GRPC_ENDPOINT: http://ompaymentapi-dapr:50001`
- `DAPR_BASE_URL: http://ompaymentapi-dapr:3500`
- Dapr app ID: `OmPaymentAPI`

The `dapr-components/` directory (empty in this clone) would contain Dapr state store, pub/sub, and binding component definitions. Dapr's use here suggests the service is designed for cloud-native sidecar-based service mesh operation, which is architecturally distinct from the Tomcat WAR deployment managed by `om-east-deploy`. This confirms a hybrid deployment model is in transition.

**Host Entries in docker-compose**:
```yaml
extra_hosts:
  - "qa.nam.wirecard.sys:10.91.22.253"
  - "ppnaut.nam.wirecard.sys:10.91.22.254"
```
These hardcoded IP addresses for legacy `nam.wirecard.sys` hosts are baked into local development configuration. In containerized production deployments, DNS resolution should handle this — these entries indicate that local developer environments may not have access to internal DNS.

**Dapr image tag**: `daprio/daprd:latest` — using `latest` is a significant operational risk. The Dapr runtime version should be pinned to a specific version for reproducibility and to avoid breaking changes from Dapr API upgrades.

## Spring Profiles

| Profile | Usage | Notes |
|---|---|---|
| `dev` + `local` | Default active profiles | Active in `application.yml` lines 5-7 |
| `mock` | Integration testing | Uses sandbox JSON response files; no live backends |
| `qa` | QA environment | `application-qa.yml` overrides |
| `prod` | Production | `application-prod.yml` overrides |
| `staging` | Staging | `application-staging.yml` overrides |

The default active profiles are `dev` and `local` — a developer-facing configuration. For deployment, the profile must be explicitly overridden (via `SPRING_PROFILES_ACTIVE` environment variable in docker-compose).

## Health Checks and Observability

### Actuator Configuration (`application.yml` lines 47-72)
```yaml
management:
  endpoints:
    web:
      exposure.include: 'health,info'
      base-path: /
      path-mapping.health: hc
  endpoint:
    health:
      show-details: always
  health:
    db.enabled: true
    probes.enabled: true    # Kubernetes liveness/readiness
    livenessState.enabled: true
    readinessState.enabled: true
    rpcConnection.enabled: true
    urls:
      - service: 'director-service'
        url: https://uat.nam.wirecard.sys:8080/service/dispatch.asp
```

The health endpoint is mapped to `/hc` (not the default `/actuator/health`). This is a deliberate obfuscation of the standard actuator path — a minor security hardening measure.

`show-details: always` exposes full health component details including database connectivity status. This is useful for operations but should be restricted to authorized clients in production (should be `show-details: when_authorized`).

The `rpcConnection` health indicator checks Director Service connectivity — a custom health check for the primary eCount backend. This means the `/hc` endpoint will return `DOWN` if the Director Service is unreachable, enabling infrastructure health monitoring.

### Logging Configuration (`log4j2-spring.xml`)

- **Non-local profiles**: JSON layout (`JSONLayout compact="true" eventEol="true"`) — structured logging for log aggregation pipelines (ELK, Splunk).
- **Local/mock profiles**: Pattern layout with human-readable format.
- **Log level**: `INFO` root; `TRACE` for `org.zalando.logbook`.

HTTP request/response logging is provided by Zalando Logbook (`logbook-spring-boot-starter:3.11.0`). Configured for `TRACE` level on Logbook — meaning all HTTP body content is logged at `TRACE`. The logbook obfuscation (application.yml lines 103-107) masks `ssn`, `cardNumber`, and `cvv` in JSON body logs.

**Logbook path filter**: Only logs `GET`, `POST`, `PUT`, `DELETE` requests to `/v1/accounts/**` — debit endpoints may not be logged by Logbook depending on path configuration.

## CI/CD Integration

The service has GitHub Actions workflows (inferred from `.github/` directory). The pom.xml includes:
- `springdoc-openapi-maven-plugin` for API doc generation during integration test phase.
- `maven-failsafe-plugin` for integration tests using `*IntegrationSpec` (Spock).
- `jacoco-maven-plugin` for test coverage reporting.
- Spring Boot Maven plugin with `pre-integration-test` and `post-integration-test` goals to start/stop the application for integration testing with the `mock` profile.

The integration test approach (start the app, run Spock specs against it, stop the app) validates the full Spring context including all bean wiring and HTTP endpoints.

## Secrets Management in Operations

Credentials are injected via environment variables:
- `MANAGEPAYMENTAPI_CBASEAPPDB_USERNAME` / `MANAGEPAYMENTAPI_CBASEAPPDB_PASSWORD`
- `MANAGEPAYMENTAPI_JOBSVCDB_USERNAME` / `MANAGEPAYMENTAPI_JOBSVCDB_PASSWORD`
- `MANAGEPAYMENTAPI_ORDERSVCDB_USERNAME` / `MANAGEPAYMENTAPI_ORDERSVCDB_PASSWORD`
- `MANAGEPAYMENTAPI_ECOUNTCOREDB_USERNAME` / `MANAGEPAYMENTAPI_ECOUNTCOREDB_PASSWORD`

These are referenced in `application.yml` via `${ENV_VAR}` syntax. They are not present in any committed file — the environment variable injection model is correct. However, the source of these environment variables in production (Kubernetes Secrets, Azure Key Vault, HashiCorp Vault) is not documented in this repo and should be defined in the deployment infrastructure.

## Key Operational Risks

1. **SNAPSHOT dependency** (`accountmanagementapi:3.0.3-SNAPSHOT`): SNAPSHOT artifacts are non-reproducible. A fresh build of the same `om-payment-api` version could produce a different binary if `accountmanagementapi` SNAPSHOT changes.
2. **`trustServerCertificate=true`**: Disables SQL Server TLS validation — MITM risk on all four database connections.
3. **`daprio/daprd:latest`**: Unpinned Dapr sidecar image; breaking Dapr API changes could surface in production unexpectedly.
4. **JwtSecurityValidator always returns true**: No authorization enforcement — any caller can invoke any payment operation.
5. **`show-details: always` on health endpoint**: Exposes internal component health details without authorization; in production should require authentication.
