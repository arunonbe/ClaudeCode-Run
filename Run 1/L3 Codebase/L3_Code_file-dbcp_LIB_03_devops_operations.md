# DevOps / Operations View — file-dbcp_LIB

## Build
- **Build system**: Maven, single-module JAR.
- **Maven wrapper**: `mvnw` / `mvnw.cmd` present.
- **Parent POM**: `com.ecount:module-parent:4` — Onbe/ecount internal parent POM.
- **Java**: Not explicitly set in POM; inherits from `module-parent`. Based on era and dependencies, targets Java 5/6.
- **Output**: `file-dbcp-1.0.2-SNAPSHOT.jar`.
- **Maven settings**: `.mvn/wrapper/settings.xml` references internal Nexus at `d-na-stk01.nam.wirecard.sys:8080`.

## Deployment
- **Deployment model**: JAR library distributed via internal Nexus. Not deployed independently.
- **Consumer deployment**: The consuming application server (Tomcat) must have the JAR on its classpath and the `ecount-db.properties` file at the configured filesystem path.
- No Docker, Kubernetes, or cloud deployment for this library itself.

## Configuration Management
- Configuration is entirely external — a `.properties` file on the server filesystem.
- Hardcoded path reference in test XML: `\\ecappdev\d$\C-Base\config\ecount-db.properties`.
- Production path would be specified in the consuming application's JNDI `context.xml` or Spring XML via the `configFile` attribute.
- No Spring Cloud Config, Azure App Configuration, or secrets manager integration.

## Observability
- Logging via Apache Commons Logging / log4j 1.2.15.
- Fatal-level log on properties file load failure (`log.fatal("Failed loading the central DB configuration file.")`).
- No metrics, health checks, or tracing.

## Infrastructure Dependencies
| Dependency | Notes |
|-----------|-------|
| Server filesystem | `ecount-db.properties` at configured path (UNC or local) |
| Tomcat 6 DBCP | `org.apache.tomcat.dbcp` (version 6.0.26) |
| Apache Commons DBCP 1.2.2 | Pool implementation |
| Internal Nexus | Maven artifact resolution |

## Operational Risks
1. Properties file path is hardcoded in tests as a Windows UNC share (`\\ecappdev\d$\C-Base\config\`) — this path must exist and be accessible on each deployment host.
2. No health check or readiness mechanism; pool exhaustion or properties file absence causes fatal failure at startup.
3. All dependencies are severely EOL (Tomcat 6, Commons DBCP 1.2.2, log4j 1.2.15, Commons Pool 1.4).
4. No connection validation beyond `validationQuery` — dead connection detection relies on manual configuration.
5. File I/O at pool construction time; if the file is unavailable (network share down), application startup will fail with no retry.

## CI/CD
- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL analysis.
- **Dependabot**: `.github/dependabot.yml`.
- No Jenkins, GitLab CI, or deployment pipeline.
- Maven deployment targets internal Nexus (inherited from `module-parent`).
