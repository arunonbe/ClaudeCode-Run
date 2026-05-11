# DevOps & Operations View — csapiws-payout_API

## Build System
- **Build tool**: Maven (mvnw wrapper)
- **Maven parent**: None — standalone pom.xml (no internal parent POM)
- **Artifact**: `CardManagementPayoutV3.war`
- **Java version**: Source/target 1.8 (Java 8 — more recent than V2's Java 5, but still outdated)
- **Version**: `2.0.2-SNAPSHOT`
- **Packaging**: Single WAR module — no Spring Boot module, no multi-module structure
- **No parent POM**: Dependency versions managed directly in pom.xml

## Key Dependencies
| Dependency | Version | Risk |
|---|---|---|
| org.springframework:spring | 2.5.4 | EOL, known CVEs |
| axis:axis | 1.4 | EOL, security vulnerabilities |
| log4j:log4j | 1.2.17 | EOL; predates Log4Shell but later than V2 (which used 1.2.9) |
| net.sourceforge.jtds:jtds | 1.2 | Old SQL Server driver; TLS 1.2 issues |
| com.ecount:xPlatformLibrary | 2014.3.1 | Internal — version name is a year/quarter stamp |
| com.ecount:xPlatform | 2019.1.1 | Internal — newer than V2 (2.4.5) but older than V3 (6.5.8) |
| com.ecount.service.xSearch-New:xSearch-impl | 2.0.0 | Internal member/device search |
| com.ecount.one.service.affiliate:xAffiliateService | 1.0.8 | Internal affiliate service — older than V3 (xaffiliate-service 4.0.1) |
| com.ecount.services:comment | 1.0.3 | Internal comment service — older than V3 (comment 3.0.1) |
| net.logstash.log4j:jsonevent-layout | 1.7 | JSON-formatted log events for log aggregation |
| junit:junit | 4.12 | Test framework |
| xerces:xercesImpl | 2.8.1 | Old XML parser |

## CI/CD
| Workflow / Pipeline | Trigger | Action |
|---|---|---|
| `.gitlab-ci.yml` | GitLab CI (northlane group) | Includes `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml` |
| `.github/workflows/codeql.yml` | Weekly (GitHub) | CodeQL static analysis |
| `.github/dependabot.yml` | Scheduled | Dependency update PRs |

**Deployment**: GitLab CI deploys to named Windows Tomcat servers. This is not container-based.
- Dev: `d-na-app02`
- QA: `q-na-app01`, `q-na-app02`

All Maven phases skip tests: `MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true"`. This means no tests run in the CI pipeline.

**GitLab origin**: `gitlab.com/northlane/development/application-development/application/csapiws-payout.git` — this is a legacy northlane/Wirecard GitLab repository, now mirrored or moved to GitHub (OnbeEast).

**Nexus server**: `d-na-stk01.nam.wirecard.sys` — legacy internal Nexus artifact server using the wirecard.sys domain. This server may not be reachable from current infrastructure.

## Deployment
- Target: Windows Tomcat 8.5.5.7 (from GitLab CI `SERVICE_NAME: CardManagementCSAPIPayout`)
- JNDI DataSources configured on Tomcat: `jdbc/JobSvcDataSource`, `jdbc/EcountCoreDataSource`, `jdbc/CbaseappDataSource`
- External properties: `D:/c-base/config/CSWS/applicationContext-CSWS.properties`
- External log4j: `D:/C-Base/config/CSWS/log4j-Payout.xml`
- Context path: `/CardManagementPayoutV3`
- Port: 9327 (dev and QA same port)
- Health check URI: `/CardManagementPayoutV3/services/AccountManagement?wsdl`

## Configuration
- External config file at `D:/c-base/config/CSWS/applicationContext-CSWS.properties` — loaded via Spring `PropertyPlaceholderConfigurer` with `file:` URI
- Keys injected: appId, agent, classification, endpoint, comment.appId, escalation.status, authSyncPrograms, cms.* properties
- `searchSystemEnvironment: true` — system environment variables can override properties file values
- No Spring profiles, no Azure App Config, no cloud configuration
- Static `displayMerchantName` program IDs are hardcoded directly in `accountManagementContext.xml` (not externalised)

## Observability
- **Logging**: Log4j 1.2.17 with jsonevent-layout for JSON-formatted structured log output
  - Log config at `D:/C-Base/config/CSWS/log4j-Payout.xml` (filesystem, not in repo)
  - JSON layout suggests log aggregation pipeline (ELK/Splunk) is in use
- **Timing**: `startTime` / `duration` logged at DEBUG level per operation
- **No health endpoint** beyond WSDL URL
- **No metrics, no distributed tracing, no request correlation infrastructure** (unlike V3 which has ProgramIdAwareGlobalRequestIDGenerator + MDC)

## Test Execution
- `MAVEN_TEST_SKIP=true` in all CI pipeline phases — no tests execute in CI
- Source contains test skeletons and `src/test/` directory (not explored in detail)
- JUnit 4.12 dependency present

## Risks
1. **Tests not running in CI**: All Maven phases skip tests. Any regression in deployed behaviour is undetected until production.
2. **SNAPSHOT version deployed**: `2.0.2-SNAPSHOT` in production-targeting CI pipeline — SNAPSHOTs are mutable and may not be reproducible.
3. **Legacy Nexus server**: Distribution management points to `d-na-stk01.nam.wirecard.sys` — this is likely inaccessible from current Onbe infrastructure. Maven deploys and dependency resolution for internal artifacts may fail silently.
4. **Windows-only deployment**: Hardcoded `D:/c-base/config/` paths and Windows Tomcat target make containerisation impossible without significant refactoring.
5. **No container build**: No Dockerfile. Cannot be moved to cloud-native deployment without full modernisation.
6. **Dual maintenance burden**: The same payout logic exists in both this standalone WAR and in `cs-api-v3_API`. Two codebases, two deployments, potential for divergence.
7. **Spring 2.5.4 + Axis 1.4 + Java 8**: All EOL. Multiple known CVEs across all three components.
8. **Log4j 1.2.17**: EOL; not vulnerable to Log4Shell (CVE-2021-44228) but has other known CVEs and is unsupported.
9. **jTDS 1.2**: Does not reliably support TLS 1.2 — database connections may not be encrypted.
