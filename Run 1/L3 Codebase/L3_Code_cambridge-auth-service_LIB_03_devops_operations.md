# cambridge-auth-service_LIB — DevOps & Operations View

## Build & Packaging

| Attribute | Value |
|---|---|
| Build tool | Apache Maven |
| Packaging | `jar` (pom.xml line 7: `<packaging>jar</packaging>`) |
| Artifact ID | `CambridgeAuth` |
| Group ID | `com.citi.prepaid` |
| Version | `1.0-SNAPSHOT` (pom.xml line 8) |
| Maven wrapper | Present (`.mvn/wrapper/maven-wrapper.jar`, `mvnw`, `mvnw.cmd`) |
| Maven settings | `.mvn/wrapper/settings.xml` — likely points to internal Nexus/Artifactory |

**Key dependencies and their versions (pom.xml):**
| Dependency | Version | Notes |
|---|---|---|
| `org.apache.axis:axis` | 1.4 | Released 2006; end-of-life. Numerous known CVEs |
| `javax.xml:jaxrpc-api` | 1.1 | Legacy JAX-RPC 1.1 |
| `commons-logging` | 1.1.1 | Old; log4j-compatible |
| `commons-discovery` | 0.4 | Very old Apache Commons component |
| `wsdl4j` | 1.6.2 | WSDL parsing library |
| `org.springframework:spring-context` | 4.3.9.RELEASE | EOL Spring 4.x; Spring 4.3 reached EOL Dec 2020 |
| `junit:junit` | 3.8.1 | JUnit 3; extremely old |

**No `maven-compiler-plugin` version or Java source/target version is specified** — the POM only suppresses M2E lifecycle warnings (pom.xml lines 85–115). The effective Java compiler target is the Maven default (JDK 5 for the version range configured).

**Commented-out Spring Boot parent** (pom.xml lines 58–81) suggests an abandoned migration attempt to Spring Boot 1.5.2 + Spring WS Core.

## Deployment

This is a **library JAR**, not a deployable service. There is:
- No `Dockerfile`
- No Kubernetes manifests
- No deployment scripts
- No Spring Boot main class with embedded container

Deployment model: the built JAR (`CambridgeAuth-1.0-SNAPSHOT.jar`) is published to an internal Maven repository (via `.mvn/wrapper/settings.xml`) and consumed as a dependency by an upstream service.

The upstream consumer is responsible for providing the runtime configuration file at:
`d:/c-base/config/service/cambridgeAuthService/cambridgeAuthService.properties`
(hard-coded Windows path in `appContext-CambridgeAuthService.xml` line 9 and `src/test/resources/appContext.xml` line 9).

## Configuration Management

| Config Item | Mechanism | Location |
|---|---|---|
| All runtime parameters | Spring XML + `.properties` file | `appContext-CambridgeAuthService.xml` loaded via `ClassPathXmlApplicationContext` in `App.java` line 17 |
| Properties file path | Hard-coded Windows path `d:/c-base/...` in XML | `src/main/resources/appContext-CambridgeAuthService.xml` line 9 |
| WSDL service address | `cambridge.auth.address` property | Injected into `ServiceLocator.basicHttpBinding_ISSOService_address` |
| WSDL service name | `cambridge.auth.name` property | Injected into `ServiceLocator.basicHttpBinding_ISSOServiceWSDDServiceName` |
| Proxy host/port | `http.proxyHost` / `http.proxyPort` properties | Set as JVM System properties at call time (`CambridgeAuthServiceImpl.java`, lines 49–50) |
| Algorithm | `algorithm` property | Passed to `java.security.MessageDigest`; no validation |

**Hard-coded Windows drive path** (`d:/c-base/...`) is an operational liability — this library cannot be run on Linux (including Docker containers) without overriding or patching the XML. The CodeQL CI runner is configured as Linux (`ubuntu-docker` — `codeql.yml` line 11), meaning CI builds will fail to load the properties file if any test actually exercises the Spring context at a Linux path.

## Observability

| Capability | Present | Detail |
|---|---|---|
| Structured logging | None | No SLF4J, Log4j, or Logback usage |
| Error logging | `System.out` / `System.err` only | `App.java` line 25 (`System.err`), `CambridgeAuthServiceImpl.java` line 76 (`System.out.println("Exception : "+e)`), `AppTest.java` line 44 (`System.out.println`) |
| Metrics | None | No Micrometer, Prometheus, or JMX |
| Distributed tracing | None | No MDC, Zipkin, or OpenTelemetry |
| Health checks | None | Not applicable to a library |
| Audit log | None | Token issuance is not logged |

The only diagnostic output is ad-hoc `System.out.println` calls. Exception swallowing is present: `ContextHelper.java` line 16 catches all exceptions and prints to stderr, silently returning `null` context.

## Infrastructure Dependencies

| Dependency | Required | Notes |
|---|---|---|
| Cambridge SSO SOAP endpoint | Hard runtime dependency | `https://<cambridge.auth.address>/Service.svc/ssoBasic` |
| HTTP/HTTPS proxy | Required at Citi/Onbe network | Set via `http.proxyHost` / `http.proxyPort` JVM system properties |
| Properties file at `d:/c-base/...` | Required — will throw if absent | Hard-coded path; Windows-only |
| Internal Maven repo | Build time | `.mvn/wrapper/settings.xml` |
| JVM (any version; likely Java 6–8 era) | Runtime | No explicit version in POM |

## Operational Risks

1. **Hard-coded Windows path** blocks Linux/container deployment (`d:/c-base/config/...` in both Spring XML files).
2. **No retry or timeout configuration** on SOAP calls — a slow Cambridge endpoint causes caller threads to hang indefinitely.
3. **Axis 1.4 is end-of-life** with publicly known CVEs; no patch path within the current framework.
4. **Spring 4.3.9 is EOL** (since December 2020); not receiving security patches.
5. **`System.out` token logging** in `App.java` line 24 — tokens exposed in container stdout.
6. **SNAPSHOT version** in production: `1.0-SNAPSHOT` is mutable and non-reproducible.
7. **JVM-global proxy mutation**: `System.getProperties().put("http.proxyHost", ...)` modifies global JVM state and will affect all other HTTP calls in the same JVM (`CambridgeAuthServiceImpl.java`, lines 49–50).

## CI/CD

| Aspect | Detail |
|---|---|
| CI platform | GitHub Actions |
| CodeQL analysis | `.github/workflows/codeql.yml` — scheduled weekly (Sundays 04:52 UTC) and on `workflow_dispatch`; Java runner on self-hosted Linux ubuntu-docker |
| CodeQL reusable workflow | `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` |
| Dependency updates | Dependabot for Maven, weekly schedule (`.github/dependabot.yml`) |
| Build/test workflow | **Not present** — no `build.yml`, `test.yml`, or `publish.yml` workflow exists in `.github/workflows/` |
| Docker build | None |
| Artifact publishing | Not automated in this repo |

There is **no automated build or test CI workflow**. Only CodeQL SAST and Dependabot are configured. This means merged PRs are not automatically compiled or tested.
