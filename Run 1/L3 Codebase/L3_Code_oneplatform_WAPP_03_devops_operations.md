# DevOps / Operations — oneplatform_WAPP

## Build System
- Maven, Java 8 (`maven.compiler.source/target = 1.8`).
- WAR packaging; `finalName = ROOT` (deploys to Tomcat root context).
- Parent POM: `com.citi.prepaid.web:webapp-parent:10.0.0`.
- Notable build plugins:
  - `maven-antrun-plugin`: runs `xDoclet` code generation at `generate-sources` phase to produce Struts action mappings from Javadoc annotations.
  - `yuicompressor-maven-plugin:1.1`: concatenates all HTML templates from `src/main/webapp/templates/**/*.html` into a single `cpmain.html` at build time for mobile use.
  - `maven-jetty-plugin:6.1.3`: embedded Jetty for local dev on port 9000.
- Build wrapper: `mvnw` / `mvnw.cmd`.
- Maven settings: `.mvn/wrapper/settings.xml`.

## CI/CD Pipeline

### Jenkins (primary pipeline)
- `Jenkinsfile`: single-stage `Build&Deploy` pipeline.
- Agent: any. Tool: `Maven3.1.0`.
- Steps: `mvn clean deploy -Dmaven.test.skip=true` — **tests are skipped in the deployment pipeline**.
- Build runs on Windows (`bat` executor).

### GitLab CI (secondary)
- `.gitlab-ci.yml`: includes shared template `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml`.
- Variables: `SERVICE_NAME=OnePlatform`, deploys to `d-na-app01` (dev) and `q-na-app01 q-na-app02` (QA).
- All Maven phases skip tests: `MAVEN_BUILD_OPTS/TEST_OPTS/DEPLOY_OPTS = "-Dmaven.test.skip=true"`.

### GitHub Actions
- `.github/workflows/codeql.yml`: CodeQL security scanning.
- `.github/dependabot.yml`: automated dependency updates.

## Config Management
- Spring context files loaded from classpath at startup (15+ XML context files configured in `web.xml`).
- Log4j configured from external filesystem path: `D:/c-base/config/oneplatform/log4j.xml` (hardcoded Windows path).
- No externalized configuration management (no Spring Cloud Config Server, no Azure App Config, no Kubernetes ConfigMap).
- Database connection strings and service URLs managed in Spring XML context files (not visible in this repo; likely in parent POM or external config repo).

## Observability
- **Application logging**: Log4j 1.x with JSON event layout (`jsonevent-layout:1.7`) for structured log shipping (presumably to Logstash/Elasticsearch).
- **Security audit events**: sent via `Message Center` service on every login, payment, and profile event.
- **Request logging**: Jetty NCSA access log (dev only, 90-day retention).
- **JMX**: `appCtx-jmx.xml` Spring context loaded — JMX management beans exposed.
- No distributed tracing (no Zipkin, Jaeger, or OpenTelemetry in this repo's dependencies).

## Infrastructure Dependencies
- **Application server**: Apache Tomcat (WAR deployment to `servers-8.5.5.7` per GitLab CI comment) on Windows hosts.
- **Database**: Microsoft SQL Server (multiple instances).
- **Message Center service**: internal messaging/notification infrastructure.
- **RSA MFA service**: RSA authentication server.
- **Biocatch**: external behavioral analytics SaaS.
- **KYC portal**: external identity verification service (URL configured via property).
- **Cambridge FX**: external FX transfer service.

## Operational Risks
1. **Tests skipped in CI/CD**: `mvn deploy -Dmaven.test.skip=true` in both Jenkins and GitLab pipelines. No automated quality gate on deployment.
2. **Hardcoded Windows paths**: `D:/c-base/...` in `web.xml` and build config makes the application non-portable and non-containerizable.
3. **Legacy Tomcat (8.5.5.7)**: Tomcat 8.5.x reached end of support. May have unpatched CVEs.
4. **No feature flags / canary deployment**: all changes deploy to all instances simultaneously.
5. **On-premises Windows hosts**: no cloud-native deployment; scaling requires manual provisioning.
6. **xDoclet code generation at build time**: fragile, JDK-version-sensitive XML generation. Failure produces silent empty Struts config.
7. **yuicompressor:1.1 (2011)**: extremely outdated build tool; may produce malformed output with modern HTML5 templates.
