# Solution Architect Report — global-deposit-batch_LIB

## 1. Complete Class and Method Inventory

### Module: `global-deposits-batch`

**Package: `com.wirecard.globaldepositsbatch.batch.common.config`**

| Class | Methods | File |
|---|---|---|
| `BatchJobContextConfig` | (Spring `@Configuration` bean definitions) | `batch/common/config/BatchJobContextConfig.java` |

**Package: `com.wirecard.globaldepositsbatch.batch.common.constant`**

| Class | Methods/Values | File |
|---|---|---|
| `BatchJob` (enum) | `GLOBAL_DEPOSIT_MIGRATION`, `GLOBAL_DEPOSIT_REJECT_PROCESS`, `RECURRING_GLOBAL_DEPOSIT_SERVICE` | `batch/common/constant/BatchJob.java` |
| `BatchJobConstants` | (string constants) | `batch/common/constant/BatchJobConstants.java` |

**Package: `com.wirecard.globaldepositsbatch.batch.common.util`**

| Class | Methods | File |
|---|---|---|
| `PathUtils` | (path utility methods) | `batch/common/util/PathUtils.java` |

**Package: `com.wirecard.globaldepositsbatch.batch.internal.globaldepositmigration`**

| Class | Methods | File |
|---|---|---|
| `GlobalDepositMigrationBatchApp` | `globalDepositMigrationJob(Step)`, `stepMigration()` | `batch/internal/globaldepositmigration/GlobalDepositMigrationBatchApp.java` |
| `GlobalDepositMigrationProcessor` | `process(GlobalDepositMigrationRecord)` | `batch/internal/globaldepositmigration/GlobalDepositMigrationProcessor.java` |
| `GlobalDepositMigrationReader` | `read()` | `batch/internal/globaldepositmigration/GlobalDepositMigrationReader.java` |
| `GlobalDepositMigrationWriter` | `write(List<GlobalDepositMigrationRecord>)` | `batch/internal/globaldepositmigration/GlobalDepositMigrationWriter.java` |

**Package: `com.wirecard.globaldepositsbatch.batch.internal.globaldepositrejectprocess`**

| Class | Methods | File |
|---|---|---|
| `GlobalDepositRejectProcessBatchApp` | `globalDepositRejectProcessJob(Step)`, `stepRejectProcess()` | `batch/internal/globaldepositrejectprocess/GlobalDepositRejectProcessBatchApp.java` |
| `GlobalDepositRejectsItemProcessor` | `process(GlobalDepositRejectRecord)` | `batch/internal/globaldepositrejectprocess/GlobalDepositRejectsItemProcessor.java` |
| `GlobalDepositRejectsItemReader` | `GlobalDepositRejectsItemReader(GlobalDepositRejectProcessConfig)`, `fileReader()`, `beforeStep(StepExecution)`, `getFiles(GlobalDepositRejectProcessConfig)` | `batch/internal/globaldepositrejectprocess/GlobalDepositRejectsItemReader.java` |
| `GlobalDepositRejectsJdbcItemWriter` | `write(List<GlobalDepositRejectRecord>)` | `batch/internal/globaldepositrejectprocess/GlobalDepositRejectsJdbcItemWriter.java` |
| `GlobalDepositRejectsMoveFileStepListener` | `beforeStep(StepExecution)`, `afterStep(StepExecution)` | `batch/internal/globaldepositrejectprocess/GlobalDepositRejectsMoveFileStepListener.java` |

**Package: `com.wirecard.globaldepositsbatch.batch.internal.recurringglobaldepositsservice`**

| Class | Methods | File |
|---|---|---|
| `RecurringGlobalDepositServiceBatchApp` | `recurringGlobalDepositServiceJob(Step)`, `stepRecurringService()` | `batch/internal/recurringglobaldepositsservice/RecurringGlobalDepositServiceBatchApp.java` |
| `RecurringGlobalDepositServiceProcessor` | `RecurringGlobalDepositServiceProcessor(RateService, JdbcTemplate)`, `process(RecurringGlobalDepositRecord)` | `batch/internal/recurringglobaldepositsservice/RecurringGlobalDepositServiceProcessor.java` |
| `RecurringGlobalDepositServiceReader` | `read()` | `batch/internal/recurringglobaldepositsservice/RecurringGlobalDepositServiceReader.java` |
| `RecurringGlobalDepositServiceRowMapper` | `mapRow(ResultSet, int)` | `batch/internal/recurringglobaldepositsservice/RecurringGlobalDepositServiceRowMapper.java` |

**Package: `com.wirecard.globaldepositsbatch.init`**

| Class | Methods | File |
|---|---|---|
| `BatchPathConfig` | (path configuration bean) | `init/BatchPathConfig.java` |
| `DirectoryGenerator` | `generateDirectories()` | `init/DirectoryGenerator.java` |
| `DirectoryGeneratorApp` | `main(String[])` | `init/DirectoryGeneratorApp.java` |

**Package: `com.wirecard.globaldepositsbatch.appconfig.internal`**

| Class | Key Methods | File |
|---|---|---|
| `GlobalDepositMigrationConfig` | `getChunkSize()`, `getPageSize()`, `getMaxItemCount()` | `appconfig/internal/GlobalDepositMigrationConfig.java` |
| `GlobalDepositRejectProcessConfig` | `getInput()`, `getProcessed()`, `getFailed()`, `getChunkSize()` | `appconfig/internal/GlobalDepositRejectProcessConfig.java` |
| `RecurringGlobalDepositServiceConfig` | `getChunkSize()`, `getPageSize()`, `getMaxItemCount()` | `appconfig/internal/RecurringGlobalDepositServiceConfig.java` |

### Module: `global-deposits-batch-cbts-client`

**Package: `com.wirecard.globaldepositsbatch.cbtsclient`**

| Class | Methods | File |
|---|---|---|
| `CbtsClient` | `getRate(...)`, `bookRate(...)`, `createTransfer(...)` (inferred) | `cbtsclient/CbtsClient.java` |
| `ErrorHandler` | `handleError(ClientHttpResponse)` | `cbtsclient/ErrorHandler.java` |

**Package: `com.wirecard.globaldepositsbatch.cbtsclient.appconfig`**

| Class | Methods | File |
|---|---|---|
| `CbtsConfig` | (HTTP client configuration beans) | `cbtsclient/appconfig/CbtsConfig.java` |
| `HttpClientConfig` | `httpClient()`, `requestFactory()` (inferred) | `cbtsclient/appconfig/HttpClientConfig.java` |
| `UrlConfig` | `getBaseUrl()`, `getRateUrl()`, `getBookRateUrl()`, `getTransferUrl()` | `cbtsclient/appconfig/UrlConfig.java` |

**Package: `com.wirecard.globaldepositsbatch.cbtsclient.service`**

| Class | Methods | File |
|---|---|---|
| `RateService` (interface) | `transfer(RecurringGlobalDepositRecord)` | `cbtsclient/service/RateService.java` |
| `RateServiceImpl` | `transfer(RecurringGlobalDepositRecord)` | `cbtsclient/service/impl/RateServiceImpl.java` |

### Module: `global-deposits-batch-xplatform-client`

**Package: `com.wirecard.globaldepositsbatch.xplatformclient.service`**

| Class | Methods | File |
|---|---|---|
| `IEFTService` (interface) | `registerBeneficiary(String, String, String)`, `registerRemitter(String, String, String)`, `cancelOnDemand(String, String)` | `xplatformclient/service/IEFTService.java` |
| `IEFTServiceImpl` | `registerBeneficiary(String, String, String)`, `registerRemitter(String, String, String)`, `cancelOnDemand(String, String)` | `xplatformclient/service/IEFTServiceImpl.java` |
| `XplatformIEFTManager` | `registerBeneficiary(String, String)`, `registerRemitter(String, String, String)`, `cancelOnDemand(String, String)` | `xplatformclient/service/XplatformIEFTManager.java` |

### Module: `global-deposits-batch-data`

| Class | Fields | File |
|---|---|---|
| `GlobalDepositRejectRecord` | `transferId`, `returnedUsd`, `amount`, `fee`, `returnReason`, `fxRate`, `created` | `data/prototype/GlobalDepositRejectRecord.java` |
| `GlobalDepositMigrationRecord` | (migration fields) | `data/prototype/GlobalDepositMigrationRecord.java` |
| `RecurringGlobalDepositRecord` | `rowId`, `rateId`, (iEFT fields) | `data/prototype/RecurringGlobalDepositRecord.java` |
| `Rate` | FX rate fields | `data/cbts/Rate.java` |
| `RateStatus` (enum) | (rate status values) | `data/cbts/RateStatus.java` |
| `RequestType` (enum) | (request type values) | `data/cbts/RequestType.java` |
| `Transfer` | Transfer fields | `data/cbts/Transfer.java` |
| `ErrorResponse` | Error fields | `data/cbts/ErrorResponse.java` |

### Module: `global-deposits-batch-config`

| Class | Methods | File |
|---|---|---|
| `GlobalDepositBatchApplication` | `main(String[])` | `GlobalDepositBatchApplication.java` |
| `AppConfigContext` | (Spring context config beans) | `appconfig/AppConfigContext.java` |
| `BatchContext` | (batch job beans) | `batch/BatchContext.java` |
| `CbtsClientContext` | (CBTS client beans) | `cbtsclient/CbtsClientContext.java` |
| `ServiceContext` | (service beans) | `service/ServiceContext.java` |
| `XplatformClientContext` | (xPlatform client beans) | `xplaformclient/XplatformClientContext.java` |

---

## 2. Security Vulnerability Assessment

### VULN-001 — CRITICAL: Hardcoded CBTS API Credentials in Source-Controlled File

**Location**: `global-deposits-batch-config/src/main/resources/application.yml` lines 28–29

```yaml
cbts:
  http-client:
    username: "[REDACTED — rotate immediately]"
    password: "[REDACTED — rotate immediately]"
```

**Risk**: Production or development CBTS API credentials are committed to source control. Anyone with access to the GitLab/GitHub repository can extract these credentials and call the Cambridge CBTS API directly, potentially initiating or cancelling cross-border fund transfers.

Violation of:
- PCI DSS v4.0.1 Requirement 6.3.3: "All security vulnerabilities are identified and addressed"
- NIST CSF 2.0 PR.AA-01
- Onbe's own credential management policies

**Remediation**: 
1. Rotate both the username and password with Cambridge Global Payments immediately
2. Remove credentials from `application.yml` and all config files
3. Inject credentials at runtime via Azure Key Vault or environment variables
4. Scan Git history for additional credential exposure (`git log -p | grep -i password`)
Priority: **CRITICAL — IMMEDIATE ACTION**.

---

### VULN-002 — HIGH: Spring Boot 2.3.4 (End-of-Life)

**Location**: Root `pom.xml` lines 125–139

**Risk**: Spring Boot 2.3.4 (released August 2020, EOL August 2021) has multiple known CVEs. Security patches are no longer provided. Key vulnerabilities in the 2.3.x lineage include Spring Framework and Tomcat embedded server vulnerabilities.

**Remediation**: Upgrade to Spring Boot 3.2.x (latest stable). Note: Spring Batch 5.x (included in Spring Boot 3.x) has breaking API changes requiring refactoring of `JobBuilderFactory`, `StepBuilderFactory`, and `@EnableBatchProcessing` usage. Priority: **HIGH**.

---

### VULN-003 — HIGH: Java 8 (End of Oracle Commercial Support)

**Location**: Root `pom.xml` line 27

**Risk**: Java 8 is past Oracle's end of commercial support. While Adoptium (Eclipse Temurin) continues to provide Java 8 builds, the Spring Boot 3.x upgrade path requires Java 17 minimum.

**Remediation**: Upgrade to Java 17 LTS (prerequisite for Spring Boot 3.x upgrade). Priority: **HIGH**.

---

### VULN-004 — HIGH: Wirecard CBTS Endpoint May Be Defunct

**Location**: `application.yml` line 32

```yaml
base-url: https://cbts-dev.amer1.wirecard.com/cross-border-transfer-service
```

**Risk**: The `wirecard.com` domain is associated with the insolvent Wirecard AG (collapsed 2020). This development endpoint may be inactive, controlled by a third party, or DNS-squatted. If CBTS API calls are routed to an unverified endpoint, transfer data is exposed to an uncontrolled external party.

**Remediation**: Verify the current Cambridge CBTS production and non-production endpoints with the Cambridge Global Payments team. Update `application.yml` to use verified, Onbe-controlled endpoint configuration. Priority: **HIGH**.

---

### VULN-005 — HIGH: Tests Never Executed in CI (`maven.test.skip=true`)

**Location**: `gitlab-ci.yml` lines 3–8

**Risk**: The comprehensive integration test suite (`global-deposits-batch-qa` module with 8+ integration test classes and 10+ test CSV files) has never been executed in CI. This means:
- No regression detection for changes to batch processing logic
- Financial transaction processing defects may reach production undetected
- NACHA compliance logic (addenda processing, return handling) is unvalidated in CI

**Remediation**: Remove `-Dmaven.test.skip=true` from all three CI variables. Fix any currently failing tests. Priority: **HIGH** (financial correctness risk).

---

### VULN-006 — MEDIUM: `spring.batch.initialize-schema: always`

**Location**: `application.yml` line 5

**Risk**: Setting `initialize-schema: always` causes Spring Batch to attempt DDL CREATE/ALTER operations against the database on every application startup. In production with a SQL Server database, this can:
- Slow startup
- Fail if the application database user lacks DDL permissions (potentially causing startup failure)
- Potentially modify schema unexpectedly if Spring Batch version changes

**Remediation**: Set to `never` in production. Manage Spring Batch schema migrations via Flyway or Liquibase. Priority: **MEDIUM**.

---

### VULN-007 — MEDIUM: Recursive Retry Without Circuit Breaker in `IEFTServiceImpl`

**Location**: `IEFTServiceImpl.java` lines 32–36

```java
if ("404".equals(e.getErrorCode()) && e.getErrorDescription().contains("Could not find Remitter")) {
    isSuccessful = registerRemitter(memberID, "", programID);
    isSuccessful = registerBeneficiary(deviceID, memberID, programID);  // Recursive call
} else if (Integer.parseInt(e.getErrorCode()) >= 500) {
    isSuccessful = registerBeneficiary(deviceID, memberID, programID);  // Recursive call
}
```

**Risk**: The `registerBeneficiary()` method calls itself recursively on HTTP 500 errors. If the CBTS API returns persistent 500 errors, this will recurse until a StackOverflowError. There is no depth limit, no exponential backoff, and no circuit breaker. In production, this could cause thread exhaustion in the Spring Batch job.

**Remediation**: Replace recursion with a loop with a maximum retry count and exponential backoff. Use Spring Retry or Resilience4j. Priority: **MEDIUM**.

---

## 3. Technical Debt Summary

| Debt Item | Severity | Effort |
|---|---|---|
| Hardcoded CBTS credentials | CRITICAL | LOW (to remove) + credential rotation effort |
| Spring Boot 2.3.4 (EOL) | HIGH | HIGH — Spring Batch 5 migration |
| Java 8 | HIGH | MEDIUM — dependency on SB 3.x upgrade |
| Wirecard CBTS endpoint | HIGH | LOW — URL update + endpoint verification |
| Tests never run in CI | HIGH | LOW — remove flag + fix tests |
| `initialize-schema: always` | MEDIUM | LOW — config change |
| Recursive retry without circuit breaker | MEDIUM | MEDIUM — add retry logic |
| Wirecard Nexus dependency | HIGH | MEDIUM — migrate to Azure Artifacts |
| Dual build system (Maven + Gradle) | LOW | LOW — remove Gradle build files |

---

## 4. Remediation Priority Matrix

| Priority | Action | Owner |
|---|---|---|
| P1 — IMMEDIATE | Rotate CBTS credentials with Cambridge Global Payments | Security + Ops |
| P1 — IMMEDIATE | Remove credentials from `application.yml` | Dev |
| P1 — Sprint 1 | Verify Cambridge CBTS endpoints are valid | Dev + Partner Management |
| P1 — Sprint 1 | Enable integration tests in CI | Dev |
| P2 — Sprint 2 | Set `spring.batch.initialize-schema: never`; add Flyway | Dev |
| P2 — Sprint 2 | Add retry/circuit breaker to `IEFTServiceImpl` | Dev |
| P3 — Q3 | Java 8 → Java 17 upgrade | Dev |
| P3 — Q3 | Spring Boot 2.3.4 → 3.x + Spring Batch 5 migration | Dev |
| P4 — Roadmap | Migrate Nexus to Azure Artifacts | DevOps |
| P4 — Roadmap | Containerize batch jobs for Azure Container Jobs | Platform Eng |
