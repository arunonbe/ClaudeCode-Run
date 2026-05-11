# xSecurity SVC — DevOps and Operations View

## 1. Build System

xSecurity is a Maven multi-module project at version `4.0.4-SNAPSHOT`. The parent POM inherits from `com.parents:prepaid-parent:6.0.12`. Java source and target: 21. The Maven Wrapper (`mvnw` / `mvnw.cmd`) is present with settings in `.mvn/wrapper/settings.xml`.

Module build order:
1. `xsecurity-common` — shared domain objects, PasswordManager interface, constants, business objects
2. `xsecurity-impl` — Hibernate DAOs, stored procedure wrappers, business logic implementations
3. `xsecurity-client` — XML-RPC client library for consuming services
4. `xsecurity-web` — Acegi Security filters, authentication processing, password encoder
5. `xsecurity-xmlrpc` — XML-RPC proxy (service-side) and Spring bean wiring
6. `xsecurity-war` — WAR packaging module (`finalName: userManagement`)

The WAR artifact is named `userManagement.war`, not `xsecurity.war` — this means the deployment URL path is `/userManagement/...` rather than `/xsecurity/...`. The CI pipeline's `BACKEND_SUFFIX: /services/userManagementServices` confirms this.

## 2. CI/CD Pipeline

**File:** `.github/workflows/deployment.yml`

```yaml
APP_NAME: userManagementAPI
PACT_PACTICIPANT: user-management-api
TARGET_ROOT: "./xsecurity-war"
MAVEN_ARGS: ' -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip '
API_SUFFIX: user-management-api
EXCLUDE_STAGE: true
PUBLISH_TO_APIM: true
BACKEND_SUFFIX: "/services/userManagementServices"
UPDATE_DEPENDENCIES: true
UPDATE_PARENT_VERSION: true
```

Key observations:
- **Tests skipped:** `-Dmaven.test.skip` means no unit or integration tests run in CI. For a service handling password hashing and authentication logic, this is a significant risk — a regression in `EcountPassword` or `VelocityCheckingAuthenticationProcessingFilter` would not be caught automatically.
- **No staging:** `EXCLUDE_STAGE: true` — changes deploy directly from build to production environment.
- **Automated dependency updates:** `UPDATE_DEPENDENCIES: true` — third-party and platform library versions can be bumped automatically via PRs, changing the behavior of security-critical code paths.

Additional CI workflows:
- `.github/workflows/code_cov_build.yml` — code coverage reporting (suggesting JaCoCo or similar is configured, though separate from the main CI pipeline)
- `.github/workflows/vm-deployment.yml` — virtual machine (non-container) deployment path, confirming the service runs on VMs rather than containers
- `.github/workflows/codeql.yml` — CodeQL static analysis
- `.github/workflows/redeploy.yaml` — force redeploy without code change

## 3. Runtime Environment

xSecurity deploys as a WAR on Apache Tomcat 10.x. There is no Dockerfile in this repository. The `xsecurity-war/pom.xml` copies the following to `target/tomcat-lib`:
- `commons-discovery:0.2` — very old Apache Commons library
- `commons-logging:1.1.1`
- `slf4j-api`
- `log4j-api`, `log4j-core`
- `mssql-jdbc:12.5.0.jre11-preview`
- `HikariCP:5.1.0`

The `vm-deployment.yml` workflow confirms deployment to virtual machines, not containers. This means the service does not benefit from container-level isolation, image scanning, or Kubernetes security policies.

## 4. Security Framework Dependencies

xSecurity uses **Acegi Security** (`org.acegisecurity:jakarta-acegi-security:1.0.3`) as its authentication framework. Acegi Security was the predecessor to Spring Security — it was last actively developed around 2005-2007 before being absorbed into the Spring Security project. Using Acegi Security in 2025 represents:

1. **An EOL security framework** — no CVE patches are applied to Acegi Security; any discovered vulnerabilities remain unpatched
2. **Jakarta EE incompatibility work:** The dependency is `jakarta-acegi-security:1.0.3`, suggesting a custom fork or Jakarta EE namespace migration of the original Acegi library
3. **Missing modern security features:** Acegi predates CSRF protection, proper session fixation defense, and many other security controls that are standard in Spring Security 5.x/6.x

The `VelocityCheckingAuthenticationProcessingFilter` extends `AuthenticationProcessingFilter` from Acegi, and `DaoAuthenticationProvider` extends `AbstractUserDetailsAuthenticationProvider` from Acegi.

## 5. Logging and Observability

Log4j2 is used throughout via Lombok `@Slf4j`. The `security-audit-common:6.1.3` library integrates with the Onbe security audit infrastructure for structured audit events. Log configuration is expected at `${CBASE_HOME_URL}/config/xSecurity/log4j2.xml` (environment variable reference pattern).

Authentication-related log messages in `VelocityCheckingAuthenticationProcessingFilter.java`:
- Line 93: `"velocityCheck count is " + velocityCheck + " attempts"` — logs the count at INFO
- Line 98: `"Throwing velocity exception for " + velocityCheck + " attempts"` — logs velocity block
- Line 268: `"Successful Authentication - setting ECOUNT_MEMBER_ID to " + ecountUser.getMemberId()` — logs member ID on success

**Risk:** The member ID is logged on every successful authentication at DEBUG level. In a high-traffic system this produces a high volume of PII-adjacent data in logs.

## 6. Integration Test Infrastructure

**File:** `xsecurity-impl/src/integration-test/java/com/ecount/one/service/security/ServiceWebJettyTest.java`

Integration tests using an embedded Jetty server are present but not executed in CI (`-Dmaven.test.skip`). The `DaoPathBasedFilterInvocationDefinitionMapTest` validates the Acegi Security URL-based access control configuration.

## 7. PACT Contract Testing

`PACT_PACTICIPANT: user-management-api` and `VERIFY_PROVIDER_PACT: false`. As with xSearch, provider contract verification is disabled. The service acts as a provider to Workbench and CSA clients — unverified provider contracts mean breaking changes in the security API could be deployed without detecting consumer impact.

## 8. Dependency Health Assessment

| Dependency | Version | Status |
|---|---|---|
| Acegi Security (`jakarta-acegi-security`) | 1.0.3 | EOL — framework discontinued ~2007 |
| `commons-discovery` | 0.2 | EOL — last release 2011 |
| `commons-logging` | 1.1.1 | Old; Apache Commons Logging 1.3+ available |
| `org.httpunit:httpunit` | 1.7.2 | EOL — last release 2011 |
| `mssql-jdbc` | 12.5.0.jre11-preview | Preview/pre-release version in production |
| `HikariCP` | 5.1.0 | Current |
| `xmlbeans` | 5.2.1 | Current |

The `mssql-jdbc:12.5.0.jre11-preview` designation as a `preview` version in production is concerning — preview versions may have unstable APIs or known issues that are not present in a GA release.

## 9. Operational Risk Summary

| Risk | Severity | Evidence |
|---|---|---|
| EOL authentication framework (Acegi) | Critical | `jakarta-acegi-security:1.0.3` dependency |
| Tests skipped in CI | High | `-Dmaven.test.skip` in deployment.yml |
| No container isolation | High | `vm-deployment.yml` + no Dockerfile |
| Preview JDBC driver in production | Medium | `mssql-jdbc:12.5.0.jre11-preview` |
| EOL supporting libraries | Medium | `commons-discovery`, `httpunit` |
| Automated dependency bumps on security-critical service | Medium | `UPDATE_DEPENDENCIES: true` |
| No staging validation | High | `EXCLUDE_STAGE: true` |
