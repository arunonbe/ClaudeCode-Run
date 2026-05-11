# clientzone_WAPP — DevOps & Operations View

## Build & Packaging

### Build System
- **Maven** — `pom.xml` at repo root; `mvnw` / `mvnw.cmd` wrappers provided.
- Maven Wrapper version pulled from `.mvn/wrapper/maven-wrapper.properties`.
- Custom Maven settings in `.mvn/wrapper/settings.xml` (likely points to internal Artifactory/Nexus).

### Artifact
- **Type**: WAR file.
- **ArtifactId**: `clientzone`, **GroupId**: `com.citi.prepaid.web.clientzone`.
- **Version**: `2.0.52-SNAPSHOT` (pom.xml line 13).
- **Deployment name**: `ROOT` (controlled by `${deployment.name}` property, pom.xml line 76). The WAR deploys as the root context of the Tomcat instance.
- **Java version**: 1.8 (Java 8). Compiler source and target both `1.8`.

### Key Build Plugins
| Plugin | Version | Purpose |
|---|---|---|
| `maven-compiler-plugin` | 3.8.1 | Java 8 compilation |
| `maven-war-plugin` | (parent-managed) | WAR assembly |
| `maven-release-plugin` | 3.0.0-M1 | Release management |
| `maven-surefire-plugin` | 2.22.2 | Test runner (JUnit 5 + Mockito) |
| `jacoco-maven-plugin` | 0.8.12 | Code coverage report on `test` phase |
| `Parasoft maven-parasoft-plugin` | (parent-managed) | Static analysis (Parasoft) |
| `maven-jetty-plugin` | (via `jetty` profile) | Local development server on port 8080 |

### Dependency Highlights
- `struts-core:1.3.10`, `struts-el`, `struts-tiles`, `struts-taglib`
- `spring:2.0.8`, `spring-mobile-device:1.0.1.RELEASE`
- `mssql-jdbc:6.1.0.jre8`
- `msal4j:1.14.3` (Microsoft Azure AD authentication)
- `log4j:1.2.17` (provided scope — supplied by container)
- `xsecurity:2016.1.1`, `xplatform:3.0.27`, `order-manager:3.1.8`, `debitapi:2015.3.1`, `accountmanagementapi-impl:2.0.9`
- `simplecaptcha:1.2.1`, `xstream:1.4.12`, `poi:3.0.1-FINAL`, `commons-fileupload:1.4`

All internal dependencies (`com.citi.prepaid.*`, `com.ecount.*`) are resolved from an internal Maven repository via the custom wrapper settings.

---

## Deployment

### Runtime Platform
- **Application Server**: Apache Tomcat 8.5 (evidenced by `cicd-deployment.yml`: `SERVICE_NAME: 'Apache Tomcat 8.5 ClientZone'`).
- **OS**: Windows Server (evidenced by deployment paths `D:\c-base\opt\tomcat\servers\ClientZone\webapps`).
- **JVM**: Java 8.

### Deployment Paths (from `cicd-deployment.yml`)
| Environment | Servers | Deployment Path |
|---|---|---|
| UAT | `u-az-app01.nam.wirecard.sys`, `u-az-app02.nam.wirecard.sys` | `D:\c-base\opt\tomcat\servers\ClientZone\webapps` |
| QA | `q-na-app01.nam.wirecard.sys`, `q-na-app02.nam.wirecard.sys` | `D:\c-base\opt\tomcat\servers\ClientZone\webapps` (commented out in workflow) |
| Production | `p-az-app01.nam.wirecard.sys` | `D:\c-base\opt\tomcat\servers\clientzone\webapps` (commented out in workflow) |

The servers use the legacy domain `nam.wirecard.sys` — indicative of infrastructure that pre-dates the Onbe rebrand.

### Deployment Mechanism
1. GitHub Actions `cicd-deployment.yml` (workflow_dispatch only — no automatic trigger on push to master).
2. Build job reuses `Onbe/om-ci-setup/.github/workflows/build-east-java.yml@main` — self-hosted runner, Java 8.
3. Deploy job reuses `Onbe/om-ci-setup/.github/workflows/deploy-east.yml@main` with `DEPLOY_RUNNER: 'ubuntu-docker'` (Linux Docker runner), deploying to Windows hosts via WinRM/SSH with `NAM\qa_east_deploy` credentials.
4. Pre-deploy: stops Tomcat service, backs up WAR to `D:\c-base\backup`, cleans webapps and work directories.
5. Post-deploy: copies new `ROOT.war`, starts Tomcat service.
6. QA and Production stages are **commented out** in the current workflow — only UAT deploys automatically.

### Legacy CI (GitLab)
`.gitlab-ci.yml` references `northlane/development/application-development/configuration/ci-templates` (the pre-GitHub, North Lane GitLab instance). Variables:
- `SERVICE_NAME: ClientZone`
- Dev hosts: `d-na-app01`; QA hosts: `q-na-app01 q-na-app02`
- All Maven phases use `-Dmaven.test.skip=true` — tests are skipped in all CI environments.

`whitesource.gitlab-ci.yml` exists for Mend/WhiteSource SCA scanning.

### Local Development
Jetty profile (`jetty` in pom.xml) runs at `http://localhost:8080/clientzone`. Requires local SQL Server connections configured in `jetty-env.xml`.

---

## Configuration Management

### Externalised Configuration
All sensitive and environment-specific configuration is loaded from the filesystem, **not** bundled into the WAR:

| Property File | Default Path | Loaded by |
|---|---|---|
| `clientzone.properties` | `${CBASE_HOME_URL}/config/cz/clientzone.properties` | `PropertyPlaceholderConfigurer` in `applicationContext.xml` |
| `edeliveryrequest.properties` | `${CBASE_HOME_URL}/config/cz/edeliveryrequest.properties` | Same |
| `applicationContext-xContent.properties` | `${CBASE_HOME_URL}/config/xContent/...` | Same |
| `log4j.xml` | `D:/c-base/config/cz/log4j.xml` | `Log4jConfigListener` via `log4jConfigLocation` context param in `web.xml` |
| `order-SynchronousCommunication.xml` | `${CBASE_HOME_URL}/config/cz/` | `applicationContext.xml` `<import>` |
| `debitapi.xml` | `${CBASE_HOME_URL}/config/cz/` | `applicationContext.xml` `<import>` |
| `amapi.xml` | `${CBASE_HOME_URL}/config/cz/` | `applicationContext.xml` `<import>` |

`CBASE_HOME_URL` is a system/JVM property resolved at startup. The hard-coded path `D:/c-base/config/cz/` is referenced directly in `EncryptionUtil.java`, `SsoUserUtil.java`, and `web.xml` (log4j path).

### Key Configuration Properties (from `applicationContext.xml` bean wiring)
- `${clientzone.agent}` — identifies the calling application to the xPlatform core.
- `${clientzone.domestic.url}`, `${clientzone.international.url}`, `${clientzone.regions.url}` — multi-region routing.
- `${sso.client.secret}`, `${sso.client.id}`, `${sso.authority}`, `${sso.scopes}`, `${sso.encryption.key}` — Azure AD SSO configuration.
- `${otp.generate.url}`, `${otp.validate.url}`, `${otp.client.secret}`, `${otp.client.id}`, `${otp.authority}`, `${otp.scope}` — OTP shared service.
- `${omrcp.seach.url}`, `${omrcp.client.secret}`, `${omrcp.client.id}`, `${omrcp.authority}`, `${omrcp.scope}` — OMRCP search service.
- `${mfaSwitch}`, `${groupCount}`, `${questionCount}`, `${attemptCount}` — MFA configuration.
- `${recaptcha.enabled}`, `${recaptcha.apiKey}`, `${recaptcha.siteKey}`, `${recaptcha.projectId}` — Google reCAPTCHA.
- `${applicationId}`, `${affiliateId}`, `${agent}`, `${classification}` — application identity.
- `${eDelivery.required}`, `${eDelivery.header.*}` — eDelivery toggle and metadata.
- `${dwp.ips}`, `${dwp.programs}`, `${dwp.context}`, `${dwp.requestheader}` — DWP / SMOTS URL configuration.
- `${display.Jcaptcha.flag}` — toggle for simple CAPTCHA display.
- `${urlHitTimeInterval}` — DoS protection time window.
- `${clientzone.requestParaLength.limit}` — maximum URL parameter length.

---

## Observability

### Logging
- **Framework**: Log4j 1.2.17 (provided scope — supplied by Tomcat), with SLF4J bridge (`slf4j-log4j12:1.7.32`).
- **JSON logging**: `jsonevent-layout:1.7` and `json-smart:1.1.1` — supports structured JSON log output (likely consumed by a log aggregator such as Splunk or ELK).
- Log configuration loaded from `D:/c-base/config/cz/log4j.xml` at startup; refresh interval 300,000 ms (5 minutes).
- `LogUtil.sanitizeForLog()` (`src/main/java/com/cbase/business/util/LogUtil.java`) strips `\r\n\t`, pipe, brackets, quotes, control characters, and non-printable ASCII from log messages to prevent log injection.
- `SecurityHelper` and action classes use `Log log = LogFactory.getLog(...)` consistently.

### Health / Monitoring Endpoint
- `monitor` servlet (`org.springframework.web.servlet.DispatcherServlet`) mapped to `/monitor` and `/monitor.select`.
- Spring MVC configuration in `src/main/webapp/WEB-INF/monitor-servlet.xml`.
- Provides a lightweight health-check endpoint used by the GitLab CI health-check (`PROJECT_SERVICE_URI: /login.jsp`).

### Metrics
- No APM instrumentation (e.g., Micrometer, Prometheus, Dynatrace agent) is visible in the pom.xml or application context.
- JaCoCo coverage reports generated at build time (`jacoco-maven-plugin:0.8.12`).

### Audit Logging
- `security-audit-common:2017.1.0` dependency provides security event auditing.
- `SecurityAuditHelper` bean wired into `UsernamePasswordLoginFilter` and `SsoAuthenticationProcessingFilter`.
- `AuditInfo.java` captures user location, event type, cardholder ID, and transaction amounts for business events.
- `CommentHelper.java` writes structured comments/audit notes via the `comment` service.

---

## Infrastructure Dependencies

| Dependency | Type | Evidence |
|---|---|---|
| Microsoft SQL Server | RDBMS | `mssql-jdbc:6.1.0.jre8`, 6 named DataSources |
| Apache Tomcat 8.5 | App Server (Windows) | `cicd-deployment.yml` `SERVICE_NAME` |
| Azure AD B2C (ladsmarkclient tenant) | IdP / SSO | `SsoUserUtil.java` TENANT constant, `msal4j` dependency |
| Adobe LiveCycle / IDP | eDelivery SOAP | `com.adobe.idp.services.*` imports in `InstantIssueHelper.java` |
| Google reCAPTCHA v3 | Bot protection | `reCaptchaService` bean, `recaptcha.*` properties |
| OTP Shared Service | REST microservice | `SharedServiceConnector.java`, `${otp.generate.url}` |
| OMRCP Search Service | REST microservice | `CustomerServiceAction`, `${omrcp.seach.url}` |
| xPlatform / ECount Core | Internal RPC | `xPlatform:3.0.27`, `ECount.System.RPC.rpcServlet` servlet |
| EhCache | In-memory cache | `ehCache-ytd.xml`, `cacheManagerContext.xml` |
| WhiteSource / Mend | SCA scanning | `whitesource.gitlab-ci.yml`, `wss-unified-agent-clientzone.config` |
| Parasoft | SAST | `maven-parasoft-plugin` in `pom.xml` |
| GitHub Actions (self-hosted) | CI/CD | `.github/workflows/` |
| GitHub Packages | Artifact registry | `DEPLOY_TO_PACKAGES: true` in `cicd-deployment.yml` |

---

## Operational Risks

1. **Windows-only deployment** — All paths are Windows (`D:\c-base\...`). Container/Linux migration requires path refactoring across `web.xml`, `applicationContext.xml`, `EncryptionUtil.java`, `SsoUserUtil.java`.

2. **Configuration drift** — `clientzone.properties` is on the filesystem of each server with no visible secrets management (Vault, AWS Secrets Manager, Azure Key Vault). Credential rotation requires manual file edits and possible service restarts.

3. **Production deployment disabled** — The production deploy stage in `cicd-deployment.yml` is commented out. Production releases must be manual or through a process not captured in this workflow, increasing the risk of human error and reducing audit trail.

4. **Tests skipped in all CI** — GitLab CI: `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"` across all stages. This means no regression gate exists in CI.

5. **Single-server production** — `SERVERS: 'p-az-app01.nam.wirecard.sys'` — only one production server listed. No load balancer or blue/green deployment is visible.

6. **Tomcat 8.5 EOL** — Apache Tomcat 8.5 reached end-of-life in March 2024. No security patches are available from the Apache project.

7. **`CBASE_HOME_URL` dependency** — The entire application is non-functional without this environment variable. There is no fallback or startup validation.

8. **Log4j 1.x EOL** — Log4j 1.2.17 has known unpatched CVEs (CVE-2019-17571). The `provided` scope means it is supplied by Tomcat; any Tomcat upgrade must also address the Log4j version.

---

## CI/CD

### GitHub Actions Pipelines (`.github/workflows/`)

| Workflow | Trigger | Purpose |
|---|---|---|
| `build-war-file.yml` | Push to `master`, PR open/sync/label, manual | Stub pipeline ("Hello World!" echo only — non-functional) |
| `cicd-deployment.yml` | Manual (`workflow_dispatch`) | Full build + UAT deploy; QA and prod stages commented out |
| `codeql.yml` | PR, manual, weekly cron (Mon 00:55) | GitHub CodeQL SAST scanning |
| `dependabot.yml` | Automated | Dependabot dependency update PRs |

### GitLab CI (`.gitlab-ci.yml`)
Extends `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml` for legacy North Lane infrastructure. Tests skipped at all stages. WhiteSource SCA integrated.

### Artifact Flow
Build produces `ROOT.war` → published to GitHub Packages → deployment workflow downloads and deploys to UAT servers.

### Security Scanning
- CodeQL (SAST) runs on PRs and weekly.
- Mend/WhiteSource (SCA) runs via GitLab CI.
- Parasoft static analysis runs as part of Maven build.
- Dependabot monitors Maven dependencies.
