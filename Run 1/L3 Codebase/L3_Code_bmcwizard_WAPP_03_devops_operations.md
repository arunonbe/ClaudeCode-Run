# bmcwizard_WAPP — DevOps & Operations View

## Build & Packaging

- **Build tool:** Apache Maven 3.x (Maven Wrapper present: `.mvn/wrapper/maven-wrapper.properties`).
- **Output artifact:** `wizard.war` (Maven `<finalName>wizard</finalName>` in `pom.xml`).
- **Java version:** Java 8 (`maven.compiler.source=1.8`, `maven.compiler.target=1.8`). This is confirmed in all CI workflows.
- **Artifact version:** `2.1.4-SNAPSHOT` (pom.xml line 14). Still on SNAPSHOT — no released version in the branch.
- **Parent POM:** `com.citi.prepaid.web:webapp-parent:10.0.0` — a private internal parent, resolving common plugin defaults. Not publicly available.
- **Source encoding:** `Cp1252` (Windows-1252) — non-standard; should be UTF-8 for portability.
- **Code generation:** xdoclet (`maven-antrun-plugin`) runs at `generate-sources` phase to produce `struts-config.xml` and Struts validation XML from Java annotations in all `**/*.java` files. This means build is sensitive to xdoclet classpath.
- **Code coverage:** JaCoCo plugin (`0.8.12`) configured; report generated at `verify` phase.
- **Static analysis:** Parasoft plugin (`maven-parasoft-plugin:3.13`) present in build.
- **Test framework:** JUnit Jupiter 5.11.1 + Mockito 4.0.0 + AssertJ 3.23.1.
- **Local dev server:** Jetty 6.0.2 (`maven-jetty-plugin`) — very old; uses `src/test/resources/jetty-env.xml` for JNDI.
- **Maven profiles:** `local` (default), `localc`, `dev`, `stage`, `prod` — all use `D:` as config drive. No profile-specific dependency changes; profiles only switch `target.env` and `cbase.config.drive`.
- **Maven settings:** `.mvn/wrapper/settings.xml` references internal artifact repository (private Nexus/Artifactory presumed).

## Deployment

- **Target server:** Apache Tomcat 8.5, Windows Server, service name `Apache Tomcat 8.5 Workbench`.
- **Deployment path:** `D:\c-base\opt\tomcat\servers\Workbench\webapps\` (from `cicd-wizard-deployment.yml`).
- **Deployment process (GitHub Actions):**
  1. Build WAR with Java 8.
  2. Stop Tomcat Windows service.
  3. Backup existing WAR/work directory to `D:\c-base\backup`.
  4. Delete `wizard.war` and `wizard/` expanded directory and Tomcat `work/` directory.
  5. Copy new `wizard.war` to webapps.
  6. Start Tomcat Windows service.
- **Environments:**
  - **Stage:** `u-az-app05.nam.wirecard.sys` — deploy user `NAM\qa_east_deploy`.
  - **Cert:** `q-na-app05.nam.wirecard.sys` — deploy user `NAM\qa_east_deploy`.
  - **Production:** referenced in `cicd-deployment.yml` as optional (`deploy_to_production` input) but production server details are in the shared reusable workflow (`Onbe/om-ci-setup`), not directly visible here.
  - **Dev (GitLab legacy):** `d-na-app002` (from `.gitlab-ci.yml`).
  - **QA (GitLab legacy):** `q-na-app005` (from `.gitlab-ci.yml`).
- **Two CI systems are active:** Both `.gitlab-ci.yml` (legacy) and `.github/workflows/` (current) exist. GitLab CI skips tests (`-Dmaven.test.skip=true`) for all phases.
- **Context path:** `/wizard` (Jetty config, and consistent with URL patterns).
- **Log4j config:** Loaded from `file:///d:/c-base/config/workbench/log4j.xml` (external, `web.xml` line 17).
- **Application properties override:** `application.properties` points to `d:/c-base/config/workbench/application.properties` for environment overrides.

## Configuration Management

All environment-specific configuration is **externalized to the filesystem** at `D:\c-base\config\workbench\`:

| File | Purpose |
|---|---|
| `D:\c-base\config\workbench\log4j.xml` | Logging configuration |
| `D:\c-base\config\workbench\application.properties` | Runtime property overrides (including `hide.deprecated.fields`) |
| JNDI data source definitions | Configured in Tomcat `server.xml` / `context.xml` (not in WAR) |

The in-WAR `src/main/webapp/META-INF/context.xml` provides a placeholder context but real JNDI resources are defined at the container level.

**Spring XML configuration files** (all loaded from classpath, `web.xml` lines 34–49):
- `applicationContext.xml` — affiliate service, Hibernate session factory, global request ID beans
- `applicationContext-xsecurity-web.xml` — Acegi security filter chain
- `applicationContext-xsecurity-thebridge-web-dao.xml` — xSecurity DAO beans
- `wizard-dbconfig.xml` — all DAO and stored proc beans (primary config file, ~1400 lines)
- `datasourceContext.xml` — JNDI data source wrappers
- `SessionContext.xml` — session context beans
- Various service-specific contexts: `affiliateServiceApplicationContext.xml`, `brandedCurrencyContext.xml`, `MessageCenter-client.xml`, `httpCryptoService-client.xml`, `applicationContext-instIssueCZScreenCfg.xml`, `appCtx-jmx.xml`, `appCtx-jobsvc-ds.xml`

**Spring bean configuration uses old DTD-based Spring 2.0 XML** (`spring-beans.dtd`) — no annotation-based config or Spring Boot.

**wizardBusiness.xml** (`WEB-INF/`) hard-codes `file:/D:/c-base/config/workbench/application.properties` as the property source path (line 8). This is a Windows-only absolute path.

## Observability

- **Logging:** Log4j 1.2.17 (EOL). Configuration loaded from external `log4j.xml`. Loggers use `org.apache.commons.logging.Log` wrappers throughout all classes. No structured/JSON logging. No log correlation beyond UUID-based Global Request ID injected into MDC via `Log4jMDCWriter` bean (`applicationContext.xml` line 264).
- **Global Request ID:** `GlobalRequestIdFilter` generates a UUID per request and populates `StaticRequestContextHolder` for downstream MDC logging. Class: `com.cbase.web.product.workbench.GlobalRequestIdFilter`.
- **Performance logging:** `PerformanceLogLifecycleManager` listener is **commented out** in `web.xml` (lines 143–150). No active performance logging.
- **JMX:** `appCtx-jmx.xml` context loaded — some beans may be exposed via JMX; not detailed in visible source.
- **Health check:** GitLab CI uses `PROJECT_SERVICE_URI=/` (root) for health check on `https://{host}:{port}/`. No dedicated `/health` or `/actuator` endpoint (this is not Spring Boot).
- **Request log:** Jetty (dev only) logs to `target/yyyy_mm_dd.request.log`, retained 90 days.
- **No distributed tracing / APM** integration is visible in the source.
- **No metrics / Prometheus / Micrometer** integration is visible.

## Infrastructure Dependencies

| Dependency | Type | Evidence |
|---|---|---|
| Apache Tomcat 8.5 | Application server | Deployment YAMLs, service name |
| Microsoft SQL Server | Primary DB (all 4 data sources) | `sqljdbc` driver dependency, `SQLServerDialect` in Hibernate config, `msbase`/`mssqlserver`/`msutil` JDBC drivers in Jetty config |
| Windows Server (`NAM` domain) | OS | Deploy user `NAM\qa_east_deploy`, `D:\` paths everywhere |
| Active Directory / NAM domain | User auth for deploy | Deploy credentials via `NAM\qa_east_deploy` |
| xPlatform (ecount platform) | Internal service library | `xPlatform:7.0.27` — huge dependency containing all profile/business logic classes |
| xSecurity service | Auth/authz library | `xSecurity-web/impl/common/client:3.0.5` |
| xAffiliateService | Affiliate management | `xAffiliateService:2019.1.3` |
| httpCryptoService | PGP key management | `httpCryptoService-common/impl:1.3` — calls external HTTP crypto servers |
| director-client | DB connection routing? | `director-client:1.0.9` — referenced but commented out in `wizard-dbconfig.xml` |
| xmlrpc | Job Scheduler communication | `xmlrpc:1.0.9` — XML-RPC calls to Job Scheduler service |
| ecount-system | Core system library | `ecount-system:1.0.7` |
| jobscheduler-common | Job scheduling | `jobscheduler-common:2016.1.1` |
| screenconfigs | Screen configuration service | `screenconfigs:2016.2.1` |
| banker-common | Banking utilities | `banker-common:2.1` |
| symbol-svc | Symbol/lookup service | `symbol-svc:1.0.0` |
| notification service | Email/SMS notifications | `notification-event-handler-impl`, `notification-rules-engine-impl`, `notification-mailer-impl:1.0.1` |
| brandedCurrency service | Branded currency support | `brandedCurrency-common/impl:2016.1.1` |
| PGP Crypto Servers | External HTTP service | `HTTPCryptoServiceClient` connects to multiple PGP servers |
| nam.wirecard.sys DNS | Network | All server names in `nam.wirecard.sys` domain (legacy Wirecard infrastructure) |
| GitHub Packages | Artifact registry | `DEPLOY_TO_PACKAGES: true` in main deployment workflow |
| GitHub Actions (self-hosted runner) | CI/CD | `BUILD_RUNNER: 'self-hosted'`, `DEPLOY_RUNNER: 'self-hosted'` |

## Operational Risks

1. **Java 8 EOL** — Java 8 is end-of-security-updates from Oracle (public updates ended Jan 2019; commercial extended to Dec 2030). Dependency on Java 8-only features limits upgradability.
2. **Log4j 1.2.17** — End-of-life since 2015. Log4Shell (CVE-2021-44228) affects Log4j 2.x, not 1.x, but Log4j 1.x has its own CVEs (e.g., CVE-2022-23302, CVE-2022-23305). Should be migrated to Log4j 2 or Logback.
3. **Spring 2.0.3 / Acegi Security** — Ancient framework versions. Spring 2.0.3 released in 2007. Acegi Security is the predecessor of Spring Security, last released ~2008. No security patches available.
4. **Struts 1.3.8** — Struts 1 is EOL since April 2013. Multiple CVEs including CVE-2014-0114 (ClassLoader manipulation) — mitigated in this codebase by `ParamFilter`, but many other Struts 1 CVEs may be unmitigated.
5. **Tomcat 8.5 approaching EOL** — Tomcat 8.5 reached EOL in March 2024.
6. **Hibernate 3 (annotation)** — Referenced via `org.hibernate.cfg.AnnotationConfiguration` (Hibernate 3 API). Hibernate 3 is long EOL.
7. **Windows-only deployment paths** — All `D:\c-base\...` paths make this application completely non-portable to Linux/cloud containers.
8. **Tests skipped in CI** — Both GitLab CI (`-Dmaven.test.skip=true`) and the wizard deployment workflow (`SKIP_TESTS: false` is configurable but defaulted to false) allow test-skip. GitLab CI hard-codes skip for all phases.
9. **No rollback automation** — The CI pipeline backs up files but rollback requires manual intervention (re-deploying from backup). No automated rollback trigger on health check failure.
10. **nam.wirecard.sys domain** — Server names reference the legacy Wirecard infrastructure domain. This may indicate dependency on infrastructure not yet migrated post-acquisition.
11. **Dual CI systems** — Both GitLab CI and GitHub Actions are active; risk of divergent deployments or conflicting pipelines.

## CI/CD

### GitHub Actions (Active)

**`.github/workflows/cicd-deployment.yml`** — Maven Deployment (general artifact publish):
- Trigger: `workflow_dispatch` (manual)
- Inputs: `skip_tests`, `deploy_to_production`
- Build: Reusable workflow `Onbe/om-ci-setup/.github/workflows/build-east-java.yml@main`, Java 8, self-hosted runner
- Publishes to GitHub Packages (`DEPLOY_TO_PACKAGES: true`)
- No deployment steps in this workflow (production deployment handled by referenced shared workflow when `deploy_to_production=true`)

**`.github/workflows/cicd-wizard-deployment.yml`** — Wizard CI/CD Deployment:
- Trigger: `workflow_dispatch` (manual)
- Inputs: `skip_tests`, `deploy_to_u_az_app05`
- Build: Same shared build workflow, Java 8, does NOT publish to Packages
- Deploy Stage: `u-az-app05.nam.wirecard.sys`, path `D:\c-base\opt\tomcat\servers\Workbench\webapps`, service `Apache Tomcat 8.5 Workbench`
- Deploy Cert: `q-na-app05.nam.wirecard.sys`
- Secret: `QA_EAST_DEPLOY_PASSWORD`

**`.github/workflows/codeql.yml`** — CodeQL security scanning:
- Triggers: `workflow_dispatch`, pull_request, weekly schedule (Tuesday 09:40 UTC)
- Uses `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- Runs on Linux self-hosted runner

**`.github/dependabot.yml`** — Dependency update automation (configuration present).

### GitLab CI (Legacy)

**`.gitlab-ci.yml`** — Delegates to `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml`:
- Dev host: `d-na-app002`
- QA host: `q-na-app005`
- Service name: `Workbench`
- All Maven phases skip tests
- No integration tests (`-Pno-it`)
