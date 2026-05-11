# cambridge-service_LIB — DevOps & Operations View

## Build & Packaging

### Build Tool
- **Maven** via Maven Wrapper (`mvnw` / `mvnw.cmd`)
- Maven Wrapper version: **3.9.1** (`.mvn/wrapper/maven-wrapper.properties` line 17: `apache-maven-3.9.1-bin.zip`)
- Maven Wrapper infrastructure version: 3.2.0

### POM Details (`pom.xml`)
| Property | Value |
|---|---|
| GroupId | `com.citi.prepaid` |
| ArtifactId | `CambridgeService` |
| Version | `1.0-SNAPSHOT` |
| Packaging | `jar` |
| Java source compatibility | Not declared (defaults to JVM default) |

The version is `1.0-SNAPSHOT`, indicating the library has **never been released to a release repository**. It is in perpetual snapshot state.

### Dependencies Declared in POM
| Dependency | Version | Scope |
|---|---|---|
| `junit:junit` | 3.8.1 | test |
| `org.springframework:spring` | 2.0.3 | compile |
| `org.apache.axis2:axis2-kernel` | 1.7.5 | compile |
| `org.apache.axis2:axis2-adb` | 1.7.5 | compile |
| `org.apache.ws.commons.axiom:axiom-api` | 1.2.20 | compile |
| `org.apache.neethi:neethi` | 3.0.1 | compile |
| `org.apache.axis2:axis2-transport-local` | 1.6.2 | compile |
| `org.apache.axis2:axis2-transport-http` | 1.7.5 | compile |
| `org.apache.axis2:axis2-saaj` | 1.7.5 | compile |

All core dependency versions are significantly outdated (Spring 2.0.3 from 2007; Axis2 1.7.5 from 2017; JUnit 3.8.1 from 2004). No dependency management via BOM or parent POM is present.

### Build Notes
- A `maven-jar-plugin` configuration is commented out in the POM (lines 62–65). It would have added `addressing-1.7.5.mar` to the manifest classpath. The addressing module must be available on the classpath at runtime (loaded via `stub._getServiceClient().engageModule("addressing")` in every service call).
- The Axis2 repository path is hardcoded to `D:\c-base\runtime\axis\repository` in `CambridgeServiceConstants.java` (line 5). This path is a Windows-specific local filesystem reference and must exist for default constructor initialization of any stub.

---

## Deployment

### Deployment Model
This is a **shared library (JAR)**, not a standalone service. It must be:
1. Built with `mvn package` (or `./mvnw package`)
2. Installed to a local or internal Maven repository (`mvn install`)
3. Declared as a dependency in consuming service POMs

No Docker, Kubernetes, or cloud deployment configuration is present in the repository.

### Runtime Prerequisites
- **JVM**: Any JDK supporting the used APIs (minimum Java 6/7 based on Axis2 1.7.5 requirements)
- **Axis2 repository**: Directory at `D:\c-base\runtime\axis\repository` containing the `addressing` module (`addressing-1.7.5.mar`). This path is OS-specific and Windows-only as hardcoded.
- **Properties file**: `d:/c-base/config/service/cambridgeService/cambridgeService.properties` must be present with keys: `return.url`, `cambridge.user.name`, `sharedSec`, `algorithm`, `http.proxyHost`, `http.proxyPort`
- **HTTP Proxy**: The `App.java` sets `http.proxyHost` and `http.proxyPort` system properties from configuration, indicating network access to Cambridge is via a corporate proxy.

### Environment Targeting
All stub default constructors point to the **beta/sandbox** environment:
- SSO: `https://isbeta.cambridgefxonline.com/Service.svc/sso`
- Trade: `https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiTrade`
- Bank: `https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiBank`
- Bene: `https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiBene`
- RegE: `https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiRegEDisclosure`

Production endpoint URLs must be supplied via constructor argument or overridden in Spring XML configuration. The consuming service bears this responsibility — there is no environment variable or profile-based endpoint resolution in this library.

---

## Configuration Management

### Spring XML Configuration
`src/main/resources/appContext-CambridgeService.xml` is the only configuration file. It:
- Defines all Spring beans via classic `<bean>` XML (Spring 2.0.3 style — no annotations, no Spring Boot)
- Uses `PropertyPlaceholderConfigurer` to load properties from a **hardcoded absolute Windows path**: `file:///d:/c-base/config/service/cambridgeService/cambridgeService.properties`
- Wires stubs to service implementations via property injection

### Configuration Parameters (from Spring XML)
| Spring Property | Source Property Key | Bean |
|---|---|---|
| `returnURL` | `${return.url}` | `serviceContext` |
| `cambridgeUserName` | `${cambridge.user.name}` | `serviceContext` |
| `sharedSecretKey` | `${sharedSec}` | `serviceContext` |
| `algorithm` | `${algorithm}` | `serviceContext` |
| `proxyHost` | `${http.proxyHost}` | `serviceContext` |
| `proxyPort` | `${http.proxyPort}` | `serviceContext` |

### Configuration Risks
1. **Hardcoded filesystem path** for properties file makes this library non-portable outside a specific Windows workstation/server layout. Containerization or cloud deployment would require significant refactoring.
2. **No environment profiles**: No Spring profiles, no YAML, no externalized config system (no Spring Boot, no Consul, no AWS Parameter Store).
3. **Secret in properties file**: `${sharedSec}` is the HMAC signing key stored in a local file. No vault or HSM integration.

---

## Observability

### Logging
- **Zero logging framework usage** across all implementation and stub classes. No SLF4J, Log4j, Logback, or JUL imports anywhere.
- Error handling in `App.java` (the demo harness) uses `e.printStackTrace()` exclusively (lines 57, 96, 109, 127, 148, 163, 183, 235).
- There is no request/response logging, no correlation ID logging, and no performance metrics emission.

### Metrics
- None. No Micrometer, no Prometheus, no JMX MBeans, no custom metrics.

### Tracing
- No distributed tracing (no OpenTelemetry, no Zipkin, no Sleuth).
- `correlationId` is passed through to Cambridge in `bookDeal` and `cancelDeal` but not logged locally.

### Health Checks
- None. No health endpoint, no readiness probe.

### Alerting
- None defined within the library.

**Operational conclusion**: This library is essentially a black box from an observability perspective. Any consuming service that does not add its own logging wrapper around these calls will have zero visibility into Cambridge API interactions.

---

## Infrastructure Dependencies

| Dependency | Type | Details |
|---|---|---|
| Cambridge FX Online (beta) | External HTTPS SOAP endpoint | `isbeta.cambridgefxonline.com` — beta only; production URL not in code |
| Corporate HTTP Proxy | Network | Host/port injected via `${http.proxyHost}` / `${http.proxyPort}`; set as JVM system properties at startup |
| Axis2 module repository | Local filesystem | `D:\c-base\runtime\axis\repository` — must contain `addressing-1.7.5.mar` |
| Properties file | Local filesystem | `d:/c-base/config/service/cambridgeService/cambridgeService.properties` — Windows absolute path |
| Maven Central | Build-time | Used to download dependencies during `mvn package` |

---

## Operational Risks

1. **Beta environment hardcoding**: All default stub constructors target `isbeta.cambridgefxonline.com`. A consuming service that instantiates stubs without endpoint override will silently send real transactions to a sandbox. No warning or validation guards this.

2. **Windows-only filesystem paths**: Both `CambridgeServiceConstants.AXIS_REPOSITORY` (`D:\c-base\runtime\axis\repository`) and the Spring XML property file path (`d:/c-base/config/...`) are hardcoded Windows drive-letter paths. The library cannot run on Linux without code or configuration changes, precluding containerisation.

3. **No error recovery**: All remote exceptions propagate upward or are printed and swallowed. There is no retry policy, timeout configuration, or circuit breaker. Network blips cause silent failures.

4. **Snapshot version**: Version `1.0-SNAPSHOT` means Maven resolves this artifact dynamically at build time. In CI, this can cause non-deterministic builds if the snapshot is updated.

5. **Outdated dependencies with known CVEs**: Spring 2.0.3 (2007), Axis2 1.7.5 (2017), JUnit 3.8.1 (2004) all have numerous published CVEs. Axis2 1.7.x specifically has known deserialization and XXE vulnerabilities.

6. **addressing module manual engagement**: Every service call includes `stub._getServiceClient().engageModule("addressing")`. If the `addressing` module is not in the Axis2 repository or fails to load, all calls fail silently (exception eaten in some paths).

---

## CI/CD

### GitHub Actions Workflows
Only one workflow is configured: `.github/workflows/codeql.yml`

```yaml
name: "CodeQL"
on:
  workflow_dispatch:
  schedule:
    - cron: 13 22 * * 4   # Weekly, Thursday 22:13 UTC
jobs:
  analyze:
    uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
    secrets: inherit
    with:
      java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"
```

- CodeQL SAST scan runs weekly on Thursdays and on manual trigger.
- Uses a self-hosted Linux runner (`ubuntu-docker`).
- Delegates to the shared Onbe CI setup repository (`om-ci-setup`).

### Dependabot
`.github/dependabot.yml` configures weekly Maven dependency version checks on the root directory.

### Gaps in CI/CD
- **No build workflow**: There is no `build.yml` or `ci.yml` that runs `mvn package` on pull requests or pushes. CodeQL is the only automated workflow.
- **No test execution in CI**: No workflow triggers `mvn test`. The only test dependency is JUnit 3.8.1 with no actual test classes present (not visible in source scan).
- **No artifact publishing**: No step publishes the JAR to an internal Maven repository (Nexus, Artifactory).
- **No vulnerability gate**: Dependabot raises PRs but there is no workflow that blocks merges on high/critical CVEs.
