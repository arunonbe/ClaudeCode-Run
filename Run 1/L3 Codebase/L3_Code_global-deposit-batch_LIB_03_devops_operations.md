# DevOps & Operations Report — global-deposit-batch_LIB

## 1. Build System

### 1.1 Build Tools

The project uses a dual build system:
- **Apache Maven** (primary): Maven Wrapper (`mvnw`, `mvnw.cmd`) with `.mvn/wrapper/`
- **Gradle** (secondary): `gradle/wrapper/gradle-wrapper.properties` and `build.gradle` files in each sub-module

Each sub-module has both a `pom.xml` and a `build.gradle`, suggesting the build system transition from Gradle to Maven was in progress when development was active.

### 1.2 Root POM

| Property | Value |
|---|---|
| GroupId | `com.wirecard.issuing` |
| ArtifactId | `globaldepositbatch` |
| Version | `2.0.4-SNAPSHOT` |
| Packaging | `pom` (aggregator) |
| Java Source/Target | `1.8` |
| Parent | `service-parent:9.0.0` (groupId `com.parents`) |

### 1.3 Sub-Module Structure

| Module | Artifact ID | Output |
|---|---|---|
| `global-deposits-batch` | `global-deposits-batch` | Batch job implementations |
| `global-deposits-batch-cbts-client` | `global-deposits-batch-cbts-client` | CBTS HTTP client |
| `global-deposits-batch-config` | `global-deposits-batch-config` | Spring Boot config + main class |
| `global-deposits-batch-data` | `global-deposits-batch-data` | Data models |
| `global-deposits-batch-qa` | `global-deposits-batch-qa` | Integration tests |
| `global-deposits-batch-xplatform-client` | `global-deposits-batch-xplatform-client` | xPlatform iEFT client |

The main application entry point is `GlobalDepositBatchApplication.java` in the `global-deposits-batch-config` module. The Spring Boot repackage plugin (`spring-boot-maven-plugin` version `2.3.4.RELEASE`, root `pom.xml` lines 125–138) creates an executable JAR with classifier `exec`.

### 1.4 Key Dependencies (from root POM and sub-modules)

| Dependency | Purpose |
|---|---|
| `spring-boot-starter` 2.3.4.RELEASE | Spring Boot base |
| `spring-batch-core` | Spring Batch framework |
| `spring-jdbc` | JDBC template |
| `commons-lang3` | Apache utilities |
| Lombok | Code generation |
| Wiremock | HTTP service mocking for tests |
| H2 | In-memory database for tests |

---

## 2. CI/CD Pipeline

### 2.1 GitLab CI (`gitlab-ci.yml`)

```yaml
include:
  - project: 'northlane/development/application-development/configuration/ci-templates'
    file: 'maven.gitlab-ci.yml'

variables:
  MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true"
  MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"
  MAVEN_DEPLOY_OPTS: "-Dmaven.test.skip=true -Dmaven.javadoc.skip=true"
```

All Maven phases **skip tests**. Despite the library having a dedicated `global-deposits-batch-qa` integration test module with a comprehensive test suite (multiple integration test classes and test data CSV files), none of these tests are executed in the CI/CD pipeline.

### 2.2 GitHub Actions (`.github/workflows/codeql.yml`)

CodeQL security analysis is scheduled weekly (Saturday at 4pm UTC):

```yaml
schedule:
  - cron: 0 16 * * 6
```

Uses the shared Onbe organization CodeQL workflow (`Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`) on self-hosted Linux runners.

### 2.3 Dependabot

`.github/dependabot.yml` configures automated dependency update PRs.

---

## 3. Artifact Repository

The root `pom.xml` (lines 32–43) defines distribution management to a **Nexus repository** at `d-na-stk01.nam.wirecard.sys`:

```xml
<repository>
  <id>ecount.release</id>
  <url>dav:http://d-na-stk01.nam.wirecard.sys:8080/nexus/...</url>
</repository>
```

This is a Wirecard-era internal Nexus repository. Post-acquisition, it is unclear if this Nexus instance is still operational. If not, `mvn deploy` will fail, and downstream consumers that depend on this artifact will be unable to resolve it from the configured repository.

---

## 4. Deployment

### 4.1 Deployment Model

As a `_LIB` library, `global-deposit-batch_LIB` is not independently deployed. It is consumed as a Maven dependency by a batch orchestration service. The `GlobalDepositBatchApplication.java` Spring Boot main class in `global-deposits-batch-config` allows the library to be run standalone for testing or direct batch execution.

The library is designed to be invoked via Spring Batch's `CommandLineJobRunner` or via a scheduler/orchestrator that calls the Spring Boot main class with specific `BatchJob` parameters.

### 4.2 Batch Job Selection

The `BatchJob` enum in `global-deposits-batch/src/main/java/com/wirecard/globaldepositsbatch/batch/common/constant/BatchJob.java` defines the available jobs:
- `GLOBAL_DEPOSIT_MIGRATION`
- `GLOBAL_DEPOSIT_REJECT_PROCESS`
- `RECURRING_GLOBAL_DEPOSIT_SERVICE`

Batch jobs are selected via Spring Batch job parameter or Spring profile activation.

### 4.3 Directory Initialization

`DirectoryGeneratorApp.java` / `DirectoryGenerator.java` in the `global-deposits-batch/src/main/java/com/wirecard/globaldepositsbatch/init/` package handle creation of the required input/processed/failed directories at startup. `BatchPathConfig.java` provides the configured paths.

---

## 5. Testing

### 5.1 Unit Tests (Per-Module)

Each module has unit tests:
- `GlobalDepositMigrationBatchAppTest.java`, `GlobalDepositMigrationProcessorTest.java`, etc.
- `CbtsClientTest.java`, `RateServiceTest.java`
- `PathUtilsTest.java`, `BatchJobTest.java`

### 5.2 Integration Tests (`global-deposits-batch-qa`)

The QA module contains comprehensive integration tests:
- `GlobalDepositMigrationIntegrationTest.java`
- `GlobalDepositRejectProcessIntegrationTest.java`
- `RecurringGlobalDepositServiceIntegrationTest.java`

Test infrastructure uses:
- `IntegrationTestConfiguration.java` — Spring context for integration tests
- Wiremock (`spring.profiles=wiremock`) for CBTS API mocking
- Real CSV test data files in `test-data/batch/internal/globaldepositrejectprocess/`

**The presence of a comprehensive test suite that is entirely skipped in CI represents a significant quality assurance gap.**

---

## 6. Monitoring and Observability

### 6.1 Logging

Spring Batch provides built-in job execution logging. The `application.yml` configures DEBUG logging for:
- `com.wirecard.globaldepositsbatch.cbtsclient`
- `com.wirecard.globaldepositsbatch.batch`
- `com.wirecard.globaldepositsbatch.RateService`

### 6.2 Spring Batch Job Repository

Spring Batch uses the `JobRepository` pattern to persist job execution metadata. The `spring.batch.initialize-schema: always` setting (`application.yml` line 5) means the Spring Batch schema tables are created/updated on every startup — this should be `never` or `embedded` in production to avoid schema modifications at runtime.

### 6.3 Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| Hardcoded CBTS credentials in `application.yml` | CRITICAL | See `02_data_architect.md` section 5.1 |
| Wirecard Nexus repository may be decommissioned | HIGH | Artifact distribution blocked |
| Tests skipped in CI | HIGH | No automated quality gate |
| `spring.batch.initialize-schema: always` | MEDIUM | Schema modification at every startup |
| Java 8 (EOL Security Support) | HIGH | No Oracle security patches |
| Spring Boot 2.3.4 (EOL) | HIGH | EOL since August 2021 |
| CBTS dev URL in config | HIGH | Wirecard-branded endpoint may be offline |
| No CBTS credential rotation mechanism | HIGH | Hardcoded credentials require code change to rotate |
