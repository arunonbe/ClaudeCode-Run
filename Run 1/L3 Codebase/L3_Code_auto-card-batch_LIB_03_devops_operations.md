# auto-card-batch_LIB — DevOps & Operations View

## Build & Packaging

**Build tool**: Apache Maven 3.9.1 (via Maven Wrapper, `.mvn/wrapper/maven-wrapper.properties`).

**Artifact**: `autocard-batch-1.0.1.jar` (fat/uber jar via `maven-shade-plugin` 1.4). The `pom.xml` `finalName` is `autocard-batch-1.0.1` (line 278) — note the mismatch with the POM `version` field (`2.0.2-SNAPSHOT`); the JAR filename is hardcoded and does not reflect the actual artifact version.

**Packaging pipeline** (`autocard-build.bat`):
1. `mvn -Dmaven.test.skip=true clean install` — skips tests at build time.
2. Manually copies `spring.schemas` and `spring.handlers` into a local `META-INF/` directory.
3. Updates the built JAR with `jar -uvf` to inject the Spring namespace handler files.
4. Cleans up the temporary `META-INF/` directory.

This manual two-phase build is a workaround for Spring XML namespace handler merging (also handled by `maven-shade-plugin` `AppendingTransformer` in the POM). The bat script and the shade plugin both attempt to handle this, creating a redundant and fragile process.

**Assembly**: `src/assembly/assembly.xml` produces a ZIP containing the fat JAR plus all runtime dependencies. Scope is `runtime`.

**Java compiler target**: Java 1.5 (`maven-compiler-plugin` source/target `1.5` in `pom.xml` lines 192–195). This is severely outdated (Java 5, EOL since 2009).

**Key dependencies and versions**:

| Dependency | Version | Notes |
|---|---|---|
| Spring Framework | 2.5.6 | EOL — released 2008 |
| Spring Batch | 2.1.1.RELEASE | EOL — released 2010 |
| Log4j | 1.2.15 | EOL — Log4Shell-era predecessor, reached EOL August 2015 |
| commons-dbcp | 1.2.2 | EOL — superseded by DBCP2 |
| commons-pool | 1.4 | EOL |
| aspectjweaver | 1.5.3 | EOL |
| sqljdbc | 1.1 | Very old SQL Server JDBC driver |
| JUnit | 3.8.1 AND 4.4 | Dual JUnit versions declared — 3.8.1 appears twice (test scope) alongside 4.4 (no scope = compile classpath) |
| mockito-core | 3.12.4 | Relatively modern for the codebase |
| spring-mock | 2.0.8 | Deprecated Spring test artifact |

## Deployment

**Deployment model**: Command-line invocation on a Windows server. Two batch scripts serve as the execution entry points:

| Script | Job | Invocation |
|---|---|---|
| `Job1.bat` | `autoCardLoadRecordsJob` | `java -Xms256m -Xmx1024m -cp %CLASSPATH%;autocard-batch.jar org.springframework.batch.core.launch.support.CommandLineJobRunner AutoCardBatch.xml autoCardLoadRecordsJob -next` |
| `Job2.bat` | `autoCardProcessJob` | `java -Xms256m -Xmx1024m -cp %CLASSPATH%;autocard-batch.jar org.springframework.batch.core.launch.support.CommandLineJobRunner AutoCardBatch.xml autoCardProcessJob -next` |

**Heap configuration**: Min 256 MB, Max 1024 MB.

**Configuration file path**: Hard-coded absolute Windows path in `AutoCardBatch.xml` (line 23):
```
file:D:\c-base\config\processes\autocard\autocardbatch.properties
file:D:\c-base\config\director-client.properties
```
This is a hard-coded `D:\c-base\` path, making the application non-portable and environment-specific.

**Log output**: Writes to `D:/c-base/log/autocardtest.log` (rolling file, max 20 MB, 10 backups). The log filename includes "test" — possibly a development artifact promoted to production.

**Containerisation**: None. No `Dockerfile` is present.

**Scheduling**: No cron or scheduler configuration exists within the repository. The `-next` flag on `CommandLineJobRunner` forces a new job instance on each invocation. External scheduling (e.g., Windows Task Scheduler or a job scheduler like Control-M/Autosys) is assumed.

## Configuration Management

**Primary configuration file**: `autocardbatch.properties` (deployed to `D:\c-base\config\processes\autocard\`):

| Key | Value (from properties file) | Notes |
|---|---|---|
| `ecountcore.agent` | `B2CTEST` | Hard-coded test agent name |
| `batchrepodatabase` | `ecountbatchjobrepository` | Batch repo DB name |
| `database` | `cbaseapp` | Unused in current XML config |
| `ecountcore.database` | `ecountcore_test` | Hard-coded "test" DB name |
| `autocard.table` | `autocard_creation_transaction_journal` | Transaction journal table |
| `autocard.gridsize` | `5` | Partition thread count |
| `autocard.pagesize` | `5` | Records fetched per partition |
| `autocard.exceptionthreshold` | `100` | Max exceptions before halt |
| `autocard.sp.*` | 3 SP names | Stored procedure references |
| `autocard.threshold.issue.plastic` | Not in properties file | Referenced in XML as `${autocard.threshold.issue.plastic}` but missing from the committed `autocardbatch.properties` — will cause startup failure if not in external config |
| `autocard.sp.autocard_order_load` | Not in properties file (key in XML differs from key in properties: XML uses `autocard.sp.autocard_order_load`, properties has `autocard.sp.auto_card_creation_order_load`) | Key mismatch — will fail to resolve at runtime |

**Director client config**: `director-client.properties` (external, not in repo). This is the source for the Director service address and database connection parameters.

**Maven settings**: `.mvn/wrapper/settings.xml` configures a Nexus proxy at `d-na-stk01.nam.wirecard.sys:8081` (Wirecard/legacy infrastructure). This hostname is from the former Wirecard organisation and may no longer be resolvable.

## Observability

**Logging**: Log4j 1.x with two appenders:
- `ConsoleAppender` (A): Pattern `%d %-5p %c %x - %m%n`
- `RollingFileAppender` (R): File `D:/c-base/log/autocardtest.log`, max 20 MB, 10 backups, pattern `%d %p %t %c - %m%n`

Root logger level: `debug` — all packages log at DEBUG, including PII (`memberid`) in `AutoCardCreateWriter`.

**Metrics**: None. No custom metrics, JMX, Micrometer, or Actuator integration.

**Alerting**: None built into the application. Exit codes provide limited signalling:
- 0 = success
- 11 = `NO RECORDS FOUND:ECORE EXCEPTION`
- 12 = `EXCEPTION THRESHOLD`
- 13 = `INFINITE LOOP`

External monitoring must parse exit codes or log output to detect failures.

**Distributed tracing**: None.

**Health checks**: None.

## Infrastructure Dependencies

| Dependency | Type | Details |
|---|---|---|
| SQL Server (`ecountcore_test`) | Database | Operational data source; connection via Director |
| SQL Server (`ecountbatchjobrepository`) | Database | Spring Batch job repository |
| Director service | Internal service | Provides JDBC connection parameters at runtime |
| eCore/FDR API | Core platform API | `com.cbase.business.core.spi.ecore.ECoreDevice` — card issuance system |
| eCount Profile System | Internal service | `AppProfileUserEnrollmentClass` — cardholder enrollment |
| Nexus (`d-na-stk01.nam.wirecard.sys:8081`) | Maven artifact repo | Build-time dependency resolution; legacy Wirecard infrastructure |
| GitHub Maven Packages (`maven.pkg.github.com/onbe/onbe_maven_releases`) | Maven artifact repo | Build-time dependency resolution |
| `D:\c-base\` filesystem | Local filesystem | Config files, log files — Windows path hard-coded |

## Operational Risks

1. **Tests are always skipped** (`MAVEN_BUILD_OPTS`, `MAVEN_TEST_OPTS`, `MAVEN_DEPLOY_OPTS` in `.gitlab-ci.yml` all set `-Dmaven.test.skip=true`). The pipeline never validates the test suite. The only tests (`CardCreateServiceTest`) would never run in CI.

2. **Hard-coded `D:\c-base\` path** in `AutoCardBatch.xml` (line 23) and `log4j.properties` (line 9) — non-portable and environment-specific. Any server migration or Docker containerisation would require code changes.

3. **Missing property `autocard.threshold.issue.plastic`** from the committed `autocardbatch.properties` — the XML references `${autocard.threshold.issue.plastic}` but the key is absent from the file. The application relies on this being present in the external (uncommitted) config.

4. **Property key mismatch**: `AutoCardLoadRecordsJob.xml` references `${autocard.sp.autocard_order_load}` but `autocardbatch.properties` declares `autocard.sp.auto_card_creation_order_load`. This mismatch will cause the SP name to be unresolved (literal placeholder string) at runtime, causing the load job to fail.

5. **Log file named `autocardtest.log`**: Suggests development log path may be in use in production environments.

6. **Plaintext passwords in `settings.xml`**: Nexus and ecount deploy credentials committed to source control.

7. **Legacy Wirecard Nexus URL**: Build may fail in environments where `d-na-stk01.nam.wirecard.sys` is not reachable.

## CI/CD

**GitLab CI** (`.gitlab-ci.yml`): Inherits a shared Maven pipeline template from `northlane/development/application-development/configuration/ci-templates` (ref: `refactor`). All three Maven phases skip tests:
- Build: `mvn build -Dmaven.test.skip=true`
- Test: `mvn verify -Dmaven.test.skip=true`
- Deploy: `mvn deploy -Dmaven.test.skip=true -Dmaven.javadoc.skip=true`

**GitHub Actions** (`.github/workflows/codeql.yml`): CodeQL analysis runs on schedule (weekly, Tuesday 03:24 UTC) and on manual dispatch. Uses `Onbe/om-ci-setup` shared workflow on `main` with a self-hosted Linux runner.

**Dependabot** (`.github/dependabot.yml`): Weekly Maven dependency update checks configured.

**Observation**: The project has dual CI configurations (GitLab CI for build/deploy, GitHub Actions for security scanning). This dual-VCS posture (GitLab SCM in `pom.xml`, GitHub workflows in `.github/`) indicates the project was migrated or is mirrored between GitLab (Northlane/legacy) and GitHub (Onbe/current).
