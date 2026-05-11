# ach-withdrawal-initiator_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven, version managed via Maven Wrapper (`mvnw` / `mvnw.cmd`). Maven Wrapper properties at `.mvn/wrapper/maven-wrapper.properties`.
- **Artifact**: Fat JAR (`jar-with-dependencies`) produced by `maven-assembly-plugin`. Final name: `ACHWithdrawalInitiator`. Standard thin JAR also produced by `maven-jar-plugin`.
- **Main class**: `com.ecount.process.ACHWithdrawalProcessMain` (declared in JAR manifest).
- **Parent POM**: `com.parents:service-parent:9.0.0` — an internal Onbe/ecount parent POM that centralizes dependency management. It is not in this repository and must be resolvable from the configured Maven repository (`.mvn/wrapper/settings.xml`).
- **Spring version**: 2.0.3 (very old Spring Framework 2.x, not Spring Boot).
- **JUnit**: Mixed — legacy JUnit 3.8.1 (test scope) and JUnit Jupiter 5.11.1 (test scope). Mockito 4.0.0 is included.
- **Key internal dependencies** (must be available in internal Nexus/Artifactory):
  - `com.ecount.service.Core2:ecount-system:2.0.0`
  - `com.ecount.service.Core2.director:director-client:1.0.11`
  - `com.ecount:xPlatform:7.0.16`
  - `com.ecount.service.autoclaimsplit:autoclaimsplit-common:2.0.2-SNAPSHOT`
  - `com.ecount.service.autoclaimsplit:autoclaimsplit-svc:2.0.2-SNAPSHOT`
  - `com.ecount.service.brandedcurrency:brandedCurrency-common:1.0.12`
  - `com.ecount.service.brandedcurrency:brandedCurrency-impl:1.0.12`
  - `com.ecount.one.service.affiliate:xAffiliateService:2016.1.1`
  - `com.ecount.services:comment:2019.1.4`
- **SNAPSHOT dependencies**: `autoclaimsplit-common:2.0.2-SNAPSHOT` and `autoclaimsplit-svc:2.0.2-SNAPSHOT` are SNAPSHOT versions, meaning builds may be non-reproducible if the SNAPSHOT changes between builds.
- **Surefire plugin**: `3.0.0-M4` (relatively recent for the overall project vintage).

## Deployment

- The process is a **standalone batch JAR** — not a web application, not containerized (no Dockerfile present).
- Execution: `java -jar ACHWithdrawalInitiator-jar-with-dependencies.jar [PTC]`
  - No `PTC` arg: ACH/claim rail processing.
  - `PTC` arg: Push-to-Card rail processing.
- The process is expected to be **scheduled externally** (cron job, Windows Task Scheduler, or job scheduler) since it runs to completion and exits (`System.exit(0)` or `System.exit(1)`).
- **Configuration file path** is hard-coded: `file:///d:/c-base/config/achwithdrawal/achwithdrawal.properties`. This requires a Windows host with a `D:` drive or a symbolic link/mount point.
- The Director service address is injected via `${director.address}` from that same properties file; all database connections are resolved at runtime through the Director service.
- **Classpath resources**: Spring application context loaded from classpath:
  - `com/ecount/process/ACHWithdrawal/appContext-ach.xml`
  - `classpath:appCtx-AutoclaimSplit.xml` (from `autoclaimsplit` dependency)
  - `classpath:brandedCurrencyContext.xml` (from `brandedCurrency` dependency)

## Configuration Management

All runtime configuration lives outside the JAR in two locations:

1. **`/configuration.properties`** (on classpath, inside the JAR): Controls processing parameters — thread counts, retry limits, records-per-iteration, failure lookback days, CPS exception codes. See `src/main/resources/configuration.properties`. This is the only configuration baked into the artifact.

2. **`achwithdrawal.properties`** (external filesystem, `d:/c-base/config/achwithdrawal/`): Contains all secrets and environment-specific values:
   - Database identifiers: `jobsvc.database`, `ecountcore.database`, `cbaseapp_database`
   - Director address: `director.address`
   - Agent ID: `ecount.agent`
   - PushPay/Tabapay credentials: `pushpay.url`, `pushpay.ms.client.secret`, `pushpay.ms.client.id`, `pushpay.ms.authority`, `pushpay.ms.scope`, `pushpay.tenant.id`, `pushpay.operator.id`
   - Payment selection: `payment.selection.clientBaseUrl`, `payment.selection.appId`
   - Member ID: `member.id`
   - Feature flag: `p2c_SD_MID_Flag`
   - Call delay: `pushPay.call.delay`

There is **no secrets management system** (e.g., Vault, AWS Secrets Manager, Azure Key Vault) wiring visible in the code. All secrets are plaintext in the external properties file.

## Observability

- **Logging**: Log4j 1.x (`log4j:1.2.17`). Configuration in `src/main/resources/log4j.properties`.
  - Root logger: `WARN` to stdout.
  - `com.cbase` and `com.ecount` packages: `TRACE` to both stdout and rolling file.
  - Rolling file: `ach_processor.log`, max 10 MB per file, 50 backup files (up to 500 MB total log retention).
  - Pattern: timestamp, thread name (20–50 chars), level, logger (50 chars), message.
- **No structured/JSON logging**: All log output is plain text. No correlation IDs from an APM perspective (though a random UUID is set as `GlobalRequestID` per transfer: `"AutoACH-" + UUID.randomUUID()`).
- **No metrics**: No Micrometer, Prometheus, JMX beans, or application-level metrics emission.
- **No distributed tracing**: No OpenTelemetry, Zipkin, or similar.
- **No health endpoint**: Batch process has no HTTP interface.
- **Process exit codes**: `System.exit(0)` on success, `System.exit(1)` on exception — suitable for use with job schedulers that check exit codes.
- **Log data risk**: Full PushPay API request body is logged at INFO level (`SharedServiceHelper` lines 104 and 186). This includes cardholder PII and card details, which should be scrubbed or masked.

## Infrastructure Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| SQL Server (JobsvcDataSource) | Database | ACH job queue; requires jTDS JDBC driver (`jtds:1.2`) |
| SQL Server (EcountCoreDataSource) | Database | Core platform event/transfer store |
| SQL Server (CbaseappDataSource) | Database | Affiliate/program data; lazy-init, used only when PushPay SD/MID features active |
| Director service | Internal service | Dynamic DBCP datasource credential resolution; address from `${director.address}` |
| EcountCore platform | Internal RPC | `TransferManagerImpl`, `MemberManagerImpl`, `DeviceManagerImpl` via internal RPC |
| PushPay/Tabapay API | External HTTPS API | Push-to-Debit disbursements; requires OAuth2 token from Microsoft Entra ID |
| Microsoft Entra ID | External OAuth2 | Client credentials flow for PushPay authentication; via MSAL4J |
| Notification service | Internal | Email dispatch via `NotificationManagerImpl`; agent/program-based |
| Profile service | Internal RPC | Program label/feature-flag retrieval via `ClassRetrieve` |
| Affiliate service | Internal | Hibernate-based; reads from `CbaseappDataSource` |
| Comment service | Internal | Inserts processing comments into `CbaseappDataSource` |

## Operational Risks

1. **Hard-coded Windows path**: `file:///d:/c-base/config/achwithdrawal/achwithdrawal.properties` prevents deployment on Linux/Unix without workaround. All modern container or cloud deployments would require path mapping.
2. **Single point of failure on Director**: If the Director service is unavailable at startup, all three datasources fail to initialize and the entire batch process fails.
3. **No circuit breaker**: If the Tabapay API is slow or intermittently failing, threads block synchronously (no timeout configured on `HttpURLConnection`). This can cause thread starvation.
4. **Log file growth**: Up to 500 MB of rolling logs with no automated cleanup policy visible in the code. On a constrained disk, this could fill the volume.
5. **SNAPSHOT dependency instability**: `autoclaimsplit-common:2.0.2-SNAPSHOT` and `autoclaimsplit-svc:2.0.2-SNAPSHOT` can change between builds without version bumps, causing silent behavioral differences across environments.
6. **No graceful shutdown**: The process uses `Thread.sleep(40)` polling loops to wait for worker threads. There is no JVM shutdown hook or interrupt handling that would cleanly flush in-progress transfers on SIGTERM.
7. **Tests skipped in CI**: The `.gitlab-ci.yml` pipeline sets `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"` — tests never run in CI, so test regressions are undetected until manual execution.
8. **Concurrent process instances**: There is no distributed lock preventing multiple instances of the process running simultaneously against the same database. Duplicate processing could occur if the scheduler fires overlapping runs.

## CI/CD

- **GitLab CI**: `.gitlab-ci.yml` includes a shared pipeline template from `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml`. Tests are skipped in all phases (build, test, deploy).
- **GitHub Actions — CodeQL**: `.github/workflows/codeql.yml` runs SAST analysis on a Thursday weekly schedule (`cron: 32 3 * * 4`) using a self-hosted Linux x64 runner. Uses the centralized `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` workflow.
- **Dependabot**: `.github/dependabot.yml` configures weekly Maven dependency version update PRs.
- **Dual SCM**: The repository has both a GitLab CI configuration and GitHub Actions, suggesting a mirror or migration scenario between the two platforms.
- **No deployment pipeline**: No pipeline stage for deployment, containerization, or environment promotion is present.
- **No integration tests in pipeline**: Only unit tests exist (`RequestProcessorThreadTest`), and even those are skipped in CI.
