# DevOps / Operations Analysis: rebate-inquiry_WAPP

## Build System
- **Maven** (mvnw wrapper present), artifact `rebatecardinquiry-2.0.2-SNAPSHOT.war`
- Java source/target: **Java 8** (maven.compiler.source/target = 1.8)
- Parent POM: `com.citi.prepaid.web:webapp-parent:9`
- Build uses **xdoclet** (generate-sources phase via maven-antrun-plugin) to generate Struts config XML from `@struts.action` JavaDoc annotations — this is a very old code-generation approach.
- Maven release plugin configured; SCM points to GitLab (`gitlab.com/northlane/...`).

## Deployment
- Packaging: **WAR** file, deploy to a Java EE application server (JBoss indicated by presence of `jboss-web.xml`).
- WAR context name: `rebatecardinquiry`.
- `jboss-web.xml` present — deployment target is **JBoss / WildFly**.
- No Dockerfile, no Kubernetes manifests, no CI/CD pipeline files present in this repo.
- Distribution repository (Nexus): `d-na-stk01.nam.wirecard.sys:8080/nexus` — internal Wirecard (pre-Onbe) Nexus server; this URL is stale.

## Configuration Management
- Configuration is loaded at startup from a hard-coded filesystem path: `D:/c-base/config/rebate-cardinquiry/rebate.properties` (Windows path — implies deployment on Windows Server).
- Log4j XML configuration loaded from: `D:/c-base/config/rebate-cardinquiry/log4j.xml`.
- No environment variable support; no Spring profiles; no external config server.
- If the properties file is absent or the path changes, the application fails to start.
- The `src/main/resources-filtered/artifactInfo.properties` file uses Maven filtering for build metadata.

## Observability
- Logging via **Log4j 1.2.17** (EOL; known CVEs including Log4Shell if JNDI is on classpath).
- JSON log layout via `jsonevent-layout 1.7` (net.logstash.log4j) — suggests log aggregation to a log shipper (Logstash/filebeat).
- No metrics, no health check endpoints, no distributed tracing.
- Application is a traditional Struts 1 WAR — no Actuator or similar.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|---|---|---|
| JBoss / WildFly | App server | Required for WAR deployment |
| SMTP server | Email relay | Required for notification delivery; no config visible in this repo |
| cbase/ecountcore libraries | Internal library | `com.ecount:xPlatform:2.5.37`; contains NotificationManagerImpl |
| `D:/c-base/config/` filesystem | Config storage | Hard-coded Windows path |
| Wirecard Nexus (`d-na-stk01.nam.wirecard.sys`) | Artifact repository | Stale; needs migration to current Nexus/Artifactory |

## Operational Risks
1. **Hard-coded Windows filesystem paths** (`D:/c-base/config/...`) in web.xml and applicationContext.xml — non-portable; deployment fails on non-Windows or path changes.
2. **No health check**: No mechanism for load balancer or monitoring system to detect application failure.
3. **Log4j 1.2.17**: EOL library; while the specific Log4Shell (CVE-2021-44228) affects Log4j 2.x, Log4j 1.x has its own known CVEs (CVE-2019-17571, CVE-2022-23302/23303/23305).
4. **Stale Nexus URL**: Build will fail if Maven attempts to resolve artifacts from the decommissioned Wirecard Nexus server.
5. **No CI/CD pipeline in repo**: Build and deployment process is manual or relies on external tooling not visible here.
6. **SNAPSHOT version in production**: Version `2.0.2-SNAPSHOT` suggests a non-release artifact may be deployed.

## CI/CD
No Jenkinsfile, GitHub Actions, or GitLab CI YAML found in this repository. Build and deployment are not automated from within this codebase.
