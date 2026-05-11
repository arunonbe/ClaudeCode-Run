# DevOps / Operations View — xsearch-new_SVC

## Build System
- **Language / Framework:** Java (compiler version not set in root POM — inherits from parent `com.citi.prepaid.service:service-parent:6`)
- **Parent POM:** `com.citi.prepaid.service:service-parent:6`; root artifact `com.ecount.service.xSearch-New:xSearch-New:2022.1.4` (POM)
- **Modules:** xSearch-common, xSearch-client, xSearch-impl, xSearch-xmlrpc
- **Build tool:** Maven (Maven wrapper `mvnw` / `mvnw.cmd` present)
- **CI tooling:** GitHub Actions — `.github/workflows/codeql.yml` (CodeQL SAST analysis, scheduled weekly)
- **Maven settings:** `.mvn/wrapper/settings.xml` (artifact repository configuration)

## Deployment
- **Deployment artifact:** `xSearch-xmlrpc` module builds a WAR file
- **Runtime container:** Tomcat (Servlet API 2.5 schema referenced in `web.xml` — Tomcat 7-era)
- **No Dockerfile** in this repository — unlike xsso_SVC, containerisation is not evidenced here
- **DataSources:** Runtime-configured via Director service (no static JNDI lookup)

## Configuration Management
- Spring XML application context loaded from classpath: `inputObjectsContext.xml`, `xmlrpcImplContext.xml`, `xSearchContext.xml`, `dataSourcesContext.xml`
- Log4j configuration path hardcoded in `web.xml`: `file:///d:/c-base/config/xSearch-xmlrpc/log4j.xml` — this is a developer Windows path; will fail in containerised or Linux deployments
- Director address (`${director.address}`) and database agent/name (`${agent}`, `${database}`, `${jobsvcdatabase}`) are runtime placeholders — configuration must be injected at deployment time
- Maven settings XML present for artifact repository access

## Observability
- Log4j XML-based logging — version and appender configuration not visible (external config file)
- `Log4jConfigListener` (Spring) referenced in `web.xml` — Spring's Log4j config listener (deprecated in Spring 3+)
- No structured logging, no distributed tracing, no metrics endpoint
- CodeQL SAST scanning runs weekly on a schedule (GitHub Actions)

## Infrastructure Dependencies
| Dependency | Version | Notes |
|---|---|---|
| Spring 2.5.4 | Root POM | Very old Spring version — see technical debt |
| Spring mock 2.0.4 | Test | Legacy test mock |
| xPlatform 2014.1.1 | Root POM | Very old xplatform version in root POM — conflict with impl module |
| director-client 1.0.11 | Root POM | Director RPC client for datasource configuration |
| ecount-system 1.0.10 | Root POM | Core2 system library |
| xmlrpc 1.0.9 | Root POM | Internal XML-RPC framework |
| junit 4.4 | Test | Old JUnit version |
| SQL Server | External | Director-configured via DBCP |
| Director Service | External | Provides database connection parameters at runtime |

**Note:** The root POM declares very old dependency versions. Individual module POMs may override these. The actual runtime versions in use require verification by examining the full effective POM.

## Operational Risks
- **Hardcoded Log4j path** (`file:///d:/c-base/config/xSearch-xmlrpc/log4j.xml` in `web.xml:35-36`) — logging fails silently in any non-developer environment
- **Director service as single point of failure:** If the Director service is unavailable at startup, datasources cannot be configured and the service will fail to start
- **Spring 2.5.4 in root POM** — EOL Spring version with known security vulnerabilities; runtime version must be confirmed
- **`xPlatform 2014.1.1` in root POM** — version from 2014; likely superseded by xplatform_LIB impl module dependency, but root POM declaration may cause classpath conflicts
- **Servlet API 2.5 schema in web.xml** — `javax.servlet` namespace (not `jakarta.servlet`); incompatible with Tomcat 10+
- **No Dockerfile / container build** — deployment mechanism is unclear; manual WAR deployment assumed

## CI/CD
- **GitHub Actions CodeQL** (`codeql.yml`): CodeQL SAST scheduled weekly on Fridays at 17:53 UTC; uses `codeql-auto.yml` from `Onbe/om-ci-setup`
- **GitHub Dependabot** (`.github/dependabot.yml`): Dependency update automation present
- No deployment workflow detected (unlike xsso_SVC which has `deployment.yml`)
- Maven wrapper present for reproducible builds
