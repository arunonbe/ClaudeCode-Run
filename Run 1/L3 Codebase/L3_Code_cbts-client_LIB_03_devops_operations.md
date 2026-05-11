# cbts-client_LIB — DevOps & Operations View

## Build & Packaging

**Build Tool**: Apache Maven 3.9.5 (pinned via Maven Wrapper — `.mvn/wrapper/maven-wrapper.properties`)

**Artifact coordinates** (`pom.xml`):
```
groupId:    com.wirecard.crossbordertransferservice
artifactId: cbtsclient
version:    2.1.5-SNAPSHOT
packaging:  jar
```

**Parent POM**: `com.parents:prepaid-parent:6.0.13` — a shared Onbe parent POM that manages transitive dependency versions and common plugin configuration.

**Java version**: 21 (both `maven.compiler.source` and `maven.compiler.target` = 21, `pom.xml` lines 18–19).

**Source encoding**: `Windows-1252` (`pom.xml` line 20) — a non-standard encoding that has already caused character corruption in `IsoCurrencyCode.java`. Should be `UTF-8`.

**Runtime dependencies** (versions resolved via parent BOM):
| Dependency | Purpose |
|---|---|
| `org.javalite:javalite-common` | Lightweight HTTP client (`Http.get`, `Http.post`, `Http.put`) and test assertion (`JSpec`) |
| `com.google.code.gson:gson` | JSON serialisation/deserialisation |
| `commons-lang:commons-lang` | `ToStringBuilder` for domain objects |

**Build profile**: The `maven-enforcer-plugin` (`banTransitiveDependencies`) is active, ensuring no unintended transitive dependencies slip through. Spring and `javalite-common` transitive deps are explicitly exempted (`pom.xml` lines 55–59).

**Standard build command** (per `README.md`):
```
mvn clean install -Dmaven.test.skip
```
Tests are skipped in the standard build. The `-s ./.mvn/wrapper/settings.xml` flag is added for CI (GitHub workflow line 41).

## Deployment

This library is deployed as a **JAR package to GitHub Packages** (Maven registry), not as a standalone deployable service. It is consumed as a dependency by other Onbe prepaid applications.

**Publish repository**: `https://maven.pkg.github.com/onbe/onbe_maven_releases`
(configured in `.mvn/wrapper/settings.xml`, lines 26–28)

**Consumer applications** (per Javadoc): OP (Online Portal) and batch processing systems, historically running on Tomcat 10.x (`README.md`).

**Versioning**: The current version is a SNAPSHOT (`2.1.5-SNAPSHOT`). The CI workflow supports manual version override (`version-tag` input), auto-increment, and dry-run modes.

## Configuration Management

All configuration is **injected at instantiation time** by the calling application:

| Parameter | Constructor Arg | Default (if not overridden) |
|---|---|---|
| `uriBase` | Required | None |
| `HEADER_ACCEPT` | Required | None |
| `HEADER_Content_Type_Json` | Required | None |
| `CONNECTION_TIMEOUT` | Required | 5000 ms |
| `READ_TIMEOUT` | Required | 5000 ms |
| `USERNAME` | Optional (overloaded constructor) | Hardcoded literal in source |
| `PASSWORD` | Optional (overloaded constructor) | Hardcoded literal in source |

**Critical gap**: There is no externalised configuration mechanism (no properties file, no Spring @Value, no environment variable lookup). The library relies on callers to supply all configuration. The default `USERNAME` and `PASSWORD` in `CBTSClient.java` lines 94–95 are **production-looking hardcoded credentials**, which is a severe operational and security risk.

**Correlation ID**: The library reads the correlation ID from SLF4J MDC key `audit.global.request.id` (constant `CORRELATION_ID_LEGACY`). If not present in MDC, a new UUID is generated per request. This propagates tracing to the CBTS service via the `CORRELATION-ID` HTTP header.

## Observability

**Logging**: SLF4J with Lombok `@Slf4j` annotation on `CBTSClient`. Log4j2 is configured for tests (`src/test/resources/log4j2-test.xml`). All package `com.*` logs at DEBUG level during test runs.

Log statements present in `CBTSClient.java`:
- INFO: "Create/Update Remitter Info as ID: ..." (line 155) — logs remitterID
- INFO: "Create/Update a beneficiary: " + `bene.toString()` (line 249) — **logs full beneficiary including bank account and routing number**
- INFO: "IBAN value for validateIban " + iban (line 491) — **logs full IBAN value**
- INFO: Remitter location header and parsed ID (lines 189–196)
- INFO: All error response bodies (`getErrorResponse`, line 448)
- DEBUG: Correlation ID resolution (lines 461–465)

**No metrics or distributed tracing** (e.g., Micrometer, OpenTelemetry) are present. Observability depends entirely on log aggregation by the consuming application.

**No health check endpoint** — this is a library, so there is no liveness/readiness probe concept.

**Connection and read timeouts** default to 5000 ms each; configurable per-instance. No retry logic is implemented. If the CBTS service is unavailable, a `RuntimeException` is thrown (evidenced by `validURL` and `validTimeout` tests in `CBTSClientTest.java`).

## Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| CBTS Service (`cross-border-transfer-service`) | External REST API | URI base injected at construction; QA env: `q-na-app08.nam.wirecard.sys:9443` (found in `CBTSClientTest.java` line 47) |
| Cambridge Global Payments | External FX provider | Reached via CBTS service, not directly by this library |
| GitHub Packages (`maven.pkg.github.com/onbe/onbe_maven_releases`) | Maven artifact registry | Both source of parent POM dependencies and publish target |
| GitHub (`github.com/Onbe/om-ci-setup`) | Reusable workflow library | CI workflow delegates to `om-ci-setup/.github/workflows/java-package-publish.yml@main` |

The library's `initSSLContext()` method sets a **JVM-global SSL context** (`SSLContext.setDefault()` and `HttpsURLConnection.setDefaultSSLSocketFactory()`) that disables certificate validation for the entire JVM process (lines 144–148). This is a significant infrastructure risk: any other HTTPS connection made by the embedding application's JVM will also skip certificate validation.

## Operational Risks

1. **JVM-wide TLS bypass** — `initSSLContext()` sets the default JVM SSL context to trust-all. This affects not just CBTS calls but ALL HTTPS connections in the embedding JVM process.
2. **Hardcoded credentials** — If the default constructor path is used (`CBTSClient(uriBase, accept, contentType, connTimeout, readTimeout)` — `pom.xml` line 113–124), the hardcoded USERNAME/PASSWORD from lines 94–95 are used. There is no guard preventing use of default credentials in production.
3. **No retry or circuit-breaker logic** — A transient CBTS failure causes an immediate exception. The calling application must implement its own retry strategy.
4. **Rate expiry window (~3 minutes)** — As evidenced in `CBTSRateExpiredTest.java` (3-minute sleep, line 107), rates expire quickly. Slow batch systems may frequently encounter `EXPIRED_RATE` errors, requiring full rate-request-book cycles to be retried.
5. **SNAPSHOT dependency** — The current version is a SNAPSHOT, meaning the artifact may change without a version bump, creating non-deterministic behaviour in downstream consumers.
6. **Windows-1252 source encoding** — Could cause build failures or data corruption on Linux CI runners (Ubuntu-latest in the CodeQL workflow, `codeql.yml` line 11) if any source file contains non-ASCII characters.

## CI/CD

### Publish Workflow (`.github/workflows/github-package-publish.yml`)
- **Triggers**: Push to `main` branch (excluding `.mvn/**`, `.github/**` changes), pull requests targeting `main`, and manual dispatch.
- **Reusable workflow**: Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`.
- **Build command**: `mvn ... -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` — tests are skipped during publish.
- **Manual inputs**: `version-tag` (override), `auto-increment` (boolean), `dry-run` (boolean), `update-dependencies` (boolean).
- **Authentication**: `GITHUB_TOKEN` via `settings.xml`; full secrets inherited from the org (`secrets: inherit`).

### CodeQL Security Scanning (`.github/workflows/codeql.yml`)
- **Triggers**: Manual dispatch and weekly schedule (Saturday 14:34 UTC — `cron: '34 14 * * 6'`).
- **Runner**: `ubuntu-latest`.
- **Reusable workflow**: Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.

### Dependency Updates (`.github/dependabot.yml`)
- **Ecosystem**: Maven.
- **Schedule**: Weekly.
- **Directory**: `/` (root `pom.xml`).

### Gaps
- **No unit test execution in CI** — the publish workflow skips tests (`-Dmaven.test.skip`). The integration tests (`@Tag("Integration")`) require a live CBTS environment and are not wired into any automated pipeline.
- **No separate staging/production promotion gate** visible in this repo.
- **No container/Dockerfile** — the library is consumed as a JAR dependency, not containerised itself.
