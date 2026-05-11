# ach-withdrawal-initiator_LIB — Solution Architect View

## Technical Architecture

The component is a **multi-threaded Java batch process** structured around a three-layer design:

```
ACHWithdrawalProcessMain          (entry point, fixed thread pool, sequential type ordering)
        │
        └── Controller (Runnable, one per RequestType)
                │
                └── ProcessorFactory → IterativeProcess | DefaultProcess   (IProcess)
                        │
                        └── Load / IterativeProcess.load()  (DB extract)
                                │
                                └── RequestProcessorThread (Runnable, worker)
                                        │
                                        ├── processAutoACH()
                                        ├── processFutureEffectiveACH()
                                        ├── processStopPaymentACH()
                                        ├── processSimpleTransferACH()
                                        ├── processAutoClaim()
                                        ├── processAutoClaimApi()
                                        ├── processPushToDebit()
                                        ├── processPushToDebitApi()
                                        └── processAutoACHApi()
```

**Spring IoC**: Single `ClassPathXmlApplicationContext` instantiated lazily in `ContextHelper.getCtx()` (singleton, not thread-safe at initialization — race condition possible if `getCtx()` is called concurrently before `ctx` is set, since the null check and assignment are not synchronized).

**Thread model**:
- Outer pool: `Executors.newFixedThreadPool(Process.MainThreads)` — default 2 threads. One `Controller` per request type is submitted to this pool sequentially (with `while(!areDone())` polling between types).
- Inner pool: Per-`Controller`, `Executors.newFixedThreadPool(Process.MaxThreads.<TYPE>)` — 3–5 threads per type. Worker threads (`RequestProcessorThread`) receive batches of `threadLoad` size (default 1 per type).
- This means at any time there are at most `MainThreads` types processing concurrently, each with its own sub-pool.

**Processing modes**:
- `IterativeProcess` (default, `configuration.properties: Processor.Process = IterativeProcess`): Polls in a loop until the DB returns no records. Each iteration fetches `Process.RecordsRetrieve.<TYPE>` records (e.g., 5 for AUTO_ACH). Supports time-windowed queries with `Timestamp currentTime` and failure-day lookback.
- `DefaultProcess`: Single bulk load of all records, then processes them. The `loadAutoClaimRequests()` method in `Load.java` is **dead code** (returns `null` after a debug `System.out.println`). This mode is not safe for AUTO_CLAIM.

## API Surface

This component **has no inbound API**. Its only interfaces are:

**Outbound — Database (SQL Server stored procedures)**:
| Stored Procedure | DataSource | Direction |
|-----------------|------------|-----------|
| `dbo.ach_transfer_initiate_extract` | JobsvcDataSource | READ |
| `dbo.ach_transfer_extract_unprocessed_records` | JobsvcDataSource | READ |
| `dbo.update_ach_transfer_detail_status` | JobsvcDataSource | WRITE |
| `dbo.app_event_service_transfer_service` | EcountCoreDataSource | READ |
| `dbo.app_event_service_transfer_create` | EcountCoreDataSource | WRITE |
| `dbo.app_event_service_transfer_inquiry` | EcountCoreDataSource | READ |
| `dbo.app_event_service_transfer_update` | EcountCoreDataSource | WRITE |
| `dbo.app_event_service_transfer_cancel` | EcountCoreDataSource | WRITE |
| `dbo.app_user_autoach_inquiry` | EcountCoreDataSource | READ |
| `dbo.app_user_recurring_push_to_debit_inquiry` | EcountCoreDataSource | READ |
| `dbo.ach_transfer_initiate_api_extract` | EcountCoreDataSource | READ |
| `dbo.update_ach_transfer_detail_api_status` | EcountCoreDataSource | WRITE |

**Outbound — Platform RPC (via ecount-system library)**:
- `DeviceManagerImpl.getDefaultACH(member)` — retrieves ACH account definition
- `DeviceManagerImpl.getDefaultEcard(member)` — retrieves eCard device
- `DeviceManagerImpl.balanceRefresh(account)` — FDR balance sync (feature-flagged)
- `MemberManagerImpl.InquiryExtended(member)` — full member profile including PII
- `TransferManagerImpl.inquiry(transferId, type)` — transfer state inquiry
- `TransferManagerImpl.commit(transferDefinition)` — commit a transfer
- `TransferManagerImpl.cancel(transferDefinition)` — cancel a transfer
- `transferFunds()` — initiate a new transfer (utility method in `RequestProcessorThread`)
- `simpleFeeInquiry()` — calculate applicable fee

**Outbound — External HTTP API**:
- `POST ${pushpay.url}` — Tabapay Push-to-Debit API. JSON body includes card details, recipient PII, amount. OAuth2 Bearer token from MSAL4J.

**Outbound — Internal Services**:
- `NotificationManagerImpl.deliver()` — email notification
- `ServiceAdapter(new ClassRetrieve(), requestContext)` — profile service RPC
- `AffiliateServiceImpl.getAffiliate(affiliateId)` — affiliate metadata
- `AffiliateServiceImpl.getMetadata(appId, affiliateId)` — contact info for email
- `ICommentService.insertComment()` — comment audit trail (IDD auto-claim)

**Command-line interface**:
- `java -jar ACHWithdrawalInitiator-jar-with-dependencies.jar` — ACH/Claim mode
- `java -jar ACHWithdrawalInitiator-jar-with-dependencies.jar PTC` — Push-to-Card mode

## Security Posture

### Authentication & Authorization
- **Push-to-Debit API**: OAuth2 client credentials flow via MSAL4J (`ConfidentialClientApplication`). Silent token acquisition with fallback to full credential flow. Token is used as Bearer token in HTTP header.
- **Database access**: Via Director service credential injection — credentials not embedded in the JAR.
- **No authentication for inbound interface**: The process has no inbound interface, so no auth is needed.

### Identified Security Issues

1. **PII logged to disk** (`SharedServiceHelper.java`, lines 104, 186): `logger.info("Pushpay: -  Post Data: " + jsonBody.toString() + "\n Response Code : " + responseCode)` — logs full JSON request body including `firstName`, `lastName`, `address`, `postalCode`, `referenceId`, and card details to `ach_processor.log`. This is a PCI DSS violation.

2. **OAuth2 client secret in plaintext properties file**: `pushpay.ms.client.secret` is read from a filesystem properties file without any key management system. If the file is readable by non-privileged OS accounts, the secret is compromised.

3. **No HttpURLConnection timeout**: `SharedServiceHelper.sharedServicePushFundCall()` creates an `HttpURLConnection` without setting `setConnectTimeout()` or `setReadTimeout()`. Calls to Tabapay can hang indefinitely, blocking the thread and eventually the thread pool.

4. **ContextHelper singleton race condition**: `ContextHelper.getCtx()` performs a non-synchronized null check and assignment of the `ApplicationContext`:
   ```java
   if(null == ctx){
       ctx = new ClassPathXmlApplicationContext(...);  // not synchronized
   }
   ```
   If two threads call `getCtx()` concurrently before initialization, two Spring contexts could be created, leading to duplicate datasource connections and bean instances. While Spring initialization is heavyweight and unlikely to race in practice, it is not thread-safe by design.

5. **`new Integer()` deprecation** (minor): Multiple uses of deprecated `new Integer(...)` constructor throughout DAO classes — not a security issue but indicates Java version age.

6. **Log4j 1.2.17**: This version is end-of-life and has known vulnerabilities (separate from Log4Shell which affects Log4j 2.x). Upgrade to Log4j 2.x or SLF4J+Logback is required.

7. **jTDS 1.2**: End-of-life JDBC driver. Contains known vulnerabilities. Should be replaced with `mssql-jdbc`.

8. **commons-codec:1.7**: Old version; while not critical, should be updated.

## Technical Debt

### Critical
1. **Dead code — `Load.java:loadAutoClaimRequests()`** (lines 151–168): Returns `null` after `System.out.println("Testing Auto Claim")`. If `DefaultProcess` mode is activated, all AUTO_CLAIM requests are dropped silently.
2. **PII/card data logged** (`SharedServiceHelper` lines 104, 186): Immediate PCI DSS concern.
3. **No `HttpURLConnection` timeout**: Risk of indefinite thread blocking on Tabapay API calls.
4. **Non-thread-safe `ContextHelper.getCtx()`**: Race condition on first call from multiple threads.

### High
5. **Hard-coded bank name** (`SharedServiceHelper` line 51, `TODO` comment): `bankName` is always `ACHConstants.SUNRISE_BANK` — multi-bank routing is broken for MB/Fifth Third programs.
6. **SNAPSHOT dependencies** (`autoclaimsplit-common:2.0.2-SNAPSHOT`, `autoclaimsplit-svc:2.0.2-SNAPSHOT`): Non-reproducible builds.
7. **Tests skipped in CI** (`.gitlab-ci.yml`): `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"` — automated quality gate is disabled.
8. **Spring 2.0.3**: Framework EOL since 2013, no security patches available.
9. **Log4j 1.2.17**: EOL; known vulnerabilities.
10. **jTDS 1.2**: EOL JDBC driver.

### Medium
11. **`e.printStackTrace()` calls** throughout `RequestProcessorThread` and `IterativeProcess`: These write to `stderr` outside the log framework, losing context and thread information.
12. **Commented-out code blocks** in `AutoACHRequestExtract.java` (old `RowCallbackHandler` implementation, lines 127–185) and in `appContext-ach.xml` (multiple commented datasource/JNDI beans). Dead code bloat.
13. **No connection pool size tuning**: `commons-dbcp` `BasicDataSource` beans are configured with no `maxActive`, `maxIdle`, `minIdle`, or `testOnBorrow` settings (only present in commented-out blocks).
14. **`Configuration` singleton not thread-safe**: `getInstance()` uses a non-synchronized null check, same issue as `ContextHelper`.
15. **`Random` import in `RequestProcessorThread`** (line 14): Non-secure `java.util.Random` imported alongside `java.security.SecureRandom`. Review whether random number generation uses the secure variant throughout.

### Low
16. **`new Integer(code)` / deprecated constructors**: Pervasive use of deprecated `Integer`, `Long` boxed constructors.
17. **`System.out.println`** in `Load.java` line 167: Debug output bypasses logging framework.
18. **README is empty**: `README.md` contains only the repository name — no operational or developer documentation.
19. **`ADDENDA_OFFCARD_RECIPIENT = 131` constant** defined but not verified against NACHA specification in comments.
20. **Unused import `java.util.Random`** alongside `SecureRandom` — security review needed.

## Gen-3 Migration Requirements

To migrate this component to a Gen-3 architecture the following changes are required, in priority order:

### Pre-requisites (must be done before migration starts)
1. **Remediate PII logging**: Remove or mask card/PII data from log statements in `SharedServiceHelper`.
2. **Resolve SNAPSHOT dependencies**: Release `autoclaimsplit` and other SNAPSHOTs to fixed versions.
3. **Fix dead code**: Implement or remove `Load.java:loadAutoClaimRequests()`.
4. **Enable CI tests**: Remove `-Dmaven.test.skip=true` from `.gitlab-ci.yml`.

### Architecture changes for Gen-3
5. **Replace batch polling with event-driven trigger**: Queue ACH jobs via a message broker (e.g., Azure Service Bus, Kafka) rather than DB polling. The stored procedure interface can act as a temporary bridge.
6. **Containerize**: Create Dockerfile, replace hard-coded `d:/c-base/` path with environment variable injection or mounted secrets. Add health endpoint (Spring Actuator or lightweight HTTP).
7. **Replace Director credential injection with secrets manager**: Integrate with Azure Key Vault or AWS Secrets Manager for DB credentials and OAuth2 secrets.
8. **Upgrade Spring**: Migrate to Spring Boot 3.x (requires Java 17+). Replace `appContext-ach.xml` with `@Configuration` classes.
9. **Replace jTDS with mssql-jdbc**: `com.microsoft.sqlserver:mssql-jdbc` is the supported driver.
10. **Replace Log4j 1.x with SLF4J + Logback or Log4j 2.x**: Required for security and structured logging support.
11. **Add HTTP client with timeout**: Replace raw `HttpURLConnection` with Spring WebClient or OkHttp with explicit connect/read timeouts and retry/circuit-breaker (Resilience4j).
12. **Thread-safe context initialization**: Synchronize `ContextHelper.getCtx()` or replace with standard Spring Boot application context lifecycle.
13. **Expose metrics**: Add Micrometer instrumentation for transfer counts, failure rates, processing latency by type.
14. **Replace internal RPC library coupling**: Define REST/gRPC contracts for `TransferManagerImpl`, `MemberManagerImpl`, `DeviceManagerImpl` operations and consume them via HTTP client rather than in-process library.
15. **Add structured audit logging**: Each transfer attempt should emit a structured event (JSON) to a centralized audit store for Reg E and NACHA compliance traceability.

## Code-Level Risks

| Risk | Location | Severity |
|------|----------|----------|
| PII/card data in logs | `SharedServiceHelper.java:104,186` | Critical |
| Dead AUTO_CLAIM code | `Load.java:151-168` | Critical |
| No HTTP timeout on Tabapay | `SharedServiceHelper.java:81-99` | High |
| Non-synchronized Spring context init | `ContextHelper.java:10-20` | High |
| Hard-coded bank name (SUNRISE) | `SharedServiceHelper.java:51` | High |
| SNAPSHOT dependency instability | `pom.xml:168-187` | High |
| Tests skipped in CI | `.gitlab-ci.yml:6-8` | High |
| Log4j 1.2.17 EOL | `pom.xml:79-82` | High |
| jTDS 1.2 EOL | `pom.xml:87-90` | High |
| Non-synchronized Configuration singleton | `Configuration.java:42-47` | Medium |
| `e.printStackTrace()` to stderr | Multiple in `RequestProcessorThread` | Medium |
| Commented-out production code | `AutoACHRequestExtract.java:127-185` | Low |
| `System.out.println` debug trace | `Load.java:167` | Low |
| Empty README | `README.md` | Low |
| Deprecated `new Integer()` constructors | Multiple DAO classes | Low |
