# DevOps & Operations View — cs-api-singlewar_API

## Build System
- **Build tool**: Maven (mvnw wrapper, settings.xml in `.mvn/wrapper/`)
- **Maven parent**: `com.citi.prepaid:prepaid-parent:4.0.0` — a Citi-era internal parent POM
- **Artifact**: `CardManagement.war` (produced by `csapi-ws` module)
- **Modules**: `csapi-impl` (business logic library), `csapi-ws` (WAR)
- **Java version**: Not specified in pom.xml — inherits from parent; likely Java 8 or earlier given dependency versions
- **Spring version**: 2.0.8 (legacy Spring Framework, not Spring Boot)

## Dependencies (key)
| Dependency | Version | Risk |
|---|---|---|
| org.springframework:spring | 2.0.8 | EOL — known CVEs |
| commons-lang | 2.1 | EOL — use commons-lang3 |
| Apache Axis (inferred from web.xml) | 1.x | EOL — serious security history |
| com.ecount.spring-dbctx | spring-dbctx-container 1.0.4 | Internal; version age unknown |

## Deployment
- Packaging: WAR file deployed to an application server (Tomcat or JBoss/WildFly, inferred from JNDI resource definitions and `jboss-web.xml` referenced in the v2 context — this WAR has similar structure)
- JNDI DataSources must be pre-configured on the server: `jdbc/CbaseappDataSource`, `jdbc/JobSvcDataSource`, `jdbc/EcountCoreDataSource`
- Spring context config location: `classpath:accountManagementContext.xml` (and several other XMLs for affiliate service, search, comments)
- External property file: `${CBASE_HOME_URL}/config/CSWS/applicationContext-Singlewar.properties` must exist on the server before deployment
- Context path: Inferred as `/CardManagement` (V1) and `/CardManagementV3` (V3) based on test fixtures

## Configuration
- Properties are externalised to a filesystem properties file referenced via `${CBASE_HOME_URL}` environment variable
- Keys: `appId`, `agent`, `classification`, `endpoint`, `comment.appId`, `escalation.status`
- No Azure App Configuration integration (this is a pre-cloud artifact)
- No Spring Profiles — single environment configuration model

## Observability
- **Logging**: Log4j 1.x
  - Rolling file appender to `D:/c-base/runtime/logs/ecountws.log` (Windows path)
  - Console appender
  - Syslog appender to a hardcoded internal IP
  - Log level: WARN at root, INFO for `com.ecount`
- **Health check**: No health endpoint (`/hc` or Actuator) — this is pre-Spring Boot
- **Metrics**: None
- **Tracing**: None
- **Performance timing**: Duration of each operation is logged at INFO level: `WEB-SERVICE: ...accountInquiry (CS-API) (N ms)`

## Infrastructure Dependencies
| Dependency | Type | Notes |
|---|---|---|
| C-Base platform (ecount xPlatform) | RPC | Core card platform via proprietary protocol |
| CbaseApp SQL Server | JDBC/JNDI | Affiliate, PUID data |
| JobSvc SQL Server | JDBC/JNDI | PUID lookup |
| EcountCore SQL Server | JDBC/JNDI | Transaction data (via platform library) |
| Comment Service | Spring bean (classpath) | CS comment history |
| Affiliate Service | Spring bean (classpath) | Affiliate metadata |
| xSearch | (not in this WAR but referenced in web.xml context) | Account search |

## CI/CD
- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL weekly static analysis only
- **GitHub dependabot**: `.github/dependabot.yml` — automated dependency PRs
- **No deployment pipeline found**: No GitHub Actions deploy workflow; no GitLab CI file present in this repo (contrast with v1, v3 which have full deployment workflows)
- Deployment is likely manual WAR file copy to the application server

## Risks
1. **No CI deployment pipeline**: No automated build-and-deploy; human error risk on deployments.
2. **Filesystem-dependent configuration**: `${CBASE_HOME_URL}` must be set and the properties file must exist on the server — no fallback defaults.
3. **Windows-specific log path hardcoded**: `D:/c-base/runtime/logs/` — non-portable; would fail on Linux.
4. **Spring 2.x and Axis 1.x**: Both are EOL with multiple known CVEs. A security scan will flag these as critical findings.
5. **Log4j 1.x**: EOL, security concerns (different from Log4Shell but still unsupported).
6. **No health endpoint**: No way to verify the service is alive without sending an actual SOAP request.
7. **Singletons in Spring XML**: Several beans are defined as `singleton="false"` (prototype scope) — this is correct for stateful action beans, but the phrasing `singleton="false"` is the old Spring 1.x idiom; modern code would use `scope="prototype"`.
