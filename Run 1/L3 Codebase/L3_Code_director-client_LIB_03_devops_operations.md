# DevOps & Operations Report — director-client_LIB

## 1. Build System

| Attribute | Value |
|---|---|
| Build tool | Maven (Maven Wrapper `mvnw`) |
| Java version | 21 (declared in `pom.xml` lines 18–19: `maven.compiler.source=21`, `maven.compiler.target=21`) |
| Packaging | JAR (`<packaging>jar</packaging>`) |
| Single-module | Yes — no sub-modules |
| Parent POM | `com.parents:prepaid-parent:6.0.12` |
| Artifact | `com.ecount.service.Core2.director:director-client:2.0.1` |
| Settings file | `.mvn/wrapper/settings.xml` |

### Key Dependencies

| Library | Version | Purpose |
|---|---|---|
| `com.citi.prepaid.service.core:xmlrpc` | `3.0.1` (property `xmlrpc.version`) | Internal Onbe XML-RPC client utilities (`XMLRPCClientUtils`, `XmlRPCFromObjectMapper`, `XmlRPCToObjectMapper`, `XMLRPCServiceLocator`) |
| `commons-httpclient:commons-httpclient` | Managed by parent | Apache Commons HTTPClient 3.x — deprecated |
| `commons-codec:commons-codec` | Managed by parent | Encoding utilities |
| `junit:junit` | Managed by parent | Test framework (JUnit 4) |

---

## 2. CI/CD

### 2.1 GitHub Actions Workflows

| Workflow | File | Trigger |
|---|---|---|
| Library publish | `.github/workflows/github-package-publish.yml` | Push to `main`, PR to `main`, `workflow_dispatch` |
| CodeQL SAST | `.github/workflows/codeql.yml` | Push / PR |
| Dependabot | `.github/dependabot.yml` | Scheduled dependency updates |

### 2.2 Package Publish Workflow
```yaml
uses: Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main
with:
  MAVEN_BUILD_ARGS: "-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip"
```

Tests are **skipped on publish** (`-Dmaven.test.skip`). The library is published to GitHub Packages on every push to `main`. Supports dry-run, auto-increment versioning, and dependency update options via `workflow_dispatch` inputs.

---

## 3. Configuration Management

The library itself has **no configuration files** — all configuration is provided by the calling service at runtime:

| Parameter | How Supplied | Notes |
|---|---|---|
| Director URL | `URI directorLocation` passed to each method call | Callers typically read from Azure App Config or classpath YAML |
| Agent | `String agent` passed to each method call | e.g., `B2C`, `B2CSTAGE`, `B2CTEST` |
| Cache TTL | `long cacheExpiracyMsec` in `DirectorServiceLocatingCache` constructor | Set by calling service |
| HTTP timeouts | Static initializer in `DirectorXMLRPCClient` lines 60–66 | Connection: 60s; Socket: 5s — hardcoded in library |

### Timeout Configuration (Hardcoded)
- **Connection Manager timeout**: `1000 * 60 = 60,000 ms` (1 minute) — `connectionManager.getParams().setConnectionTimeout()` (line 63)
- **Per-request socket timeout**: `5000 ms` (5 seconds) — `myMethod.getParams().setParameter("http.socket.timeout", 5000)` (line 87)
- **Per-request connection timeout**: `5000 ms` (5 seconds) — line 89

These are **hardcoded** and cannot be overridden by callers. The 5-second socket timeout means any Director slowness will fail credential/service lookups after 5 seconds.

---

## 4. Observability

| Signal | Mechanism |
|---|---|
| Request logging | `log.get().error(String.format("Http response is %d", result))` on non-200 HTTP (line 107) |
| Exception logging | `log.get().debug(...)` on exception — **DEBUG level only** (line 119) |
| No success logging | No INFO/DEBUG on successful credential retrieval |
| ThreadLocal Logger | Each thread has its own `Logger` instance (safety measure for shared classloader) |
| Log name | `com.ecount.Core2.director` (constant `IDirectorClient.LOG_NAME`) |

**Gap**: Exceptions are logged at DEBUG level (line 119) and the method returns `null`. In production, DEBUG is typically not enabled, so credential failures will be **silent** unless the caller inspects the return value.

---

## 5. Infrastructure Dependencies

| System | Address | Protocol | Notes |
|---|---|---|---|
| Director service (prod) | `https://prod.nam.wirecard.sys:8080/service/dispatch.asp` | HTTPS/XML-RPC | From debit-api app-config |
| Director service (QA/staging) | `https://qa.nam.wirecard.sys:8080/service/dispatch.asp` / `https://uat.nam.wirecard.sys:8080/service/dispatch.asp` | HTTPS/XML-RPC | From debit-api app-config |
| Director service (dev test) | `Http://ecappdev/service/dispatch.asp` | HTTP (no TLS) | Hardcoded in test class |
| GitHub Packages | Maven registry | HTTPS | Artifact published here |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Director single point of failure | Critical | All Gen-2 services that use this library for credentials/service discovery fail if Director is unavailable |
| Silent credential failure | Critical | `get()` returns `null` on exception with only DEBUG logging; callers may proceed with null credentials causing NullPointerException or authentication failure with no clear error |
| Hardcoded 5-second timeout | High | Director slowness cascades to all services; not configurable per-caller |
| Apache Commons HTTPClient 3.x | High | EOL; known TLS vulnerabilities; should use Apache HttpClient 5.x |
| Tests skipped on publish | Medium | `Dmaven.test.skip` in publish workflow means regressions can be published |
| `test.java` in production JAR | Low | Swing GUI test utility packaged in main source; adds unnecessary size and dependency on Swing |
| No retry logic | High | Single attempt per Director call; transient network errors cause immediate failure |
| HTTP connection pool not bounded | Medium | `MultiThreadedHttpConnectionManager` with default parameters; may exhaust connections under load |
