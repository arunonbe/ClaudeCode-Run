# DevOps & Operations Report — file-transfer-service_LIB

## 1. Build System

### 1.1 Build Tool

The project uses **Apache Maven** with the Maven Wrapper (`mvnw`, `mvnw.cmd`) shipping in `.mvn/wrapper/`. The wrapper properties file at `.mvn/wrapper/maven-wrapper.properties` pins a specific Maven version for reproducible builds.

### 1.2 POM Configuration (`pom.xml`)

| Property | Value |
|---|---|
| GroupId | `FileTransferService` |
| ArtifactId | `FileTransferService` |
| Version | `1.0.1-SNAPSHOT` |
| Packaging | `jar` |
| Java Source/Target | `1.6` (maven-compiler-plugin, lines 30–33) |
| Final Name | `FileTransferService` |
| Main Class | `com.citiprepaid.process.FileTransferProcessMain` |

### 1.3 Build Plugins

| Plugin | Version | Purpose |
|---|---|---|
| `maven-compiler-plugin` | (inherited) | Compile Java 1.6 source |
| `maven-jar-plugin` | (inherited) | Package JAR with manifest declaring main class |
| `maven-assembly-plugin` | (inherited) | Build `jar-with-dependencies` fat JAR for standalone execution |
| `maven-source-plugin` | 3.2.0 | Attach source JAR |
| `maven-release-plugin` | 3.0.0-M1 | Manage version tagging and release promotions |
| `maven-install-plugin` | 2.5.2 | Install to local Maven repository |

The `maven-assembly-plugin` goal `attached` (line 59) runs during the `package` phase, producing a self-contained fat JAR. This is the primary deployment artifact.

### 1.4 Key Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `jscape:jscape` | 9.3.21 | Commercial SFTP/SSH client library (bundled via `jscapeLicense/sftp.zip`) |
| `org.springframework:spring` | 2.5.6 | Spring IoC for datasource and DAO wiring |
| `log4j:log4j` | 1.2.12 | Logging |
| `commons-logging` | 1.0.4 | Commons logging bridge |
| `commons-lang` | 2.1 | String utilities |
| `apache commons-io` | 1.3.2 | File I/O utilities |
| `junit:junit` | 3.8.1 | Unit testing |
| `director-client` | 1.0.11 | Onbe internal Director service client |
| `ecount-system` | 2.0.0 | Onbe ecount-system library |

All dependency versions are significantly outdated (Spring 2.5.6 is from 2008; log4j 1.2.12 is from 2004 and is end-of-life). See `05_solution_architect.md` for risk assessment.

---

## 2. CI/CD Pipeline

### 2.1 GitLab CI (`.gitlab-ci.yml`)

The GitLab CI configuration includes a shared pipeline template from the organization's CI template repository:

```yaml
include:
  - project: 'northlane/development/application-development/configuration/ci-templates'
    ref: 'refactor'
    file: 'maven.gitlab-ci.yml'
```

All three Maven phase options explicitly skip tests:

```yaml
MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true"
MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"
MAVEN_DEPLOY_OPTS: "-Dmaven.test.skip=true -Dmaven.javadoc.skip=true"
```

This means **no unit or integration tests are executed in CI/CD** for this service. The single test class `SFtpExample.java` (under `src/test/java/com/ecount/fts/`) is never executed in the pipeline.

### 2.2 GitHub Actions (`.github/workflows/codeql.yml`)

A GitHub Actions CodeQL workflow performs static security analysis:

```yaml
schedule:
  - cron: 0 16 * * 6   # Weekly on Saturday at 4pm UTC
```

The workflow delegates to a shared Onbe-organization reusable workflow (`Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`) and runs on self-hosted Linux runners tagged `X64`, `Linux`, `ubuntu-docker`.

### 2.3 Dependabot (`.github/dependabot.yml`)

A Dependabot configuration exists, indicating automated dependency update PR generation is enabled for the GitHub mirror.

---

## 3. Deployment

### 3.1 Deployment Model

The service is a standalone batch JAR deployed on a Windows application server. Based on configuration files:

- **Production host references**: `p-na-app31` (noted in `finance-webservice_API` README for the same environment)
- **Configuration directory**: `D:\c-base\config\FileTransferService\` (hardcoded in `Configuration.java` line 93 and `spring.xml` lines 10–11)
- **Working directories**: `c:/temp/b2c/` (local transfer path), `c:/temp/b2c/archive/` (archive path)
- **xContent paths**: `\\PPNACLDDJAS3\d$\NA_SFTP\xContent\` (UNC network share)

### 3.2 Invocation

```
java -jar FileTransferService.jar             # Normal SFTP flow
java -jar FileTransferService.jar xContent    # xContent automation flow
```

The process exits with code 0 (success) or 1 (failure) for easy integration with a scheduler.

### 3.3 Configuration Files (External to JAR)

| File | Location | Contents |
|---|---|---|
| `configuration.properties` | `D:\c-base\config\FileTransferService\` | SFTP connection, thread counts, folder names |
| `db-config.properties` | `D:\c-base\config\FileTransferService\` | Database agent and DB name |
| `director-client.properties` | `D:\c-base\config\FileTransferService\` | Director service address |
| `log4j.properties` | Classpath (`src/main/resources/`) | Logging configuration |

The configuration is loaded at startup only. There is no hot-reload capability.

---

## 4. Artifact Repository

The POM parent references `service-parent` version 8 (groupId `com.citi.prepaid.service`). Distribution management is not explicitly defined in this POM but is inherited from the parent. The SCM URL points to GitLab at `northlane/development/application-development/libraries/file-transfer-service`.

---

## 5. Monitoring and Observability

### 5.1 Logging

Logging is configured via `log4j.properties` (classpath resource). The code uses `commons-logging` API throughout. Log statements are extensive but inconsistently leveled — many `LOG.info()` calls contain raw SFTP credentials (see `02_data_architect.md` section 6.1 for details).

### 5.2 Exit Code Monitoring

The process exits with 1 on any error. A scheduler or monitoring agent watching the exit code provides the primary failure signal.

### 5.3 Database Status Table

The `sftp_process_status` table in the `jobsvc_database` provides a persistent audit trail of all file transfer attempts. Operations teams can query this table to determine in-flight or failed transfers from prior runs.

### 5.4 No Metrics / No Health Endpoint

There are no Prometheus metrics, JMX endpoints, Spring Actuator health checks, or any other observability instrumentation. The service predates modern observability practices.

---

## 6. Environment Lifecycle

| Environment | SFTP Server | Notes |
|---|---|---|
| Development/Test | Inferred from `#hostname = PPA_UAT_SFTP@169.175.98.88` (commented out, `configuration.properties` line 38) | UAT-era configuration |
| Production | `169.171.30.166` (`configuration.properties` line 40) | Active production IP |

There is no environment-specific configuration switching mechanism within the JAR. The appropriate `configuration.properties` must be placed at the hardcoded path before execution.

---

## 7. Operational Risk Summary

| Risk | Severity | Notes |
|---|---|---|
| Tests skipped in CI | HIGH | No automated quality gate |
| Hardcoded Windows paths | HIGH | Deployment tied to single server layout |
| No container/cloud portability | HIGH | Cannot be deployed to Kubernetes or Azure without significant refactoring |
| Single SFTP endpoint, no failover | MEDIUM | Any SFTP server outage halts all file transfers |
| Log4j 1.x (EOL) | HIGH | Vulnerable to known CVEs; see `05_solution_architect.md` |
| No secrets management | CRITICAL | Credentials in plaintext properties file |
