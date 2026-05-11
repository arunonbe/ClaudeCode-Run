# DevOps / Operations View — cross-border-transfer-service_SVC

## 1. Build System

| Attribute | Value |
|---|---|
| Build tool | Maven (Maven Wrapper `mvnw` / `mvnw.cmd`) |
| Java target | Java 21 (`pom.xml` lines 35–36: `maven.compiler.source/target=21`) |
| Parent POM | `com.parents:prepaid-parent:6.0.12` |
| Artifact version | `3.2.0-SNAPSHOT` |
| Multi-module | 10 modules (rest-controller, service, config, data, cambridge-client, db-app, db-scripts, persistence, batch, qa) |
| Checkstyle | `checkstyle.xml` + `suppressions.xml` enforced via Maven compiler plugin |
| Snapshot enforcement | `requireReleaseDeps` enforcer in place — SNAPSHOTs blocked except for internal `com.parents`, `com.ecount`, `com.wirecard.*` groups |
| Test framework | JUnit (unit) + Spring Boot Test (integration in `cross-border-transfer-service-qa`) |
| Code coverage | JaCoCo (configured via parent POM) |
| Dependency updates | Weekly automated Dependabot PRs (`dependabot.yml`) targeting Maven ecosystem |

### Build Command
```bash
./mvnw clean install -s ./.mvn/wrapper/settings.xml
```
(Note: `MAVEN_BUILD_OPTS="-Dmaven.test.skip"` is set in all CI stages in `.gitlab-ci.yml`, meaning tests are routinely skipped in pipeline builds.)

## 2. Deployment Artifacts

| Artifact | Type | Module |
|---|---|---|
| `cross-border-transfer-service-rest-controller-*-exec.jar` | Spring Boot executable JAR | REST API runtime |
| `cross-border-transfer-service-batch-*-exec.jar` | Spring Boot executable JAR | Batch jobs runtime |
| `cross-border-transfer-service-db-app-*-exec.jar` | Spring Boot executable JAR | Liquibase DB migration runner |
| Docker image | OCI image (via Dockerfile) | REST controller only |

## 3. Containerization

- **Base image**: `azul/zulu-openjdk-alpine:21` (`Dockerfile` line 6).
- **Layered JAR**: Spring Boot layertools used for optimized image layers (`Dockerfile` line 15).
- **Port**: `EXPOSE 80` / `SERVER_PORT=80`.
- **JVM flags**: `JDK_JAVA_OPTIONS="--add-opens=java.base/java.lang=ALL-UNNAMED"` (`Dockerfile` line 25).
- **TLS keystore**: `config/server.jks` copied into the image at build time (`Dockerfile` line 12) — keystore committed to repository.
- **Dapr sidecar**: `docker-compose.yml` includes a `daprio/daprd:latest` sidecar for potential actor/pub-sub patterns; port 3500 mapped but there is no Dapr-specific application code visible in current source.
- **Debug port**: 8000 exposed in `docker-compose.yml` (line 21–22) for remote debugging — must not be exposed in production.

## 4. CI/CD Pipeline

### GitHub Actions (primary — Onbe platform)
- File: `.github/workflows/deployment.yml`
- Trigger: push or PR to `main` branch (path-filtered, ignoring `.mvn/**`, `.github/**`, `mvnw`, `README.md`).
- Reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` with `secrets: inherit`.
- Key pipeline parameters:
  - `APP_NAME: CrossBorderTransferServiceSVC`
  - `TARGET_ROOT: ./cross-border-transfer-service-rest-controller` (only REST controller deployed as container)
  - `PUBLISH_TO_APIM: true` — publishes API spec to APIM
  - `EXCLUDE_STAGE: true` — staging environment is skipped
  - `UPDATE_DEPENDENCIES: true`, `UPDATE_PARENT_VERSION: true` — automatic dependency bumping
  - `MAVEN_ARGS: '-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip'` — **tests skipped in deployment pipeline**
- Redeploy workflow: `.github/workflows/redeploy.yaml` (manual trigger)
- Package publish: `.github/workflows/github-package-publish.yml`

### GitLab CI (legacy — likely for former on-premises deployment)
- File: `.gitlab-ci.yml` — includes `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml`
- `SERVICE_NAME: CBTS` (Windows service name)
- All Maven phases have `"-Dmaven.test.skip"` — tests never run in CI
- Dev and QA hosts not populated (empty strings)

### CodeQL Static Analysis
- File: `.github/workflows/codeql.yml`
- Schedule: weekly (Sunday 20:09 UTC) + manual dispatch
- Uses `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`

## 5. Configuration Management

- **Spring Cloud Config**: Both the REST controller and batch modules use Spring Cloud Config Server (`bootstrap.yml` lines 3–4: `uri: http://localhost:9990/config-server`). Config server credentials are hardcoded in bootstrap YAML (`password: s3cr3t`).
- **Profile-based config**: `application-qa.yml` in `cross-border-transfer-service-config` provides QA-specific overrides; all secrets (DB password, Cambridge signatures, SMTP password) are in this file — which is source-controlled.
- **External secrets**: No Vault, AWS Secrets Manager, or Azure Key Vault integration is present. All operational secrets live in YAML files.

## 6. Observability

### Health Check
- Spring Boot Actuator exposed at `/hc` (path mapped from `/health`) (`application-qa.yml` lines 88–94).
- Circuit breaker health included: `management.health.circuitbreakers.enabled: true`.
- Only `health` and `info` endpoints exposed.

### Logging
- Framework: SLF4J / Logback (Spring Boot default).
- QA config sets all Spring and CBTS classes to `DEBUG` level (`application-qa.yml` lines 22–23).
- No structured logging (JSON) configured; plain text format.
- Log file paths commented out in QA config (lines 14–21); logs go to console only unless config server overrides.
- Key log statements: `AutomaticRateCancellationProcessor` line 97 logs rate cancellation failures at `WARN` with exception.

### Tracing / Correlation
- Correlation ID filter: `CorrelationIdFilterConfiguration.java` propagates X-Correlation-ID header.
- `TraceFilter.java` + `CustomTraceRepository.java` provide custom HTTP trace capture.
- No distributed tracing (Zipkin/Jaeger/OpenTelemetry) is configured.

### Metrics
- `MonitoringConfiguration.java` is **entirely commented out** (lines 1–47) — custom health aggregator and Jackson serializer disabled.
- No Prometheus/Micrometer metrics export configured beyond Actuator defaults.

### Circuit Breakers (Resilience4j)
- Configured in `application-qa.yml` lines 100–147.
- Instances: `cancel-rate`, `beneficiary-create`, `beneficiary-rules`, `beneficiary-view`, `remitter-create`, `remitter-view`, `spot-service`, `token-service`, `beneficiary-banks`.
- Default: sliding window 100 calls, failure threshold 40%, wait in open state 60 seconds, auto-transition half-open enabled.
- `CambridgeGatewayCommunicationException` is the recorded failure class (`application-qa.yml` line 128).

## 7. Infrastructure

- **Database**: SQL Server at `Q-LIS-DB03.nam.wirecard.sys:2231`, database `CBTS`, user `cbts_data` — the hostname `wirecard.sys` suggests legacy infrastructure pre-dating the Onbe rebrand.
- **Connection pool**: HikariCP, max 50 connections, min-idle 10, connection test query `SELECT 1`.
- **Transaction timeout**: 30 seconds (`application-qa.yml` line 79).
- **Mail relay**: Mailgun SMTP at `smtp.mailgun.org:587` (`application-qa.yml` lines 65–73). Credentials (API key embedded in password) in plaintext YAML.
- **EhCache heap**: 200 MB JVM heap for beneficiary rules cache (`ehcache3.xml`).
- **JPA dialect**: `SQLServer2012Dialect` — may be outdated for modern SQL Server versions.
- **ORM**: Hibernate / Spring Data JPA; `show-sql: true` in QA (logs all SQL — performance/security concern in production).
- **Liquibase**: Schema migrations managed but **disabled in application** (`liquibase.enabled: false` in `application-qa.yml` line 53); run separately via `cross-border-transfer-service-db-app` module.

## 8. Batch Operations

Five Spring Batch jobs, each launchable via command-line (`--spring.batch.job.names=<job-name>`):

| Job Name | Launch Script | Direction | SFTP Partner |
|---|---|---|---|
| `import-cambridge-recon-file` | `import-cambridge-recon-file.sh` | Inbound | Cambridge |
| `import-cambridge-reject-file` | `import-cambridge-reject-file.sh` | Inbound | Cambridge |
| `automatic-rate-cancellation` | `automatic-rate-cancellation.sh` | Internal | None |
| `publish-recon-file` | `publish-cambridge-recon-file.sh` | Outbound | Cambridge / eCount |
| `publish-reject-file` | `publish-cambridge-reject-file.sh` | Outbound | Cambridge / eCount |

Batch init profile creates required working directories:
```bash
java -jar cross-border-transfer-service-batch-*-exec.jar --spring.profiles.active=init
```

## 9. Risks and Operational Concerns

| Risk | Severity | Detail |
|---|---|---|
| Tests skipped in all CI/CD pipelines | High | `MAVEN_TEST_SKIP` in all CI configs; no test gate before deployment |
| QA credentials in Git | Critical | DB password, Cambridge API signatures, SMTP API key in `application-qa.yml` (lines 26–385) |
| PGP private key in Git | Critical | `0x6392B27D-sec.asc` in `cross-border-transfer-service-config/src/main/resources/pgp/` |
| JKS keystore in Git | High | `config/server.jks` and `config/truststore.jks` committed to `cross-border-transfer-service-rest-controller/` |
| No secrets manager integration | High | All runtime secrets in plain YAML files |
| Debug port 8000 in docker-compose | Medium | Remote debug port exposed — must be removed or guarded for production |
| `show-sql: true` in QA config | Medium | Hibernate logs all SQL; risk if this profile is used in production or log shipping is enabled |
| Dapr sidecar with no application code | Low | Dapr dependency adds image complexity and attack surface without demonstrated use |
| Spring Cloud Config password hardcoded | Medium | `bootstrap.yml` has `password: s3cr3t` for config server — likely placeholder but present in source |
| Suppressed CVEs | Medium | Four Spring Framework CVEs suppressed in `.trivyignore` and `allowedlist.yaml` (CVE-2024-22262, CVE-2024-34750, CVE-2024-38816, CVE-2024-38821) — review required for PCI DSS vulnerability management obligation |
