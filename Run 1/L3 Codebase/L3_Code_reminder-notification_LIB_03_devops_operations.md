# 03 DevOps / Operations — reminder-notification_LIB

## Build
- **Tool**: Maven (Maven Wrapper `mvnw`)
- **Java compile target**: 1.6 (Java 6) — severely outdated
- **Packaging**: Fat JAR (`jar-with-dependencies` via `maven-assembly-plugin`); final artifact name `reminder-notification-1.0.jar`
- **Parent POM**: `com.citi.prepaid.service:service-parent:8`
- **Version**: `2.0.1-SNAPSHOT`
- GitLab CI pipeline defined in `.gitlab-ci.yml`; GitHub Actions CodeQL workflow also present (dual-VCS era artifact)
- Release pipeline uses `maven-release-plugin 3.0.0-M1`

## Deployment
- Deployment is manual / scheduler-driven; the fat JAR is executed as a batch process:
  `java -jar reminder-notification-1.0.jar <contextXml> <jobName> <purpose> [processingDate=MM/dd/yyyy]`
- Windows batch launchers exist (`reminderNotification.bat`, `autobuild-reminderNotificationBatch.bat`, `releases/GEEnrollReminderBatchJob.bat/.vbs`)
- Deployment target: Windows server with `D:/c-base/` directory conventions (inferred from peer repos)
- No Dockerfile; no container deployment

## Config Management
- Runtime config loaded from a `.properties` file at a file-system path (defined in `ReminderNotificationConstants.propFileName`)
- Database connection strings resolved via the Director service at startup; no hard-coded JDBC URLs
- Spring application context XMLs: `dataSourceContext.xml`, job XML files in `resources/job/`
- No environment-specific override mechanism beyond the `.properties` file path

## Observability
- Logging via Apache Commons Logging / Log4j (`log4j.properties` in resources)
- Log4j version is unspecified but consistent with the Spring 2.5 era (Log4j 1.x) — Log4j 1.x reached EOL in 2015; Log4Shell (CVE-2021-44228) does not apply to 1.x but other 1.x CVEs exist
- No structured logging; no APM integration; no metrics export
- Spring Batch execution status available via `jobExecution.getExitStatus()` logged to console/file

## Infrastructure Dependencies
- Windows application server (c-base stack)
- SQL Server (three databases: ecountcore, batchrepodatabase, cbaseapp) via Director service
- Director service for DB connection resolution (`DirectorConfiguredDBCPdatasourceCreator`)
- xPlatform library (`com.ecount:xPlatform:2.5.35`) for email dispatch
- xAffiliateService (`com.ecount.one.service.affiliate:xAffiliateService:1.0.6`) as a transitive dependency
- Internal Maven repository (Northlane/Onbe GitLab) for parent POM and internal artifacts

## Operational Risks
- Java 6 runtime: no vendor support, no security updates
- Spring 2.5.6 and Spring Batch 2.1.1: multiple known CVEs; both are effectively unmaintained
- Log4j 1.x: EOL; CVE exposure
- Properties file missing at runtime: job will continue with empty config, silently disabling `member_details_gridsize` threading
- No restart / retry on transient DB failures
- `GEEnrollReminderBatchJob.vbs` launcher in releases indicates Windows Task Scheduler deployment; no container-level health checks or supervision

## CI/CD
- GitLab CI (`.gitlab-ci.yml`) for build and publish to GitLab package registry
- GitHub Actions CodeQL (`.github/workflows/codeql.yml`) for static analysis on the GitHub mirror
- Dependabot configured (`.github/dependabot.yml`) for GitHub-side dependency alerts
- No automated deployment pipeline; release is a manual Maven release plugin invocation
