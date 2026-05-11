# DevOps & Operations Report — message-center_SVC

## 1. Build and Packaging

`message-center_SVC` uses a multi-module Maven project structure (`pom.xml` at root, version `3.0.1-SNAPSHOT`) with three modules:
- `message-common` — shared DTOs and interfaces
- `message-impl` — stored-procedure DAO and business logic
- `message-service` — WAR packaging, Spring XML config, and deployment artifact

The root POM inherits from `com.parents:prepaid-parent:6.0.12` (the Gen-2 parent POM). The compiler is set to **Java 21** (`maven.compiler.source=21`, `maven.compiler.target=21` in the root `pom.xml` lines 20-21), making this the highest Java version in the Gen-2 stack. The Maven Enforcer plugin is configured to reject SNAPSHOT dependencies in production builds (with exclusions for internal Onbe and legacy Citi/Wirecard group IDs).

The build produces a WAR artifact: `message-service.war`, deployed to `/opt/tomcat/webapps/message-service.war` inside the container.

## 2. Container and Runtime

**Dockerfile** (`message-service/Dockerfile`):
- Base image: `bellsoft/liberica-openjre-alpine:21` — consistent with Java 21 compiler target.
- Embedded servlet container: **Apache Tomcat 10.1.28**, downloaded at image build time from `archive.apache.org` (line 8). This is a build-time network dependency that breaks reproducible builds in air-gapped environments.
- A QA-environment TLS certificate (`certfile_qa.crt`) is injected into the JVM trust store at build time using `keytool` (lines 19-20). This means the production image must be rebuilt to change the trusted CA chain.
- The keystore password is hardcoded as `changeit` (the default JVM keystore password) in line 20, which is a security finding.
- `JAVA_OPTS` includes multiple `--add-opens` for deep reflection — required by the legacy XML-RPC libraries that predate the Java module system.

## 3. CI/CD Pipeline

**GitHub Actions workflow** (`.github/workflows/deployment.yml`):
- Reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` (Gen-2 CI pipeline, distinct from the NexPay Gen-3 `nexpay-iac` pipeline)
- `APP_NAME: MessageCenterSVC`
- `PACT_PACTICIPANT: message-center-svc` — Pact contract testing is configured; `VERIFY_PROVIDER_PACT: false` means this service only acts as a consumer in Pact tests.
- `PUBLISH_TO_APIM: true` — the WSDL/API definition is published to API Management, suggesting SOAP/XML-RPC exposure.
- `INTERNAL_APIM: false`, `EXTERNAL_APIM: false` — no Azure APIM routing; deployment uses a legacy API gateway pattern.
- `BACKEND_SUFFIX: "/services/MessageCenterWebServices"` — the XML-RPC endpoint suffix.
- `UPDATE_DEPENDENCIES: true`, `UPDATE_PARENT_VERSION: true` — automated dependency updates are enabled, which is a dependency freshness management mechanism but increases risk of unintended upgrades.
- `EXCLUDE_STAGE: true` — stage environment deployment is skipped, meaning changes go directly from QA to production.
- `MAVEN_ARGS: ' -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip '` — **tests are skipped in the CI build**. This is a significant quality risk.

## 4. GitHub Security Workflows

- **CodeQL** (`.github/workflows/codeql.yml`): Static analysis is enabled.
- **Dependabot** (`.github/dependabot.yml`): Dependency vulnerability scanning is configured.
- **Container scan** (`.github/containerscan/allowedlist.yaml`): Container image vulnerability scanning with an allowlist for known accepted CVEs.
- **GitHub Package Publish** (`.github/workflows/github-package-publish.yml`): Maven artifacts are published to GitHub Packages.

## 5. Environment Configuration

Configuration is loaded from `${CBASE_HOME_URL}\config\service\message\message.properties` — a file path resolved from an environment variable `CBASE_HOME_URL`. In containerized deployments, this is set to `file:///cbase` (Dockerfile line 24). The external config volume must be mounted at `/cbase` in the container at runtime, meaning configuration is injected through a volume mount rather than environment variables or Azure App Configuration. This is a Gen-2 pattern that predates the NexPay approach of using Azure Key Vault and App Configuration.

## 6. Observability

- **Health check**: `message-service/src/main/java/com/onbe/messagecenter/health/HealthCheck.java` is the only Java file in the `message-service` module, suggesting a minimal HTTP health endpoint is exposed.
- **No Actuator, Prometheus, or OpenTelemetry** endpoints are configured. Monitoring relies on Tomcat access logs and application logs shipped via the log4j/logback stack.
- **No structured logging**: The service uses `LogFactory.getLog()` (Apache Commons Logging) — a Gen-2 pattern without structured JSON output, making log aggregation in a cloud-native stack (Azure Monitor, ELK) less effective.

## 7. Operational Risks

1. **Tomcat downloaded at build time**: Network failure during `docker build` causes pipeline failure.
2. **Test skip in CI**: `Dmaven.test.skip` in `MAVEN_ARGS` means no automated regression gating before deployment.
3. **No stage environment**: `EXCLUDE_STAGE: true` reduces pre-production validation opportunity.
4. **Volume-mounted config**: The `/cbase` config volume is a deployment dependency that is not tracked in this repository; misconfigured mounts silently fail at startup.
5. **`changeit` keystore password**: Default JVM keystore password is used for the trust store; any process on the host can read the trust store.
