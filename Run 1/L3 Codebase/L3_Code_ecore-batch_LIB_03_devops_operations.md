# ecore-batch_LIB — DevOps / Operations View

## Build Process
- **Maven build** (`pom.xml`), groupId=`springbatch`, artifactId=`ecore-batch`, version=`1.0.1-SNAPSHOT`
- Java source/target compatibility: **Java 1.5** (Java 5) — extremely legacy
- Build produces two JARs:
  - `ecore-batch-1.0.0-SNAPSHOT.jar` — library JAR
  - `ecore-batch-1.0.0-SNAPSHOT-jar-with-dependencies.jar` — fat JAR (all dependencies bundled)
- Maven Surefire plugin sets `ENVIRONMENT=sqlserver` for tests
- Maven Assembly plugin creates the fat JAR at the `package` phase
- Maven wrapper (`mvnw`, `mvnw.cmd`) present — allows builds without local Maven installation
- `.mvn/wrapper/settings.xml` — custom Maven settings (Onbe internal Nexus/Artifactory)
- `autobuild-ecorebatch.bat` — Windows batch script for automated build

## Deployment Method
- Fat JAR is deployed to the eCount batch server (Windows, based on `autobuild-ecorebatch.bat`)
- Configuration read from: `D:\c-base\config\xProcess\eCoreBatch\ECoreBatch.properties` and `D:\c-base\config\director-client.properties` — hardcoded absolute Windows paths in `ECoreBatch.xml`
- Test invocation scripts in `src/test/`:
  - `CoreDeviceBatchJob.vbs` — VBScript launcher
  - `CoreTransactionBatchJob.bat`, `EventACHBatchJob.bat`, `EventACHJobEndBatchJob.bat`, `EventIEFTBatchJob.bat` — Windows batch job launchers
- These `.bat`/`.vbs` scripts confirm the deployment target is a **Windows server** running Java
- No containerization (no Dockerfile, no Kubernetes manifest)
- No Ansible, Chef, Puppet, or Terraform deployment scripts

## Configuration Management
Properties files (NOT in repo — runtime-loaded from `D:\c-base\config\`):
- `ECoreBatch.properties` — contains: `director.address`, `springbatch-agent`, `database`, `batchrepodatabase`, stored proc names (`eventach.sp.*`, `core_transfer.sp.*`), thresholds (`eventach_exception_threshold`, `core_transfer_exception_threshold`), grid sizes (`eventach.gridsize`)
- `director-client.properties` — Director service connection settings (eCount's service registry/config server)
- Spring XML config is loaded from classpath; properties files are loaded from the absolute `D:\c-base\` path — environment-specific config is injected at runtime

## Observability
- Logging via Apache Commons Logging (`commons-logging 1.1`) — configured externally (log4j or similar, not in repo)
- Log statements present at INFO and ERROR levels throughout service implementation classes
- **PII in logs** — `EcountCoreServiceHelperImpl.java:80-82` logs member email, first name, last name at INFO level when `isInfoEnabled()`
- Spring Batch execution history stored in `BATCH_` tables in the batch repo database
- GitHub Actions: CodeQL analysis (weekly, Tuesdays at 15:20 UTC) via Onbe's shared `om-ci-setup` reusable workflow
- Dependabot: weekly Maven dependency update checks (configured in `.github/dependabot.yml`)
- No external APM (Datadog, New Relic, Dynatrace) configured in the repo
- No Prometheus/Grafana metrics endpoints

## Infrastructure Dependencies
| Dependency | Purpose | Risk if Unavailable |
|---|---|---|
| EcountCore SQL Server (db02) | Source of batch events and transactions | All batch jobs fail — no events processed |
| Batch repo SQL Server | Spring Batch metadata | Job history unavailable; new jobs may fail to start |
| Director service (`${director.address}`) | DataSource factory; resolves DB connections | All DB connections fail |
| Strongbox RepositoryService | Bank account data retrieval | ACH notifications cannot retrieve bank details |
| ECountCore eMember service | Cardholder data retrieval | Notifications cannot retrieve member info |
| Profile service | Program label retrieval | Notifications cannot retrieve program branding |
| Notification service (NotificationManagerImpl) | Email delivery | Cardholder emails not sent |
| Windows batch server (D:\c-base\) | Runtime environment | Batch jobs cannot execute |

## Operational Risks
1. **Hardcoded `D:\c-base\` path** in `ECoreBatch.xml` — any change to deployment directory requires recompiling the config file.
2. **Java 5 target** — no longer supported; JVM running this code must be backwards-compatible; modern JDK may refuse to run Java 5 bytecode in some configs.
3. **`SimpleAsyncTaskExecutor`** — creates new threads for each task without a pool limit; under high load, this could exhaust thread resources.
4. **No graceful shutdown** visible — if the JVM is killed during a batch step, partially committed transactions may leave eCount Core in an inconsistent state.
5. **No health check endpoint** — no way to query job status from external monitoring without direct DB access to BATCH_ tables.
6. **VBScript launcher** (`CoreDeviceBatchJob.vbs`) — VBScript is deprecated in modern Windows; may not execute on Windows Server 2022+.
7. **`setShouldValidate(false)`** on notifications — silent delivery failures if notification service rejects malformed requests.

## CI/CD Assessment
- **GitHub Actions**: CodeQL security scanning (weekly) — only security scanning; no build/test pipeline.
- **Dependabot**: Weekly Maven dependency version checks — good practice but only automated PRs, not automated merges.
- **No automated build/test pipeline** on commit/PR — no Maven build, no unit test execution in CI.
- Pre-built JAR (`ecore-batch-1.0.0-SNAPSHOT-jar-with-dependencies.jar`) committed to `target/` — JARs should not be committed to source control; indicates manual build workflow.
- The `autobuild-ecorebatch.bat` script is the closest thing to a build pipeline; it is a manual step.
