# job_LIB — DevOps / Operations View

## Build System

- **Build tool**: Maven (Maven Wrapper `mvnw`)
- **Maven version**: Defined in `.mvn/wrapper/maven-wrapper.properties`
- **Multi-module structure**:
  - Root POM: `com.citi.prepaid.service.job:job:4.0.1`
  - Modules: `job-common`, `job-impl`
- **Java target**: Not explicitly set in sub-POMs; inherited from parent (`com.citi.prepaid.service.job`)
- **Packaging**: Both modules produce JAR artefacts via `maven-jar-plugin`
- **Enforcer plugin**: `banTransitiveDependencies` rule is active with explicit exclusions — this enforces deliberate dependency declarations
- **Build args used in CI**: `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip`

## Deployment

- This is a **library** (JAR), not a deployable service. It is consumed by other services/applications as a Maven dependency.
- Published to **GitHub Packages** (`maven.pkg.github.com/onbe/...`) via the `github-package-publish.yml` workflow.
- Publication is triggered on: push to `main`, pull request to `main`, or `workflow_dispatch`.

## Config Management

- Runtime configuration is loaded via `PropertyPlaceholderConfigurer` from two locations:
  1. Classpath default: `classpath*:com/ecount/service/job/service.default.properties` (empty in source)
  2. External override: `${CBASE_HOME_URL}/config/service/job/service.properties` (filesystem path on host)
- JMS-specific config follows the same pattern: `service.jms.default.properties` and `${CBASE_HOME_URL}/config/service/job/service.jms.properties`
- The `CBASE_HOME_URL` environment variable must be set on the host; it points to the legacy on-premise config root — a Gen-1 pattern.
- No Azure App Configuration, no Kubernetes ConfigMaps, no Spring Cloud Config used.

## Observability

- Logging: SLF4J with Lombok `@Slf4j` in `JobManagerImpl`. Log statements are limited to startup banner and instant-issue card status. No structured/JSON logging.
- No distributed tracing (no OpenTelemetry, no Zipkin, no Sleuth configured).
- No metrics (no Micrometer, no Prometheus).
- No health check endpoint (library, not service).
- Audit interception via Spring AOP `AuditMethodInterceptor` is applied around all DAO proxy beans and `JobManager` — provides method-level audit logging via `com.ecount.springutils.aop.AuditMethodInterceptor`.

## Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| SQL Server (`jobsvc` DB) | Relational DB | Accessed via `JobSvcDataSource` Spring bean; must be injected by host service |
| JMS provider (ActiveMQ/JNDI) | Messaging | Used for remote JMS-based `JobManagerClient`; JNDI factory class and provider URL from properties |
| `xplatform` library | Internal JAR | Ecount platform framework |
| `springutils-generic`, `springutils-jms` | Internal JAR | Custom Spring utilities for JMS remoting and AOP |
| `spring-dbctx` | Internal JAR | Database context management |
| XStream | Third-party | Serialization for JMS messages |
| Commons Lang | Apache Commons | String utilities |

## Operational Risks

1. **CBASE_HOME_URL dependency**: The library fails to load configuration at runtime if this environment variable is absent or incorrect — a single point of failure with no fallback.
2. **JMS JNDI dependency**: Remote JMS path requires a live JNDI registry and JMS broker; failure means no remote job manager lookups.
3. **No circuit breaker**: The `AgentCachingJobManagerClient` wraps a JMS invoker proxy with no timeout guard or circuit breaker beyond a configurable `timeoutMillis`.
4. **Library test skipped in CI**: `Dmaven.test.skip` is set in the CI build args, meaning tests are not run on publication.
5. **Legacy parent POM**: `com.citi.prepaid.service.job` group ID — if this parent POM is not resolvable from the configured repositories, builds will break.

## CI/CD

| Workflow | Trigger | Action |
|---|---|---|
| `github-package-publish.yml` | push to `main`, PR to `main`, `workflow_dispatch` | Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`; publishes JAR to GitHub Packages |
| `codeql.yml` | Weekly schedule (Friday 17:53 UTC), `workflow_dispatch` | Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` for Java SAST on `ubuntu-latest` |
| Dependabot | Per `.github/dependabot.yml` | Automated dependency update PRs |

No deployment pipeline (library only). No Docker build. No container registry push.
