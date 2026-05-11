# DevOps & Operations View — strongbox-lib_LIB

## Build
- Build tool: Apache Maven (wrapper present; `.mvn/wrapper/maven-wrapper.jar` included in repo — note: JAR in VCS is a supply chain risk).
- Java target: 21 (`maven.compiler.source=21`, `maven.compiler.target=21`).
- Modules: `strongbox-impl` (JAR), `strongbox-client` (JAR).
- Parent POM: `com.parents:prepaid-parent:6.0.12` (external, not in this repo).
- Enforcer plugin configured with `banTransitiveDependencies` — explicit allowlist required for transitive deps.
- Test scope: JUnit, commons-dbcp, commons-pool, jtds. Tests require live SQL Server; CI pipeline skips tests: `MAVEN_BUILD_ARGS: "-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip"`.

## Deployment
- Published as Maven library JARs to GitHub Packages.
- No Docker image or WAR deployment in this repository.
- Consumer services (ECount Core, Job Service, Repository Service) depend on this library via Maven coordinates.

## Config Management
- `.mvn/wrapper/settings.xml` configures the Maven repository mirrors/authentication for GitHub Packages.
- No application properties file is present in main source. Configuration (DB URL, credentials) is externalized to the consuming service or injected via Spring XML.
- Test Spring XML (`spring.xml`) contains hardcoded SQL Server hostnames and credentials — these must never reach production.

## Observability
- Logging via SLF4J (referenced in `StrongBoxXMLRPCClient` via `LoggerFactory`); Log4j / logback binding expected to be provided by the consuming application.
- `LoggingUtils.ThreadLocalLogger` is used for thread-safe logger access.
- Log statements log: service version at startup, decrypted data value before decryption (`"Data to be decrypted:" + data.getData_value()`), decoded plaintext at DEBUG level — **this is a significant PCI DSS concern** (see Solution Architect file).
- No metrics or distributed tracing instrumentation observed.

## Infrastructure Dependencies
| Dependency | Details |
|------------|---------|
| Microsoft SQL Server | Named `StrongBox`; accessed via JTDS JDBC driver (`net.sourceforge.jtds`) |
| Director Service | Used by `StrongBoxXMLRPCClient` to discover StrongBox service URL; interface `IDirectorClient` |
| Apache HttpClient 3.x | Used by XML-RPC client (`org.apache.commons.httpclient`) — EOL library |
| XML-RPC library | `com.citi.prepaid.service.core:xmlrpc:3.0.1` (internal artifact) |

## Operational Risks
| Risk | Severity |
|------|----------|
| In-process `HashMap` asymmetric key cache (`aKeyCache`) has no TTL or eviction — key rotation requires a JVM restart | High |
| `MultiThreadedHttpConnectionManager` (Apache HttpClient 3.x) is EOL; no TLS 1.3 support | High |
| Service location cached for 1 hour (`1000 * 60 * 60` ms); a StrongBox service failover will not be detected for up to 60 minutes | Medium |
| `maven-wrapper.jar` committed to VCS — supply chain risk | Medium |
| Tests require live SQL Server; no in-memory test alternative means CI always skips tests | High |

## CI/CD
- GitHub Actions workflow: `.github/workflows/github-package-publish.yml`
  - Triggers: push to `main`, pull_request to `main`, manual `workflow_dispatch`.
  - Delegates to reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`.
  - Tests skipped in all CI runs (`-Dmaven.test.skip`).
- CodeQL workflow: `.github/workflows/codeql.yml`
  - Schedule: weekly (Sunday 23:49 UTC).
  - Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
  - Runs on `ubuntu-latest`.
- Dependabot: `.github/dependabot.yml` present (configuration not read; assumed standard Maven dependency update config).
