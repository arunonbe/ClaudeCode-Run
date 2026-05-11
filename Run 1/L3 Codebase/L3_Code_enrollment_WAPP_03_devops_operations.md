# DevOps & Operations Analysis — enrollment_WAPP

## Repository Overview

**Repo:** `enrollment_WAPP`
**Build:** Maven WAR (`enrollment-2020.1.1-SNAPSHOT.war`)
**Java:** 1.8
**CI:** Jenkins (`Jenkinsfile`) + GitLab CI (`.gitlab-ci.yml`)
**Deployment:** Apache Tomcat WAR deployment (manual or GitLab deploy stage)
**Branch model:** `development` (dev) → `master` (QA/prod)

---

## Build System

### Maven
- Parent: `com.citi.prepaid.web:webapp-parent:8` — an internal parent POM that controls plugin versions and shared config.
- Packaging: `war` — traditional servlet container deployment.
- The POM references the legacy Nexus at `d-na-stk01.nam.wirecard.sys:8080/nexus/` for both snapshot and release repositories.
- **xDoclet** (`xdoclet-web-module`) is used to generate Struts `struts-config.xml` and web descriptor files during `generate-sources` phase — this is a circa-2004 code generation technique rarely seen in modern projects.
- **Maven Checkstyle plugin** (`checkstyle.xml`) enforces code style at build time.
- **Maven Source plugin** — publishes a `-sources.jar` alongside the artifact.

### Key Build Commands
```bash
# Full build (skip tests)
./mvnw.cmd clean package -Dmaven.test.skip=true

# Checkstyle check
./mvnw.cmd checkstyle:check

# Deploy to Nexus
./mvnw.cmd deploy -Dmaven.test.skip=true
```
As used in `Jenkinsfile` (lines 17, 22, 30).

### Local Development Script
`dev-deploy-local-script.bat` is present — confirms this app was historically deployed locally on Windows for development, consistent with the `JAVA_HOME=D:\\c-base\\JDK-AWS-8` setting in `Jenkinsfile` line 7.

---

## CI/CD Pipelines

### Jenkins Pipeline (`Jenkinsfile`)
Three stages:
1. **Build** — `mvnw.cmd clean package -Dmaven.test.skip=true -X`
2. **Checkstyle** — `mvnw.cmd checkstyle:check`
3. **Nexus** — `mvnw.cmd deploy -Dmaven.test.skip=true -X`

`agent any` — runs on any available Jenkins agent.
`JAVA_HOME=D:\\c-base\\JDK-AWS-8` — a Windows path, meaning the Jenkins agent must be a Windows machine with this path mapped.

**Gaps:**
- Tests are always skipped (`-Dmaven.test.skip=true`).
- No static analysis stage beyond Checkstyle.
- No deployment to an application server (only pushes to Nexus).

### GitLab CI Pipeline (`.gitlab-ci.yml`)
More complete pipeline than Jenkins:

| Stage | Job | Trigger |
|-------|-----|---------|
| build | `build:app` | All branches |
| test | `test:app` | All branches (`allow_failure: true`) |
| deploy | `deploy:dev` | `development` branch |
| deploy | `deploy:qa` | `master` branch, manual |

Deploy targets:
- **Dev:** `d-na-app01` (single server)
- **QA:** `q-na-app01`, `q-na-app02` (two-server cluster)

Uses `northlane/development/application-development/configuration/ci-templates:maven.gitlab-ci.yml@master` — a shared GitLab CI template (standard Onbe/North Lane pattern for Maven apps).

**Observations:**
- `test:app` uses `allow_failure: true` — meaning broken tests do not block deployment. This is a red flag for a PCI-scoped application.
- QA deploy requires manual trigger — appropriate gate before production promotion.
- No production deploy stage defined — presumably a separate pipeline or manual process.

---

## Deployment Architecture

### Runtime
- **Server:** Apache Tomcat (`startup.bat` referenced in README).
- **Port:** Not specified; default Tomcat port inferred.
- **Context path:** `/enrollment` (from WAR file name convention; or `/rebateinquiry` per README — README is stale).
- **Session management:** HTTP session (in-memory); multi-node requires sticky sessions or session replication.

### Configuration
Loaded via Spring XML property placeholder from:
- `${CBASE_HOME_URL}/config/processes/enrollment/application.properties`
- `${CBASE_HOME_URL}/config/director-client.properties`

Same cBase config server dependency as `enrollment_LIB`.

### Infrastructure Dependencies

| Component | Purpose |
|-----------|---------|
| Tomcat | Servlet container |
| SQL Server | Login/security stored procs |
| cBase config server | Externalised configuration |
| Director service | DB connection routing |
| RSA SecurID | MFA authentication |
| CMS service | Brand/programme content |
| SMTP server | Notification emails |
| xPlatform / xSecurity | eCount authentication framework |
| Affiliate service | Brand metadata |

---

## Monitoring and Observability

- **Logging:** Log4j 1.2.15 (`log4j:log4j:1.2.15`, `pom.xml` line 113). `ExceptionLogger` and `Log4jInit` classes exist for custom logging setup.
- **No metrics endpoint** — no Actuator, no JMX exposure.
- **No health check endpoint** — no `/health` or `/ping`.
- **No distributed tracing** — no Zipkin/Sleuth integration.

---

## Security Operations

| Item | Status |
|------|--------|
| CAPTCHA | `simplecaptcha:1.2.1` on login form — prevents bot enrollment |
| RSA MFA | `rsa-mfa-impl:1.0.9` — second factor for sensitive operations |
| Security audit | `security-audit-common:2017.1.0` — audit logging library |
| HTTPS | Not configured at app level; assumed terminated at load balancer |
| Log4j version | 1.2.15 — CVE-2019-17571 (SocketAppender RCE); must be upgraded or disabled |
| `spring-mock:2.0.3` | Not test-scoped (missing `<scope>test</scope>`) — deployed to production WAR |

**Critical finding:** `spring-mock` (`pom.xml` line 163) is included without `<scope>test</scope>`, meaning test infrastructure code is bundled into the production WAR.

---

## Operational Recommendations

1. **Scope `spring-mock` to test** — add `<scope>test</scope>` immediately.
2. **Upgrade Log4j** — replace Log4j 1.x with Log4j 2.x or Logback to address CVE-2019-17571.
3. **Remove `allow_failure: true` from test stage** — failing tests should block deployment.
4. **Add health check** — implement a `/health` endpoint for load balancer monitoring.
5. **Enable session replication** — for the QA two-server cluster, configure Tomcat session persistence or sticky sessions.
6. **Automate production deploy** — add a gated production stage to the GitLab CI pipeline.
