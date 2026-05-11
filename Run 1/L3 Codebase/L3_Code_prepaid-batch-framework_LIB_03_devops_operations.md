# prepaid-batch-framework_LIB — DevOps and Operations View

## 1. Build System

The project uses Apache Maven with a multi-module structure. Parent POM references `service-parent` version 8 (`com.citi.prepaid.service:service-parent`), which is an internal Onbe/Northlane parent, not the `prepaid-parent_PARENT` repo analyzed elsewhere.

| Attribute | Value |
|---|---|
| GroupId | `com.libraries.prepaid-batch-framework` |
| ArtifactId | `prepaidbatch` |
| Version | `1.0.1-SNAPSHOT` |
| Packaging | `pom` (multi-module aggregator) |
| Java | Spring 2.5.6 (Java 5+ compatible) |
| Main entry point | `com.citi.prepaid.batch.PrepaidBatchMain` (manifest main-class) |
| Build output | `prepaidbatch-impl-1.0.0-SNAPSHOT-jar-with-dependencies.jar` (fat JAR) |

**Modules** (in dependency order): `prepaidbatch-common` → `prepaidbatch-library` → `prepaidbatch-impl` → `ModuleCommon` → `CMFA-AltInbound` → `CMFA-AltOutbound` → `CMFA-Inquiry` → `CMFAReportSync` → `submithierarchy` → `submitinquiry`

## 2. CI/CD Pipeline

The `.gitlab-ci.yml` extends a shared GitLab CI template from:
```
project: 'northlane/development/application-development/configuration/ci-templates'
ref: 'refactor'
file: 'maven.gitlab-ci.yml'
```

All Maven phases skip tests:
```yaml
MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true"
MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"
MAVEN_DEPLOY_OPTS: "-Dmaven.test.skip=true -Dmaven.javadoc.skip=true"
```

This means **zero automated test validation occurs in CI**. The build only validates compilation. A `.github/dependabot.yml` and `.github/workflows/codeql.yml` are also present, indicating dual GitLab + GitHub hosting, with CodeQL static analysis on GitHub.

## 3. Runtime Environment

Batch jobs are invoked from the command line (Windows) using the launcher script `scripts/processBatch.bat`:

```batch
set CLASSPATH=D:/c-base/runtime/prepaidbatch/lib/prepaidbatch-impl-1.0.0-SNAPSHOT-jar-with-dependencies.jar
java -Xms256m -Xmx1024m -Dlog4j.configuration=file:///D:/c-base/config/service/prepaidBatch/log4j.xml -cp %CLASSPATH% com.citi.prepaid.batch.PrepaidBatchMain BusinessInquiry
```

| Parameter | Value | Notes |
|---|---|---|
| JVM heap min | 256 MB | Fixed; may be insufficient for large settlement files |
| JVM heap max | 1024 MB | Fixed; no dynamic scaling |
| Log4j config | `D:/c-base/config/service/prepaidBatch/log4j.xml` | External, not in repo |
| Module registry | `D:\c-base\config\service\prepaidBatch\ModuleRegistry.xml` | External, not in repo |
| Scheduler | ActiveBatch (inferred from exit code comment, `PrepaidBatchMain.java` line 91) |

## 4. Dependency Versions

| Dependency | Version | Risk |
|---|---|---|
| `org.springframework:spring` | 2.5.6 | EOL; known CVEs (Spring4Shell lineage) |
| `log4j:log4j` | 1.2.15 | EOL; CVE-2019-17571, CVE-2022-23302/3/5 |
| `junit:junit` | 4.4 | Test only; minor |
| `org.springframework.batch:spring-batch-test` | 2.1.1.RELEASE | EOL |
| `commons-beanutils` | 1.7.0 | CVE-2019-10086 (ClassLoader manipulation) |
| `director-client` | 2.0.2 | Internal |

**Note**: `log4j 1.2.15` is specifically vulnerable to CVE-2019-17571 (if `SocketServer` is used) and the JMSAppender chain exploit (CVE-2022-23302). These must be remediated for PCI DSS Requirement 6.3.3 compliance.

## 5. Deployment Procedures

The current deployment model is fully manual on-premises:
1. Build the fat JAR: `mvn clean package -Dmaven.test.skip=true`
2. Copy `prepaidbatch-impl-*-jar-with-dependencies.jar` to `D:/c-base/runtime/prepaidbatch/lib/`
3. Update `ModuleRegistry.xml` in `D:\c-base\config\service\prepaidBatch\` for new/changed modules
4. ActiveBatch scheduler invokes `processBatch.bat` (or variant) with module ID argument

No container, no artifact registry publishing visible in this repo (though `maven-release-plugin` 3.0.0-M1 is configured, suggesting Nexus/GitHub Package deployments may occur for the library JAR).

## 6. Operational Runbook

### Starting a Batch Job Manually
```batch
set CLASSPATH=<path_to_jar>
java -Xms256m -Xmx1024m -Dlog4j.configuration=file:///<log4j_config> -cp %CLASSPATH% com.citi.prepaid.batch.PrepaidBatchMain <MODULE_ID>
```
With optional inputs:
```batch
... PrepaidBatchMain <MODULE_ID> INPUTFILE=<filepath> REPORTTYPE=<type>
```

### Exit Codes
| Code | Meaning |
|---|---|
| 0 | `PROCESSING_STATUS_SUCCESS` — batch completed normally |
| 1 | `PROCESSING_STATUS_GENERIC_FAILURE` — any exception or validation failure |

### Failure Diagnosis
- Check `log4j.xml`-configured log file for exception stack traces
- Common failure: Module ID not found in `ModuleRegistry.xml` → `NullPointerException` on `BatchModule` bean lookup
- FTP failure: `PrepaidBatchException` in `FTPLibraryImpl` — check FTP credentials in Profile service
- BCP failure: SQL Server connectivity; check Director service and data source configuration

## 7. Monitoring Gaps

No metrics, no health checks, no alerting configuration exists in this repository. For NACHA/settlement batch monitoring, the following should be added:
- Alert on non-zero exit codes from ActiveBatch
- Alert on log `ERROR` entries from the batch log
- Reconcile expected vs. actual record counts from BCP import/export
