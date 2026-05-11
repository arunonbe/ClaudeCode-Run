# DevOps & Operations View — sweep-client_LIB

## Build
- Build tool: Apache Maven (wrapper present; `.mvn/wrapper/maven-wrapper.jar` in VCS — supply chain risk).
- Parent POM: `com.ecount.service:service-parent:5` (external).
- `maven-assembly-plugin` creates a fat JAR (`sweep-client-jar-with-dependencies.jar`) with main class `com.ecount.service.sweep.Main`.
- `maven-antrun-plugin` copies the fat JAR to `sweep-client.jar` in the build output directory.
- Spring version: `2.0.8` (declared explicitly as a `compile` dependency — bypasses parent exclusion of `spring`).
- AspectJ: `1.5.2a` (extremely old; 2006 era).
- Java target: inherited from `service-parent:5` (not visible in this repo).
- No test classes present in this repository.

## Deployment
- Deployed as a standalone executable JAR: `sweep-client.jar`.
- Invoked via command line: `java -jar sweep-client.jar -method Create [-time <seconds>] [-dryRun]`.
- Scheduled execution expected via OS scheduler (cron, Windows Task Scheduler) or an external job framework.
- `CBASE_HOME_URL` environment variable must be set to locate production configuration.

## Configuration Management
- Three-level property override chain (lowest to highest priority):
  1. `classpath:com/ecount/service/sweep/sweep.client.default.properties` (bundled defaults — includes `B2CTEST` agent and test member GUID).
  2. `${CBASE_HOME_URL}/config/service/order/sweep.client.properties` (environment-specific).
  3. `file:/${user.dir}/sweep.client.properties` (local override).
- `systemPropertiesModeName=SYSTEM_PROPERTIES_MODE_OVERRIDE` — JVM system properties take highest precedence.
- `ignoreResourceNotFound=true` for levels 2 and 3 — if production config file is missing, the application silently falls back to test defaults (`B2CTEST` agent, test member ID).

## Observability
- Logging via Apache Commons Logging; Log4j 1.x (`log4j.properties` in `src/main/resources/`).
- AOP audit interceptor (`AuditMethodInterceptor`) wraps all `MethodInvoker` calls via Spring AOP.
- Logs sweep profile lookups (agent, affiliate, member ID, active time) and per-programme outcomes (new/skipped/failed order counts).
- Exit codes provide coarse-grained operational signal to the calling scheduler.
- No structured logging, no metrics endpoint, no distributed trace.

## Infrastructure Dependencies
| Dependency | Details |
|------------|---------|
| xPlatform / CBase | Profile store; `AppPromotionInstantSweepOrderProfileClass.retrieveAll()` |
| Order Service | HTTP Invoker endpoint; URL from `${CBASE_HOME_URL}/config/...` |
| Spring 2.0.8 | IoC container, AOP |
| AspectJ 1.5.2a | AOP weaving |
| XStream (via `xPlatform`) | Object serialisation for HTTP Invoker |

## Operational Risks
| Risk | Severity |
|------|----------|
| Fallback to `B2CTEST` / test member GUID if production config file missing | Critical |
| Spring 2.0.8 EOL — no security patches | Critical |
| AspectJ 1.5.2a (2006) — no security patches | High |
| XStream deserialization vulnerabilities (used by `XStreamMarshaller`) | High |
| Log4j 1.x EOL — known CVEs (CVE-2019-17571, etc.) | High |
| No retry / dead-letter handling for Order Service failures | Medium |
| No idempotency — duplicate order creation possible on re-run | Medium |
| `maven-wrapper.jar` in VCS | Medium |

## CI/CD
- GitHub Actions workflow: `.github/workflows/codeql.yml`
  - Schedule: weekly (Tuesday 07:33 UTC).
  - Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
  - Runs on `self-hosted` Linux runner.
- **No build/publish workflow found** — no automated Maven build or artifact publication pipeline.
- Dependabot: `.github/dependabot.yml` present.
