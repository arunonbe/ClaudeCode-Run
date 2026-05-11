# card-enrollment-maricopa_LIB — Solution Architect View

## Technical Architecture

This is a **standalone Java batch application** packaged as a JAR, structured as a single Maven module with four production classes and one Spring XML configuration file. There are no web endpoints, no message consumers, and no service interfaces.

### Class Hierarchy

```
EnrollmentProcessMain                          (entry point — static main)
  └─ loads Spring ApplicationContext (ClassPathXmlApplicationContext)
       ├─ EnrollmentHelper                     (service/orchestrator bean)
       │    ├─ IAccountIdDAO ─── AccountIdDAOImpl   (DAO interface + impl)
       │    │                         └─ GetCardIdsList (StoredProcedure)
       │    │                                └─ AccountList (inner RowMapper)
       │    └─ IDeviceManager ─── DeviceManagerImpl (external cbase lib)
       └─ EcountCoreDataSource               (DBCP via Director factory)
```

### Package Structure

```
com.citi.process
├── enrollment
│   ├── EnrollmentProcessMain.java    — main entry point, Spring context loader, batch loop
│   └── EnrollmentHelper.java         — orchestrator: fetches accounts, calls issuePlastic
└── dao
    ├── IAccountIdDAO.java             — DAO interface: getAccountIds() → Collection<String>
    ├── AccountIdDAOImpl.java          — delegates to GetCardIdsList stored proc wrapper
    └── proc
        └── GetCardIdsList.java        — Spring StoredProcedure: Get_MaricopaDDA_With_No_Card
```

Resources:
```
src/main/resources/com/citi/process/cardenrollment/appContext.xml   — Spring XML bean definitions
```

## API Surface

This library exposes **no external API**. It has:
- One public entry point: `EnrollmentProcessMain.main(String[])` — invoked directly by JVM.
- One public service method: `EnrollmentHelper.issuePlastic(String accountNumber)` — public but only called internally.
- One public DAO method: `IAccountIdDAO.getAccountIds()` — returns `Collection<String>`.

The only outbound "API call" made by this library is to `IDeviceManager.issuePlastic(Account, String, Funds, boolean)` from the `com.cbase.business.core` library — this is an in-process Java API call, not a network call from the perspective of this library.

There is no REST API, SOAP service, gRPC interface, or message queue consumer/publisher.

## Security Posture

### Critical Issues

1. **Plaintext credentials in version-controlled `settings.xml`** (`.mvn/wrapper/settings.xml` lines 33–50):
   - `wirecard-mavenproxy-repository`: `acmng` / `acmng`
   - `nexus-qa`: `deployment` / `dwil15?`
   - `ecount.release` and `ecount.snapshot`: `deployment` / `d3v0nly`
   These credentials are committed to git history and must be considered compromised. Immediate rotation and removal from source control is required. Use `git filter-branch` or BFG Repo Cleaner to purge history.

2. **Account identifiers logged in clear text** (`EnrollmentProcessMain.java` lines 49, 54, 57):
   ```java
   logger.info("Processing Account " + accountId);
   logger.info("Issue Plastic Sucessfully for Account " + accountId);
   logger.error("Error Issuing Plastic for Account Id " + accountId);
   ```
   If `accountId` maps to or is derivable from a PAN or card device ID, this is a PCI DSS Requirement 3.3.1 violation. Masking is required.

3. **No authentication or authorization**: The batch job runs with whatever OS-level permissions it is granted. There is no application-layer authentication before accessing the database or the card issuance API.

4. **Supply chain risk**: Artifacts are pulled from `d-na-stk01.nam.wirecard.sys` (legacy Wirecard Nexus). If this host is compromised or if an attacker can serve malicious artifacts from it, the build is poisoned. Additionally, `ecount.release` and `ecount.snapshot` Nexus credentials are in plaintext — an attacker could use these to inject artifacts.

### Moderate Issues

5. **Spring 2.5.4 (EOL 2008)**: Known CVEs exist. No security patches will be issued. The framework is loaded into the runtime process.
6. **Log4j 1.x (EOL)**: Apache Log4j 1.2.x has known deserialization vulnerabilities (e.g., CVE-2019-17571 — SocketServer deserialization). While this application likely does not use the vulnerable components directly, running EOL logging infrastructure is a PCI DSS Requirement 6.3.3 concern.
7. **No input validation**: The `accountId` string from the stored procedure is passed directly to the `Account` constructor and the `issuePlastic` API without any null check, length check, or format validation.
8. **Stack trace logged via array toString()** (`EnrollmentProcessMain.java` line 59): `logger.error(e.getStackTrace())` logs the `StackTraceElement[]` array reference, not the actual stack trace. Actual error context is lost, hampering incident investigation.

### Low / Informational

9. **No TLS enforcement visible**: JDBC connection to eCount Core is DataSource-managed externally. SSL/TLS configuration is not visible or enforced in this codebase.
10. **`ignoreUnresolvablePlaceholders = true`** (`appContext.xml` line 12): Silently ignores missing property keys, which could mask misconfiguration errors at startup.

## Technical Debt

| Item | Location | Severity | Description |
|---|---|---|---|
| `//TBD` unimplemented logic | `EnrollmentHelper.java` lines 68–71 | High | The `issuePlastic` method body contains commented pseudo-code and a `//TBD` marker. The actual implementation wraps around the TBD with a live API call but no validation of the approach. |
| `DEFAULT_RETRY_COUNT = 3` declared but never used | `EnrollmentHelper.java` line 37 | High | Retry resilience was planned but never implemented. A constant with no callers is dead code. |
| `AccountDefinitionECard` imported but not used | `EnrollmentHelper.java` line 13 | Low | Unused import — either a vestige of an earlier implementation or planned future code. |
| `logger` field in `EnrollmentHelper` never called | `EnrollmentHelper.java` line 36 | Low | A `Log` instance is created via `LogFactory` but never invoked in any method. |
| Double semicolon typo | `AccountIdDAOImpl.java` line 10 | Low | `private GetCardIdsList getCardIdsList;;` — double semicolon; harmless but indicative of low code quality standards. |
| `e.getStackTrace()` instead of `e` passed to logger | `EnrollmentProcessMain.java` lines 59, 70 | Medium | `logger.error(e.getStackTrace())` logs the array's `toString()` (e.g., `[Ljava.lang.StackTraceElement;@...`), not the actual stack trace. Should be `logger.error("...", e)`. |
| Typo in log message: "Sucessfully" | `EnrollmentProcessMain.java` line 54 | Low | Misspelling in log message. |
| Typo in method name: `loadApplicationConext` | `EnrollmentProcessMain.java` line 78 | Low | Misspelling: `Conext` instead of `Context`. |
| Typo in code comment: "MaryCopa" | `EnrollmentHelper.java` line 74 | Low | Comment says "No fee for MaryCopa" — inconsistent with "Maricopa" program name. |
| Spring XML DTD (deprecated) | `appContext.xml` line 2 | High | Uses Spring's legacy DTD-based bean definition format, not even the XSD-based format. Incompatible with any modern Spring version. |
| `@SuppressWarnings("unchecked")` raw Map usage | `GetCardIdsList.java` lines 27–31 | Medium | Raw `Map` usage suppressed with annotation. Should use generics. |
| Spring JDBC 1.2.6 | `pom.xml` line 33 | High | spring-jdbc 1.2.6 is from approximately 2006 — predates even Spring 2.x. Severe EOL. |
| JUnit 3.8.1 with no tests | `pom.xml` lines 53–57 | Medium | Test dependency declared for a 2002-era framework; no tests exist. |
| `continue` at end of for loop body | `EnrollmentProcessMain.java` line 61 | Low | Redundant `continue` statement at the end of the loop body — no-op but adds confusion. |

## Gen-3 Migration Requirements

To migrate this batch to a Gen-3 cloud-native pattern, the following are required:

1. **Replace stored procedure with a service/query layer**: The `Get_MaricopaDDA_With_No_Card` stored procedure logic must be ported to a Gen-3 data access layer (e.g., JPA repository or REST query on a Gen-3 account service), preserving the Maricopa DDA + no-card eligibility logic.

2. **Replace `IDeviceManager.issuePlastic()` with Gen-3 card issuance API**: The `com.cbase.business.core.impl.DeviceManagerImpl` is a Gen-1 in-process API. Gen-3 equivalent would be a REST call to a card lifecycle service or an event published to a card-fulfillment topic (e.g., Kafka `card.issuance.requested` event).

3. **Externalize all configuration to a secrets manager**: Replace the `D:\c-base\` flat file properties with environment variables or a secrets store (Vault, AWS Secrets Manager, or equivalent). Remove all credentials from `settings.xml`.

4. **Containerize**: Replace Windows-path-dependent deployment with a Docker container using environment variable injection. Eliminate `D:\c-base\` path dependency.

5. **Add idempotency and audit trail**: Implement a post-issuance status write-back (or event emission) to prevent double-processing and satisfy Reg E audit requirements.

6. **Implement retry with backoff**: Replace the unused `DEFAULT_RETRY_COUNT` constant with actual resilience logic (e.g., Spring Retry, Resilience4j).

7. **Replace Log4j 1.x with SLF4J + Logback/Log4j2**: And remove hardcoded log config path. Use structured (JSON) logging for observability.

8. **Mask sensitive identifiers in logs**: Before any Gen-3 deployment, validate whether `accountId` is PAN-adjacent and apply masking if required.

9. **Add test coverage**: Write unit tests for `EnrollmentHelper` and `AccountIdDAOImpl` with mocked dependencies. Minimum: test the null-list branch, the successful issuance path, and the per-account exception handling path.

10. **Upgrade to modern Spring (Spring Boot 3.x)**: Replace XML bean definitions with `@SpringBootApplication`, `@Component`, and `@Value` annotations. Replace `ClassPathXmlApplicationContext` with Spring Boot's auto-configuration.

## Code-Level Risks

| Risk | Location | Description |
|---|---|---|
| Account ID logged in plain text | `EnrollmentProcessMain.java` lines 49, 54, 57 | Potential PCI DSS violation if `accountId` is PAN-adjacent |
| Hardcoded `D:\c-base\` paths will throw at startup on any non-Windows host | `EnrollmentProcessMain.java` line 14, `appContext.xml` lines 8–9 | `FileNotFoundException` or Spring context load failure on Linux/macOS/containers |
| `ignoreUnresolvablePlaceholders = true` silences startup misconfiguration | `appContext.xml` line 12 | Missing `${director.address}`, `${ecount.agent}`, or `${ecountcore.database}` will not cause a startup error — the beans will be created with null/literal-string values, causing runtime failures in the Director factory or device manager |
| `execute(new HashMap())` with raw types | `GetCardIdsList.java` line 30 | Unchecked cast on result map; null return from `out.get("transactions")` would be cast to `Collection<String>` without error, returning null silently |
| No null check on `accountId` before `issuePlastic` | `EnrollmentHelper.java` line 76 | `new Account(null)` — behavior depends on `Account` constructor; may throw NullPointerException or silently issue a card with a null account reference |
| `e.getStackTrace()` logged as object reference | `EnrollmentProcessMain.java` lines 59, 70 | Error context lost in logs; operators cannot diagnose failures from log output alone |
| `fee.setAmount(0)` hardcoded with no config | `EnrollmentHelper.java` line 74 | Any future fee requirement for Maricopa requires a code change and re-deployment |
| Spring context not closed at JVM exit | `EnrollmentProcessMain.java` — `finally` block is empty (line 74) | DBCP connection pool is not properly shut down; may leave dangling DB connections on the server |
