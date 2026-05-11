# citi-direct-file-process_LIB — Solution Architect View

## Technical Architecture

The library is a single-module Maven project producing a self-contained executable JAR. It is a classical Java batch application with the following layers:

```
Entrypoint
  CitiDirectFileProcess.main()         (reports package)
    │
    ├─ Spring XML context bootstrap     (ClassPathXmlApplicationContext)
    │    etlContext.xml → etlContext.properties
    │
    ├─ Configuration resolution
    │    Context bean (common.Context)  → citiDirectFilePath, agent
    │
    ├─ DataSource initialisation
    │    Director HTTP → DirectorConfiguredDBCPdatasourceCreator → DBCP pool
    │    JdbcTemplate wrapping the DBCP DataSource
    │
    ├─ Template loading
    │    CitiDirectAccountFile.loadNewAccountXMLFile()
    │    DOM parser + XSD validation → static Document field
    │
    ├─ Writer initialisation
    │    FixedLengthPrintWriter(BufferedWriter(FileWriter(path)))
    │
    └─ Processing loop
         CitiDirectAccountFile.processNewAccounts(jdbcTemplate)
           JdbcTemplate.query("exec core_citi_direct_process_extract",
                              CitiDirectDBListProcessor)
             CitiDirectDBListProcessor.processRow(ResultSet)
               CitiDirectFileMapper.processRowIntoRecord(rs, Hashtable)
               CitiDirectAccountFile.appendNewBatchAccountRecordToFile(...)
                 DOM traversal of template → FixedLengthPrintWriter.print(...)
```

**Class inventory** (8 classes total):

| Class | Package | Responsibility |
|---|---|---|
| `CitiDirectFileProcess` | `reports` | Entry point; bootstraps Spring, orchestrates the run |
| `CitiDirectAccountFile` | `reports` | Core logic: XML template processing, per-record file writing, DB query execution |
| `CitiDirectDBListProcessor` | `reports` | Spring `RowCallbackHandler`; iterates result set, dispatches to `CitiDirectAccountFile` |
| `CitiDirectFileMapper` | `citidirectdao` | Spring `RowMapper`; maps `ResultSet` columns to `Hashtable` |
| `Context` | `common` | POJO holding runtime configuration (`citiDirectFilePath`, `agent`) |
| `FixedLengthPrintWriter` | `common` | `PrintWriter` subclass with fixed-length field formatting |
| `DateTimeHelper` | `common` | Timezone-aware date/time utility (not called in the active code path) |
| `TimeZoneHelper` | `common` | Static factory for `TimeZone` instances (used by `DateTimeHelper`) |
| `FDRStringValidator` | `common` | French-to-ASCII transliteration (not called in the active code path) |

Note: `DateTimeHelper`, `TimeZoneHelper`, and `FDRStringValidator` are present but are not invoked anywhere in the active processing path. They appear to be shared utilities carried over from a common library.

## API Surface

**External API**: None. This is a CLI-only application. There is no REST, SOAP, JMS, or RMI interface.

**Internal API** (public methods that form the library's logical surface):

| Class | Method | Signature | Notes |
|---|---|---|---|
| `CitiDirectFileProcess` | `writeECSProcessNasnewExtractFile()` | `void` | Main orchestration method |
| `CitiDirectFileProcess` | `main()` | `static void main(String[])` | CLI entry point |
| `CitiDirectAccountFile` | `loadNewAccountXMLFile()` | `static String loadNewAccountXMLFile(String folder, Log log)` | Returns error string or null |
| `CitiDirectAccountFile` | `processNewAccounts()` | `static boolean processNewAccounts(JdbcTemplate, Log, FixedLengthPrintWriter)` | Returns false on DB/write error |
| `CitiDirectAccountFile` | `appendNewBatchAccountRecordToFile()` | `static String appendNewBatchAccountRecordToFile(Hashtable, FixedLengthPrintWriter, StringBuffer)` | Returns error string or null |
| `CitiDirectAccountFile` | `setAgent()` | `static void setAgent(String)` | Sets module-level static field |
| `CitiDirectAccountFile` | `isEnabled()` | `static boolean isEnabled()` | Reads static `enabled` flag |
| `CitiDirectFileMapper` | `processRowIntoRecord()` | `void processRowIntoRecord(ResultSet, Hashtable)` | Populates Hashtable from ResultSet |
| `FDRStringValidator` | `getValidateString()` | `static String getValidateString(String)` | French-to-ASCII |
| `FixedLengthPrintWriter` | `print()` | Multiple overloads | Field-formatted output |

**Heavy use of static state**: `CitiDirectAccountFile` holds `newAccountXMLFileDoc`, `agent`, and `enabled` as static fields. This makes the class non-thread-safe and non-reentrant — only one instance of the file generation process can safely execute per JVM.

## Security Posture

| Control | Status | Evidence |
|---|---|---|
| TLS for outbound HTTP | ABSENT | `etlContext.properties`: `director.address=http://ecappdev/...` (plain HTTP) |
| Database credential protection | ABSENT | Credentials obtained from Director service; whether Director itself uses TLS is unknown; no credential is visible in this repo |
| Output file encryption | ABSENT | `FileWriter` writes plaintext |
| Input validation | PARTIAL | `safeGetString()` null-guards; no injection prevention needed (stored proc, no user input) |
| XML external entity (XXE) | VULNERABLE | `DocumentBuilderFactory.newInstance()` without `factory.setFeature("http://xml.org/sax/features/external-general-entities", false)` — XXE is enabled by default in the JDK version this code targets. The template XML is loaded from the filesystem, which limits exploitability in normal operation but remains a code-level risk. See `CitiDirectAccountFile.java` lines 118-129. |
| Dependency vulnerabilities | HIGH | Log4j 1.2.15 (CVE-2019-17571 — SocketServer deserialization RCE). Spring 1.2.7 (multiple CVEs). jTDS 1.2.2 (unmaintained). |
| Secret in source control | PRESENT | `etlContext.properties` contains `agent=B2CTEST` and a Director URL. If Director uses API keys or tokens embedded in the URL, these would be exposed. |
| Least privilege | UNKNOWN | The stored procedure `core_citi_direct_process_extract` is called with whatever credentials Director returns; minimum-privilege DB account cannot be verified from this library. |
| No PAN/SAD in field set | TRUE (as observed) | The four mapped fields do not include PAN, CVV, or PIN. |

### Critical Vulnerability: Log4j 1.2.15

`log4j:1.2.15` is affected by CVE-2019-17571 (CVSS 9.8), which allows remote code execution via a crafted log message through the `SocketServer` class. While this specific attack vector requires `SocketServer` to be running (which is not instantiated in this code), the version is well beyond EOL and carries additional known vulnerabilities. It must be replaced.

### XXE in DocumentBuilderFactory

`CitiDirectAccountFile.loadNewAccountXMLFile()` (lines 118-124) creates a `DocumentBuilderFactory` without disabling external entity resolution. Standard OWASP XXE mitigation requires:
```java
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
factory.setXIncludeAware(false);
factory.setExpandEntityReferences(false);
```
None of these are set. Since the template XML is loaded from a local filesystem path, exploitation requires write access to that path — but any supply-chain or misconfiguration attack on the template XML could leverage XXE.

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| All dependencies EOL | `pom.xml` | Critical |
| XXE-vulnerable XML parsing | `CitiDirectAccountFile.java` lines 118-124 | High |
| Static mutable state (`newAccountXMLFileDoc`, `agent`, `enabled`) | `CitiDirectAccountFile.java` lines 76-80 | High |
| `System.exit()` called 5+ times | `CitiDirectFileProcess.java` lines 67, 90, 97, 117; `CitiDirectDBListProcessor.java` line 49 | High |
| Raw `Hashtable` (non-generic) | All mapper/processor classes | Medium |
| `java.util.Hashtable` instead of `HashMap` | `CitiDirectDBListProcessor`, `CitiDirectFileMapper` | Medium |
| Commented-out 140-char record length validation | `CitiDirectAccountFile.java` lines 372-379 | Medium |
| Duplicate `seq="9"` in template | `newAccountFileTemplate.xml` lines 13-14 | Medium |
| `log.file` system property set but ignored | `CitiDirectFileProcess.java` line 136 vs `log4j.properties` | Medium |
| Dead code: `DateTimeHelper`, `TimeZoneHelper`, `FDRStringValidator` not called | `common` package | Low |
| `getFullCountryName()` returns only `"US"` for US, empty for everything else | `CitiDirectAccountFile.java` lines 431-438 | Low |
| `parseDate()` always returns null (assigns `dthResult` which is never set) | `DateTimeHelper.java` lines 384-393 | Low |
| Zero unit tests | entire repo | Critical |
| `etlContext.properties` with dev config committed | `src/main/resources/` | High |
| Windows-only output path | `etlContext.properties` line 4 | Medium |

## Gen-3 Migration Requirements

To migrate this ETL component to a Gen-3 (cloud-native, Spring Boot 3.x) architecture, the following work is required:

1. **Replace dependencies**:
   - Spring 1.x → Spring Boot 3.x (Spring Framework 6.x)
   - Log4j 1.x → SLF4J + Logback or Log4j 2.x
   - jTDS → Microsoft JDBC Driver for SQL Server (`com.microsoft.sqlserver:mssql-jdbc:12.x`)
   - `commons-dbcp:1.2.2` → HikariCP (Spring Boot default)
   - JUnit 3 → JUnit 5

2. **Replace static mutable state**: Refactor `CitiDirectAccountFile` static fields (`newAccountXMLFileDoc`, `agent`, `enabled`) into instance fields managed by Spring's bean lifecycle.

3. **Replace `System.exit()` calls**: Propagate exceptions and return meaningful exit codes via Spring Batch `JobExecution` status or standard exception handling.

4. **Fix XXE vulnerability**: Apply OWASP-recommended `DocumentBuilderFactory` hardening.

5. **Externalise configuration**: Replace classpath-embedded `etlContext.properties` with Spring Boot `application.yml` and environment-specific profiles (`application-prod.yml`). Wire secrets via Vault or AWS Secrets Manager.

6. **Add TLS**: The Director service call must be replaced with a TLS-secured endpoint (or replaced entirely with a modern datasource configuration approach, e.g., Spring Boot + HikariCP + Vault-injected credentials).

7. **Add structured logging and observability**: Replace Log4j pattern logging with structured JSON logs. Add metrics (Micrometer/Prometheus). Add a meaningful correlation/run ID.

8. **Add unit and integration tests**: Minimum requirement: `CitiDirectFileMapper`, `CitiDirectAccountFile.getFieldValue()`, `FixedLengthPrintWriter` field-width methods, and end-to-end file generation against a mocked DataSource.

9. **Spring Batch wrapping**: Consider wrapping the processing loop with a Spring Batch `Job` / `Step` / `ItemReader` / `ItemWriter` to gain checkpoint/restart, skip/retry policies, and job history.

10. **Containerise**: Replace Windows filesystem paths with volume mounts or object storage (S3/Azure Blob). Produce a Docker image with a non-root user.

11. **Resolve `core_citi_direct_process_extract`**: Document and test the stored procedure's result set contract. Determine whether it should be migrated to a JPA/JPQL query or retained as a procedure call.

## Code-Level Risks

| Risk | Class / Line | Description |
|---|---|---|
| Silent truncation of `transactionAmount` | `FixedLengthPrintWriter.leftJustifyWithBlanks()` lines 126-130 | Payment amounts silently shortened if they exceed field length |
| `toUpperCase()` on all field values | `CitiDirectAccountFile.getFieldValue()` line 428 | Numeric strings survive uppercasing, but any case-sensitive identifier would be corrupted |
| `NullPointerException` on null `file_date` | `CitiDirectAccountFile.getFieldValue()` lines 413-418 | `df.format(account.get(value))` throws NPE if `file_date` is null |
| Unsafe `rs.close()` inside `processRow()` | `CitiDirectDBListProcessor.java` lines 49, 55 | Calling `rs.close()` inside a `RowCallbackHandler` is not the correct Spring pattern; it can leave the `Statement` and `Connection` in an undefined state |
| Static `Document` not synchronised | `CitiDirectAccountFile.java` line 78 | `newAccountXMLFileDoc` is a static field written in `loadNewAccountXMLFile()` and read in `appendNewBatchAccountRecordToFile()`; unsafe for concurrent use |
| Exception swallowed in `printStackTrace()` | `CitiDirectAccountFile.getFieldValue()` line 419 | `ex.printStackTrace()` swallows the error for `LOGIC_FILEDATE` parse failure; processing continues with empty string |
| `DateTimeHelper.parseDate()` null dereference | `DateTimeHelper.java` line 391 | `dthResult` is always null at `return dthResult`; any caller would receive null and likely NPE |
| XXE in XML parsing | `CitiDirectAccountFile.java` lines 118-124 | Described above in Security Posture |
