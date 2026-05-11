# Solution Architect Analysis — enrollment_LIB

## Repository Overview

**Repo:** `enrollment_LIB`
**Main entry point:** `src/main/java/com/citi/processes/enrollment/extract/ProcessMain.java`
**Key packages:** `common`, `dao`, `extract`, `file`, `helpers`, `strongbox`, `type`
**Java:** 1.6 source/target; Spring 2.0.8 XML

---

## Solution Architecture

### Component Breakdown

| Component | Class | Responsibility |
|-----------|-------|---------------|
| Entry point | `ProcessMain` | Drives the programme loop; orchestrates extract, StrongBox, file, and status |
| Profile DAO | `Profile` | Retrieves programme processing profiles |
| Extract DAO | `Extract` | Executes stored procedure; maps results to `ExtractInfo` |
| Status DAO | `Status` | Reads and writes report processing status |
| StrongBox client | `StrongBoxClient` | XML-RPC client for sensitive data retrieval |
| StrongBox processor | `ProcessStrongBox` | Multi-threaded StrongBox request dispatcher |
| File handler | `FileHandler` | Generates fixed-width flat file; moves to FTP staging |
| Thread pool | `RequestProcessorThread` | Worker thread for parallel StrongBox requests |
| Data transfer | `ExtractInfo` | Mutable POJO carrying all cardholder fields |
| Utilities | `Utility`, `SpringUtils` | Date helpers, Spring context bootstrap |
| Types | `EventType`, `FieldType`, `FrequencyType`, `RecordType`, `ReportStatus` | Enumerations |

### Processing Flow

```
ProcessMain.main()
  |
  +--> profile.getProfileInfo(1) --> List<ProfileInfo>
  |
  +--> for each ProfileInfo:
  |     +--> Utility.getReportRunDates(profileInfo) --> List<ReportRunDate>
  |     +--> for each ReportRunDate:
  |           +--> switch(programCurrentStatus):
  |                 case 0 (NEW):
  |                   +--> extract.getExtractInfo(programId, reportRunDate) -- stored proc
  |                   +--> processStrongBox.processRequest(listExtractInfo)  -- parallel StrongBox
  |                   +--> fileHandler.generateFile(programId, listExtractInfo, fileName, runTime)
  |                 case 2 (FAILED_MOVE):
  |                   +--> fileHandler.moveFiles(programId, fileName)
  |           +--> status.setReportStatus(statusInfo)
```

**Note:** There is a missing `break` statement between `case 0` and `case 2` in `ProcessMain.java` lines 76–94. This is intentional fall-through — after generating and moving the file in case 0, it falls into case 2 to perform the move. However, this is a code-clarity issue that could confuse maintainers.

---

## Security Risks

### 1. Cleartext PII in Memory (MEDIUM-HIGH)
`ExtractInfo` objects hold SSN, DOB, routing numbers, and account numbers in plain `String` fields after StrongBox retrieval. Java `String` objects are immutable and cannot be zeroed — they persist in heap until GC. For PCI DSS Req 3.3 and GLBA, sensitive data should be held in `char[]` or `byte[]` and zeroed immediately after use.

### 2. StrongBox Transport Security Unknown (HIGH)
`StrongBoxClient.java` uses Apache `HttpClient` (commons-httpclient 3.x, EOL since 2011). The StrongBox URI is injected via `${director.address}` — if this resolves to an `http://` URL, all PII responses are unencrypted in transit. The code makes no assertion that TLS is required.

**Location:** `StrongBoxClient.java` lines 94–126 (constructor injects `serviceURI` without TLS validation).

### 3. Singleton HTTP Client (MEDIUM)
`StrongBoxClient.java` uses a `static final HttpClient httpClient` (line 50). This is a JVM-global shared instance. Connection manager settings applied in one constructor call affect all future calls. If multiple instances of `StrongBoxClient` are created with different configurations, the last-one-wins for connection pool parameters.

### 4. End-of-Life Dependencies (HIGH)
| Dependency | EOL Since | CVEs (approximate) |
|------------|-----------|-------------------|
| `commons-httpclient:3.x` | 2011 | Multiple (e.g., CVE-2012-5783 — hostname verification bypass) |
| `jtds:1.2` | ~2012 | Known issues with SQL injection via metadata |
| `spring:2.0.8` | 2009 | Numerous; Spring 2.x is unsupported |
| `commons-lang:2.1` | ~2010 | CVE exposure in serialisation |

### 5. XML-RPC Deserialisation (MEDIUM)
`XmlRPCToObjectMapper.toObject(response, output, logger)` (line 152 of `StrongBoxClient.java`) deserialises an XML-RPC response. XML deserialisation from external sources can be vulnerable to XXE (XML External Entity injection) if the parser is not hardened. The `XmlRPCToObjectMapper` is from the internal `com.ecount.xmlrpc.utils` library — its security posture is not visible in this repo.

### 6. Fall-through `switch` Statement (LOW - Correctness)
`ProcessMain.java` lines 76–94: `case 0` falls through to `case 2` without a `break`. While this may be intentional, it makes the flow difficult to audit and modify safely.

---

## Technical Debt Inventory

| Item | Location | Severity |
|------|----------|----------|
| Java 1.6 source level | `pom.xml` lines 118–120 | Critical — Java 6 EOL since 2013 |
| Spring 2.0.8 XML config | `pom.xml` line 32 | Critical — EOL since 2009 |
| jTDS JDBC driver | `pom.xml` line 35 | High — EOL; should be `mssql-jdbc` |
| commons-httpclient 3.x | Used in `StrongBoxClient.java` | High — EOL; CVE-2012-5783 hostname bypass |
| No unit tests | Entire `src/` tree | High |
| Mutable `ExtractInfo` with PII in plain strings | `ExtractInfo.java` | High (PCI/GLBA) |
| Typo in field name `secutiryToken` | `ExtractInfo.java` line 37 | Low (frozen API) |
| Hardcoded T: drive in distribution management | `pom.xml` lines 56–68 | Medium |
| `switch` fall-through without comment | `ProcessMain.java` lines 76–94 | Low |
| No MDC/correlation ID in logging | `ProcessMain.java` throughout | Medium |
| `System.exit()` call | `ProcessMain.java` line 138 | Low (prevents use as library) |

---

## Refactoring Recommendations

1. **Migrate to Spring Batch** on Spring Boot 3.x — provides built-in job/step tracking, retry, skip, and chunk-oriented processing that replaces the hand-rolled loop in `ProcessMain.java`.
2. **Replace StrongBox with Vault or AWS Secrets Manager** — provides TLS, audit logging, and lease management for sensitive credentials and tokens.
3. **Upgrade to `mssql-jdbc`** and Spring Data JDBC — eliminates jTDS and provides modern SQL Server features.
4. **Encrypt flat files** using PGP (BouncyCastle) before FTP staging, consistent with the `cross-border-transfer-service-batch` module's PGP implementation.
5. **Add unit tests** — minimum coverage for `ProcessMain` logic, `ExtractInfoRowMapper`, and `StrongBoxClient` retry logic.
6. **Zero sensitive strings** after use — consider a `SecureExtractInfo` variant that holds sensitive fields in `char[]` with explicit zeroing.
