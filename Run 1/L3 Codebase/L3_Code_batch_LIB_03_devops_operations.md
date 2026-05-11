# batch_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven. Wrapper scripts `mvnw` / `mvnw.cmd` / `autobuild.bat` are present.
- **Maven coordinates**: `com.ecount.service.core:batch:2.0.29-SNAPSHOT`, `<packaging>jar</packaging>`.
- **Java source/target**: `1.5` (Java 5) specified in `maven-compiler-plugin` (`pom.xml`, lines 405–408). The actual JVM executing the built artifact is not specified in any Dockerfile or CI script — it is presumed to be a higher JVM version installed on the deployment host.
- **Fat JAR**: `maven-shade-plugin:1.4` produces a shaded (uber) JAR at `target/batch-1.0.0.jar` with the main class `org.springframework.batch.core.launch.support.CommandLineJobRunner`. All Spring handler/schema META-INF resources are merged via `AppendingTransformer`. JAR signatures are stripped.
- **Assembly JAR**: `maven-assembly-plugin` also produces a `jar-with-dependencies` artifact in the same package phase.
- **Source JAR**: `maven-source-plugin:3.2.1` attaches a sources artifact.
- **Tests**: All tests are unconditionally skipped in CI (`MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"`). ENVIRONMENT property `sqlserver` is set in Surefire for local test runs.
- **Parent POM**: `com.parents:service-parent:9.0.0` — not present in this repository; resolved from the internal Maven repository.
- **SCM**: `scm:git:ssh://git@gitlab.com/northlane/development/application-development/application/batch.git`

## Deployment

- **Execution model**: The batch jobs are not a long-running service. Each job is launched as a separate JVM invocation by an external scheduler (Active Batch, as evidenced by `scripts/activebatchconfig/*.xml`), calling the shaded JAR via:
  ```
  java -jar batch-1.0.0.jar <XML context file> <jobId> [parameters]
  ```
  Example from `scripts/altobacsdirectload/pacsProcess/AltoBacsLoadBatchJob.bat`.
- **Scheduler**: IBM Active Batch. XML job definitions in `scripts/activebatchconfig/` define the schedule and command lines for each batch:
  - `PrepaidDailySync.xml` — daily account/balance sync jobs
  - `PrepaidWeeklySync.xml` — weekly GPP Alto report
  - `ECSAtptPostedPost.xml` — ECS ATPT settlement
  - `EncashmentECSSettlement.xml`, `EncashmentPaypointSettlement.xml`
  - `FPAccStatusSync.xml` — account status sync
  - `IVREpmemoDetailsPosting.xml` — IVR EP memo
  - `PaypointSiteFileImport.xml`
  - `PrepaidAltoArucs.xml`, `PrepaidAltoPacs.xml`
- **Shell scripts**: `.bat` scripts in `scripts/` subdirectories invoke the JAR. Some processes use legacy VBScript (`.vbs`) wrappers for FTP/SFTP file download before the Java batch reads them (e.g., `IVREPMemoDetailsFileDownload.vbs`, `altoPACSImport.vbs`).
- **Pre-processing**: Perl scripts (`.pl`) parse raw files into SQL-loadable format before the Java batch reads from the database (e.g., `ArucsFileParser.pl`, `altoPacsLoadFundsFileParser.pl`, `ecsReportParser.pl`).
- **Config file location**: All runtime configuration is read from `D:\c-base\config\batch\...` on the deployment host (`propertyPlaceHolder.xml`, lines 21–52).
- **No containerisation**: No `Dockerfile` or container image definition is present in this repository. Deployment is to a bare Windows host (paths are `D:\c-base\...`).

## Configuration Management

All configuration is externalised to property files at fixed paths on the deployment server under `D:\c-base\config\batch\`. Each batch job has its own `.properties` file:

| Property File | Batch |
|---|---|
| `CoreBatch.properties` | Global batch settings |
| `director-client.properties` | Director service address |
| `balancesync/BalanceSync.properties` | Balance sync grid size, commit interval |
| `claimcodeexpiration/ClaimCodeExpiration.properties` | Claim expiry thresholds |
| `RewardsPosting/RewardsPosting.properties` | Rewards posting config |
| `returnedemailbatch/ReturnedEmailBatch.properties` | Exchange URL, OAuth credentials, chunk size |
| `AccountStatusSync/AccountStatusSync.properties` | Account status IBM MQ queue settings |
| `AltobacsDirectLoad/AltoBacsDirectLoad.properties` | BACS file paths, grid size |
| `GPPAltoReportProcess/gppAltoReportProcess.properties` | GPP report paths |
| `EncashmentPaypointSettlement/EncashmentPaypointSettlement.properties` | Settlement file paths |
| `IVREPMemo/IVREPMemoDetails.properties` | IVR memo paths |
| `ATPT_Posted/ATPTPosted.properties` | ECS batch count |
| `ECSDailyAuthPost/ECSDailyAuth.properties` | ECS daily auth config |
| `PaymentHub/PaymentHub*.properties` | Multiple Payment Hub configs |
| `accountdata/AccountData.properties` | Account data export config |
| `paypalsettlementfile/PaypalSettlementFileProcess.properties` | PayPal settlement file path |
| `PushToCardTransactionReportImport/PushToCardTransactionImport.properties` | TabaPay import |
| `PayPalChoiceRecurringDetails/PayPalChoiceRecurringDetails.properties` | PayPal choice agent/env |
| `VenmoChoiceRecurringDetails/VenmoChoiceRecurringDetails.properties` | Venmo choice config |
| `claimablechoicecodeexpiration/ClaimableChoiceCodeExpiration.properties` | Choice expiry API URL/timeouts |
| `CbtsPendingConfirmationBatch/CbtsPendingConfirmationBatch.properties` | CBTS confirmation config |

Key property tokens observed in XML configs:
- `${director.address}` — Director service URI
- `${agent.ecountcore}`, `${agent.springbatch}`, `${agent.notificationsvc}` — DB connection agents
- `${database.*}` — logical DB names resolved by Director
- `${autoClaim.grid_size}`, `${autoClaim.transaction_records_count}` — parallelism tuning
- `${ecount.agent}` — ecount platform agent name
- `${paypalchoicerecurringdetails.agentName}`, `${paypal.operatorId}`, `${paypal.targetEnv}` — PayPal environment

**No environment-specific profile switching**: There is no Spring profile, environment variable switch, or Maven profile differentiation between DEV/UAT/PROD. All environment differences are managed solely through the content of the external properties files.

## Observability

- **Logging**: `log4j:1.2.15` + `slf4j-log4j12:1.6.2`. Configuration at `src/test/resources/log4j.properties` (test only). Production `log4j.properties` is external (not in source). Perl scripts use `log4perl.conf` in their respective directories.
- **Method tracing**: `BatchProcessMethodTracingInterceptor` (AOP `MethodInterceptor`) logs class name, method name, and execution time in milliseconds for all Spring Batch repository calls. Output prefix distinguishes `SPRING-BATCH-EXECUTE`, `CPP-BATCH-EXECUTE`, and `LOCAL-EXECUTE`.
- **Job status in DB**: Custom job instance tables track start/end times and status for ClaimExpiration, ClaimableChoiceExpiration, and ReturnedEmail jobs.
- **Execution context counters**: Total/processed/remaining transaction counts are stored in Spring Batch `ExecutionContext` and promoted across steps — observable via the Spring Batch admin or by querying `BATCH_JOB_EXECUTION_CONTEXT`.
- **No APM integration**: No Dynatrace, New Relic, or OpenTelemetry instrumentation is present.
- **No health endpoint**: This is a command-line batch, not a Spring Boot app — there is no Actuator, metrics endpoint, or readiness probe.
- **Exit codes**: `BatchConstants` defines 0 (COMPLETED), 1 (FAILED), 2 (INFINITELOOP), 11 (COMPLETED_RETRY_RECORDS). The `.bat` launcher scripts can check `%ERRORLEVEL%` to detect failures.

## Infrastructure Dependencies

| Dependency | Component | Version |
|---|---|---|
| Microsoft SQL Server | All databases | Driver `sqljdbc:1.1` |
| IBM WebSphere MQ | Account status sync (JMS), possibly CBTS | `com.ibm.mq:7.0.1.4`, `spring-jms:2.5.6` |
| Active Batch | Job scheduler | XML configs in `scripts/activebatchconfig/` |
| Director service | DB connection routing and credential resolution | `director-client:1.0.11`, `ecount-system:2.0.0` |
| ecount Core (XML-RPC) | Member/transfer/account operations | `coreLiteXMLRPCClient`, `memberXMLRPCClient`, `transferXMLRPCClient` (port 40000) |
| Payment Service Library | AutoClaim certificate creation | `Payment-Common:2016.1.1`, `Payment-Service:2016.1.1` |
| Affiliate Service | Program/presentation metadata lookup | `xAffiliateService:2016.1.1` |
| Branded Currency Service | Currency handling | `brandedCurrency-common/impl:2016.1.1` |
| xSearch | Search operations | `xSearch-impl:2014.1.1` |
| xPlatform | Platform utilities | `xPlatform:7.0.24` |
| Strongbox | Secret management | `strongboxImpl:1.0.2` |
| Microsoft Exchange / Office 365 | Returned email reading | EWS Java API `2.0`, MSAL4J |
| PayPal Shared Service | PayPal payout execution | REST HTTP (`ClaimableChoiceAPIClient`, `SharedServiceHelper`) |
| Repository Service | File/artifact repository client | `repository-client:2013.3.2` |
| Job Manager Service | Job lifecycle management | `jobmanager-client:2015.1.1` |
| Custom Files Common | File processing | `CustomFilesCommon:1.1.1` |
| FTP/SFTP (implied) | VBS scripts for file download (PACS, ARUCS, IVR files) | VBScript wrappers |
| Windows (bare metal) | Deployment OS | Paths `D:\c-base\...` — Windows only |

## Operational Risks

1. **No containerisation / infrastructure-as-code**: Deployment is to bare Windows hosts with fixed paths. There is no Dockerfile, no Kubernetes manifest, no Helm chart. Any host migration requires manual reconfiguration of all 25+ property files.
2. **Tests always skipped**: `.gitlab-ci.yml` sets `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"` — no regression testing runs in CI. Quality gate is absent.
3. **Java 5 source compatibility**: `maven-compiler-plugin` targets Java 1.5. Modern features (lambdas, streams, try-with-resources) are not available. The codebase relies on raw types, `Hashtable`, and `Dictionary` extensively.
4. **Single-node execution**: No evidence of distributed execution or HA failover for the batch processes. The Active Batch scheduler is the single point of orchestration.
5. **Legacy VBScript and Perl pre-processors**: Pre-processing scripts in `scripts/` use VBScript and Perl — technologies that have no modern support lifecycle or security patching. Any CVE in the Perl interpreter or VBScript engine directly affects these workflows.
6. **`Thread.sleep(5000)` in processor**: `PayPalChoiceRecurringDetailsProcessor.handleRefundAmountFromPaypal()` blocks an item processor thread for 5 seconds — if many items require refund, this severely degrades job throughput.
7. **Stale versions**: Spring 2.5.6 (2009), Spring Batch 2.1.9 (2011), AspectJ 1.5.3, Log4j 1.2.15, XStream 1.3.1 — all end-of-life with known CVEs (particularly XStream and Log4j 1.x).

## CI/CD

- **GitLab CI**: `.gitlab-ci.yml` inherits a shared Maven template from `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml`.
  - Build phase: `mvn build` with `-Dmaven.test.skip=true`
  - Test phase: `mvn verify` with `-Dmaven.test.skip=true` (no actual testing)
  - Deploy phase: `mvn deploy` / `release:*` with test and javadoc skipped
- **GitHub Actions**: `codeql.yml` runs GitHub CodeQL static analysis on a weekly schedule (`cron: 12 5 * * 0`) on a self-hosted `X64 Linux` runner, reusing the centralised `Onbe/om-ci-setup` workflow.
- **Dependabot**: `.github/dependabot.yml` is present, suggesting automated dependency update PRs are configured (ecosystem and schedule not confirmed without reading the file).
- **No deployment automation**: No Ansible playbooks, Terraform, or deployment scripts are present. Deployment appears to be manual JAR copy + script update on the Windows host.
- **Artifact repository**: SCM coordinates reference `gitlab.com/northlane/...`. Maven deploy presumably pushes to an internal Nexus/Artifactory.
