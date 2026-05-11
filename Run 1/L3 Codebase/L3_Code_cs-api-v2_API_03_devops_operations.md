# DevOps & Operations View — cs-api-v2_API

## Build System
- **Build tool**: Maven (mvnw wrapper)
- **Maven parent**: None declared — standalone pom.xml
- **Artifact**: `CardManagementV2.war`
- **Java version**: Source/target 1.5 (Java 5 — extremely outdated)
- **Packaging**: Single WAR, no Spring Boot module
- **No parent POM**: Unlike V1 and V3, V2 has no internal parent POM — all dependency versions are managed directly

## Key Dependencies
| Dependency | Version | Risk |
|---|---|---|
| org.springframework:spring | 2.5.4 | EOL, known CVEs |
| axis:axis | 1.4 | EOL, security vulnerabilities |
| log4j:log4j | 1.2.9 | EOL, predates Log4Shell but still unsupported |
| net.sourceforge.jtds:jtds | 1.2 | Old SQL Server driver; TLS 1.2 issues |
| com.ecount:xPlatformLibrary | 1.0.6 | Internal |
| com.ecount:xPlatform | 2.4.5 | Internal; old version |
| junit | 3.8.1 | Obsolete test framework version |
| javax.servlet:servlet-api | 2.4 | Very old servlet API |

## CI/CD
| Workflow | Trigger | Action |
|---|---|---|
| `.github/workflows/codeql.yml` | Weekly (Thursday) | CodeQL static analysis only |
| `.github/dependabot.yml` | Scheduled | Dependency update PRs |

**No deployment pipeline**: There is no GitHub Actions deployment workflow or GitLab CI pipeline for V2. V2 is likely deployed manually or via a legacy internal pipeline not represented in this repository.

## Deployment
- Target: Application server (JBoss/WildFly or Tomcat) via WAR deployment
- JNDI DataSources must be configured on server: `jdbc/JobSvcDataSource`, `jdbc/EcountCoreDataSource`
- External properties file required: `file:D:/c-base/config/xCSAPI/applicationContext-xCSAPI.properties`
- Context path: `/CardManagementV2`
- Jetty plugin configured for local development (`port 9001`, `contextPath /CardManagementV2`) — suggests developers can run locally via `mvn jetty:run`

## Configuration
- External config: `D:/c-base/config/xCSAPI/applicationContext-xCSAPI.properties` — loaded via `PropertyPlaceholderConfigurer` with `file:` URI
- Keys: `appId`, `agent`, `classification`, `endpoint`
- `jetty-env.xml` present for local development JNDI setup
- No environment variable support; no cloud config integration
- No Spring Profiles

## Observability
- **Logging**: Log4j 1.2.9 (very old)
  - Properties file at `src/test/resources/log4j.properties` — test-only; no production log config in the main source
  - Production log configuration likely comes from the server or the `D:/c-base/config/` directory
- **Timing**: `startTime` / `duration` logged at INFO level per operation
- **No health endpoint**
- **No metrics, no tracing, no structured audit logging**

## Local Development
The Jetty Maven plugin is configured in pom.xml:
```xml
<contextPath>/CardManagementV2</contextPath>
<port>9001</port>
<jettyEnvXml>src/main/resources/jetty-env.xml</jettyEnvXml>
```
Developers can run `mvn jetty:run` for local testing against a Jetty server with JNDI configured.

## Test Execution
- Integration tests in `src/integration-test/java/` using `AccountManagementServiceTest` and `AccountManagementServiceTwoTest`
- Unit tests in `src/test/java/`
- No Maven Failsafe plugin configured for integration tests — they may not run automatically
- JUnit 3.8.1 used (pre-annotation syntax)

## Risks
1. **Java 1.5 target**: Unsupported since 2009. Modern JVMs will compile this but the language level limits expressiveness and safety.
2. **Per-request Spring context creation**: `new ClassPathXmlApplicationContext(...)` on every invocation — severe performance bottleneck. Under moderate load this will exhaust memory and CPU.
3. **No automated deployment pipeline**: WAR deployments are manual or via undocumented legacy tooling.
4. **Dependency versions with known CVEs**: Spring 2.5.4, Axis 1.4, Log4j 1.2.9, jTDS 1.2 — all have multiple known vulnerabilities.
5. **No container build**: No Dockerfile — cannot be containerised without significant refactoring.
6. **JBoss deployment descriptor**: `jboss-web.xml` present — suggests JBoss/WildFly was or is a target deployment server; this is environment-specific configuration.
