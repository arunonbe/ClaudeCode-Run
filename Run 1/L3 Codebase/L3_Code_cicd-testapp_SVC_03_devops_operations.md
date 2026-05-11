# cicd-testapp_SVC — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven 3 (Maven Wrapper present at `.mvn/wrapper/maven-wrapper.properties`; `MavenWrapperDownloader.java` in `.mvn/wrapper/`).
- **Java version**: Java 8 (`source` and `target` both `8` in root `pom.xml` maven-compiler-plugin, line 544–545). GitHub Actions workflow uses `zulu` distribution JDK 8.
- **Project structure**: Multi-module Maven POM with 12 modules:
  - `common` — interfaces, enums, exceptions, DTO value objects
  - `ecountCoreDAO` — JDBC DAO implementations and stored procedure wrappers
  - `MQLibrary` — IBM MQ JMS abstraction (`MQJMSImp`, `MQJMS`)
  - `ecountCoreLibrary` — business library implementations
  - `ecountCoreService` — service layer implementations
  - `eCoreWar` — WAR packaging; Spring XML configuration; servlet definition
  - `ProcessorServices/FDRDebitService` — FDR debit service implementation
  - `coreTester` — internal test web app
  - `ecountCoreRestController` — Spring MVC REST controllers (annotated)
  - `ecountCoreRestApi` — REST request/response DTO model
  - `ecountCoreDocumentation` — documentation module (AsciiDoc/PDF)
  - `ecountCoreQA` — QA integration test module (only included in `has-it` profile)
- **Profiles**: `has-it` (default, includes `ecountCoreQA`) and `no-it` (excludes QA module); CI builds use `-Pno-it`.
- **Output artifact**: `eCoreWar` module produces `TestCoreWar.war` (packaging declared as `war` in `eCoreWar/pom.xml`).
- **Nexus repositories**: Release → `http://d-na-stk01.nam.wirecard.sys:8080/nexus/content/repositories/releases`; Snapshot → same host `/snapshots`. Both URLs reference a `wirecard.sys` internal domain (legacy Wirecard infrastructure). The HTTP (not HTTPS) protocol is a security concern.
- **Coverage thresholds**: JaCoCo configured in root `pom.xml` at 90% for instruction, class, line, branch, and method coverage.

## Deployment

- **Deployment model**: Traditional WAR deployed to Apache Tomcat (evidenced by `context.xml` with `<Context antiJARLocking="true">`, JNDI `<ResourceLink>` entries, and Jenkinsfile referencing `D:\c-base\JDK-AWS-8`).
- **Target hosts** (from `.gitlab-ci.yml`):
  - Dev: `d-na-app04` (single host, port 31337)
  - QA: `q-na-app07`, `q-na-app08` (two hosts, port 31337)
- **Service name** (Windows service): `Pipelab` — corresponds to the Tomcat service name on Windows deployment hosts.
- **WAR path for deployment**: `eCoreWar` module (variable `PROJECT_ARTIFACT_PATH: eCoreWar`).
- **Health check URL**: `http://{host}:31337/service/` (`PROJECT_SERVICE_URI: /service/`).
- **Health monitor**: Spring bean `MonitorFormController` (`HealthMonitor.xml`) exposes checks for:
  - `EcountCore` DB (`ecountCoreDS`) — warn >200ms, error >1000ms
  - `JobService` DB (`jobsvcDS`) — warn >200ms, error >1000ms
  - `StrongBox` DB (`strongboxDS`) — warn >200ms, error >1000ms
  - `FDRODS` DB (`fdrODSDS`) — commented out in monitor list but defined; warn >500ms, error >10000ms
  - `requestXmitQueue` (IBM MQ) — warn >50 messages, error >100 messages
  - `replyQueue` (IBM MQ) — warn >50 messages, error >100 messages

## Configuration Management

- **Runtime properties source**: Spring Cloud Config Server via `com.northlane.configserver.client.bootstrapping.SpringCloudConfigContext` (declared as `contextClass` in `web.xml` line 49–50). This is the primary runtime configuration source.
- **Fallback properties**: `SpringFallbackPropertiesReader.xml` activates under Spring profile `no-config-server` and reads `file:${cbase.home.directory}/ecountcore.fallback.properties`. This profile is used for local development and Cargo IT tests.
- **Environment-specific settings sourced at runtime**:
  - `${agent}` — identifies the agent/environment; used as `<bean id="Agent">` in `Configuration.xml`.
  - `${starNetworkID}` — FDR star network identifier (in `FDRDebitServices.xml`).
  - `${fdr.receiveTimeout}`, `${fdr.receiveTimeoutShort}`, `${fdr.ttl}`, `${fdr.ttlshort}` — FDR JMS timeouts.
  - `${fdr.userId}`, `${fdr.passwordHash}`, `${fdr.encryptCodePage}` — FDR ODS security credentials.
  - `${xmit.queue}` — IBM MQ transmit queue name for health monitor.
  - `${writeReference.version}` — StrongBox write reference version.
- **MQ properties in file**: `MQLibrary/src/main/resources/MQConfig.properties` contains message expiry times (172,800,000 ms / 120,000 ms) and receive timeout (90,000 ms). These are baked into the artifact.
- **JNDI resources**: All data sources and MQ connection factories are bound via JNDI (`<ResourceLink>` in `eCoreWar/src/main/webapp/META-INF/context.xml`), requiring proper Tomcat server.xml configuration with matching global resources.
- **JMX**: State map reloading exposed via `prepaid:name=StateMap` MBean (`Configuration.xml`).

## Observability

- **Logging**: Log4j 1.x (`log4j:log4j:1.2.15`) used throughout; `web.xml` registers `Log4jConfigListener` (Spring 4 API). `log4j.fallback.xml` present in `eCoreWar/src/main/webapp/WEB-INF/`. Log4j 1.x is end-of-life and has known critical vulnerabilities (CVE-2019-17571).
- **Log MDC**: `Log4jMDCWriter` bean (`GlobalRequestID.xml`) propagates correlation ID and request context into MDC for log correlation.
- **Correlation ID**: `correlationIdFilter` (DelegatingFilterProxy, `web.xml` lines 113–121) injects a correlation ID into every inbound request; `com.ecount.opensource.correlation-web` library used.
- **Method tracing**: AOP advisor `methodTracer` (class `MethodTracingInterceptor`, `Configuration.xml`) traces all method calls on DAO, service, device, proxy, and ICS client layers.
- **Health endpoint**: `/service/` URI path monitored by health check; `MonitorFormController` returns status for all infra dependencies.
- **No distributed tracing** (e.g., Zipkin, Jaeger, OpenTelemetry) is configured.
- **No metrics endpoint** (e.g., Micrometer, Prometheus) is configured.

## Infrastructure Dependencies

| Dependency | Type | JNDI / Endpoint |
|---|---|---|
| SQL Server (ecountCoreDS) | JDBC via JNDI | `jdbc/ecountCoreDS` |
| SQL Server (jobsvcDS) | JDBC via JNDI | `jdbc/jobsvcDS` |
| SQL Server (strongboxDS) | JDBC via JNDI | `jdbc/strongboxDS` |
| FDR ODS | IBM MQ + custom protocol | `jms/FDRQueueConnectionFactory`, `jms/FDRRequestQueue`, `jms/FDRReplyQueue` |
| ECS+ | IBM MQ | `jms/ECSQueueConnectionFactory`, `jms/ECSRequestQ`, `jms/ECSResponseQ` |
| Actimize | IBM MQ | `jms/ActimizeQueueConnectionFactory`, `jms/ActimizeRequestQ` |
| GPP | IBM MQ | `jms/GPPAccStatusQ` |
| Northlane Config Server | HTTP (Spring Cloud Config) | `com.northlane.configserver.client` |
| Nexus (artifact repo) | HTTP DAV | `d-na-stk01.nam.wirecard.sys:8080` (wirecard.sys domain) |
| Apache Tomcat | Servlet container | Port 31337 (dev/QA) |
| IBM MQ Broker | JMS | JNDI `jms/ECSXAQueueConnectionFactory` also declared (XA) |
| CyberSource ICS | HTTPS (external fraud) | `cybersource:ics:5.0.3` library; settings from `CoreGetCyberSourceSettings` SP |

## Operational Risks

1. **Log4j 1.x (EOL)**: `log4j:1.2.15` has critical unpatched vulnerabilities including CVE-2019-17571 (socket server deserialization RCE). No migration to Log4j 2.x or SLF4J/Logback is present.
2. **Spring 4.3.27 (EOL)**: Spring Framework 4.x has been end-of-life since December 2020. Known CVEs exist. Comment in `pom.xml` line 76–77 acknowledges the upgrade is blocked.
3. **Wirecard Nexus dependency**: artifact resolution points to `d-na-stk01.nam.wirecard.sys:8080` — a Wirecard internal host. If this infrastructure has been decommissioned or migrated, artifact builds will fail. Protocol is plain HTTP (not HTTPS), allowing MITM during artifact download.
4. **Tests skipped in CI**: `Jenkinsfile` line 19 (`-Dmaven.test.skip=true`) and `.gitlab-ci.yml` lines 15–17 skip all tests in build, test, and deploy phases. No automated quality gate before deployment.
5. **SNAPSHOT versions deployed**: `2.0.0-SNAPSHOT` and transitive SNAPSHOTs (`springutils 2.0.0-SNAPSHOT`, `config-server-client 2.0.0-SNAPSHOT`) are unstable and non-reproducible.
6. **JMS correlation ID matching for response retrieval**: `MQJMSImp.receiveMessage()` blocks with `receiveTimeout` (90 seconds) using a JMS selector on `JMSCorrelationID`. In high-concurrency scenarios, slow FDR ODS responses can exhaust thread pool.
7. **`aether.connector.https.securityMode=insecure`** in GitHub Actions workflow (line 26): disables TLS certificate verification during Maven artifact resolution, permitting MITM attacks on artifact downloads.
8. **Single dev host, dual QA hosts**: no load balancing or HA at app tier for dev; QA has only two nodes with no description of session affinity or failover logic.

## CI/CD

### Jenkins (Jenkinsfile)
```
Stage: Build
  bat "mvn clean install -Dmaven.test.skip=true -Pno-it"
  dir('ecountCoreQA') { bat 'mvn clean package verify' }
```
- Agent: `any` (no dedicated build agent constraint)
- Java: `JDK1.8`, Maven: `Maven3.1.0` (named tool references)
- `JAVA_HOME` hardcoded to `D:\c-base\JDK-AWS-8` — Windows path, Windows build agent
- No deployment stages, no test reporting, no artefact archiving in Jenkinsfile

### GitLab CI (.gitlab-ci.yml)
- Inherits template from `northlane/development/.../ci-templates` ref `refactor` — the actual pipeline jobs are defined in the template, not in this file.
- Variables override build/test/deploy Maven options to skip tests: `MAVEN_BUILD_OPTS`, `MAVEN_TEST_OPTS`, `MAVEN_DEPLOY_OPTS` all set `-Dmaven.test.skip=true -Pno-it`.
- Dev deployment: `d-na-app04:31337`; QA: `q-na-app07:31337`, `q-na-app08:31337`

### GitHub Actions (.github/workflows/codeql-java.yml)
- Triggered on push/PR to `master`, `main`, `development`; also `workflow_dispatch`
- Runs CodeQL `security-extended` query suite (`.github/codeql/codeql-config-java.yml`)
- Runs on self-hosted `[X64, Linux, ubuntu-docker]` runner
- Builds with `./mvnw clean verify` + insecure HTTPS mode

### Dependabot (.github/dependabot.yml)
- Maven ecosystem; weekly schedule; monitors root directory only.
