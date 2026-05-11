# clientapi_API — DevOps & Operations View

## Build & Packaging

- **Language**: Java 21 (compiler source/target both `21` in root `pom.xml`)
- **Build tool**: Apache Maven (wrapper at `.mvn/wrapper/maven-wrapper.properties`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.13`
- **Root artifact**: `com.citi.prepaid.webservices.clientapi:clientapi:3.0.6-SNAPSHOT` (multi-module POM)
- **Build output name**: `clientapiws` (set via `<deployment.name>` in `clientapi-boot/pom.xml`)

**Modules (build order):**
1. `clientapi-ws` — SOAP interface, request/response POJOs, validators (packaged as JAR)
2. `clientapi-impl` — Business service implementations (JAR)
3. `clientapi-war` — Legacy WAR packaging (for VM deployment)
4. `clientapi-boot` — Spring Boot fat JAR (`clientapiws.jar`) via `spring-boot-maven-plugin:repackage`
5. `clientapi-tester` — Commented out in root POM `<!-- <module>clientapi-tester</module> -->`
6. `clientapi-https` — Not listed in root POM modules; appears to be a legacy/separate module

**Key build flags:**
- `MAVEN_ARGS: ' -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip'` in main deployment workflow (tests skipped in CI)
- Maven enforcer plugin: no SNAPSHOT dependencies for external artifacts (local module SNAPSHOTs allowed)
- `ban-transitive-dependencies` enforcer rule is configured but `<fail>false</fail>` means it is advisory only

**Artifact publication:**
- GitHub Packages workflow (`github-package-publish.yml`) publishes both JAR and WAR artifacts on push to `main`
- Version can be overridden or auto-incremented via workflow dispatch inputs

## Deployment

**Two deployment paths exist in parallel:**

### Path 1: Kubernetes (AKS) — Primary/Modern
- **Trigger**: Push to `main` branch in `deployment.yml`
- **Workflow**: Delegates to `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`
- **Target**: `clientapi-boot` (Spring Boot fat JAR in container)
- **Container**: Docker image built from `clientapi-boot/Dockerfile`
  - Base: `bellsoft/liberica-openjre-alpine:21`
  - Exposes ports: 80 (HTTP), 9090, 9091, 50505
  - Custom CA certificate imported at build time: `nam.wirecard.sys.crt`
  - Dynatrace APM: injected at pod deployment (comment in Dockerfile line 29)
- **API Management**: Published to external APIM (`EXTERNAL_APIM: true`, `INTERNAL_APIM: false`) at suffix `client-api`
- **Backend path**: `/services/ClientApiWebServices`
- **Rollout config**: `USE_ROLLOUT_CONFIG: false` for main deployment
- **Environments**: QA (`EXCLUDE_STAGE: false`), Staging, Production
- **Redeploy**: Manual re-deploy to QA via `redeploy.yaml` workflow → `Onbe/om-cd-setup` pipeline with `application-name: clientapi`

### Path 2: Virtual Machine — Legacy
- **Trigger**: Manual `workflow_dispatch` with version tag in `vm-deployment.yml`
- **Target**: WAR file deployed to Windows IIS/Tomcat at `d-app02.nam.wirecard.sys` (dev VM)
- **Destination**: `C:/Users/azureuser/Documents/clientapiws.war`
- **Mechanism**: SCP from GitHub Actions self-hosted runner (`ubuntu-docker`) to Azure VM via `azureuser` account

### Per-Version API Deployments (V2, V3, V4)
- Separate workflows: `deployment-v2.yml`, `deployment-v3.yml`, `deployment-v4.yml`
- All target `clientapi-war` (WAR module), NOT `clientapi-boot`
- Published to APIM at suffixes `client-api/v2`, `client-api/v3`, `client-api/v4`
- Backend paths: `/services/ClientApiWebServices/v2`, `/v3`, `/v4`
- `EXCLUDE_STAGE: true` for all versioned workflows (not deployed to staging)
- `USE_ROLLOUT_CONFIG: true` for V2/V3/V4
- Use `java-workflow.yml@feature/VIST-1558_apim` branch (not `@main`), indicating these are in active development

## Configuration Management

- **Primary config store**: Azure App Configuration service (endpoint via `AZURE_APP_CONFIG_ENDPOINT` env var)
- **Secret store**: Azure Key Vault (database credentials only)
- **Config refresh**: 15-minute interval in production; controlled by `AZURE_APP_CONFIG_REFRESH_INTERVAL` env var
- **Profile-based config**: Spring profiles control which Azure App Config connection string vs Managed Identity is used; `local` profile uses connection string, all other profiles use Managed Identity
- **Key filter**: `clientapiws/` prefix in App Config; label matches Spring active profile (`spring.profiles.active`)
- **Environment-specific files**: `app-config/{prod,qa,staging}/appsettings.json` — these are committed to the repository and represent the App Config key-value payloads for each environment
- **Sensitive values in appsettings.json**: `key_vault_references` section stores KeyVault secret names (not values) — credentials never appear in source
- **Local development**: `docker-compose.yaml` runs the service on port 9100, requires `AZURE_APP_CONFIG_CONNECTION_STRING` env var
- **In-app config files** (classpath): `application.yml`, `bootstrap.yaml`, and 7 `config/*.yml` files provide defaults; all sensitive values are `from-app-config` placeholders

**Placeholder convention**: All values that come from Azure App Config are set to `from-app-config` in source-controlled YAML files (e.g., `bootstrap.yaml`, `clientapi.yml`). This makes it explicit that no real values are in source control.

## Observability

- **Logging framework**: Log4j2 (`spring-boot-starter-log4j2`; default logging excluded)
- **Log levels** (non-local profile): root=WARN, Spring=WARN, `com.citi`=INFO, `com.ecount`=INFO. Azure App Config bootstrap logs at DEBUG.
- **Request tracing**: `GlobalRequestIDInterceptor` (wraps all SOAP service handlers as AOP interceptor) generates a `GlobalRequestID` and writes to Log4j MDC via `Log4jMDCWriter` (`ClientApiWSConfiguration.java`)
- **Performance logging**: `logPerformanceInfo()` logs BEGIN/END timing with programId, packageId, transactionId, response code, and duration for every SOAP operation (`ClientApiWebServiceHandlerImpl.java`)
- **Audit logging**: `AuditMethodInterceptor` with `collectStatistics=true` wraps all SOAP handlers; `LoggingSecurityAudit` captures security check events
- **Health check**: `GET /hc` returns "OK" (`HealthCheck.java`); Spring Actuator exposes `/actuator/health` and `/actuator/info`
- **Monitor endpoint**: `MonitorFormController` with a ping test to OrderService (`MonitorConfiguration.java`) — accessible at the monitor URL, tests JMS/Instant Issue connectivity
- **APM**: Dynatrace (injected at pod level per Dockerfile comment); no explicit Dynatrace configuration in source
- **Ports**: 80 (main HTTP), 9090, 9091 (likely JMX/management), 50505 exposed in Dockerfile

**Gap**: No structured/JSON logging configuration found in source. Log4j2 configuration XML not present in this repo (likely in parent POM or external). Stack traces from `remoteEx.printStackTrace()` in service implementations write to stdout without structured formatting.

## Infrastructure Dependencies

| Dependency | Type | Purpose | Host/URL |
|---|---|---|---|
| `prod.nam.wirecard.sys:8080` | Internal HTTPS | ECount system boot address / Director | `appsettings.json` prod |
| `prod.nam.wirecard.sys:9003` | Internal HTTPS | OrderService (core card processing) | `appsettings.json` prod |
| `P-LIS-DB03.nam.wirecard.sys:2231` | SQL Server | cbaseapp database (security entities) | `appsettings.json` prod |
| `P-LIS-DB01.nam.wirecard.sys:2231` | SQL Server | jobsvc database | `appsettings.json` prod |
| `was-az1-recipientcacheadminapp-prod-ss.azurewebsites.net` | Azure Web App (HTTPS) | Redis admin service (international flags) | `appsettings.json` prod |
| Azure App Configuration | Azure SaaS | Externalised config | `AZURE_APP_CONFIG_ENDPOINT` |
| Azure Key Vault | Azure SaaS | Database credentials | Managed Identity |
| `login.northlane.com` | External HTTPS | Payment xContent root path | `appsettings.json` prod |
| `login.mypaymentvault.com` | External HTTPS | Recipient content URL | `appsettings.json` prod |
| GitHub Packages / Maven Registry | Build | Internal library dependencies (xplatform, order-common, api-security-lib, spring-dbctx) | `.mvn/wrapper/settings.xml` |
| `Onbe/om-ci-setup` (GitHub) | CI/CD | Reusable GitHub Actions workflows | `github.com/Onbe/om-ci-setup` |
| `Onbe/om-cd-setup` (GitHub) | CD | Reusable deployment/redeploy workflows | `github.com/Onbe/om-cd-setup` |

## Operational Risks

1. **Dual deployment paths with version skew**: The main `clientapi-boot` (Spring Boot / K8s) is the current deployment, but V2/V3/V4 versioned deployments still target `clientapi-war` (classic WAR). These use a feature branch workflow (`@feature/VIST-1558_apim`), not `@main`. This means V2/V3/V4 may be on a different CI/CD process than the main service.

2. **VM deployment still operational**: `vm-deployment.yml` deploys WAR to `d-app02.nam.wirecard.sys` (dev). If this machine is also used in QA/prod traffic routing, there is risk of inconsistent deployments.

3. **Tests skipped in CI**: `-Dmaven.test.skip` in `MAVEN_ARGS` for main deployment means no unit/integration tests run in the CI pipeline (`deployment.yml`, `github-package-publish.yml`).

4. **Azure App Config refresh lag**: With 15-minute refresh interval, configuration changes (e.g., updated database URLs, new program registrations) have up to a 15-minute propagation delay.

5. **`axis.disableServiceList=1`**: The Axis servlet has the WSDL/service listing endpoint disabled (security hardening), but the `wsdl.xml` committed to the repo (`wsdl.xml`) is a stub (`GenericOperation`) not matching the actual service — it may be used as APIM placeholder. This could cause WSDL-driven client generation to fail.

6. **Container scan allowlist**: `allowedlist.yaml` suppresses 9 CVEs from container scanning, including `CVE-2024-50379` and `CVE-2024-56337`. These should be tracked for resolution as Spring Boot and container base image updates become available.

7. **`spring.main.allow-circular-references: true`**: Enabled in `application.yml`. This is a Spring Boot 2.6+ breaking change workaround indicating the application has unresolved circular dependency issues.

8. **`spring.main.allow-bean-definition-overriding: true`**: Also enabled, indicating conflicts between JNDI-based XML bean imports and Boot-defined beans that have not been fully resolved.

## CI/CD

```
Push to main
    |
    +-- deployment.yml
    |       --> om-ci-setup/java-workflow.yml@main
    |           1. Checkout + Java 21 (liberica)
    |           2. mvn build (tests skipped)
    |           3. Docker build (clientapi-boot/Dockerfile)
    |           4. Publish image to container registry
    |           5. Deploy to AKS (QA + Prod)
    |           6. Publish WSDL to APIM (external)
    |
    +-- github-package-publish.yml
    |       --> om-ci-setup/java-package-publish.yml@main
    |           1. Build + publish JAR/WAR to GitHub Packages
    |
    +-- deployment-v2/v3/v4.yml (separate, using feature branch workflow)
            --> om-ci-setup/java-workflow.yml@feature/VIST-1558_apim
                Targets clientapi-war, publishes to APIM v2/v3/v4

Scheduled (weekly Friday):
    codeql.yml --> CodeQL SAST scan (Java)

Manual triggers:
    redeploy.yaml -- Redeploy to QA AKS
    vm-deployment.yml -- Deploy WAR to dev VM
    app-config.yml -- App Config update (details in workflow)
```

**Pact contract testing**: `PACT_PACTICIPANT: client-api` is configured but `VERIFY_PROVIDER_PACT: false` in all deployment workflows, meaning this service does not verify provider pacts (it is treated as a consumer only, or pact verification has been disabled).
