# aml-name-screening_LIB — Solution Architect View

## Technical Architecture

The library is a **monolithic standalone Java batch application** with a flat class structure of 6 classes in a single package (`com.citi.prepaid.namescreening`). Dependency injection is provided by Spring Framework 2.5.6 via XML configuration loaded from the classpath at startup.

### Class Inventory

| Class | Role |
|-------|------|
| `NameScreeningMain` | Entry point; parses CLI args, loads Spring context, invokes `INameScreening` |
| `INameScreening` | Interface defining `processNameScreening(String, Map<String,String>): int` |
| `NameScreeningImpl` | Implements `INameScreening`; orchestrates file reading, DB query, and workbook update per row |
| `NameScreeningDAO` | JDBC data access; builds and executes SQL; returns `ArrayList<ArrayList<String>>` |
| `NameScreeningHelper` | File I/O; reads input XLS via Apache POI HSSF; writes results to output sheet |
| `NameScreeningConstants` | Constants: status codes, sentinel string, hardcoded credentials |

### Spring Bean Wiring (`applicationContext.xml`)

```
nameScreeningImpl (NameScreeningImpl)
  ├── inputFilePath  <- java.lang.String  <- ${inputfilepath} from NameScreening.properties
  ├── nameScreeningHelper (NameScreeningHelper)
  └── nameScreeningDAO (NameScreeningDAO)
        └── dataSource (ecountCoreDS)
              └── DriverManagerDataSource
                    └── jdbc:jtds:sqlserver://ppamwdcpisql1b1.nam.nsroot.net:2431/Ecountcore
```

`PropertyPlaceholderConfigurer` reads from the hardcoded path `C:\c-base\config\namescreening\NameScreening.properties`.

## API Surface

**There is no API.** The only external interface is:

```
java -jar NameScreening-1.0.0-SNAPSHOT-jar-with-dependencies.jar <inputFileName> [USERNAME=<u> PASSWORD=<p>]
```

- `args[0]`: input XLS filename (relative to `${inputfilepath}`).
- `args[1]`: `USERNAME=<value>` (optional; validated by string prefix check in `NameScreeningMain.setAdditionalInputs`).
- `args[2]`: `PASSWORD=<value>` (optional; must accompany USERNAME).
- Return: OS exit code `0` (success) or `1` (failure).

No REST endpoints, no gRPC, no messaging consumers, no JMX MBeans.

## Security Posture

### Critical Findings

1. **SQL Injection (High)**
   - `NameScreeningDAO.java` line 85 constructs the SQL query via string concatenation:
     ```java
     String sql = "select ... from fdr_dda_account_registration where "
       + "(first_name+' '+middle_name+' '+last_name like '%" + firstName +"%" + middleName + "%" + lastName + "%')";
     ```
   - The only mitigation is apostrophe doubling (lines 67–78), which is incomplete. Other SQL metacharacters (`;`, `--`, `%`, `_`) are not escaped. A LIKE wildcard in a name value would broaden the query silently.
   - Fix required: Use `PreparedStatement` with parameterized LIKE patterns.

2. **Hardcoded Credentials (Critical)**
   - `NameScreeningConstants.java` lines 25–26: `USERNAME = "report"`, `PASSWORD = "[REDACTED — rotate immediately]"` committed to VCS.
   - `.mvn/wrapper/settings.xml` lines 38–51: Plaintext passwords for Nexus (`dwil15?`), ecount.release (`d3v0nly`), ecount.snapshot (`d3v0nly`) committed to VCS.
   - These violate PCI DSS Requirement 8.3.6 and constitute secrets-in-code.

3. **No Input Validation (Medium)**
   - XLS column count is inferred from the header row only; no schema enforcement.
   - File path is taken directly from CLI and Spring properties without sanitization; path traversal is theoretically possible.
   - `args[0]` is accessed before the `args.length < 1` guard (NameScreeningMain.java lines 56–58), causing `ArrayIndexOutOfBoundsException` when no arguments are supplied.

4. **Unencrypted JDBC Transport (High)**
   - `applicationContext.xml` line 44: `jdbc:jtds:sqlserver://ppamwdcpisql1b1.nam.nsroot.net:2431/Ecountcore` — no `ssl=require` or equivalent parameter. jTDS defaults to no TLS.

5. **PII Logged at INFO (High)**
   - `NameScreeningDAO.java` lines 108–110 log `dda_number` and `card_id` at INFO level per row. Full SQL with name values logged at line 86.

6. **EOL Dependencies with Known CVEs (Critical)**
   - Log4j 1.2.15: CVE-2019-17571 (deserialization RCE via SocketServer), CVSS 9.8.
   - Spring Framework 2.5.6: Multiple historical CVEs, no patches available.
   - Apache Commons DBCP 1.2.2: Multiple CVEs.
   - Jakarta POI 3.0.1: Unmaintained.

7. **No Authentication / Authorization**
   - The tool runs with whatever OS user invokes it. No RBAC, no audit of who ran the tool or what names were screened.

## Technical Debt

| Item | Location | Severity |
|------|----------|----------|
| Java 1.6 target | `pom.xml` lines 65–66 | Critical |
| Spring 2.5.6 | `pom.xml` line 10 | Critical |
| Log4j 1.2.15 EOL + CVEs | `pom.xml` lines 42–45 | Critical |
| Hardcoded Windows path `C:\c-base\` | `applicationContext.xml` line 20 | Critical |
| SQL injection via string concatenation | `NameScreeningDAO.java` line 85 | Critical |
| Credentials in source code | `NameScreeningConstants.java` lines 25–26 | Critical |
| Credentials in VCS-tracked settings.xml | `.mvn/wrapper/settings.xml` lines 38–51 | Critical |
| Defunct Citi-era DB hostname | `applicationContext.xml` line 44 | Critical |
| `ArrayIndexOutOfBoundsException` when no args | `NameScreeningMain.java` lines 56–58 | High |
| `DriverManagerDataSource` (no connection pool) | `applicationContext.xml` line 41 | High |
| HSSF `.xls` format (BIFF8, deprecated) | `NameScreeningHelper.java` | High |
| Unclosed `FileInputStream` when result is null | `NameScreeningHelper.updateWorkbook` line 209 | High |
| `ArrayList<ArrayList<String>>` as return type (no domain model) | `NameScreeningDAO.java` line 63 | Medium |
| `java.awt.List` imported but never used | `NameScreeningDAO.java` line 5 | Low |
| `javax.swing.text.Style` imported but never used | `NameScreeningHelper.java` line 14 | Low |
| Dead code (commented-out column set calls) | `NameScreeningHelper.java` lines 132–137 | Low |
| `TODO{Description}` in all Javadoc | All source files | Low |
| `@author TCS` — no Onbe ownership recorded | All source files | Low |
| Version stuck at `1.0.0-SNAPSHOT` since 2015 | `pom.xml` line 5 | Low |
| No unit tests | Entire repo | High |
| `maven-assembly-plugin` uses deprecated `attached` goal | `pom.xml` line 80 | Low |

## Gen-3 Migration Requirements

A faithful Gen-3 replacement of this function would require:

1. **External AML watchlist integration** — The current tool queries only the internal database. A compliant AML screening solution requires integration with a certified sanctions/PEP screening provider (e.g., Refinitiv World-Check API, LexisNexis Bridger, Dow Jones). This is a net-new capability, not a rewrite of existing logic.

2. **REST API or event-driven trigger** — Replace CLI invocation with a REST endpoint (`POST /aml/screening/jobs`) or a Kafka-consumed event, deployable as a Spring Boot 3.x microservice on Kubernetes.

3. **Eliminate XLS file I/O** — Replace Excel input/output with API request/response payloads (JSON) or a case management system integration. If batch file processing is genuinely required, use `.xlsx` (XSSF) with Apache POI 5.x.

4. **Secrets management** — All credentials must be injected via environment variables sourced from Vault or AWS Secrets Manager. No credentials in source or configuration files.

5. **Parameterized SQL or ORM** — Replace dynamic SQL string construction with JPA/Hibernate or at minimum `PreparedStatement` with named parameters.

6. **PII logging controls** — Remove all log statements that output DDA numbers, card IDs, email, phone, or name values at INFO/DEBUG level. Implement structured logging with PII masking.

7. **TLS for all DB connections** — Enforce TLS on all JDBC connections; use Microsoft JDBC Driver 12.x (not jTDS).

8. **Audit trail** — Every screening execution must be recorded: who initiated it, what names were queried, what matches were returned, what disposition was applied. This is a regulatory requirement for AML programs.

9. **Java 17 or 21 LTS** — Compile and run on a supported LTS JDK.

10. **Container packaging** — Produce a Docker image; no Windows-path dependencies.

## Code-Level Risks

### Risk 1 — SQL Injection (`NameScreeningDAO.java` line 85)
The LIKE query is constructed by concatenating user-supplied name strings. Although apostrophes are doubled, other SQL injection vectors remain. If the input XLS is ever sourced from an untrusted party (e.g., a file upload), this becomes a direct DB compromise vector.

### Risk 2 — ArrayIndexOutOfBoundsException on zero args (`NameScreeningMain.java` lines 56–58)
```java
String inputFileParam = args[0];  // line 56 -- throws AIOOBE if args is empty
if(args.length < 1) {             // line 58 -- guard is too late
```
The check at line 58 is unreachable when `args` is empty because the exception is thrown at line 56. Any automated invocation with missing arguments produces an unhandled stack trace rather than a clean error message.

### Risk 3 — FileInputStream leak (`NameScreeningHelper.updateWorkbook`)
`xlInputStream` (line 121) is only closed at line 209, inside the `if(null != result)` block. If `result` is null (passed from DAO on SQL exception path), the input stream is never closed, leaking a file handle on every failed row.

### Risk 4 — In-place XLS overwrite with open read handle
`xlInputStream` is still open when `FileOutputStream` is opened on the same file path (line 210). On Windows, this can cause `FileNotFoundException` or file corruption depending on JVM and OS buffering behavior. The correct pattern is to close the input stream before opening the output stream, or to write to a temp file and rename.

### Risk 5 — Silent data loss on column mismatch
`NameScreeningImpl.java` line 49 splits the pipe-delimited row string. If the input XLS has fewer than 3 data columns, `input[1]` or `input[2]` access throws `ArrayIndexOutOfBoundsException`, which is caught at the outer try/catch (line 72), increments `batchProcessingStatus` to failure, and exits — silently abandoning remaining rows.

### Risk 6 — Defunct database connectivity
The JDBC URL targets `ppamwdcpisql1b1.nam.nsroot.net:2431`, a Citi-era hostname. If this host is unreachable, every `NameScreeningDAO.execute()` call throws a connection exception, which is re-thrown as a generic `Exception("DB Connection failure")`. The tool would produce an XLS full of "No Possible Outcomes" entries with no clear indication to the operator that the database was never reached.
