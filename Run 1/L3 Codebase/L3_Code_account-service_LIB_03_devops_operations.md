# account-service_LIB — DevOps & Operations View

## Build & Packaging

**Build Tool**: Apache Maven, multi-module project.

| Artifact | GroupId | ArtifactId | Packaging | Purpose |
|---|---|---|---|---|
| Parent POM | `com.ecount.service` | `accountservice` | `pom` | Version management, dependency management |
| Common Module | `com.ecount.service.accountservice` | `account-common` | `jar` | API interfaces, value objects, constants |
| Service Module | `com.ecount.service.accountservice` | `account-svc` | `jar` | Business logic implementation, DAOs, helpers |

Current version: `4.0.33-SNAPSHOT` (parent `pom.xml` line 14).
Parent POM inherits from `com.parents:prepaid-parent:6.0.13`.
Java source/target level: **Java 21** (`maven.compiler.source=21`, `maven.compiler.target=21`, root `pom.xml` lines 19–20).

**Enforcer Rules**: Both modules use `maven-enforcer-plugin` with `banTransitiveDependencies` and `requireReleaseDeps`. Snapshots are forbidden in dependencies (except the parent groupId itself), enforcing release-quality dependency chains.

**Maven Wrapper**: `.mvn/wrapper/maven-wrapper.properties` and `mvnw`/`mvnw.cmd` are present for CI-reproducible builds.

**Maven Settings**: `.mvn/wrapper/settings.xml` is referenced by the GitHub Actions workflow (`-s ./.mvn/wrapper/settings.xml`). This settings file configures the internal artifact registry.

**Key Dependencies (runtime)**:
- `org.ehcache:ehcache:jakarta` — caching
- `org.springframework:spring-context`, `spring-context-support` — IoC
- `com.thoughtworks.xstream:xstream` — XML serialization
- `net.sourceforge.jtds:jtds` — SQL Server JDBC driver (jTDS)
- `commons-dbcp:commons-dbcp`, `commons-pool:commons-pool` — legacy connection pooling
- `aspectj:aspectjrt`, `aspectjweaver` — AOP
- `jakarta.xml.bind:jakarta.xml.bind-api`, `org.glassfish.jaxb:jaxb-runtime` — JAXB

**Test Dependencies**: JUnit 4 (`junit:junit`), Mockito (`mockito-core`), AssertJ (`assertj-core`), `spring-dbctx-mock`.

---

## Deployment

This library is **not deployed as a standalone service**. It is packaged as two JARs (`account-common-4.0.33-SNAPSHOT.jar` and `account-svc-4.0.33-SNAPSHOT.jar`) published to the internal Maven artifact registry (GitHub Packages based on the publish workflow). Consuming services embed these JARs on their classpath.

The Spring application context is assembled by the consumer using the XML configuration files bundled inside the JARs:
- `account-svc/src/main/resources/appCtx-AccountService.xml` — main service bean definitions
- `account-svc/src/main/resources/AccountServiceDAO.xml` — DAO beans
- `account-svc/src/main/resources/cache/cacheManager.xml` — EhCache manager
- `account-svc/src/main/resources/cache/ehCache3-mapping-{naProd,naqa,nasit}.xml` — per-environment cache configuration

The consuming service selects the correct cache file via `${cacheFileName}` property.

---

## Configuration Management

All runtime configuration is injected via Spring property placeholders (`${...}`). No configuration values are hardcoded in the XML files (with the exception of the sentinel phone `610-941-4600` hardcoded in `RegisterUserInput.validate()` at line 89 — a code-level default, not a property).

Key externalized properties (referenced in `appCtx-AccountService.xml`):

| Property Key | Bean / Usage | Notes |
|---|---|---|
| `account.payment.selection.clientBaseUrl` | `accountContext` | VirtualExpress redirect base URL |
| `account.recipient.ve.clientBaseUrl` | `accountContext` | Recipient VirtualExpress URL |
| `account.recipient.ve.programid` | `accountContext` | Program ID for recipient VE |
| `account.payment.selection.appId` | `accountContext` | App ID for affiliate metadata lookup |
| `account.notification.passthrough.programids` | `accountContext` | Comma-separated passthrough program IDs |
| `notification.common.receiver.email.id` | `accountContext` | Common/fallback receiver email |
| `notification.common.faked.Receiver.email.id` | `accountContext` | Faked receiver email (test) |
| `Restricted.email.domain` | `accountContext` | Comma-separated blocked email domains |
| `redis.cacheservice.url` | `InternationalFlagService` | Redis cache service URL |
| `sms.enabled.programid` | `SmsNotificationService` | SMS-enabled program ID |
| `sms.generate.url` | `SmsNotificationService` | SMS API endpoint |
| `sms.client.secret` | `SmsNotificationService` | OAuth client secret for SMS |
| `sms.client.id` | `SmsNotificationService` | OAuth client ID for SMS |
| `sms.authority` | `SmsNotificationService` | OAuth authority URL for SMS |
| `sms.scope` | `SmsNotificationService` | OAuth scope for SMS |
| `generic.template.id` | `SmsNotificationService` | Fallback SMS template ID |
| `sms.configuration.feature.enable` | `SendNotification` | Feature flag for SMS config routing |
| `sms.queue.enabled` | `SmsQueueService` | Enable/disable SMS queue (`true`/`false`) |
| `sms.consent.suffix` | `SmsQueueService` | TCPA consent text appended to SMS |
| `sms.default.shortcode` | `SmsProgramConfigurationHelper` | Default short code (default: `38323`) |
| `crcp.notifications.enabled` | `CrcpNotificationService` | Feature flag for CRCP channel |
| `crcp.service.url` | `CrcpNotificationService` | CRCP API endpoint |
| `crcp.client.id` | `CrcpNotificationService` | CRCP OAuth client ID |
| `crcp.client.secret` | `CrcpNotificationService` | CRCP OAuth client secret |
| `crcp.authority` | `CrcpNotificationService` | CRCP OAuth authority |
| `crcp.scope` | `CrcpNotificationService` | CRCP OAuth scope |
| `director.address` | DataSource factory | Director connection pool manager address |
| `agent.notificationsvc` | NotificationSvc DataSource | Agent name for notification DB connection |
| `data.environment.notificationsvc` | NotificationSvc DataSource | Environment identifier for notification DB |
| `checkOperator` | `Withdraw` bean | Check operator identifier |
| `memberId` | `balancesweepImpl`, `member` | Member ID for debit API |
| `agent` | `RequestContextSource` | Agent identifier |
| `monitor.core.affiliateId` | `RequestContextSource` | Affiliate ID for core monitoring |
| `account.xcontent.rootPath` | `AffiliateLocaleSkinHelper` | Content root path |
| `account.recipientContentUrl` | `AffiliateLocaleSkinHelper` | Recipient content URL |
| `notificationProgramEnableCacheName` | `AccountServiceCacheManagerImpl` | EhCache cache name for notification program enable |
| `cacheFileName` | `JCacheManagerFactoryBean` | URI of the ehcache XML config file |

No Kubernetes/Docker/Helm configuration files are present — this is a library, not a containerized service.

---

## Observability

**Logging Framework**: SLF4J with a `log4j2.xml` test configuration in `account-svc/src/test/resources/log4j2.xml`. Production logging configuration is excluded from the JAR (`<exclude>**/log4j*</exclude>` in both `pom.xml` build configurations) — the consuming application supplies its own logging configuration.

**Log Patterns Observed**:
- `AccountServiceImpl`: DEBUG-level entry/exit logs for every operation with input/output summaries.
- `AccountServiceDAOJDBCImpl`: DEBUG-level logs for all DAO calls including input parameters (includes PUID and emember IDs in plaintext).
- `CrcpNotificationService`: INFO-level request logs with sanitized values; ERROR-level for failures.
- `SmsQueueService`: INFO-level on queue insert; ERROR on failure.
- `AddFunds`: ERROR-level for QuickLoad failures, WARN for claimable DAO issues.
- `ThreadLocal<Logger>` pattern: Used in `AccountServiceImpl`, `AccountServiceDAOJDBCImpl`, `AddFunds`, `RegisterUser` — each thread gets its own logger instance (non-standard; typically loggers are static final).

**Metrics / Tracing**: No Micrometer, Prometheus, OpenTelemetry, or distributed tracing instrumentation is present. Observability depends entirely on log aggregation by the hosting application.

**Health Checks**: None defined in this library. The consuming service is responsible for datasource health.

**Correlation IDs**: `CrcpNotificationService.buildSharedServiceRequest()` generates a `UUID.randomUUID()` correlation ID per CRCP call. No correlation ID propagation from the inbound caller context is observed.

---

## Infrastructure Dependencies

| External System | Access Mechanism | Config Reference |
|---|---|---|
| Ecount Core (Member, Device, Transfer XML-RPC) | XML-RPC over internal network | `memberXMLRPCClient`, `deviceXMLRPCClient`, `transferXMLRPCClient` |
| Director (connection pool manager) | `DirectorConfiguredDBCPdatasourceCreator` | `${director.address}` |
| Job Service DB (SQL Server) | JDBC / jTDS | `JobSvcDataSource` |
| EcountCore DB (SQL Server) | JDBC / jTDS | `EcountCoreDataSource` |
| NotificationSvc DB (SQL Server) | JDBC / jTDS via Director | `notificationSvcDS` |
| Cbaseapp DB (SQL Server) | JDBC / jTDS | `CbaseappDataSource` |
| SMS Service API | HTTPS / OAuth2 | `${sms.generate.url}`, `${sms.authority}` |
| CRCP Notification Service | HTTPS / OAuth2 | `${crcp.service.url}`, `${crcp.authority}` |
| Redis Cache Service | HTTP (`java.net.http.HttpClient`) | `${redis.cacheservice.url}` |
| Payment Service (internal) | Spring bean injection | `paymentService` bean |
| StrongBox (secrets vault) | XML-RPC | `strongBoxXMLRPCClient` |
| Profile Service | XML-RPC | `profileClient` / `ProfileXMLRPCClient` |
| Event Service | XML-RPC | `eventXMLRPCClient` / `eventserviceclient` |
| Affiliate Service | Hibernate5 / SQL Server | `appContextFactory` → `CbaseappDataSource` |

---

## Operational Risks

1. **SNAPSHOT Version in Production**: Version `4.0.33-SNAPSHOT` indicates this is not a released artifact. Deploying SNAPSHOTs to production is a reproducibility risk (the artifact content can change without a version bump).

2. **Legacy jTDS JDBC Driver**: `net.sourceforge.jtds:jtds` is used for SQL Server connectivity. jTDS is unmaintained and does not support SQL Server 2019+ authentication features (e.g., Azure Active Directory). Microsoft JDBC Driver for SQL Server is the recommended replacement.

3. **Legacy Connection Pooling**: `commons-dbcp` / `commons-pool` are legacy pooling libraries. HikariCP is the standard for Spring-based services.

4. **ThreadLocal Logger Pattern**: Using `ThreadLocal<Logger>` (seen in `AccountServiceImpl`, `AddFunds`, `RegisterUser`) is non-standard. If threads are reused from a pool, logger instances may accumulate or reference incorrect class contexts. Standard practice is `private static final Logger log = LoggerFactory.getLogger(ClassName.class)`.

5. **No SMS Queue Worker in Library**: Messages are written to `sms_notification_queue` with `status=PENDING`. If the external worker stops, the queue grows unbounded. No dead-letter / alert mechanism is visible.

6. **Director-Managed DataSources**: All SQL Server datasources created via `DirectorConfiguredDBCPdatasourceCreator` depend on the Director service being reachable at startup. A Director outage will prevent Spring context initialization.

7. **EhCache In-Memory Only (Production)**: `ehCache3-mapping-naProd.xml` configures `<ehcache:heap unit="entries">250000</ehcache:heap>` with no overflow to disk. Loss of the hosting JVM loses all cached notification configuration.

8. **Hibernate5 for Affiliate Service**: `appContextFactory` uses `org.springframework.orm.hibernate5.LocalSessionFactoryBean` with SQLServerDialect. Spring ORM for Hibernate 5 is deprecated in Spring 6+; migration to Hibernate 6 / Jakarta Persistence is required.

9. **Silent Event Dispatch Failures**: All event dispatch calls (`accountEventServiceLibrary.addFundsCompleteEvent`, `registerUserCompleteEvent`) are wrapped in try-catch that logs and continues. Failed events are not re-queued; they are silently dropped.

---

## CI/CD

### GitLab CI (`.gitlab-ci.yml`)
- Inherits from a shared template: `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml`
- All phases (build, test, deploy) skip tests: `MAVEN_TEST_OPTS="-Dmaven.test.skip=true"` and `MAVEN_DEPLOY_OPTS="-Dmaven.test.skip=true"`. **Tests are skipped in CI/CD for all three phases** — a significant quality gate gap.
- No specific stage overrides beyond the skip flags.

### GitHub Actions
**`github-package-publish.yml`**:
- Trigger: `workflow_dispatch` (manual) or push to `main` (paths excluding `.mvn/**`, `.github/**`, wrapper files); also on PRs to main.
- Delegates to reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`
- Build args: `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` (tests skipped in publish workflow too).
- Supports `version-tag` override, `auto-increment`, `dry-run`, `update-dependencies` inputs.

**`codeql.yml`**:
- Trigger: `workflow_dispatch` or scheduled (`cron: '53 17 * * 5'` — Fridays at 17:53 UTC).
- Delegates to: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- Java runner: `ubuntu-latest`.

**Dependabot** (`.github/dependabot.yml`):
- Monitors Maven dependencies on a weekly schedule.

### Notable CI/CD Gaps
- Tests are skipped in both GitLab and GitHub publish pipelines. Integration tests never execute in CI.
- No observed container build, deployment manifest, or environment promotion steps — expected since this is a library.
- No SonarQube / SAST step beyond CodeQL.
