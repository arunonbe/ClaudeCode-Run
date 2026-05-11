# az-appconfig-demo — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven 3.9.9 via Maven Wrapper (`mvnw` / `mvnw.cmd`; `.mvn/wrapper/maven-wrapper.properties` line 1).
- **Language/Runtime**: Java 21 (`pom.xml` lines 20–22). JRE image: `bellsoft/liberica-openjre-alpine:21` (`Dockerfile` line 1).
- **Parent POM**: `com.onbe.spring.boot:onbe-spring-boot-parent:0.0.22-SNAPSHOT` — an Onbe internal parent. Versioned as SNAPSHOT, which is a build stability risk.
- **Artifact**: `az-appconfig-demo.jar` (fat JAR via `spring-boot-maven-plugin`; `spring-boot.repackage.skip=false` in `pom.xml` line 24).
- **Docker image build**: Uses Spring Boot's built-in image builder (`spring-boot.build-image.skip=false`, `pom.xml` line 25; `USE_SPRING_BOOT_BUILD_DOCKER_IMAGE: true` in `deployment.yml` line 29). Docker tag pinned to `0.5.1` (`deployment.yml` line 30) — this is the buildpack version, not the application version.
- **SBOM**: CycloneDX Maven plugin included (`pom.xml` lines 112–114) — generates a Software Bill of Materials at build time. This is a positive security posture for dependency tracking.
- **Maven repositories**: Private GitHub Packages (`maven.pkg.github.com/onbe/onbe_maven_releases`, `onbe_maven_thirdparty`) plus Maven Central. Authentication via `GITHUB_USER` / `GITHUB_TOKEN` environment variables (`settings.xml` lines 45–66).
- **Dependency updates**: Dependabot configured for weekly Maven dependency updates (`.github/dependabot.yml`).
- **Tests**: `spring-boot-starter-test` present; Maven invoked with `-Dmaven.test.skip=false`. No test source files found in the repository — build will pass with 0 tests executed.

## Deployment

- **Platform**: Azure Kubernetes Service (AKS). Redeploy workflow (`redeploy.yaml`) targets application `appconfigdemo` in environment `qa` via `Onbe/om-cd-setup/.github/workflows/redeploy.yaml@main`.
- **Environments**: QA is the only explicitly named deployment environment. `EXCLUDE_STAGE: true` in `deployment.yml` line 23 skips stage deployment. Production deployment is not configured in this repository.
- **Container orchestration**: Kubernetes (via AKS); no Helm chart, Kustomize, or raw k8s manifests are present in this repository — deployment manifests are managed in the `om-cd-setup` shared repository.
- **Local development**: Docker Compose (`compose.yaml`) using `az-appconfig-demo:0.0.1-SNAPSHOT` image, with SPN credentials from a `.env` file.
- **Port**: `8080` (container and host, `compose.yaml` line 6).
- **Container user**: `user: "0:0"` in `compose.yaml` line 9 — container runs as root locally. Production AKS pod security context is defined in `om-cd-setup`.
- **Timezone**: `America/New_York` baked into buildpack image env (`pom.xml` lines 121–125).

## Configuration Management

- **Primary mechanism**: Azure App Configuration (PaaS). All environment-specific configuration is externalised; the application carries only bootstrap/startup config in `bootstrap.yaml` and `application.yaml`.
- **Config keys consumed**:
  - `database.cbaseapp.url`, `database.cbaseapp.username`, `database.cbaseapp.password` (the latter via Key Vault reference)
  - Feature flags: `FeatureA`, `FeatureB`
  - Azure App Config itself configured by environment variables: `AZURE_APP_CONFIG_ENDPOINT`, `AZURE_APP_CONFIG_ENABLED`, `AZURE_APP_CONFIG_KEY_FILTER`, `AZURE_APP_CONFIG_LABEL_FILTER`, `AZURE_APP_CONFIG_MONITORING_ENABLED`, `AZURE_APP_CONFIG_REFRESH_INTERVAL`, `AZURE_APP_CONFIG_TRIGGER_KEY`, `AZURE_APP_CONFIG_TRIGGER_LABEL`, `AZURE_APP_CONFIG_PUSH_TOKEN_NAME`, `AZURE_APP_CONFIG_PUSH_TOKEN_SECRET`, `AZURE_APP_CONFIG_FEATURE_FLAGS_ENABLED`, `AZURE_APP_CONFIG_FEATURE_FLAG_KEY_FILTER`, `AZURE_APP_CONFIG_FEATURE_FLAG_LABEL_FILTER`.
  - Identity: `AZURE_MANAGED_IDENTITY_CLIENT_ID` (qa/stage/prod), `AZURE_CLIENT_ID` + `AZURE_CLIENT_SECRET` (local).
- **Profile-based config activation**: `bootstrap.yaml` uses Spring profile activation (`on-profile: qa,stage,prod` and `on-profile: local`) to switch between Managed Identity and SPN credential modes.
- **Dynamic refresh**: Sentinel key monitoring with 15-minute default refresh interval and push-notification support (`bootstrap.yaml` lines 29–44). The sentinel key in local compose is `database.cbaseapp.username` (`compose.yaml` line 27) — using a data key (not a dedicated sentinel) as a change trigger is fragile.
- **QA settings file**: `app-config/qa/appsettings.json` — likely consumed by the `app-config.yml` workflow to publish config entries to Azure App Configuration under the `PetStoreAPI` prefix.
- **App Config publish prefix mismatch**: `app-config.yml` line 12 specifies `AZURE_APP_CONFIG_PREFIX: "PetStoreAPI"` but `compose.yaml` line 22 uses key filter `"/om-audit-logging-api/"`. This inconsistency suggests the file was adapted from the PetStore reference app without full alignment.

## Observability

- **Logging framework**: Logback via `onbe-spring-boot-starter-logback` (`pom.xml` line 52). Config: `classpath:/onbe-common-structured-logback-spring.xml` (Onbe shared config).
- **Log format**: Structured JSON (Logstash format) for both console and file output (`compose.yaml` lines 34–35: `LOGGING_STRUCTURED_FORMAT_CONSOLE: logstash`, `LOGGING_STRUCTURED_FORMAT_FILE: logstash`).
- **Log file**: `/log/appconfigdemo.log` on the Docker volume `log-data`.
- **Log levels**:
  - `application.yaml`: root=INFO, Spring=DEBUG, Azure=DEBUG, Onbe=DEBUG (development-oriented).
  - `compose.yaml` overrides: root=INFO, Spring=INFO, Azure=TRACE, Onbe=DEBUG, Reactor Netty=DEBUG — extremely verbose Azure SDK tracing.
- **Distributed tracing**: `MANAGEMENT_TRACING_ENABLED: false` in `compose.yaml` line 32 — tracing disabled in local compose. Production tracing configuration is not defined in this repository.
- **Feature flag logging**: `AppConfig.java` lines 33–38 schedule a log line every 5 minutes recording `FeatureA` and `FeatureB` states — provides a basic audit trail of feature flag changes.
- **Startup event logging**: `AppConfigController.java` lines 26–33 log resolved `DatabaseConfigProperties` and feature flag states at `ApplicationStartedEvent` — useful for confirming correct config resolution after deployment.
- **No metrics**: No Micrometer, Actuator metrics endpoints, or health indicators are configured in this repository.

## Infrastructure Dependencies

| Dependency | Type | Required For | Notes |
|---|---|---|---|
| Azure App Configuration (`as-app-configuration.azconfig.io`) | Azure PaaS | Runtime config | All environments; endpoint hardcoded in compose |
| Azure Key Vault | Azure PaaS | Secret resolution | `bootstrap.yaml` lines 62–64 |
| Azure Managed Identity | Azure IAM | Auth (qa/stage/prod) | `AZURE_MANAGED_IDENTITY_CLIENT_ID` |
| Azure SPN | Azure IAM | Auth (local) | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |
| GitHub Packages (`maven.pkg.github.com`) | Artifact registry | Build | `onbe_maven_releases`, `onbe_maven_thirdparty` |
| MSSQL Server (`petstore` DB) | Database | Application data | `appsettings.json` — demo/reference only |
| AKS cluster | Kubernetes | Deployment | Managed via `om-cd-setup` |

## Operational Risks

1. **SNAPSHOT parent POM** (`pom.xml` line 9: `0.0.22-SNAPSHOT`): Deployed builds may differ from release to release if the parent SNAPSHOT is updated mid-deployment cycle. This makes builds non-reproducible.
2. **Container scan disabled** (`deployment.yml` line 24): CVE detection on the container image is suppressed. Two CVEs are already allow-listed in `.github/containerscan/allowedlist.yaml` (`CVE-2024-24790` from paketo buildpacks, `CVE-2024-45337`). Disabling the scan means new CVEs in the base image or dependencies will not be caught.
3. **Root container in compose** (`compose.yaml` line 9: `user: "0:0"`): Local development runs as root. While likely not mirrored in AKS (pod security policy should enforce non-root), this habit normalises root execution.
4. **Sentinel key is a data key** (`compose.yaml` line 27: `AZURE_APP_CONFIG_TRIGGER_KEY: "/om-audit-logging-api/database.cbaseapp.username"`): Using an application data key as the refresh trigger means any routine username rotation will trigger a full config refresh. A dedicated sentinel key (e.g., `sentinel` with no data meaning) is the recommended pattern.
5. **`fail-fast: false`** (`bootstrap.yaml` line 25): If Azure App Config is unreachable at startup, the application starts with stale or default config. This could lead to production services running with incorrect configuration silently.
6. **No liveness/readiness probes defined** in this repository. The application provides only `GET /` returning a static string, which is not a meaningful health check for production use.
7. **External log volume** (`compose.yaml` line 39: `external: true`): The `log-data` volume must be pre-created before `docker compose up`. Missing volume causes startup failure with no clear error message in the compose output.

## CI/CD

| Workflow | Trigger | Action |
|---|---|---|
| `deployment.yml` | Push to `main`, PR opened/sync/labeled | Build, test, publish image, deploy to QA via `om-ci-setup/java-workflow.yml@feature/spring-boot-build-image` |
| `app-config.yml` | Push to `main`, manual dispatch | Publish Azure App Configuration entries for `PetStoreAPI` prefix via `om-ci-setup/app-config-call.yml@feature/CLOUDADM-948-app-config` |
| `codeql.yml` | Weekly (Wed 08:23 UTC), manual dispatch | CodeQL static analysis via `om-ci-setup/codeql-auto.yml@main` |
| `redeploy.yaml` | Manual dispatch only | Redeploy `appconfigdemo` to QA AKS without a new build |

Key observations:
- `deployment.yml` references a feature branch of `om-ci-setup`: `@feature/spring-boot-build-image` — this is not a stable ref and may break if the branch is rebased or deleted.
- `app-config.yml` also references a feature branch: `@feature/CLOUDADM-948-app-config` — same risk.
- `PACT_PACTICIPANT: appconfigdemo-api` is configured but `VERIFY_PROVIDER_PACT: false` — consumer-driven contract testing is not active.
- `PUBLISH_TO_APIM: false` — no APIM integration; this service is not a public/partner API.
- `CODEQL_QUALITY: true` — CodeQL quality gates are enabled in the build workflow.
- `UPDATE_DEPENDENCIES: false` — automated dependency bumping in the CI pipeline is disabled (Dependabot handles this separately).
