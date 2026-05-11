# xcontent_SVC — DevOps / Operations View

## Build
- **Build tool**: Maven (Maven Wrapper `mvnw`/`mvnw.cmd`)
- **Java version**: Java 21 (`maven.compiler.source=21`, `maven.compiler.target=21`)
- **Packaging**: WAR file (`finalName=xcontent`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12`
- **Additional build step**: `maven-dependency-plugin` copies shared JARs to `target/tomcat-lib/` at package phase:
  - `commons-discovery:0.2`, `commons-logging:1.1.1`, `slf4j-api`, `log4j-api`, `log4j-core`, `mssql-jdbc:12.5.0.jre11-preview`, `HikariCP:5.1.0`
- **Build args (CI)**: `'-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip'`

## Deployment
- **Container**: Dockerized with `bellsoft/liberica-openjre-alpine:21` base image
- **Application server**: Apache Tomcat 10.1.28 (downloaded from archive.apache.org during Docker build)
- **Exposed port**: 80 (HTTP)
- **WAR deployment**: `xcontent.war` → `/opt/tomcat/webapps/xContent.war` → context path `/xContent`
- **Shared libs**: `target/tomcat-lib/*.jar` → `/opt/tomcat/lib/` (SQL/HikariCP/logging JARs)
- **CI/CD**: GitHub Actions with `deployment.yml` (branch: `main`); delegates to `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`
- **APIM publishing**: `PUBLISH_TO_APIM: true` with `BACKEND_SUFFIX: "/services/xcontentWebServices"` — endpoint registered in API Management
- **Stages**: Build and deploy on `main` push; also triggers on PRs to `main`
- **EXCLUDE_STAGE: true** — stage environment skipped in deployment pipeline

## Configuration Management
- **Runtime config**: `ENV CBASE_HOME_URL=file:///cbase` (Dockerfile line 24) — expected mount at `/cbase` inside container
- **Properties file**: `applicationContext-xContent.properties` expected at `${CBASE_HOME_URL}/config/xContent/applicationContext-xContent.properties`
- **Configurable values**: `lucene.cms.dir`, `lucene.cms.name`, `lucene.cms.analyzer`
- **Environment via Tomcat**: `catalina.properties` modified to use `EnvironmentPropertySource` for reading environment variables in Tomcat XML config
- **No Kubernetes manifests or Helm charts** visible in this repository

## Observability
- **Logging**: Log4j2 (dependencies: `log4j-api`, `log4j-core`, `log4j-1.2-api` bridge, `log4j-jakarta-web`)
- **Access log**: Configured in `server.xml` via Tomcat `AccessLogValve` — writes `localhost_access_log.*.txt` to `logs/`
- **No APM or distributed tracing** configured
- **No health endpoint** defined in application; APIM/load balancer health checks presumably use `/xContent/` or `welcome.html`
- **`welcome.html`** and `unknown_error.html` present as static pages in `src/main/webapp/`

## Infrastructure Dependencies
| Dependency | Type | Details |
|-----------|------|---------|
| CMS Filesystem | Volume mount | `/cbase` — contains config and content files |
| SQL Server | RDBMS | Driver + HikariCP in shared Tomcat lib; no app-level datasource bean configured |
| APIM (API Management) | Gateway | Endpoint published as `xcontent-svc-api` |
| Container registry | Docker | Image pushed by CI; `Onbe/om-ci-setup` pipeline |
| PACT broker | Contract testing | `PACT_PACTICIPANT: xcontent-svc-api`; `VERIFY_PROVIDER_PACT: false` |

## Operational Risks
1. **Content files on volume mount**: If `/cbase` volume is unavailable at startup, Lucene index is empty; service starts but returns no content — silent data-unavailability
2. **Lucene RAMDirectory**: All content held in JVM heap; large content repositories can cause memory pressure; no configurable heap size in Dockerfile
3. **No content cache invalidation mechanism**: Content updates require pod/container restart
4. **Tomcat downloaded at build time**: `curl https://archive.apache.org/...` during Docker build; build fails if archive.apache.org is unreachable or the version is removed
5. **QA cert in image**: `certfile_qa.crt` included in all Docker images regardless of environment
6. **`autoDeploy=false`** in server.xml (`config/server.xml`, line 130) — correct for production, but manual WAR deployment is required if hotfix is needed without rebuild

## CI/CD Pipeline
```
GitHub Actions (deployment.yml)
  → Triggers on push to main or PR to main
  → Delegates to Onbe/om-ci-setup java-workflow.yml@main
  → APP_NAME: xcontentSVC
  → MAVEN_ARGS: '-s .mvn/wrapper/settings.xml -Dmaven.test.skip'
  → Builds WAR → Builds Docker image → Pushes to registry
  → Deploys to environment (stage excluded: EXCLUDE_STAGE=true)
  → Publishes WSDL to APIM (PUBLISH_TO_APIM=true)
  → UPDATE_DEPENDENCIES: true, UPDATE_PARENT_VERSION: true

GitHub Actions (github-package-publish.yml)
  → Triggers on main push and PRs
  → Delegates to Onbe/om-ci-setup java-package-publish.yml@main

GitHub Actions (codeql.yml)
  → CodeQL security analysis

GitHub Actions (redeploy.yaml)
  → Manual redeploy workflow

Dependabot
  → Automated dependency update PRs
```
