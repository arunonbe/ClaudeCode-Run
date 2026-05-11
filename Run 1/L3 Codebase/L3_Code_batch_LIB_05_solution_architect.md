# batch_LIB — Solution Architect View

## Technical Architecture

batch_LIB is a monolithic Spring Batch 2.1.9 fat JAR library. It follows the standard Spring Batch reader-processor-writer (RPW) pattern with XML-driven job definitions. The architectural layers are:

```
scripts/ (Active Batch XML + .bat + .vbs + .pl)  [Orchestration & File Pre-processing]
    |
    v
CommandLineJobRunner (main entry point — shaded JAR)
    |
    v
Spring Application Context (loaded from XML files per job)
    |
    +-- common/: SpringBatchCommon.xml, data-source-context.xml, propertyPlaceHolder.xml
    +-- job/: per-job Step/Job XML definitions
    +-- context/: per-process service/helper bean definitions
    |
    v
Job Layer (Spring Batch Job / Step / Partitioner)
    |
    +-- src/main/java/com/citi/prepaid/core/batch/domain/       [Business Logic]
    |       per-process packages: processor/, writer/, helpers/, partitioner/
    |
    +-- src/main/java/com/citi/prepaid/core/batch/dao/          [Data Access]
    |       RowMappers, StoredProcedure subclasses, JdbcTemplate callers
    |
    +-- src/main/java/com/citi/prepaid/core/batch/dto/          [DTOs]
    |
    +-- src/main/java/com/citi/prepaid/core/batch/common/       [Constants, Exit Code Mappers]
    |
    +-- src/main/java/com/citi/prepaid/core/batch/service/      [Service interfaces]
    |
    +-- src/main/java/com/citi/prepaid/core/batch/exception/    [CoreBatchException, ValidationException]
```

**Package naming artefact**: The package root is `com.citi.prepaid.core.batch` — a historical Citi Prepaid branding. Group ID is `com.ecount.service.core`.

**Parallelism model**: Multiple jobs use `SimpleAsyncTaskExecutor` (unbounded thread creation — no thread pool limit enforced in the XML configs reviewed) with Spring Batch `Partitioner` for data segmentation. Grid size is property-driven (e.g., `${autoClaim.grid_size}`).

## API Surface

batch_LIB exposes **no inbound API**. It is purely outbound-calling. The library is invoked exclusively via `CommandLineJobRunner` with command-line arguments specifying the Spring context XML files and job name.

**Outbound interfaces:**

| Interface | Protocol | Target | Classes |
|---|---|---|---|
| ecount Core | XML-RPC (HTTP) | `ECountCore.eTransfer` service on port 40000 | `CoreLiteXMLRPCClient`, `MemberXMLRPCClient`, `TransferXMLRPCClient` |
| Payment Service | Library (in-process) | `PaymentServiceLibraryImpl` | `AutoClaimProcessHelper` |
| cbase Device/Member Manager | Library (in-process, via XML-RPC) | `IDeviceManager`, `IMemberManager`, `ITransferManager` | `CardCreateService`, `BalanceSyncProcessor`, `PayPalChoiceRecurringDetailsProcessor` |
| Claimable Choice API | REST HTTP POST | `/redeemDefaultExpiredClaimCode` | `ClaimableChoiceAPIClient` |
| PayPal Shared Service | REST HTTP POST | External PayPal payout service | `SharedServiceHelper` |
| Microsoft Exchange EWS | HTTPS/EWS | `${ms.exchange.service.url}` (Office 365) | `MSExchangeEmailReaderDelegateImpl` |
| IBM WebSphere MQ | JMS | FP Account Status queue | `RequestSendMessageCreator` |
| SQL Server databases | JDBC | 7 logical databases via Director | All DAO classes |
| Affiliate Service | Library (in-process) | `AffiliateServiceImpl.getMetadata()` | `PayPalChoiceRecurringDetailsProcessor` |
| Notification Manager | Library (in-process) | `INotificationManager.deliver()` | `PayPalChoiceRecurringDetailsProcessor`, `VenmoChoiceRecurringDetailsProcessor` |

## Security Posture

### Authentication & Authorization
- **Database access**: Credential-less from the application code perspective — credentials are held in the Director service and injected at runtime via `DirectorConfiguredDBCPdatasourceCreator`.
- **Exchange EWS**: Modern OAuth2 MSAL4J `ConfidentialClientApplication` with `ClientCredentialFactory.createFromSecret(clientSecret)`. Client secret is injected from a properties file at `D:\c-base\config\batch\returnedemailbatch\ReturnedEmailBatch.properties`. This is a secret stored on disk — not in Strongbox.
- **Exchange legacy credentials**: `constructCredentials()` in `MSExchangeEmailReaderDelegateImpl` (line 484) still parses `emailAccountUserId` and `emailAccountPassword` strings — these appear to be legacy credential fields retained alongside the OAuth flow.
- **PayPal Shared Service**: Authentication mechanism not visible in the reviewed code — handled inside `SharedServiceHelper` (not read).
- **No mutual TLS (mTLS)**: No evidence of client certificate authentication for any outbound HTTP call.

### Input Validation
- `PushtodebitTransactionItemProcessor.isRecordValid()` validates date formats, numeric ranges, and string lengths (≤256) — the most thorough validation in the codebase.
- `PayPalChoiceRecurringDetailsProcessor.getAccountDetails()` validates affiliate ID is non-negative and exactly 8 digits (line 260–268).
- `ClaimableChoiceAPIClient.redeemDefaultExpiredClaimCode()` throws on any non-200 HTTP response code — no retry logic.
- Most other processors have minimal or no explicit input validation before calling downstream services.

### Secret Management
- **Client secret on disk**: `clientSecret` for MSAL4J (`MSExchangeEmailReaderDelegateImpl`) is a Spring-injected string from a plaintext properties file.
- **Email passwords on disk**: `emailAccountPassword` is a Spring-injected string from a plaintext properties file.
- **Strongbox dependency exists** (`strongboxImpl:1.0.2`) but explicit Strongbox API calls are not visible in the reviewed code paths.

### Transport Security
- ecount Core XML-RPC uses `Director`-resolved HTTP — TLS cannot be confirmed.
- `ClaimableChoiceAPIClient` uses `org.javalite.http.Http.post()` — URL scheme (`http` vs `https`) is determined by the `uriBase` property configured at runtime.
- Exchange EWS uses `new URI(msExchangeServiceURL)` — the scheme depends on the configured URL.

### Known Vulnerable Dependencies (CVE risk)
| Library | Version | Risk |
|---|---|---|
| `com.thoughtworks.xstream:xstream:1.3.1` | 1.3.1 (2009) | Multiple critical RCE CVEs (CVE-2021-29505, CVE-2021-39139 etc.) |
| `log4j:log4j:1.2.15` | 1.2.15 | CVE-2019-17571 (deserialization), end-of-life |
| `org.springframework:spring-*:2.5.6` | 2.5.6 | Multiple CVEs including Spring4Shell predecessors |
| `org.springframework.batch:2.1.9.RELEASE` | 2.1.9 | End of life; multiple known vulnerabilities |
| `aspectj:aspectjweaver:1.5.3` | 1.5.3 | Very old; patched versions exist |
| `commons-dbcp:commons-dbcp:1.2.2` | 1.2.2 | End-of-life |
| `commons-pool:commons-pool:1.4` | 1.4 | End-of-life |
| `org.springframework:spring-support:2.0.6` | 2.0.6 | Very old Spring module |

## Technical Debt

### Critical (Security/Compliance)
1. **`cvv2` field in `PushtodebitTransactionVo`** (line 33): If persisted, violates PCI DSS Req. 3.2.1 (post-authorization CVV2 storage prohibition). Path: `src/main/java/com/citi/prepaid/core/batch/dto/pushtodebittransactionimport/PushtodebitTransactionVo.java`.
2. **XStream 1.3.1**: Multiple critical RCE CVEs affecting XML deserialization. Used in `pom.xml` line 279.
3. **Log4j 1.x**: CVE-2019-17571 deserialization vulnerability. `pom.xml` line 290.
4. **Plaintext secrets in properties files**: `clientSecret` and `emailAccountPassword` stored in `D:\c-base\config\...` files.
5. **All CI tests skipped**: `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"` — zero test coverage enforced in CI.

### High (Correctness / Reliability)
6. **Silent failure in `AutoClaimProcessor.process()`**: The catch block at line 43 catches `Exception` and logs it but returns the unchanged `autoClaimTransactions` object. The writer then processes this record as normal, potentially persisting an incomplete state. The status should be set to FAILED before returning.
7. **`Thread.sleep(5000)` in item processor thread** (`PayPalChoiceRecurringDetailsProcessor`, line 707): Blocks a batch worker thread. With 100+ items requiring refund, this adds 500+ seconds of latency and risks Active Batch timeout.
8. **`SimpleAsyncTaskExecutor` without pool limit**: Partitioned jobs use `SimpleAsyncTaskExecutor` which spawns unbounded threads. Under high load or misconfigured grid size, this can exhaust heap or OS thread limits. Example: `autoClaimProcessBatchjob.xml`, line 88.
9. **In-memory deduplication set in `PushtodebitTransactionItemProcessor`**: `processedTransactions` (line 25) is an instance-level `HashSet`. Not restart-safe — restarted jobs lose dedup state. Also not thread-safe if the step were ever partitioned.
10. **`HashMap` as raw type throughout**: Multiple processors use `Map context = new Hashtable()` (raw type, no generics) — `AutoClaimProcessHelper` line 89. This bypasses compile-time type safety.

### Medium (Maintainability / Operability)
11. **Duplicate DAO packages with typos**: `paymenthubremindernotification` vs `paymenthubremimdernotification` (missing 'n' in "reminder") — two separate packages exist with overlapping row mapper classes (`PaymentHubReminderNotificationMemberDetailsRowMapper` duplicated in both). `paymentselectionremimdernotification` vs `paymentselectionremindernotification` similarly.
12. **Hard-coded `"Disney Global Deposit"` description**: `AutoClaimProcessHelper.populateCertificateInput()`, line 202. Any non-Disney program using this batch receives an incorrect transaction description.
13. **Dead commented-out code**: `CardCreateService` has large commented-out blocks (lines 252–259) and `AppProfileUserPaymentSelection` references. The refactored approach calls `userProfileDetails.fetchUserProfileOptionName()` but the old approach is preserved as comments.
14. **XML Spring context without component scanning**: All beans are manually wired via 50+ XML files. No `@Component` / `@Autowired`. Any rename or refactor requires manual XML updates across multiple files.
15. **`allowStartIfComplete="true"` on partitioned steps** (`autoClaimProcessBatchjob.xml`, line 79): Allows a completed step to re-run, which combined with the infinite-loop guard logic may produce unpredictable repeat processing.

### Low (Code Quality)
16. **ThreadLocal logging antipattern**: `ThreadLocal<Log>` is used in `AutoClaimProcessor` and others — unusual, since `Log` instances from Apache Commons Logging are already thread-safe. Adds unnecessary allocation overhead.
17. **`DynamicJobParameters` as incrementer**: Custom `DynamicJobParameters` appends a timestamp to ensure unique job instances, which is standard, but there is no idempotency key for re-runs.
18. **Missing `@Override` on `process()` methods**: Several `ItemProcessor` implementations do not use `@Override` annotation, reducing IDE and compiler error detection.

## Gen-3 Migration Requirements

The following work is required before any component of batch_LIB can be re-platformed to Gen-3:

1. **Framework upgrade**: Spring Batch 5.x (requires Spring 6, Java 17+). All XML context files must be rewritten to annotation/Java-config based contexts. This is a full rewrite of the wiring layer.

2. **Replace Director with cloud-native secrets/config**: All `DirectorConfiguredDBCPdatasourceCreator` usage must be replaced with Spring Boot `DataSource` auto-configuration backed by a secrets manager (AWS Secrets Manager or Azure Key Vault via Strongbox).

3. **Replace IBM MQ with cloud-native broker**: Account status sync JMS (`FPAccountStatQueue.xml`) must be rearchitected for the target message broker.

4. **Containerise**: Create Dockerfiles per logical job group (or a single multi-job container). Replace `D:\c-base\config\...` paths with environment variable injection or mounted secrets.

5. **Replace Active Batch with cloud-native scheduler**: Define CronJob manifests (Kubernetes) or equivalent for each Active Batch job definition.

6. **Replace VBScript/Perl file processing**: Re-implement file download/staging as cloud storage event-driven consumers or managed ETL pipelines.

7. **CVV2 remediation**: Either confirm `cvv2` field is never written to persistent storage, or remove it from `PushtodebitTransactionVo` entirely before migration.

8. **Replace ecount Core XML-RPC calls with Gen-3 service APIs**: All `CoreLiteXMLRPCClient`, `DeviceManagerImpl`, `IMemberManager`, `ITransferManager`, `PaymentServiceLibraryImpl` calls must be replaced with Gen-3 REST/gRPC equivalents.

9. **Replace Payment Service Library**: `AutoClaimProcessHelper.processTransaction()` calls `PaymentServiceLibraryImpl.createCertificate()` — this API must be exposed as a Gen-3 service endpoint.

10. **Secrets migration**: Move `clientSecret` and `emailAccountPassword` from properties files into Strongbox or equivalent secrets management.

11. **Enable CI testing**: Remove `maven.test.skip=true` from GitLab CI and fix/expand the test suite (currently 9 test classes, mostly row mapper unit tests). Add integration tests with an embedded H2/MSSQL container.

## Code-Level Risks

| Risk | Location | Severity |
|---|---|---|
| CVV2 possibly persisted post-auth | `PushtodebitTransactionVo.java:33` | Critical — PCI DSS |
| XStream RCE vulnerability | `pom.xml:279`, transitive usage | Critical |
| Log4j 1.x deserialization | `pom.xml:290` | High |
| Silent exception swallow | `AutoClaimProcessor.java:43` | High |
| `Thread.sleep` in processor | `PayPalChoiceRecurringDetailsProcessor.java:707` | High |
| Unbounded thread spawning | `autoClaimProcessBatchjob.xml:88`, other job XMLs | High |
| Plaintext secret injection | `MSExchangeEmailReaderDelegateImpl.java:77,80` | High |
| Non-restart-safe dedup | `PushtodebitTransactionItemProcessor.java:25` | Medium |
| Duplicate/typo DAO packages | `dao/paymenthubremimdernotification/` vs `dao/paymenthubremindernotification/` | Medium |
| Hard-coded Disney description | `AutoClaimProcessHelper.java:202` | Medium |
| Raw type `Map`/`Hashtable` usage | `AutoClaimProcessHelper.java:89`, `ClaimExpirationReverseHelper.java:72` | Low |
| Java 5 source target | `pom.xml:405-408` | Low (build risk) |
| Tests always skipped in CI | `.gitlab-ci.yml:5-8` | High (quality gate absent) |
