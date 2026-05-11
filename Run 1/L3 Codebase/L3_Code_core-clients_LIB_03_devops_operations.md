# core-clients_LIB — DevOps & Operations View

## Build & Packaging

- **Build system**: Apache Maven 3.9.5 (pinned via Maven Wrapper at `.mvn/wrapper/maven-wrapper.properties`)
- **Java version**: 21 (`maven.compiler.source` and `maven.compiler.target` both set to `21` in root `pom.xml` line 29-30)
- **Packaging**: Multi-module POM (`packaging: pom`) at the root, with seven child modules each producing a JAR:
  - `director-client` → `director-client-2.0.3-SNAPSHOT.jar`
  - `profile-client` → `profile-client-2.0.3-SNAPSHOT.jar`
  - `ecount-core-client` → `ecount-core-client-2.0.3-SNAPSHOT.jar`
  - `securityServiceClient` → `securityserviceclient-2.0.3-SNAPSHOT.jar`
  - `eventServiceClient` → `eventserviceclient-2.0.3-SNAPSHOT.jar`
  - `strongBoxClient` → `strongboxclient-2.0.3-SNAPSHOT.jar`
  - `orderXMLRPCClient` → `orderxmlrpcclient-2.0.3-SNAPSHOT.jar`
- **Parent POM**: `com.parents:prepaid-parent:6.0.13` — an Onbe internal parent that controls plugin versions.
- **Tests**: `mvn clean install -Dmaven.test.skip` is the documented build command (README). Tests are skipped by default in CI (`MAVEN_BUILD_ARGS` in `github-package-publish.yml` line 41).
- **Enforcer rules**: `maven-enforcer-plugin` enforces `banTransitiveDependencies` and `requireReleaseDeps` in all modules, with selective exclusions for internal `com.citi.prepaid.service.core:*` SNAPSHOTs.

## Deployment

- **Artefact type**: Shared library JAR — this is not a deployable service (no Tomcat WAR, no Spring Boot fat JAR, no Dockerfile found in the repository).
- **Deployment mechanism**: Published to GitHub Packages (`https://maven.pkg.github.com/onbe/onbe_maven_releases`) via the `github-package-publish.yml` workflow. Downstream services consume it as a Maven dependency.
- **Runtime prerequisite**: Tomcat 10.x is listed in README as a prerequisite, but this appears to be a copy-paste artefact — the library itself has no servlet or web artefact. The real runtime requirement is any JVM 21 host that can reach the Director service URL.
- **Version strategy**: Currently on `2.0.3-SNAPSHOT`. The change.log shows historical production versions at `1.0.10` for both domestic and international environments. The `2.x` lineage is a rewrite in progress.

## Configuration Management

- **No application.properties / application.yml** — the library carries zero configuration files of its own. All runtime configuration (service URLs, agent settings, credentials) is fetched from Director at call time.
- **Director key structure** (observed from test and code):
  - `System\DataCredentials\{agent}` — DB credentials (UserID, Password)
  - `System\DataEnvironment\{agent}` — environment routing (e.g. `ECountCore.TEST1B1`)
  - `System\DataSettings\{agent}` — ADO-style cursor/timeout settings
  - `System\Servers` — alias-to-URI map for all services
  - `Services\{RPC_INTERFACE_NAME}` — service-specific settings including `InterfaceServer` alias
- **Maven settings**: `.mvn/wrapper/settings.xml` configures the package registry. Authentication uses `${env.GITHUB_TOKEN}` injected at CI time. No secrets are committed to the repository.
- **Dependabot**: Weekly Maven dependency update checks are configured in `.github/dependabot.yml`.

## Observability

- **Logging framework**: SLF4J with Lombok `@Slf4j` annotation. Used in `DirectorXMLRPCClient`, `DirectorServiceLocator`, `DeviceXMLRPCClient`, `MemberXMLRPCClient` (via `XMLRPCClient` base class). Log4j2 is the backend (evidenced by `log4j2-test.xml` in `director-client` test resources).
- **Log levels in use**:
  - `log.error()` — HTTP non-200 responses (`DirectorXMLRPCClient` line 110)
  - `log.debug()` — exception stack traces from Director calls (line 122)
  - `log.warn()` — Director unavailable but cached URI available (`DirectorServiceLocator` line 98)
  - `log.info()` — member search parameters (`MemberXMLRPCClient` line 242); example/test code
  - `log.debug()` — `TransferXMLRPCClient` QuickLoad strategy (line 123)
- **No metrics / tracing** — no Micrometer, no OpenTelemetry, no distributed tracing instrumentation in the library. Transaction IDs are generated via `UUID.randomUUID()` in `EventXMLRPCClient`, `SecurityServiceXMLRPCClient`, `SecurityHierarchyServiceXMLRPCClient`, and `StrongBoxXMLRPCClient` but are internal correlation IDs only.
- **No health endpoint** — library only; no health-check surface.
- **Exception swallowing**: `DirectorXMLRPCClient.get()` catches all `Exception` types and returns `null` without re-throwing (lines 120-123). Callers must null-check but receive no exception detail.

## Infrastructure Dependencies

| Dependency | Version | Scope | Purpose |
|---|---|---|---|
| `com.citi.prepaid.service.core:xmlrpc` | `3.1.3-SNAPSHOT` | compile | XML-RPC transport base classes (`XMLRPCClient`, `XMLRPCServiceLocator`, serialisation utils) |
| `com.ecount.service.core.ecountcore:common` | `3.1.5` | compile | Domain value objects (`Member`, `Account`, `Transfer`, `TransferDefinition`, etc.) |
| `com.ecount.service.common:services-common` | `3.0.1` | compile (securityServiceClient only) | `ServiceObjectEx`, `ActionMemo`, `ServiceObject` base types |
| `com.ecount.service.xSecurity:xsecurity-common` | `4.0.3` | compile (securityServiceClient only) | `BulkHierarchyNodeFileRecord` and security domain types |
| `com.citi.prepaid.service.order:order-common` | `4.1.4` | compile (orderXMLRPCClient only) | `OrderRef`, `CreateFileOrderRequest`, `OrderActivityFacility` domain types |
| Apache Commons HttpClient | 3.x (transitive) | compile | HTTP transport for `DirectorXMLRPCClient` |
| Lombok | (transitive) | compile/annotation | `@Slf4j` logging annotations |
| JUnit 4 | (transitive) | test | Unit tests in `director-client` |
| Parent POM | `com.parents:prepaid-parent:6.0.13` | import | Plugin version management |

**Network dependencies at runtime**:
- Director service URL (HTTP, configurable)
- ECountCore services (resolved via Director)
- Profile, Security, Event, Order, StrongBox services (all resolved via Director)

## Operational Risks

1. **HTTP connection pool sizing** — `DirectorXMLRPCClient` static initialiser sets `defaultMaxConnectionsPerHost=1000` and `maxTotalConnections=1000`. These are very large defaults for a shared static client; under load this can exhaust OS file descriptors.
2. **1-minute connection timeout on Director** — `connectionManager.getParams().setConnectionTimeout(1000*60)` (line 55). A 60-second stall waiting for Director can cascade thread exhaustion in calling services.
3. **5-second socket + connection timeout on service calls** — `myMethod.getParams().setParameter("http.socket.timeout", 5000)` (line 88). Under network congestion this may cause spurious failures.
4. **Apache Commons HttpClient 3.x is EOL** — it was superseded by HttpClient 4.x/5.x over a decade ago. No TLS 1.2/1.3 tuning is available via this API without reflection hacks.
5. **Tests make live network calls** — `TestDirectorXMLRPCClient` connects to `http://ppamwdcddcor1/service/dispatch.asp` and asserts on real credentials. These are integration tests masquerading as unit tests, and they will fail in any environment that cannot reach internal Onbe infrastructure.
6. **SNAPSHOT parent and XML-RPC transport** — both `prepaid-parent:6.0.13` (released, but opaque) and `xmlrpc:3.1.3-SNAPSHOT` are not under source control here. Changes in those can silently break builds.
7. **Tests skipped in CI** — the publish workflow always passes `-Dmaven.test.skip`, so regressions in the library are not caught by CI builds.

## CI/CD

### Publish Workflow (`.github/workflows/github-package-publish.yml`)
- **Triggers**: `push` to `main` (ignoring `.mvn/**`, `.github/**`, `mvnw`, `mvnw.cmd`); `pull_request` to `main`; manual `workflow_dispatch` with override inputs:
  - `version-tag` — override the version tag
  - `auto-increment` — auto bump version (boolean, default false)
  - `dry-run` — simulate publish without pushing (boolean, default false)
  - `update-dependencies` — update downstream dependency references (boolean, default true)
- **Reusable workflow**: Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` with `secrets: inherit`. The actual publish logic is centralised in the `om-ci-setup` repository.
- **Build command**: `mvn -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip`

### CodeQL Workflow (`.github/workflows/codeql.yml`)
- **Triggers**: `workflow_dispatch`; scheduled `cron: '53 17 * * 5'` (weekly Friday at 17:53 UTC)
- **Reusable workflow**: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` with `java-runner: "['ubuntu-latest']"`
- **Secrets**: inherited from repository/organisation

### Dependabot
- Weekly Maven ecosystem scan from the repository root. PRs are auto-generated for dependency version updates.

### Container Scan
- `allowedlist.yaml` suppresses `CVE-2018-1000632` and `CVE-2020-10683` (both dom4j XML parsing CVEs) in the Azure container scan step embedded in the CI pipeline.

### Gaps
- No automated integration test stage
- No staging/preview deployment step (library only)
- No semantic versioning automation (version is still `2.0.3-SNAPSHOT`)
- CodeQL runs only on Ubuntu; no Windows build verification
