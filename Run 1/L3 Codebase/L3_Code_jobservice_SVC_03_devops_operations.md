# DevOps / Operations View — jobservice_SVC

## Build System

| Attribute | Value |
|---|---|
| Build tool | Maven (mvnw wrapper) |
| Java | 21 (source and target in root pom.xml) |
| Maven parent | `prepaid-parent:6.0.13` |
| Version | `4.0.7-SNAPSHOT` |
| Packaging | WAR (two deployable WARs: `service.war`, `JobAgentService.war`) |
| Modules | `jobmanager-svc`, `jobmanager-war`, `jobmanager-client`, `jobagent-svc`, `jobagent-war` |
| Spring | 6.2.11 (`spring-core`, `spring-test`) |
| Jakarta | `jakarta.xml.bind-api:4.0.2`, `jakarta.activation-api:2.1.3` (Jakarta EE namespace) |

### JMS Provider Selection

Four JMS filter profiles (`activemq`, `ibmmq`, `tibcojms`, `weblogicjms`) exist in both `jobmanager-war/src/main/filters/` and `jobagent-war/src/main/filters/`. The active profile is selected at Maven build time. The `.gitlab-ci.yml` configuration does not specify a JMS profile, suggesting the default profile in `prepaid-parent` determines this. Production evidence (TIBCO properties in `PropertyPlaceholder.xml`) indicates TIBCO JMS is the active provider.

## Containerisation

### JobAgent Dockerfile (`jobagent-war/Dockerfile`)

- **Base image**: `bellsoft/liberica-openjre-alpine:21`
- **Tomcat**: 10.1.28 (downloaded from archive.apache.org at image build time — internet dependency)
- **User**: Non-root (`PPA_QA_MQ` user in `NAM` group, UID/GID 1000) — correct security practice
- **TLS certs**: QA certificate (`certfile_qa.crt`) imported into the JVM truststore during build
- **JVM flags**: Multiple `--add-opens` for legacy reflection access on Java 21 (unavoidable with old SOAP/JMS libraries)
- **Exposed ports**: 80

### JobManager Dockerfile (`jobmanager-war/Dockerfile`)

- **Base image**: `bellsoft/liberica-openjdk-alpine:21` (note: JDK, not JRE — larger image than needed for runtime)
- **Tomcat**: 10.1.19 (older than JobAgent's 10.1.28 — version drift)
- **User**: No non-root user created — runs as root (security risk)
- **War target**: Deploys as `ROOT.war` (context root `/`)

### Key Docker Issues

| Issue | Severity | Detail |
|---|---|---|
| JobManager runs as root | High | No USER instruction in Dockerfile — container process is root |
| Tomcat version mismatch | Medium | JobAgent: 10.1.28; JobManager: 10.1.19 |
| Runtime Tomcat download | Medium | `curl` downloads Tomcat during `docker build` — network dependency; build fails if archive.apache.org is unavailable |
| JDK vs JRE in JobManager | Low | JDK image is larger than needed; JRE is sufficient for runtime |

## CI/CD Pipelines

### Dual Pipeline Architecture

The service has both a **GitLab CI** pipeline (legacy) and **GitHub Actions** pipelines (new):

#### GitLab CI (`.gitlab-ci.yml`) — Legacy/Active
```
include: 'northlane/development/.../ci-templates/maven.gitlab-ci.yml'
SERVICE_NAME: JobAgent
SERVERS: q-na-app017 q-na-app018
```
Deploys `JobAgentService.war` to on-premises Tomcat servers via the `maven.gitlab-ci.yml` shared template. This appears to be the legacy deployment path.

#### GitHub Actions — New

| Workflow | Purpose |
|---|---|
| `cicd-deployment.yml` | Main CI/CD: build → deploy JobManager WAR to `q-app09`, deploy JobAgent WAR to `q-app08`+`q-app09` |
| `vm-deployment.yml` | Downloads `accountmanagementapi-war` from GitHub Packages and SCP-deploys to `d-app02.nam.wirecard.sys` |
| `redeploy-jobagentsvc.yaml` | Re-deploy JobAgent only (quick redeployment without rebuild) |
| `codeql.yml` | Weekly CodeQL security scanning |
| `github-package-publish.yml` | Publishes artifacts to GitHub Packages |

#### GitHub Actions Deployment Detail (`cicd-deployment.yml`)

The deployment uses `om-ci-setup/.github/workflows/deploy-east.yml@main`, which:
1. Stops the Tomcat Windows service (`Apache Tomcat - JobManager` or `Apache Tomcat - JobAgent`)
2. Backs up to `D:\c-base\backup`
3. Cleans webapps and work directories
4. Copies new WAR
5. Restarts the service

**Target servers**:
- `q-app09.nam.wirecard.sys` — JobManager WAR (`service.war`)
- `q-app08.nam.wirecard.sys` + `q-app09.nam.wirecard.sys` — JobAgent WAR

**Deployment credentials**: `NAM\qa_east_deploy` with `QA_EAST_DEPLOY_PASSWORD` secret.

**Java version selection**: The `cicd-deployment.yml` workflow supports selecting Java 8 or 21, with different server names/paths for each version — indicating an active Java 8 → Java 21 migration is in progress, with both versions potentially running in parallel.

## Configuration Management

Configuration is file-based, loaded from `${CBASE_HOME_URL}/config/`:
```
${CBASE_HOME_URL}/config/director-client.properties
${CBASE_HOME_URL}/config/service/jobManager/JobManagerSVC.properties
${CBASE_HOME_URL}/config/service/workflowservice/workflowservice.properties
${CBASE_HOME_URL}/config/service/payment/payment.properties
${CBASE_HOME_URL}/config/service/prepaidJMS/tibcojms.properties
```

In Docker, `CBASE_HOME_URL=file:///cbase` means configuration must be bind-mounted into the container at `/cbase/config/`. This is a legacy configuration management pattern with no equivalent to Spring Boot external config or Azure App Configuration.

There is no secrets management integration (no Key Vault, no Vault, no environment variable injection for database passwords). Credentials are likely embedded in the property files on the server filesystem — a PCI DSS concern (Req 8.3, credential management).

## Observability

- **Logging**: `log4j2.xml` in test resources (implies log4j2 is the logging framework). No production log4j2 configuration is visible in the repository, suggesting it is provided at runtime from `CBASE_HOME_URL/config/`.
- **No metrics**: No Micrometer, no Prometheus, no OpenTelemetry. This service predates modern observability tooling.
- **No health endpoints**: No Spring Boot Actuator (this is a legacy Spring/Tomcat WAR, not Spring Boot). Health checks rely on the `JobAgentService/dispatch.asp` URL probe defined in `.gitlab-ci.yml`.
- **No distributed tracing**: No correlation IDs, no trace context propagation.

## Infrastructure Dependencies

| Dependency | Type | Purpose |
|---|---|---|
| `q-app08/q-app09.nam.wirecard.sys` | Windows Server / Tomcat | Production deployment hosts |
| `d-na-app014` / `q-na-app017/018` | On-prem servers | Legacy GitLab CI deployment targets |
| SQL Server (jobsvc DB) | Database | Job/action state store |
| SQL Server (cbaseapp DB) | Database | Cardholder data store |
| Director Service (`nam.wirecard.sys:8080`) | Internal service | Data source resolution, system configuration |
| TIBCO JMS broker | Message broker | Job execution queue |
| Repository Service | Internal service | File storage for batch files and reply files |
| Account Service (XmlRPC) | Internal service | Card/account operations |
| Payment Service (XmlRPC) | Internal service | Payment certificate creation |

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| No zero-downtime deployment | High | WAR deployment requires Tomcat service stop/start — service unavailable during deploy |
| Credentials in filesystem config files | High | No secrets manager; database and JMS credentials stored in `CBASE_HOME_URL/config/` files on server |
| Java 8 / Java 21 dual version in flight | Medium | Both Java versions may be deployed simultaneously with different server names; coordination required |
| Running as root (JobManager Docker) | High | Security violation; container escape would give root on host |
| No automated rollback | Medium | `deploy-east.yml` backs up but no automatic rollback on startup failure |
| No health-based deployment gate | Medium | Deployment proceeds without verifying the service starts successfully after WAR replacement |
