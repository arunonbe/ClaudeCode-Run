# DevOps / Operations View — xsso_SVC

## Build System
- **Language / Framework:** Java 21, Maven
- **Parent POM:** `com.parents:prepaid-parent:6.0.12`
- **Artifact:** `xSSO:xsso:3.0.1-SNAPSHOT` (WAR)
- **Compiler target/source:** Java 21
- **Build command:** `mvn -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` (from deployment workflow)
- **Plugins:** `maven-war-plugin`, `maven-dependency-plugin` (copies tomcat-lib JARs), `maven-enforcer-plugin`
- **Tomcat lib JARs copied at build time:** `commons-discovery-0.2`, `commons-logging-1.1.1`, `slf4j-api`, `log4j-api`, `log4j-core`, `mssql-jdbc:12.5.0.jre11-preview`, `HikariCP:5.1.0`
- **Final name:** `xsso.war`

## Deployment
- **Container:** Apache Tomcat 10.1.28 (downloaded in Dockerfile at build time via `archive.apache.org`)
- **Base image:** `bellsoft/liberica-openjre-alpine:21` (BellSoft Liberica JRE 21 on Alpine)
- **Port exposed:** 80 (internal), mapped to 9006 in docker-compose
- **Config mount:** `${CONFIG_DIR}:/cbase/config` (volume mount — externalised configuration)
- **WAR deployment:** `target/xsso.war` deployed as `xSSO.war` in `/opt/tomcat/webapps/`
- **Tomcat config:** Custom `config/server.xml` replaces default Tomcat server.xml
- **QA certificate:** `config/certfile_qa.crt` imported into cacerts in Dockerfile (`keytool -import`)
- **TLS:** `keytool -storepass changeit` — default Java cacerts store password used

## Configuration Management
- **External config path:** `${CBASE_HOME_URL}/config/xSSO/applicationContext-xSSO.properties` (set via `CBASE_HOME_URL=file:///cbase` environment variable in Dockerfile)
- **Config mount:** `/cbase/config` — JKS keystores, properties file, log4j2 config all expected here
- **Environment variables:** `CBASE_HOME_URL`, `SERVER_PORT`, `JAVA_OPTS` (module opens), `.env` file via `env_file` in docker-compose
- **Keystore passwords:** Set in `applicationContext-xSSO.properties` — externalised but must not be the default `ecount` value in production
- **Log4j2 config:** `${CBASE_HOME_URL}/config/xSSO/log4j2.xml` (externalised)
- **JNDI DataSource:** `java:comp/env/jdbc/JobSvcDataSource` — configured in Tomcat JNDI / container

## Observability
- **Logging:** Log4j2 (`log4j-api`, `log4j-core`, `log4j-jakarta-web`); configuration externalised to `/cbase/config/xSSO/log4j2.xml`
- **Log4j refresh interval:** 300,000 ms (5 minutes) — config reloads without restart
- **Health check endpoint:** `GET /hc` via Spring MVC `HealthCheck` controller
- **No distributed tracing, no metrics endpoint**
- **`pragma: no-cache` header** set on all servlet responses
- **Lombok `@Slf4j`** used throughout SSO classes for structured logging

## Infrastructure Dependencies
| Component | Version | Notes |
|---|---|---|
| Tomcat | 10.1.28 | Downloaded at Docker build time from `archive.apache.org` |
| BellSoft Liberica JRE | 21 (Alpine) | Base container image |
| mssql-jdbc | 12.5.0.jre11-preview | SQL Server JDBC driver; `jre11-preview` variant |
| HikariCP | 5.1.0 | Connection pool |
| xplatform_LIB | 6.1.8 | Business logic dependency |
| spring-dbctx-mock | 2.0.1 | Database context mock (compile scope — unusual) |
| XStream | Managed | XML serialisation |
| jtds | Managed | Legacy JTDS SQL Server driver (alongside mssql-jdbc) |
| dom4j | Managed | XML document API |
| displaytag | Managed | Table rendering tag library |
| wirecard QA hosts | Network | `qa.nam.wirecard.sys:10.91.22.253`, `ppnaut.nam.wirecard.sys:10.91.22.254` in docker-compose |

## Operational Risks
- **`spring-dbctx-mock` in compile scope:** A mock/test library in compile scope means it is bundled in the production WAR — this is a code quality risk and may indicate the production code depends on mock behaviour
- **`mssql-jdbc:12.5.0.jre11-preview`:** `jre11-preview` is a pre-release variant; `jre11` or `jre21` release builds should be used in production
- **Tomcat downloaded at build time from `archive.apache.org`:** If the archive URL becomes unavailable or the file is tampered with, builds fail or produce a compromised image; hash verification is not present in the Dockerfile
- **Hardcoded Wirecard host IPs in docker-compose:** `qa.nam.wirecard.sys:10.91.22.253` — environment-specific and Wirecard-branded; these entries should be environment-specific config, not committed
- **Default JKS passwords (`ecount`) in committed properties file:** If the dev properties file reaches a non-dev environment, cryptographic material is exposed
- **SNAPSHOT version (`3.0.1-SNAPSHOT`):** Non-deterministic build; image tags may not be reproducible

## CI/CD
- **GitHub Actions deployment workflow** (`deployment.yml`): Triggers on push/PR to `main`; uses `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`; publishes to APIM; skips STAGE
- **GitHub Actions GitHub Package publish** (`github-package-publish.yml`): Publishes Docker image to GitHub Container Registry
- **GitHub Actions redeploy** (`redeploy.yaml`): Separate redeployment trigger
- **CodeQL SAST** (`codeql.yml`): Weekly scheduled scan
- **Dependabot** (`.github/dependabot.yml`): Dependency update automation
- **Container scan allowlist** (`.github/containerscan/allowedlist.yaml`): 8 CVEs explicitly allowed — see CVE list in solution architect view
- **Maven args:** `-Dmaven.test.skip` — tests skipped in CI
- **PACT contract testing:** `PACT_PACTICIPANT: xsso-svc`; `VERIFY_PROVIDER_PACT: false` — consumer pact enabled but provider verification disabled
