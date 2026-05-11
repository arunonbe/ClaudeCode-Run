# account-management-payout_API — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven via the Maven Wrapper (`mvnw`). Settings in `.mvn/wrapper/settings.xml`.
- **Java version**: 21 (set in root `pom.xml` lines 19–20: `maven.compiler.target` and `maven.compiler.source`).
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` — a platform-level parent controlling shared dependency versions.
- **Multi-module layout**:
  - `accountmanagementapi-payout-impl` → JAR (business logic, services, helpers)
  - `accountmanagementapi-payout-ws` → JAR (SOAP handler, request/response objects, web service interface)
  - `accountmanagementapi-payout-war` → WAR artifact named `accountmanagementpayoutapiws.war`
- **Artifact version**: `3.0.1-SNAPSHOT` (`pom.xml` line 15).
- **Build command** (README): `mvn clean install -Dmaven.test.skip` — test skip is standard.
- **WAR final name**: `accountmanagementpayoutapiws` (set in `accountmanagementapi-payout-war/pom.xml` line 19).
- **Tomcat libs copied to image**: At package phase, `maven-dependency-plugin` copies the following JARs to `target/tomcat-lib/` for Docker COPY: `commons-discovery:0.2`, `commons-logging:1.1.1`, `slf4j-api`, `log4j-api`, `log4j-core`, `mssql-jdbc:12.5.0.jre11-preview`, `HikariCP:5.1.0`.
- **JaCoCo**: Agent (`0.8.12`) and CLI JARs are copied to `target/jacoco-lib/` for instrumented code-coverage runs in CI.
- **Enforcer plugin**: `banTransitiveDependencies` rule is enabled in all three modules, with explicit exclusion lists for Spring, eCount, Citi-prepaid, Hibernate, Jackson, and XStream.
- **WSDL filtering**: `wsdl/wsdl.xml` is Maven-filtered (property substitution) and copied to `target/` at the `validate` phase.

---

## Deployment

### Container Image
- **Base image**: `bellsoft/liberica-openjre-alpine:21` (LiberICA JRE 21 on Alpine Linux — `Dockerfile` line 1).
- **Tomcat version**: `10.1.28` downloaded from `archive.apache.org` during image build (`Dockerfile` line 8). This is a build-time download — network availability is required during build.
- **Deployed artifact**: `target/accountmanagementpayoutapiws.war` placed as `ROOT.war` in Tomcat webapps (`Dockerfile` line 17).
- **Port**: Container exposes port 80 (`Dockerfile` line 22).
- **Environment variables baked at startup**: `CBASE_HOME_URL=file:///cbase` (default), JVM module opens for Java 21 compatibility (`--add-opens` flags in `JAVA_OPTS`).
- **Config volume**: External configuration files are mounted at `/cbase/config` (via `docker-compose.yaml` line 16: `${CONFIG_DIR}:/cbase/config`).
- **Certificate injection**: QA certificate imported to JVM truststore during image build (`Dockerfile` line 21). Certificate alias: `certfile_qa`. Uses default keystore password `changeit`.

### Kubernetes (AKS)
- **Redeploy workflow**: `.github/workflows/redeploy.yaml` triggers `om-cd-setup/.github/workflows/redeploy.yaml@main` for AKS QA environment. Application name: `accountmanagementpayoutapi`.
- **GitOps**: Deployment uses shared Onbe `om-ci-setup` and `om-cd-setup` pipeline workflows via GitHub Actions `uses:` reuse.
- **Rollout config**: `USE_ROLLOUT_CONFIG: true` in `deployment.yml` — controlled rollout strategy managed by the shared CI/CD platform.

### Legacy / On-Premise
- **GitLab CI**: `.gitlab-ci.yml` remains present and includes `northlane/development/.../maven.gitlab-ci.yml`. It targets `d-na-app02` (DEV) and `q-na-app01 q-na-app02` (QA) as bare-metal or VM hosts. Service URI: `/accountmanagementpayoutapiws/services/AccountManagementApiWebServices?wsdl`. This suggests the service dual-deployed during a migration period.
- **Service port**: 9326 (from `docker-compose.yaml` and `.gitlab-ci.yml`).

---

## Configuration Management

All runtime configuration is externalized and loaded from a mounted `cbase` config volume. The `PropertyPlaceholderConfigurer` in `accountmanagementapi-implContext.xml` loads the following files at startup from `${CBASE_HOME_URL}`:

| File | Purpose |
|---|---|
| `config/accountmanagementapi/accountmanagementapi.properties` | Core properties: `memberId`, `jwe.encryptDDA`, `jwe.secretKey`, `jwe.expirationTime`, security service names/methods, KYC properties |
| `config/accountmanagementapi/api-security.properties` | API security domain configuration |
| `config/service/order/service.jms.properties` | JMS connection properties for Order Service |
| `config/accountmanagementapi/APIValidation.properties` | Field-length and content validation rules |
| `config/accountmanagementapi/service.monitor.properties` | Monitor page settings (DB query timeouts) |
| `config/accountmanagementapi/OrderService_Connection.xml` | Spring XML for Order Service JMS connection factory |
| `config/accountmanagementapi/log4j2-payout.xml` | Log4j2 configuration (refreshed every 5 minutes) |

Database credentials are injected via environment variables (`CBASEAPP_JDBC_URL`, `JOBSVC_JDBC_URL`, `ECOUNT_JDBC_URL`, and matching username/password vars) into `server.xml` using Tomcat's `EnvironmentPropertySource` (enabled in `catalina.properties` via Dockerfile line 11).

**CI secrets used** (from `code_cov_build.yml`):
- `CBASEAPP_JDBC_URL`, `JOBSVC_JDBC_URL`, `ECOUNT_JDBC_URL`
- `ACCOUNTMANAGEMENTPAYOUT_CBASEAPPDB_USERNAME/PASSWORD`
- `ACCOUNTMANAGEMENTPAYOUT_JOBSVCDB_USERNAME/PASSWORD`
- `ACCOUNTMANAGEMENTPAYOUT_ECOUNTDB_USERNAME/PASSWORD`
- `PAT_TOKEN` (GitHub PAT for config repo checkout)
- `CODECOV_TOKEN`

**Config repo**: Integration tests check out `OnbeEast/api-config-repo` at `master` branch into the WAR module directory (`code_cov_build.yml` lines 49–53).

---

## Observability

### Health Check
- **Endpoint**: `GET /hc` — returns `"OK"` as plain text (`HealthCheck.java` lines 11–13). Exposed via Spring MVC `@RestController` at `com.onbe.accountmanagementapi.health.HealthCheck`. Component-scanned from `accountmanagementapi-servlet.xml` line 13.

### Monitoring Page
- `monitor.xml` wires a `MonitorFormController` bean (eCount springutils framework) exposed at the monitor URL. Three test executors are registered:
  - `Job-Access`: Database connectivity test against `JobSvcDataSource`.
  - `Job-Query`: Row-count test against `JobSvcDataSource` (configurable SQL from properties).
  - `SynchronousOrderProcessor.ping`: JMS ping to the Order Service (instant issue queue).
  - `VisitAllMonitor`: Method-level call statistics for all `accountManagementHandler` operations.
- Application version string displayed: `Account Management API - ${maven.version}, Build: ${maven.build.number}, SVN: ${svn.revision} (${maven.build.date})`.

### Logging
- **Framework**: Log4j2 with log4j-1.2-api bridge (for legacy code using Log4j 1.x) and `log4j-jakarta-web` for the Jakarta/Tomcat integration.
- **JSON layout**: `net.logstash.log4j:jsonevent-layout` is a dependency in the ws module — JSON-structured log output to log shipping pipeline.
- **MDC**: `GlobalRequestIDInterceptor` writes a request ID to Log4j2 MDC via `Log4jMDCWriter` (`accountmanagementapi-wsContext.xml` line 106). App name in MDC: `account.mngmt`.
- **Request logging**: Each handler method logs entry IP address, timing (start/end), and serializes request/response objects to XML via `DomainHelper.printObjectToXML()` (using XStream).
- **Log config location**: `${CBASE_HOME_URL}/config/accountmanagementapi/log4j2-payout.xml`, refreshed every 300,000 ms (5 minutes) via `log4jRefreshInterval` context param (`web.xml` lines 27–29).

### Code Coverage
- JaCoCo 0.8.12 instrumented runs are executed in the `code_cov_build.yml` workflow via Docker Compose. Coverage reports are uploaded to Codecov (`codecov/codecov-action@v4.0.1`).
- Postman tests run against the live container (docker-compose-test.yaml) as part of integration test execution.

---

## Infrastructure Dependencies

| Dependency | Type | How Connected |
|---|---|---|
| eCount/eCore | Legacy RPC (ECount.System.RPC) | PIN set, card activation, account status — direct RPC calls via `eDevice` / `eMember` beans (appCtx-core.xml) |
| Order Service | JMS (`SynchronousOrderProcessor`) | Update registration, all commented-out JIRA-476 operations — via JMS connection defined in `OrderService_Connection.xml` |
| JobSvc DB (SQL Server) | JDBC / HikariCP | User mapping lookups |
| CbaseApp DB (SQL Server) | JDBC / HikariCP + Hibernate | Affiliate metadata, security domains, member/user data |
| EcountCore DB (SQL Server) | JDBC / HikariCP | FDR card detail, BIN/program lookup, KYC status persistence |
| KYC Portal | HTTPS (MS MSAL token) | External KYC vendor API called for KYC-required programs |
| Azure API Management (APIM) | External | WSDL published to external APIM (`PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`) |
| api-config-repo | Git (GitHub) | Externalised runtime configuration, checked out at CI test time |
| Pact Broker | HTTP | Contract testing (`PACT_PACTICIPANT: account-management-payout-api`); not acting as provider (`VERIFY_PROVIDER_PACT: false`) |

---

## Operational Risks

1. **Tomcat downloaded at build time**: `Dockerfile` line 8 fetches `apache-tomcat-10.1.28.tar.gz` from `archive.apache.org` — failure of this external URL will break the Docker build. No mirroring or internal artifact registry is used for Tomcat.
2. **HTTP only on port 80**: Tomcat is configured for plain HTTP. TLS must be enforced at the ingress/load-balancer layer. If misconfigured, sensitive data (CVV, PIN, card numbers) will traverse the network unencrypted.
3. **Session timeout = 5 minutes**: `web.xml` session timeout is 5 minutes. The service is stateless SOAP, so this has minimal impact, but lingering sessions could hold resources.
4. **Container scan suppressions**: `.trivyignore` suppresses 7 CVEs. `allowedlist.yaml` (Azure container scan) suppresses 3 more. Some of these relate to Spring (`CVE-2024-22262`) and Tomcat (`CVE-2024-50379`, `CVE-2024-52316`, `CVE-2024-56337`). The Tomcat CVEs in particular should be tracked against the deployed version.
5. **`autoDeploy=false`** on Tomcat Host (server.xml line 171): Safe configuration — prevents hot deployment of arbitrary WARs. `xmlNamespaceAware=false` and `xmlValidation=false` are set.
6. **JVM `--add-opens` flags**: Five module-open statements are required for Java 21 compatibility with legacy reflection-based frameworks (Axis, XStream). These are a technical debt indicator.
7. **SHA1PRNG usage**: `JWEHelper.java` uses `SecureRandom.getInstance("SHA1PRNG")` — this algorithm is deprecated on some JDK distributions and may fall back to a platform default. For a payments service, an explicit `SecureRandom.getInstanceStrong()` or `NativePRNG` is preferred.
8. **Postman tests with `continue-on-error: true`**: Integration test failure in `code_cov_build.yml` line 80 does not fail the build. This means a broken integration test will not block a deployment.

---

## CI/CD

### GitHub Actions Workflows

| Workflow File | Trigger | Purpose |
|---|---|---|
| `.github/workflows/deployment.yml` | Push/PR to `main` | Main build-and-deploy pipeline via `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`. Builds, tests, publishes WSDL to external APIM, deploys. |
| `.github/workflows/code_cov_build.yml` | Push to `main`, PR to `main`, `workflow_dispatch` | Builds, spins Docker Compose for integration tests (Postman), generates JaCoCo report, uploads to Codecov. |
| `.github/workflows/codeql.yml` | Weekly (Fridays 17:53 UTC), `workflow_dispatch` | GitHub CodeQL SAST scan via `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`. |
| `.github/workflows/github-package-publish.yml` | (not read) | Likely publishes Maven artifacts to GitHub Packages. |
| `.github/workflows/redeploy.yaml` | `workflow_dispatch` | Manual trigger to redeploy the QA AKS environment via `Onbe/om-cd-setup`. |

### Dependabot
- `.github/dependabot.yml` configures **weekly** Maven dependency updates from the root directory.

### Stage environment
- `EXCLUDE_STAGE: true` in `deployment.yml` — no stage environment deployment. The pipeline skips stage and goes directly to QA/production.

### GitLab CI (legacy)
- `.gitlab-ci.yml` still present, referencing `northlane/` namespace Northlane-era CI templates. This is a legacy artifact from before the Onbe GitHub Actions migration.
