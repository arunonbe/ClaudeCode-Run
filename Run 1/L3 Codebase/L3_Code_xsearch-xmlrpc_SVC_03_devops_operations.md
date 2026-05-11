# xSearch XML-RPC SVC — DevOps and Operations View

## 1. Build System and Toolchain

The service is a Maven multi-module project packaged under `com.ecount.service.xsearch-new:xsearch-new:4.0.2-SNAPSHOT`. The build uses the Maven Wrapper (`mvnw` / `mvnw.cmd`) pinned to the settings in `.mvn/wrapper/maven-wrapper.properties`. The Java source and target are both set to Java 21 (`maven.compiler.source=21`, `maven.compiler.target=21`), consistent with the platform-wide Java 21 mandate visible across all Gen-1 services.

Module build order:
1. `xsearch-common` — shared domain objects and interfaces
2. `xsearch-client` — consumer library distributed to calling services
3. `xsearch-impl` — business logic, DAO layer, stored procedure wrappers
4. `xsearch-xmlrpc` — WAR module exposing the XML-RPC HTTP endpoint

The `maven-enforcer-plugin` configuration in `pom.xml` enforces `requireReleaseDeps` (no SNAPSHOT transitive dependencies) except for the internal Onbe/Citi artifact groups (`com.parents*`, `com.ecount*`, `com.citi*`). This provides a degree of supply chain governance for third-party libraries but does not constrain internal snapshot proliferation.

## 2. CI/CD Pipeline

**File:** `.github/workflows/deployment.yml`

The pipeline delegates to the shared Onbe CI reusable workflow:
```
uses: Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main
secrets: inherit
```

Key pipeline parameters:
- `APP_NAME`: `XsearchXmlrpcSVC`
- `TARGET_ROOT`: `./xsearch-xmlrpc` — only the xmlrpc WAR module is deployed; the common, client, and impl modules are library artifacts
- `MAVEN_ARGS`: `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` — tests are skipped in CI. This is a significant operational risk: code changes are promoted to deployment without automated test execution.
- `PUBLISH_TO_APIM`: `true` — the WSDL/API descriptor is published to the API Management platform on every successful build
- `API_SUFFIX`: `xsearch-xmlrpc-api`
- `BACKEND_SUFFIX`: `/services/xsearch-xmlrpc_SVC`
- `EXCLUDE_STAGE`: `true` — no staging environment deployment; changes go directly from build to production-equivalent environments
- `UPDATE_DEPENDENCIES`: `true` / `UPDATE_PARENT_VERSION`: `true` — automated dependency updates are enabled, meaning PRs may be auto-generated to bump versions

There is also a GitLab CI file (`.gitlab-ci.yml`) in the root, suggesting a hybrid CI history or migration-in-progress. A second `.gitlab-ci.yml` appears in the file listing with a leading space in the name (` .gitlab-ci.yml`) — likely a copy artifact from a branching operation.

There is a separate `redeploy.yaml` workflow for force-redeployment without a code change, and a `github-package-publish.yml` for publishing the client JAR to GitHub Packages (making `xsearch-client` consumable as a dependency by other services).

## 3. Container and Runtime

There is no `Dockerfile` or `docker-compose.yaml` in this repository, unlike `xsso_SVC`. The service is deployed as a WAR file on Apache Tomcat 10.x, consistent with the Jakarta EE 10 / Servlet 6.0 API dependencies (`jakarta.servlet-api` is referenced transitively via the xPlatform dependency). The `xsearch-xmlrpc` module produces a WAR artifact which is deployed by the CI pipeline via the shared `java-workflow.yml`.

The Tomcat library requirement includes `mssql-jdbc:12.5.0.jre11-preview` copied to `tomcat-lib` during the Maven `package` phase — JDBC driver isolation is handled at the Tomcat level.

## 4. Dependency Management and Security Scanning

**Container scanning:** `.github/containerscan/allowedlist.yaml` exists but there is no container image built in this repository. The allowedlist may be inherited infrastructure from the parent CI template.

**CodeQL:** `.github/workflows/codeql.yml` is present, indicating static application security testing (SAST) runs on the codebase. However, given that tests are skipped (`-Dmaven.test.skip`) in the build, dynamic security tests are absent.

**Dependabot:** `.dependabot.yml` / `.github/dependabot.yml` is configured, meaning automated dependency update PRs will be raised for third-party libraries.

**Trivy:** `.trivyignore` is present. Without reviewing its contents, it may suppress known CVEs. This file should be reviewed by the security team to ensure no critical CVEs are being suppressed inappropriately.

## 5. Service Discovery and Health

The `HealthCheck.java` class (`xsearch-xmlrpc/src/main/java/com/ecount/services/xsearch/xmlrpc/HealthCheck.java`) is present but was not reviewed in detail. The service registers its location with the Director service (`director-client:2.0.1`) enabling dynamic service discovery. Clients cache the discovered endpoint for 1 hour. The CI pipeline's `BACKEND_SUFFIX` of `/services/xsearch-xmlrpc_SVC` implies the service is fronted by a reverse proxy or load balancer.

## 6. Logging

The service uses Log4j2 (`log4j-api`, `log4j-core` via the `prepaid-parent` POM). The `XSearchProxy.java` uses Lombok's `@Slf4j` annotation for logger injection. Log output includes:
- `INFO`: mobile phone number in `FindMemberByMobilPhone` request/response (`XSearchProxy.java` lines 43-45) — **this is a PII risk; mobile phone numbers should not be logged in plain text**
- `INFO`: member count in response
- `INFO`: duration metrics

Log configuration is referenced via `${env:CBASE_HOME_URL}/config/...` environment variable pattern (consistent with the xSSO logging configuration pattern), meaning log levels and appenders are managed outside the WAR at the host OS / container level.

## 7. Thread Safety and Connection Pooling

`XSearchXMLRPCClient.java` explicitly states: _"Implementation of this interface is guaranteed to be thread-safe."_ The HTTP connection manager uses `MultiThreadedHttpConnectionManager` (Apache Commons HttpClient 3.x) with:
- Max connections per host: 300
- Max total connections: 300
- Connection timeout: 2000 ms

The use of Apache Commons HttpClient 3.x is noteworthy — this library is EOL and was superseded by HttpComponents 4.x and then 5.x. This is a dependency hygiene concern from both a security patching and support perspective.

## 8. Operational Risks and Gaps

| Risk | Severity | Detail |
|---|---|---|
| Tests skipped in CI | High | `-Dmaven.test.skip` means regressions are only detected post-deployment |
| No staging environment | High | `EXCLUDE_STAGE: true` — production changes are unvalidated in a pre-prod environment |
| EOL HTTP client library | Medium | Apache Commons HttpClient 3.x is end-of-life |
| Director cache TTL | Medium | 1-hour cache for service location means slow failover on xSearch endpoint change |
| PII in logs | Medium | Mobile phone number logged at INFO level without masking |
| No container image | Low-Medium | No containerization makes it harder to apply modern security controls (read-only FS, non-root user, image scanning) |
| Dual CI system remnants | Low | Both `.gitlab-ci.yml` and GitHub Actions workflows exist; the GitLab file may be stale and potentially confusing |

## 9. PACT Contract Testing

The `PACT_PACTICIPANT` is `xsearch-xmlrpc_SVC-api` and `VERIFY_PROVIDER_PACT: false`. This means the service participates in PACT consumer-driven contract testing as a provider, but provider verification is disabled. Consumer contracts exist (published to the PACT broker) but the xSearch service itself does not verify them, meaning API breaking changes may not be detected before deployment.
