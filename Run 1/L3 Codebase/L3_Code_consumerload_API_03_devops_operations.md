# consumerload_API — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven. A Maven Wrapper is included (`mvnw`, `mvnw.cmd`, `.mvn/wrapper/maven-wrapper.properties`), pinning the Maven version via the wrapper JAR.
- **Parent POM**: `service-parent:9.0.0` (`com.parents`) — an internal corporate parent POM not present in this repository.
- **Multi-module layout**:
  - Root POM (`pom.xml`): `groupId=com.citi.prepaid.webservices.consumerload`, `artifactId=consumerload`, `version=1.0.0`, `packaging=pom`.
  - `consumerload-ws` (`packaging=war`): the deployable web application. Final name: `consumerload` (produces `consumerload.war`).
  - `consumerload-impl` (`packaging=jar`): business logic library, bundled inside the WAR.
- **Java version**: Source and target set to `1.6` (Java 6) in the root POM `maven-compiler-plugin` configuration (version 2.0.2, also extremely old).
- **Key dependencies**:
  - Apache Axis 1.4 (circa 2006) — SOAP engine.
  - Spring Framework 2.0.8 — IoC and MVC.
  - XStream 1.3.1 — XML serialization used for debug logging.
  - Log4j 1.2.15 — logging.
  - `com.ecount:xPlatform:2.5.44` — internal eCount/cbase platform SDK.
  - `com.ecount.spring-dbctx:spring-dbctx-container:1.0.4` — Spring DB context container.
  - `com.ecount.springutils:springutils-generic:1.0.8` — internal Spring utilities.
  - `com.ecount.services:comment:1.0.0` — audit comment service.
  - `com.citi.cibtech.elf:elf:1.4` — Citi ELF library (Enterprise Logging Framework).
  - `commons-lang:2.1` (declared in root POM properties as `commonslang.version`).
- **Internal artifact registry**: All `com.ecount`, `com.citi`, and `com.parents` artifacts must be resolved from a private Maven repository (Nexus/Artifactory). The `.mvn/wrapper/settings.xml` is present but its content is the standard Maven wrapper settings — actual repo config is in `settings.xml` outside the repository.
- **No test module**: There are no test source directories (`src/test/java`) or test dependencies beyond `spring-mock:2.0.8` declared in `dependencyManagement`. No unit or integration tests exist.

## Deployment

- **Runtime**: Deployed as a WAR (`consumerload.war`) to a Java Servlet container. The `web.xml` uses the Servlet 2.3 DTD — compatible with Tomcat 5.x/6.x. The application was built for Tomcat, evidenced by the `META-INF/context.xml` JNDI resource links.
- **URL mapping**:
  - `/services/*` → `AxisServlet` (Apache Axis SOAP endpoint). WSDL available at `/services/ConsumerLoadService?WSDL`.
  - `/*` → Spring `DispatcherServlet` (`consumerload` servlet).
  - Service list is disabled (`axis.disableServiceList=1` in `web.xml` line 46) — WSDL enumeration is blocked.
- **Session timeout**: 5 minutes (`<session-timeout>5</session-timeout>` in `web.xml`).
- **JNDI datasources**: `jdbc/JobSvcDataSource` and `jdbc/CbaseappDataSource` are linked in `META-INF/context.xml` as ResourceLinks. They must be defined as global resources in the Tomcat `server.xml`.
- **Deployment platform**: The hardcoded path `D:/c-base/config/ConsumerLoad/` in `consumerload-wsContext.xml` (line 8) and `web.xml` (line 24) confirms the service was originally deployed on a **Windows host** with this directory structure. The `codeql.yml` CI runner tag (`ubuntu-docker`) suggests Linux is targeted for scanning, but the application configuration is Windows-specific.
- **No containerization**: No `Dockerfile`, `docker-compose.yml`, or Kubernetes manifests exist in this repository. The service is a classic bare-metal / VM WAR deployment.

## Configuration Management

- **External properties file**: `D:/c-base/config/ConsumerLoad/ConsumerLoad.properties` is the sole runtime configuration file. It must supply:
  - `consumerload.agent` — the agent/caller identity for RequestContext construction (also used as `userId` in `EcountBusinessObject` and `commentHelper`).
  - `consumerload.memberId` — the operator/caller member ID.
  - `consumerload.userId` — the EcountBusinessObject agent ID.
  - Any other properties consumed by `PropertyPlaceholderConfigurer` via `searchSystemEnvironment=true` and `SYSTEM_PROPERTIES_MODE_OVERRIDE`.
- **Log4j config**: Read from `file:///D:/c-base/config/ConsumerLoad/log4j.xml` (absolute Windows path, `web.xml` line 24). This means the logging configuration is entirely outside the WAR.
- **Spring context loading order** (from `web.xml` context-param):
  1. `classpath:validation.xml` (input validation type beans)
  2. `classpath:validator.xml` (validator beans with regex rules)
  3. `classpath:com/ecount/resources/db/appCtx-cbaseapp-ds.xml` (cbase DataSource)
  4. `classpath:com/ecount/resources/db/appCtx-jobsvc-ds.xml` (job service DataSource)
  5. `classpath:consumerload-wsContext.xml` (request context, memberId, property placeholder)
  6. `classpath:consumerload-implContext.xml` (service beans, helpers, platform beans)
  7. `classpath:com/ecount/services/comment/comment.xml` (comment service)
- **Commented-out service bean registrations**: In `consumerload-wsContext.xml` lines 26–31, all six service beans (`getCCLoadFeeService`, `loadFundsUsingCCService`, etc.) are commented out. The working registrations are in `consumerload-implContext.xml`. This is a configuration maintenance risk — a developer might uncomment these and create duplicate (likely broken) bean definitions.
- **Hardcoded IP address**: `CLConstants.IP_ADDRESS = "123.123.123.123"` — defined but the constant does not appear to be used in any active code path (the `Session.setIpAddress()` calls in `AccountHelper` use `"127.0.0.1"` directly, not this constant).

## Observability

- **Logging framework**: Log4j 1.2.15, configured externally. Logger names used:
  - `ConsumerLoadWebServiceImpl.class` (Commons Logging facade)
  - `AccountHelper.class` (note: string literal `"AccountHelper.class"`, not the class reference — this is a non-standard logger name)
  - `ProfileHelper.class`
  - `CommentHelper.class`
  - `ValidationHelper.class`
  - `InputHelper.class`
- **Log levels in use**: `log.debug(...)` is the primary level used across all services, with `log.info(...)` for error conditions in `AccountHelper` and `log.warn(...)` in `CommentHelper`.
- **Logged content risk**: Debug logs include full XStream XML serialization of request/response objects (e.g., `ConsumerLoadWebServiceImpl` line 30: `log.debug(" Consumer Load - Check KYC Status Request" + print(checkKYCStatusRequest))`). In debug mode this will write PAN, CVV, SSN, and DOB to log files.
- **No metrics or health checks**: No Actuator, Micrometer, JMX, or custom health endpoint is present.
- **No distributed tracing**: No correlation ID header propagation, no OpenTelemetry, no MDC population.
- **No alerting configuration**: No alerting rules or SLA thresholds defined in the application.

## Infrastructure Dependencies

| Dependency | Type | Evidence |
|---|---|---|
| eCore / cbase platform | Remote proprietary service | All `ECoreDevice`, `ECoreMember`, `ECoreTransfer` beans in `consumerload-implContext.xml` |
| JobSvc RDBMS | JDBC | `jdbc/JobSvcDataSource` JNDI; `GetPuid` SQL query |
| cbase RDBMS | JDBC | `jdbc/CbaseappDataSource` JNDI |
| Comment service DB | Via `ICommentService` | `com.ecount.services.comment` Spring context |
| eCount Profile Service | Remote | `ECountProfileDriver`, `AppProfileProgramMembership.retrieve()`, `AppProfileProgramStrategyClass.retrieve()` |
| Servlet container (Tomcat) | Runtime | WAR packaging, `web.xml` Servlet 2.3, JNDI resource links |
| File system (Windows) | Configuration | `D:/c-base/config/ConsumerLoad/` — properties file and log4j config |

## Operational Risks

1. **Java 6 EOL**: The service compiles to Java 6. Java 6 reached end-of-life in February 2013. No security patches are available. The runtime JVM must still be running something reasonably modern, but the compiled bytecode and API usage is locked to ancient versions.
2. **Apache Axis 1.4 EOL**: Axis 1.4 was released in 2006 and is no longer maintained. It has multiple known CVEs. The WSDL2Java-generated classes (all request/response domain objects) are auto-generated boilerplate that is tightly coupled to Axis serialization.
3. **Spring 2.0.8 EOL**: Spring 2.0 is extremely old (2007). No security support. The DTD-based Spring XML configuration (`spring-beans.dtd`) reflects this vintage.
4. **Log4j 1.2.15**: Log4j 1.x is EOL and has known CVEs (though not the JNDI Log4Shell vector, which is 2.x). Should be upgraded.
5. **XStream 1.3.1**: Very old version with known CVEs related to deserialization attacks.
6. **Single configuration file path**: If `D:/c-base/config/ConsumerLoad/ConsumerLoad.properties` is absent, the application fails to start due to `PropertyPlaceholderConfigurer` without `ignoreResourceNotFound`.
7. **No graceful degradation**: Service bean lookups use `getWebApplicationContext().getBean(...)` in a way that will throw `NoSuchBeanDefinitionException` if any bean is missing — no null checks or fallback handling.
8. **Dual-SVN and Git history**: The repository contains both a `.git` and a `.svn` directory, indicating it was at some point tracked in Subversion and then migrated (or dual-tracked). This creates branching/merge confusion risk.

## CI/CD

- **GitHub Actions**: One workflow defined — `.github/workflows/codeql.yml`.
  - Trigger: manual (`workflow_dispatch`) and weekly schedule (Sundays at 15:37 UTC — `cron: 37 15 * * 0`).
  - Uses a shared reusable workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
  - Runner: `self-hosted, X64, Linux, ubuntu-docker`.
  - This is a static analysis / security scan only — no build, test, or deploy steps.
- **Dependabot**: Configured (`.github/dependabot.yml`) for Maven ecosystem, weekly updates from the root directory. However, given the dependency on internal artifacts and extreme version ages, Dependabot PRs are likely to be blocked by the parent POM or internal artifact resolution.
- **No automated build pipeline**: No `mvn package`, `mvn deploy`, Docker build, or deployment steps in any workflow.
- **No test automation in CI**: No test execution step (consistent with the absence of test classes).
- **Dual VCS**: Both `.git` and `.svn` directories suggest the primary SCM may still be SVN (the `.git` may be a mirror or a one-time import).
