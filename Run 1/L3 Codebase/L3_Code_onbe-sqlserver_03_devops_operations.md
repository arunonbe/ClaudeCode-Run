# onbe-sqlserver — DevOps / Operations View

## Build System

The project uses Apache Maven with the `mvnw` wrapper. The build produces a Spring Boot JAR (`onbe-sqlserver-0.0.1-SNAPSHOT.jar`) and a Docker image.

| Component | Technology | Notes |
|---|---|---|
| Build tool | Maven 3.x via `mvnw` | Java 21 target |
| Parent POM | `spring-boot-starter-parent:3.3.5` | Does NOT use `onbe-spring-boot-parent` |
| Java version | 21 | Current LTS |
| Spring Boot | 3.3.5 | One minor version behind `onbe-spring-boot-parent` which uses 3.4.3 |
| Docker base image | `mcr.microsoft.com/mssql/server:2022-CU13-ubuntu-22.04` | Pinned CU for reproducible builds |

### Notable Build Configuration
- **Maven test skip**: `deployment.yaml` passes `-Dmaven.test.skip` — tests are not run in CI.
- **GitHub profile**: `-P github` activates the GitHub Packages authentication profile in `settings.xml`.
- **No `onbe-spring-boot-parent` inheritance**: The POM inherits directly from `spring-boot-starter-parent:3.3.5`. This means Onbe's centralised dependency management, BOM versions, and platform-wide plugin configurations do not apply. Any updates to Onbe's standard parent POM require manual backport.

## Deployment Pipeline

### GitHub Actions (`.github/workflows/deployment.yaml`)
The pipeline uses the reusable Onbe Java workflow: `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`

| Parameter | Value | Implication |
|---|---|---|
| `APP_NAME` | `onbesqlserver` | Docker image and deployment target name |
| `PACT_PACTICIPANT` | `onbesqlserver-api` | Registered in Pact broker but `VERIFY_PROVIDER_PACT: false` |
| `PUBLISH_TO_APIM` | `false` | No API Gateway publishing (correct — this is a DB container) |
| `CONTAINER_SCAN` | `false` | Container vulnerability scanning disabled |
| `EXCLUDE_STAGE` | `true` | No staging environment deployment |
| `MAVEN_ARGS` | `-s .mvn/wrapper/settings.xml -Dmaven.test.skip -P github` | Tests skipped; GitHub Packages auth active |

### Triggers
- Push to `main` branch.
- Pull request opened, synchronized, or labeled.

### Pipeline Stages (inferred from reusable workflow standard pattern)
1. Build Maven JAR (tests skipped).
2. Build Docker image (`docker build` using `Dockerfile`).
3. Push Docker image to container registry (Azure Container Registry or GitHub Container Registry).
4. No deployment stage (`EXCLUDE_STAGE: true`).

## Docker Configuration

### Dockerfile
```dockerfile
FROM mcr.microsoft.com/mssql/server:2022-CU13-ubuntu-22.04
ENV ACCEPT_EULA=Y
ENV MSSQL_PID=Developer
ENV MSSQL_AGENT_ENABLED=true
COPY scripts/ /scripts/
USER root
RUN chmod +x /scripts/entrypoint.sh
USER mssql
CMD [ "/opt/mssql/bin/sqlservr" ]
ENTRYPOINT [ "/scripts/entrypoint.sh" ]
```

Security controls:
- Privileges dropped to `mssql` user after file permission setup.
- No hardcoded passwords in the image layer.
- Base image is pinned to a specific CU (reproducible builds, controlled patching).

### Startup Sequence (`scripts/entrypoint.sh`)
1. Runs `permissions_check.sh` in the background.
2. Polls `sqlcmd SELECT 1` every 30 seconds until SQL Server is ready (~30–60 second startup overhead).
3. Executes `init-db.sql` with SA credentials from `MSSQL_SA_PASSWORD` env var.
4. Waits for background processes.

## Configuration Management

| Config Item | Location | Mechanism | Notes |
|---|---|---|---|
| SQL Server SA password | Runtime env var `MSSQL_SA_PASSWORD` | Kubernetes Secret / Docker `-e` flag | Not in image; must be injected at runtime |
| SQL Server edition | Dockerfile `ENV MSSQL_PID=Developer` | Build-time environment variable | Must be changed for production use |
| CDC configuration | `scripts/init-db.sql` | Init script runs at first startup | Idempotent only if run on a fresh database |
| Spring app name | `application.properties` | Spring standard | Only `spring.application.name=onbe-sqlserver` configured |

## Observability

| Aspect | Current State | Gap |
|---|---|---|
| Application logging | Windows Event Log / stdout | SQL Server logs to container stdout; accessible via `docker logs` |
| SQL Server Agent job status | Not monitored externally | CDC capture/cleanup job failures would go undetected |
| CDC lag monitoring | Not configured | No metric for how far behind CDC capture is relative to transaction log |
| Health check | Not defined in Dockerfile | `HEALTHCHECK` instruction should be added for container orchestration |
| Metrics | None | Spring Boot Actuator is not configured (no `spring-boot-starter-actuator` in POM) |

### Recommended Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=5 \
  CMD /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "${MSSQL_SA_PASSWORD}" -Q "SELECT 1" || exit 1
```

## Infrastructure Dependencies

| Dependency | Type | Required For |
|---|---|---|
| `MSSQL_SA_PASSWORD` | Runtime secret | Container startup and database initialization |
| `mssql-tools` | Included in base image | `sqlcmd` for health-check polling and init script execution |
| SQL Server Agent | Enabled via env var | CDC capture and cleanup jobs |
| GitHub Packages (npm/Maven) | CI dependency | Maven settings.xml authenticates for private packages |
| `Onbe/om-ci-setup` reusable workflow | CI dependency | `java-workflow.yml@main` is the pipeline definition |

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Container scan disabled | High | `CONTAINER_SCAN: false` — SQL Server image CVEs undetected; violates PCI DSS Req 6.3.3 |
| SA password in `sqlcmd` command line | Medium | Visible in `/proc/$PID/cmdline`; use config file approach instead |
| `MSSQL_PID=Developer` | Medium | Developer Edition — not licensed for production; must be changed before any production use |
| `init-db.sql` not idempotent | Low | Running on existing database (non-fresh container) will fail with `database already exists` error |
| No `HEALTHCHECK` in Dockerfile | Low | Container orchestrators (Kubernetes) cannot determine readiness; may route traffic before SQL Server is ready |
| Tests skipped in CI | Low | No automated regression testing for the Spring Boot component |
| Long startup polling (30s intervals) | Low | First poll check happens 30+ seconds after startup; adds to integration test execution time |
