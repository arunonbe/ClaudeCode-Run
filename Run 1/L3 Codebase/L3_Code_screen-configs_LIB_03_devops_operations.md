# DevOps / Operations View — screen-configs_LIB

## Build System

- **Build tool**: Maven with Maven Wrapper (`mvnw`, `mvnw.cmd`, `.mvn/wrapper/maven-wrapper.properties`)
- **Java version**: Not explicitly set in pom.xml (no `maven.compiler.source/target` properties); inherits from `service-parent:7`. Based on Spring 2.0.4 dependency and project lineage, this builds against Java 5/6 era source level.
- **Parent POM**: `com.citi.prepaid.service:service-parent:7` (eCount Gen-1 service parent)
- **Packaging**: JAR library (`<packaging>jar</packaging>` implied by default)
- **Version**: `2016.2.1` — a date-versioned artifact indicating last release in 2016
- **Key dependencies**:
  - `commons-logging:1.1` — EOL logging facade
  - `commons-lang:2.3` — EOL; current is 3.x
  - `commons-collections:3.2` — EOL (3.2.1 had remote code execution vulnerability CVE-2015-6420)
  - `org.springframework:spring:2.0.4` — severely EOL (2007); multiple unpatched CVEs
  - `xPlatform:2.5.28` — internal eCount platform library
  - `sqljdbc:1.1` — Microsoft SQL Server JDBC driver (extremely old; current is 12.x)
  - `junit:3.8.1` — EOL test framework (JUnit 4/5 are current)
  - `easymock:2.3` — EOL mocking framework

## CI/CD Pipeline

- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL static analysis configured; Java language
- **Dependabot**: `.github/dependabot.yml` — automated dependency update PRs configured
- **No deployment workflow**: No GitHub Actions deployment workflow observed. This is a library (JAR) artifact; deployment is through Maven publish to the internal Nexus repository, likely triggered from the calling service's build.
- **No container**: This is a pure JAR library; no Dockerfile or container deployment.

## Deployment Model

- **Artifact type**: JAR library; consumed as a Maven dependency by web applications (clientzone_WAPP, cs-api family) that include it on their classpath
- **No standalone deployment**: The library is loaded into the JVM of its consuming application (Tomcat or JBoss WAR deployment)
- **Distribution**: Internal Nexus repository at `d-na-stk01.nam.wirecard.sys:8080/nexus` (per service-parent URL — this hostname suggests Wirecard/Northlane infrastructure; may no longer be accessible)

## Runtime

- **Java**: Effectively Java 5/6 source compatibility (Spring 2.0.4 era); runs on whatever JVM the consumer application uses
- **Spring**: 2.0.4 (Spring Framework — **this version is from 2007 and has no security support**)
- **Application server**: Deployed within consumer application's servlet container (JBoss/Tomcat)
- **Database**: Microsoft SQL Server accessed via JDBC stored procedure calls

## Secrets Management

- Database credentials are injected via Spring XML application context (`applicationContext-instIssueCZScreenCfg.xml`), which references DataSource beans defined in the consuming application context
- The library itself does not manage secrets; it relies on the hosting application's Spring context for DataSource injection
- Test datasource context (`datasourceTestContext.xml`) likely contains hardcoded test credentials for integration testing — this must be verified and any real credentials removed

## Observability

- **Logging**: `commons-logging` facade (version 1.1); no SLF4J or Logback. Log output depends on the consuming application's logging configuration.
- **No metrics**: No metrics instrumentation
- **No health checks**: Library has no health endpoint; health is inferred from the consuming application's availability
- **No alerting**: No alerting configuration; monitoring responsibility belongs to the consuming application

## Known EOL Runtimes and CVEs

This library has a severe technical debt profile:

- **Spring 2.0.4** (2007): Multiple known CVEs including cross-site scripting, information disclosure, and remote code execution. No security patches will be released. **Critical risk for any CDE-adjacent deployment.**
- **commons-collections 3.2**: CVE-2015-6420 (Remote Code Execution via Java deserialization). This is a well-known critical vulnerability. The fixed version is 3.2.2 or 4.x.
- **sqljdbc 1.1**: Ancient Microsoft SQL Server JDBC driver; modern TLS versions (1.2+) may not be supported. Current driver is 12.x.
- **junit 3.8.1**: EOL test framework; no security concerns but incompatible with modern test infrastructure.
- **Version 2016.2.1**: No releases since 2016. The library is effectively frozen.
- **Strategic recommendation**: This library should be retired and its functionality either consolidated into the consuming services or replaced with a configuration service (e.g., Spring Cloud Config or Azure App Config) for the Gen-3 platform. It should not be migrated as-is; the business logic should be re-implemented with current frameworks.
