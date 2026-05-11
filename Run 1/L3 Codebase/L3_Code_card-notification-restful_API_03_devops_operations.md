# card-notification-restful_API — DevOps & Operations View

## Build & Packaging

### Build System
- **Maven** multi-module project (`mvnw` wrapper, Maven 3.x)
- Java **21** (LiberICA distribution; enforced in all POMs via `maven.compiler.source/target = 21`)
- Spring Boot **3.5.7**, Spring Cloud **2025.0.0**, Spring Cloud Azure **5.23.0**
- Parent BOM: `com.parents:prepaid-parent:6.0.13`

### Modules
| Module | Artifact | Packaging | Description |
|---|---|---|---|
| `card-notification-ws` | `card-notification-ws-3.0.1-SNAPSHOT.jar` | JAR | Business logic, domain models, JAX-RS resources, DAOs |
| `card-notification-war` | `cardnotification.war` | WAR | Legacy Tomcat deployment; wraps `card-notification-ws` |
| `card-notification-boot` | `card-notification-ws.jar` (finalName) | Spring Boot fat JAR | Modern containerised deployment; wraps `card-notification-ws` |

Both the WAR and the Boot JAR are maintained simultaneously. The Boot module is the current active deployment target (`deployment.yml` uses `TARGET_ROOT: "./card-notification-boot"`).

### Key Build Commands
```bash
./mvnw clean install -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip
```

Maven settings are stored in `.mvn/wrapper/settings.xml` (internal Nexus/Artifactory credentials expected).

### Code Coverage
- JaCoCo 0.8.12 configured in `card-notification-ws/pom.xml` for the `ws` module
- Coverage report: `card-notification-ws/target/site/jacoco/jacoco.xml`
- Codecov integration in `code_cov_build.yml`
- Only 3 unit tests exist in `CardNotificationServiceImplTest` (cache hit/miss/put only — core business logic is untested)

### Dependency Scanning
- **Dependabot** weekly Maven dependency updates (`.github/dependabot.yml`)
- **Trivy** container scan with CVE ignore list (`.trivyignore`, `.github/containerscan/allowedlist.yaml`)
- Ignored CVEs: CVE-2024-22262, CVE-2024-38816, CVE-2024-38819, CVE-2024-47072, CVE-2024-50379, CVE-2024-52316, CVE-2024-56337

---

## Deployment

### Current Production Deployment (Containerised / AKS)
1. GitHub Actions `deployment.yml` triggers on push to `main`
2. Delegates to shared workflow `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`
3. Builds Boot JAR from `./card-notification-boot`
4. Container image built from `card-notification-boot/Dockerfile`
5. Base image: `bellsoft/liberica-openjre-alpine:21`
6. Deployed to **Azure Kubernetes Service** (AKS) in QA and production environments
7. APIM publication: `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`, backend suffix `/Cardnotification/CardnotificationService`

### Legacy VM Deployment (Still Maintained)
- `vm-deployment.yml` workflow supports manual deployment of the WAR artifact to Windows VM
- Target: `azureuser@d-app02.nam.wirecard.sys` via SSH/SCP
- Destination: `C:/Users/azureuser/Documents/cardnotification.war`
- Context path: `cardnotification` (Tomcat)
- Service name in Windows: `CardNotificationSMSPull` (from `.gitlab-ci.yml`)

### Redeploy
- `redeploy.yaml` workflow manually redeploys QA AKS deployment via `Onbe/om-cd-setup/.github/workflows/redeploy.yaml@main`
- Application name: `cardnotificationapi`, environment: `qa`

### Docker Compose (Local Dev)
- `card-notification-boot/docker-compose.yaml`
- Port mapping: `9324:80`
- Profile: `local`
- Requires `AZURE_APP_CONFIG_CONNECTION_STRING` environment variable

### Exposed Ports
- `80` — HTTP (primary application port, `SERVER_PORT:80`)
- `9090`, `9091` — declared in Dockerfile EXPOSE but not assigned by application config
- `50505` — declared in Dockerfile EXPOSE (likely Dynatrace agent)

---

## Configuration Management

### Azure App Configuration (Primary)
- All environment-specific settings are externalised to **Azure App Configuration**
- Key prefix: `cardnotificationws/`
- Label: environment profile (e.g., `qa`, `staging`, `prod`)
- Refresh interval: `${AZURE_APP_CONFIG_REFRESH_INTERVAL:15m}` (default 15 minutes)
- Populated by `app-config.yml` GitHub Actions workflow when `app-config/**` files change
- `app-config/` directory contains JSON files for `qa`, `staging`, `prod` environments

### Azure Key Vault (Secrets)
- All database credentials and SAP MT credentials are stored in Key Vault
- Key Vault references are resolved by `spring-cloud-azure-starter-keyvault-secrets`
- In non-local environments, Managed Identity with `AZURE_MANAGED_IDENTITY_CLIENT_ID` is used

### Local Configuration Files (Defaults / Fallbacks)
| File | Purpose |
|---|---|
| `card-notification-boot/src/main/resources/application.yml` | Default properties; all runtime values are `url-from-app-config` placeholders |
| `card-notification-boot/src/main/resources/bootstrap.yaml` | Azure App Config bootstrap; read before application context starts |
| `card-notification-boot/src/main/resources/config/CardNotification.yaml` | Service-specific config (agent, DB name, source types, SAP MT URL) |
| `card-notification-boot/src/main/resources/config/ecount-config.yaml` | ECount system boot address / timeouts |
| `card-notification-boot/src/main/resources/config/director-client.yaml` | Director address |

### Configuration Properties Map
| Property | Description |
|---|---|
| `cardnotification.agent` | ECount agent identifier (B2C in prod, B2CSTAGE in QA/staging) |
| `director.address` | ECount Director HTTP endpoint (internal) |
| `cardnotification.sapmturl` | Sinch SMS MT endpoint |
| `cardnotification.sapmtusername` | Sinch auth username (Key Vault) |
| `cardnotification.sapmtpassword` | Sinch auth password (Key Vault) |
| `cardnotification.lasttransactionsourcetypes` | Pipe-delimited transaction source type filter |
| `spring.datasource.cbaseapp.*` | CBase application DB connection |
| `spring.datasource.ecountcore.*` | ECount core DB connection |
| `spring.datasource.jobsvc.*` | Job service DB connection |
| `ecount.config.system.defaultSystem.*` | ECount system boot configuration |

---

## Observability

### Health Check
- `GET /hc` — `HealthCheck` Spring MVC `@RestController` in `card-notification-boot`; returns `"OK"` string
- Spring Actuator: `health` and `info` endpoints exposed at `/actuator/health`, `/actuator/info`
- A second `HealthCheck` class exists in `card-notification-war` with the same endpoint, including verbose log output at INFO/ERROR/WARN to test log routing

### Logging
- **Log4j2** (Boot fat JAR excludes default Logback; uses `spring-boot-starter-log4j2`)
- Log levels (`application.yml`):
  - root: ERROR
  - `org.springframework`: ERROR
  - `com.citi`, `com.onbe`: DEBUG
  - Azure App Config / Spring Cloud Bootstrap: DEBUG
- In the WAR deployment, log4j2 config is loaded from `${CBASE_HOME_URL}/config/cardnotification/log4j2.xml` (external file system)
- **Critical**: Full MSISDN is logged at INFO level in `JaxRsCardNotificationService` (lines 113–116)

### Distributed Tracing / APM
- Dynatrace agent is expected to be injected at Kubernetes pod level ("No configuration required for Dynatrace, it's injected when the pod is deployed to K8S" — Dockerfile comment line 29)

### Metrics
- No custom metrics or micrometer instrumentation is present in the source code
- Spring Actuator provides basic JVM and HTTP metrics if actuator auto-configuration is enabled

### Integration Testing
- Postman collection in `card-notification-war/integration-test/postman-tests/API.postman_collection.json`
- One test: HTTP POST to `{{card-notification-restful_API-URL}}` with a sample `SMS_MO` XML payload
- Test asserts HTTP 200 response status only
- `code_cov_build.yml` runs Postman tests via Docker Compose (`docker-compose-test.yaml` — file not present in repo, likely in separate config repo)

---

## Infrastructure Dependencies

| Dependency | Type | Connection Detail | Required For |
|---|---|---|---|
| `P-LIS-DB03.nam.wirecard.sys:2231` (`cbaseapp`) | SQL Server | JDBC, Key Vault creds | Member profiles, SMS logs, affiliate data, SMS message templates |
| `P-LIS-DB02.nam.wirecard.sys:2231` (`EcountCore`) | SQL Server | JDBC, Key Vault creds | ECount core data |
| `P-LIS-DB01.nam.wirecard.sys:2231` (`jobsvc`) | SQL Server | JDBC, Key Vault creds | Configured but no direct DAO in this service |
| `prod.nam.wirecard.sys:8080` (Director) | HTTP/RPC | URL property | xSearch member lookup, EDevice account inquiry |
| `prod.nam.wirecard.sys:9003` (Order Service) | HTTP | URL property | Configured; not used in this service's code |
| `eu.sms.sdi.sinch.com` (Sinch) | HTTPS | Basic auth | Outbound SMS MT delivery |
| **Azure App Configuration** | PaaS | Managed Identity | All runtime configuration |
| **Azure Key Vault** | PaaS | Managed Identity | All credentials |
| **Azure Kubernetes Service** | PaaS | Container orchestration | Production runtime |
| **Azure Container Registry** | PaaS | GitHub Actions CI | Docker image storage |
| **Azure API Management** | PaaS | External APIM | API gateway/routing |
| `nam.wirecard.sys` CA | TLS Certificate | Imported to JRE truststore | Internal HTTPS connections |

---

## Operational Risks

1. **Dual Deployment Maintenance** — Both a Spring Boot JAR (`card-notification-boot`) and a Tomcat WAR (`card-notification-war`) are maintained. The WAR deployment targets `d-app02.nam.wirecard.sys` (legacy Windows VM). Running two parallel deployments increases operational complexity and risk of version divergence.

2. **Missing docker-compose-test.yaml** — The `code_cov_build.yml` workflow references `docker-compose-test.yaml` in `card-notification-war/`, which is not present in this repository. Integration tests will fail unless the file exists in an external config repo checkout step.

3. **`allow-bean-definition-overriding: true`** — `application.yml` enables Spring bean overriding, which can hide misconfiguration and make the application context non-deterministic in failure scenarios.

4. **`allow-circular-references: true`** — Also enabled in `application.yml`. Circular dependencies indicate architectural problems and can cause subtle startup ordering issues.

5. **Ehcache Persistence Directory** — `ehcache.xml` sets `persistence directory="java.io.tmpdir"`. In containers, `/tmp` is ephemeral and non-persistent. If the JVM crashes, cache state is lost (acceptable for this use case), but disk-based overflow could cause unexpected I/O.

6. **Connection Timeout 120,000ms** — ECount/Director RPC timeouts are 120 seconds (`RPCTimeout.properties`, `ecount-config.yaml`). An upstream Director outage will hold threads for 2 minutes before timing out, risking thread pool exhaustion.

7. **SAP/Sinch credential as static fields** — `sapMtusername` and `sapMtpassword` are `static` fields in `JaxRsCardNotificationService`. A Key Vault secret rotation would require an application restart to take effect.

---

## CI/CD

```
Push to main
  ├── deployment.yml      → java-workflow.yml (Onbe/om-ci-setup) → Build → Test → Docker Build → AKS Deploy (QA + Prod)
  ├── github-package-publish.yml → java-package-publish.yml (Onbe/om-ci-setup) → Publish JAR/WAR to GitHub Packages
  ├── app-config.yml      → app-config-call.yml (if app-config/** changed) → Push to Azure App Configuration
  └── code_cov_build.yml  → Maven build + Integration test + JaCoCo + Codecov upload

Manual Triggers
  ├── redeploy.yaml       → Redeploy QA AKS without rebuild
  ├── vm-deployment.yml   → Deploy WAR to Windows VM (legacy)
  └── codeql.yml          → CodeQL static analysis (also scheduled weekly Thursday 22:17 UTC)

GitLab CI (.gitlab-ci.yml)
  └── Delegates to northlane/development/application-development/configuration/ci-templates (legacy GitLab pipeline)
      Service name: CardNotificationSMSPull, context path: cardnotification
```

**Note**: Both GitHub Actions and a legacy GitLab CI pipeline are present, suggesting the repository migrated from GitLab to GitHub but the GitLab pipeline has not been removed.
