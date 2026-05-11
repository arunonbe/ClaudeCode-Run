# DevOps / Operations Analysis — ivr-ws_API

## 1. Technology Stack

| Component | Version / Details |
|---|---|
| Java | 21 (pom.xml lines 25–26) |
| Spring Boot | 3.5.7 (pom.xml line 28) |
| Spring Cloud | 2025.0.0 |
| Spring Cloud Azure | 5.23.0 |
| MSAL4J | 1.22.0 (Azure AD authentication) |
| Build tool | Maven (mvnw wrapper) |
| Container | Docker — `ivrapi-boot/Dockerfile` (Bellsoft Liberica OpenJRE 21 Alpine) |
| Parent POM | `prepaid-parent` v6.0.13 |
| Packaging | WAR (`ivrapi-war`) + Spring Boot JAR (`ivrapi-boot`) |
| Service type | SOAP web service (JAX-RPC / Apache Axis) + Spring Boot actuator |
| Config source | Azure App Configuration |

## 2. CI/CD Pipeline

### GitHub Actions Workflows (`.github/workflows/`)

**Primary Deployment** (`deployment.yml`):
```yaml
name: "IVR API Shared Services Deployment"
on:
  push:
    branches: ["main"]
jobs:
  build-and-deploy:
    uses: Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main
    with:
      APP_NAME: IvrWsAPI
      PACT_PACTICIPANT: ivr-ws-api
      TARGET_ROOT: "./ivrapi-boot"
      PUBLISH_TO_APIM: true
      EXTERNAL_APIM: true
      MAVEN_ARGS: '-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip'
      API_SUFFIX: ivr-ws-api
      BACKEND_SUFFIX: "/services/AccountTransactionInquiryServices"
      UPDATE_DEPENDENCIES: true
```
Key observations:
- Deployment triggers on push to `main` branch.
- Uses centralized Onbe CI workflow (`om-ci-setup`) — standardized pipeline.
- `PUBLISH_TO_APIM: true` and `EXTERNAL_APIM: true` — the WSDL is published to Azure API Management for external consumption.
- `EXCLUDE_STAGE: false` — staging environment is included in deployment.
- Tests are skipped (`-Dmaven.test.skip`).
- `UPDATE_DEPENDENCIES: true` — CI workflow auto-updates dependencies.
- `USE_ROLLOUT_CONFIG: false` — gradual rollout not configured.

**Per-Service Deployment Workflows** — individual GitHub Actions files exist for each service endpoint:
- `deployment-AccountBalanceInquiryServices.yml`
- `deployment-AccountTransactionInquiryServices.yml`
- `deployment-AchAccountSetupServices.yml`
- `deployment-AchInquiryServices.yml`
- `deployment-AchTransferSetupServices.yml`
- `deployment-ClaimableServices.yml`
- `deployment-MobilePhoneServices.yml`

These allow individual service endpoints to be deployed independently — useful for rolling updates to specific IVR functions.

**Re-deploy Workflow** (`redeploy.yaml`) — allows manual re-deployment without code changes.

**Code Coverage Build** (`code_cov_build.yml`) — separate build with coverage reporting.

**CodeQL SAST** (`codeql.yml`) — scheduled static analysis on self-hosted runners.

**Package Publish** (`github-package-publish.yml`) — publishes Maven artifacts to GitHub Packages.

**App Config Sync** (`app-config.yml`) — syncs configuration from Azure App Configuration.

## 3. Docker / Container Deployment

**Dockerfile** (`ivrapi-boot/Dockerfile`):
```dockerfile
FROM bellsoft/liberica-openjre-alpine:21
EXPOSE 80 9090 9091 50505
RUN apk update && apk upgrade --no-cache && apk add --no-cache jq curl bash ca-certificates
COPY target/*.jar /app/app.jar
COPY bindings/ca-certificates/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
RUN keytool -import -noprompt -trustcacerts -alias nam.wirecard.sys \
    -file /tmp/nam.wirecard.sys.crt \
    -keystore /usr/lib/jvm/jre/lib/security/cacerts -storepass changeit
ENTRYPOINT ["java", "-jar", "./app.jar"]
```

**Notable observations**:
- Base image: Bellsoft Liberica OpenJRE 21 on Alpine Linux — minimal footprint.
- Ports: 80 (HTTP), 9090, 9091 (likely management/metrics), 50505 (possibly JMX/debug).
- CA certificates: `nam.wirecard.sys.crt` is imported into the Java truststore — connecting to on-premises Wirecard/Northlane infrastructure (XML-RPC backends) that use a self-signed/internal CA.
- Dynatrace APM is injected at Kubernetes pod deployment time (comment on line 29).
- No `USER` instruction — container runs as root. Should add a non-root user for security hardening.

**docker-compose.yaml** (`ivrapi-boot/docker-compose.yaml`) — for local development.

## 4. Configuration Management

**Azure App Configuration** (`bootstrap.yaml`, `app-config.yml` workflow):
- Spring Cloud Azure App Configuration (`spring-cloud-azure-dependencies` v5.23.0)
- Configuration values for datasource URL, credentials, Director service URL loaded at runtime from Azure App Configuration
- Per-environment configs in `app-config/{prod,qa,staging}/appsettings.json`

**Key config files** (`ivrapi-boot/src/main/resources/config/`):
- `director-client.yaml` — Director service endpoint configuration
- `ecount-config.yaml` — eCount Core system configuration (boot address, agent name)
- `ivrws.yaml` — IVR-specific configuration

**`application.yml`** (lines 52–67):
```yaml
ecount:
  agent: 'B2CSTAGE'
  config:
    system:
      defaultSystem:
        bootAddress: url-from-app-config
        connectTimeout: 120000
        readTimeout: 120000
```
The `agent` name `B2CSTAGE` suggests the staging/dev environment may use a different agent than production. Confirm production uses a production agent name.

## 5. Session Management

`application.yml` line 31–34:
```yaml
server:
  servlet:
    session:
      timeout: 5m
```
Sessions expire after 5 minutes. For an IVR context this is appropriate as IVR calls are typically short. No explicit session persistence configuration is visible — sessions are in-memory (ephemeral on pod restart in K8s).

## 6. Health Checks and Observability

- Spring Boot Actuator endpoints exposed: `health`, `info` (`application.yml` lines 37–41)
- Custom `HealthCheck.java` in both `ivrapi-boot` and `ivrapi-war` — provides health check beyond Spring Boot actuator
- Dynatrace APM injection at Kubernetes deployment time
- Logging levels: `root: ERROR`, `com.citi: DEBUG`, `com.onbe: DEBUG` (`application.yml` lines 44–50)

**Concern**: `root: ERROR` logging suppresses all INFO/WARN logs at the root level. `com.citi: DEBUG` level produces verbose debug logs for the IVR service code. DEBUG-level logs in production may expose sensitive data (card numbers, etc.) from log statements in the service implementation classes.

## 7. Security Configuration

**TrustStore**: `ivrapi-boot/bindings/ca-certificates/nam.wirecard.sys.crt` — self-signed cert for on-premises infrastructure is bundled in the container image. This is a maintenance concern — if the cert expires or rotates, a new image build is required.

**Trivvy scan**: `.trivyignore` file present — container vulnerability scanning configured, with specific CVEs acknowledged/suppressed.

**Dependabot**: `.github/dependabot.yml` configured for automated dependency updates.

## 8. Legacy GitLab CI Artifacts

`.gitlab-ci.yml` at repo root — legacy GitLab pipeline configuration:
```yaml
SERVICE_NAME: IVRWS
PROJECT_SERVICE_PROTO: http
PROJECT_SERVICE_DEV_PORT: 9325
DEV_SERVICE_HOSTS: d-na-app02
QA_SERVICE_HOSTS: q-na-app01 q-na-app02
```
This is a legacy config from the Wirecard/Northlane era. It references on-premises hosts and HTTP protocol. The GitHub Actions deployment (`deployment.yml`) is the current pipeline; the GitLab CI config is vestigial but its `http` protocol reference confirms the service historically ran over plain HTTP on-premises.

## 9. Integration Tests

Postman collection and environment files in `ivrapi-war/integration-test/postman-tests/`:
- `API.postman_collection.json` — API test collection
- `QA.postman_environment.json` — QA environment configuration

These are manual Postman test collections, not automated in CI. They should be integrated into the CI pipeline via Newman.
