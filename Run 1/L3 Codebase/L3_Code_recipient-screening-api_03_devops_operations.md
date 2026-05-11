# DevOps / Operations View — recipient-screening-api

## Build System

Maven with Maven Wrapper (`mvnw`). Parent: `spring-boot-starter-parent:3.5.8`. Multi-module project:
- `om-recipientsanctioning-svc` — auto-generated OpenAPI client for the sanctions vendor API
- `recipientscreening-api` — OpenAPI-generated server stub (API interface)
- `recipientscreening-svc` — main implementation module

Java compiler target: **Java 25** (declared in parent pom.xml `<maven.compiler.source>25</maven.compiler.source>`).

The Dockerfile uses `bellsoft/liberica-openjdk-alpine:25`, confirming Java 25 is the runtime. Java 25 is not yet LTS (LTS cadence: 21, 25 is scheduled as LTS but not yet released at time of analysis). Note: Java 25 is the current LTS preview — this should be confirmed against the actual Java 25 release schedule and Onbe's approved Java version policy.

## CI/CD Pipeline

GitHub Actions workflow defined at `.github/workflows/deployment.yml`:
- **Triggers**: Manual dispatch, PR open/sync/label, push to `main`
- **Reuses**: `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` — the shared Java build/deploy pipeline
- **Key parameters**:
  - `APP_NAME: RecipientScreeningSvc`
  - `PACT_PACTICIPANT: recipient-screening-api` (Pact contract broker registered)
  - `VERIFY_PROVIDER_PACT: false` (this service is a consumer, not a provider in Pact terms)
  - `TARGET_ROOT: ./recipientscreening-svc`
  - `PUBLISH_TO_APIM: true`, `INTERNAL_APIM: true`, `EXTERNAL_APIM: false` — published to internal Azure API Management only
  - `API_SUFFIX: /recipientscreeningsvc`
  - `EXCLUDE_STAGE: false` — deploys to stage environment

A secondary workflow `.github/workflows/app-config.yml` manages Azure App Configuration deployment (likely the `appsettings.json` per-environment key injection).

CodeQL analysis is also present (`.github/workflows/codeql.yaml`), providing static application security testing in the pipeline.

The repository carries recent deployment tags: `20260409.181703`, `20260409.183416`, `20260426.042220`, indicating active production deployments as recently as April 2026.

## Deployment Model

Containerized microservice deployed via Azure Container Apps or AKS (inferred from the `om-ci-setup` composite action patterns). Per-environment configuration is supplied via Azure App Configuration references (`appsettings.json` per environment: `qa/`, `stage/`, `prod/`).

Runtime configuration injection:
- OAuth 2.0 credentials → Azure Key Vault (referenced as `key_vault_references` in appsettings.json)
- Database credentials → Azure Key Vault
- Database URLs → inline in appsettings.json (SQL Server in the `wirecard.sys` domain)

Exposed ports: 80 (HTTP), 9090 (actuator), 9091 (secondary), 50505 (debug/agent port — notable for production exposure).

## Runtime Details

- **Base image**: `bellsoft/liberica-openjdk-alpine:25`
- **Framework**: Spring Boot 3.5.8
- **Java version**: 25
- **JVM flags**: `-XX:FlightRecorderOptions=stackdepth=256 -Xms512m -Xmx2048m -Duser.timezone=America/New_York`
- **Timezone**: America/New_York (hardcoded — potential issue for global deployments)
- **User context**: Docker image creates a non-root `app` user and group — good security practice

The Dockerfile includes `jq` and `curl` installed via `apk`, which are common operational utilities but also expand the container attack surface. These should be reviewed for necessity in production images.

## Secrets Management

All secrets are stored in Azure Key Vault and referenced via the application's `key_vault_references` configuration block. No secrets are committed to source code. The Key Vault reference pattern is:
- `SHARED-RECIPIENTSANTIONING-SVC-CLIENT-ID` → OAuth client ID
- `SHARED-RECIPIENTSANTIONING-SVC-CLIENT-SECRET` → OAuth client secret
- `CBASEAPP-DB-USERNAME`, `CBASEAPP-DB-PASSWORD` → SQL Server credentials
- `ECOUNTCORE-DB-USERNAME`, `ECOUNTCORE-DB-PASSWORD` → SQL Server credentials

This is a well-structured secrets management approach consistent with Azure cloud-native patterns.

## Observability

- **JFR**: Java Flight Recorder enabled with `stackdepth=256` — supports profiling and performance analysis
- **Spring Actuator**: Port 9090 (separate from application port 80)
- **Structured logging**: SLF4J via `LoggerFactory`, with parameterized log messages (appropriate for log injection prevention)
- **Pact broker integration**: Consumer-driven contract testing registered (`PACT_PACTICIPANT`)

Missing: explicit mention of Azure Application Insights, Prometheus scraping configuration, or distributed tracing (OpenTelemetry). These should be confirmed in the `om-ci-setup` shared workflow.

## EOL / CVE Concerns

- **Java 25**: Cutting-edge — confirm LTS status and patch cadence.
- **Spring Boot 3.5.8**: Recent; no known critical CVEs at time of analysis.
- **`trustServerCertificate=true`** in SQL connection strings: Disables SQL Server certificate validation. This is a security misconfiguration — the SQL Server certificate should be properly trusted via the Java truststore rather than bypassed.
- **Port 50505 exposed**: In the Dockerfile `EXPOSE 50505` — if this is a Java debug/JDWP port, it must never be reachable from external networks in production.
