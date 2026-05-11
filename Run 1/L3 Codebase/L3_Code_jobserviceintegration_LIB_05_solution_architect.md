# jobserviceintegration_LIB — Solution Architect View

## Technical Architecture

- **Language**: Java (compiled to Java 1.6 bytecode)
- **Framework**: None — plain Java SE with Apache Commons Logging
- **Module layout**:
  - `Common`: Shared file-format utilities (`BatchFile`, parsers, validators, `ZipUtils`)
  - `chrysler`, `toyota`, `subaru`, `nextel`, `qwest`, `jwt`, `LegacyForLife`: Per-client converters
  - `ECountStandard/Common/JavaValidator`: Data-generation utilities (older copy outside Maven module)
  - `BulkCardGen`: Binary JARs and scripts (not a Maven module)
  - `alg`: ALG-specific VBScript/Java automation
  - `SMoTS`: Secure Mail automation (separate Maven module with its own POM)
- **Execution model**: Command-line application (`main(String[] args)`) invoked by external scheduler
- **Data structures**: `Hashtable` (legacy, pre-generics), `Vector` (legacy), raw arrays
- **File I/O**: `PrintWriter`, `BufferedReader`, `ZipFile`, `ZipEntry`, `InputStreamReader`

## API Surface

This library has no HTTP/REST/JMS API. Its public interface is:

### `BatchFile` (Common module)
Constructor entry points and write methods:
```java
BatchFile(String fileName)  // creates output file
void writeFileHeader(String programID, String passthrough, String createDate, String outputFileName)
void writeFileFooter()
void writeBatchHeader(String programID, String batchDescription, String passthrough, String promoID)
void writeBatchFooter()
void writeRequestHeader(String ecountId, String partnerUserID, String passthrough)
void writeAddFundsAction(String passthru, int amount, boolean taxable, int notificationIndicator)
void writeAddFundsAction(String passthru, int amount, boolean taxable, int notificationIndicator, String partnerPaymentId)
void writeCreateAccountAction(String passThrough, String firstName, ...)  // 16 parameters
void writeSpinPaymentAction(...)
void writeStopPaymentAction(...)
void writeCreateCertificateAction(...)
void writePPDRecord(String name, String value)
```

### `ChryslerFileConverter` (chrysler module)
```java
ChryslerFileConverter(String inputFileName, String outputFileName, String programID, String createDate)
int processFile()
static void main(String[] args)  // 4 args: inputFileName, outputFileName, programId, createDate
```

Similar `main`-based entry points exist in other client modules.

## Security Posture

### Authentication / Authorization
None. The library is invoked by a host process with filesystem access. There is no concept of authentication; any process with access to the input directory can trigger a conversion.

### Cryptography
None. All file I/O is plaintext. No encryption, no signing, no integrity checking of input files.

### Secrets
No credentials or secrets in source code. However, promotion config files and client data files are on the filesystem — access control depends entirely on OS file permissions.

### Known CVE-relevant Dependencies
- **Commons Logging 1.1.1**: Released ~2007. While the library itself does not have critical CVEs, it is a facade; the underlying logging implementation (Log4j 1.x is present in `alg/common/log4j-1.2.15.jar`) is **critically vulnerable**.
- **Log4j 1.2.15** (`alg/common/log4j-1.2.15.jar`): This is a binary JAR committed to source control. Log4j 1.x is **end-of-life** and has multiple known CVEs. Notably, CVE-2019-17571 (deserialization via SocketServer), CVE-2020-9488 (SMTP appender), and various other issues affect 1.2.x branches. **This JAR should be treated as a critical security risk.**
- **Hibernate 3.2.0.cr5, Acegi Security 1.0.3** (in `BulkCardGen` JARs): Ancient versions with numerous known CVEs. Committed as binaries.
- **Spring 1.x/2.x framework JARs** (in `BulkCardGen`): Similarly ancient; many known CVEs.

## Technical Debt

| Item | File | Severity |
|---|---|---|
| Java 1.6 target; EOL since 2013 | Root `pom.xml` | Critical |
| `SNAPSHOT` version never stabilised | Root `pom.xml` | High |
| Raw `Hashtable`, `Vector` (pre-generics) | `ChryslerFileConverter.java` | Medium |
| `System.exit()` called from library code | `ChryslerFileConverter.java` lines 88, 115, 116 | High — library should not call `System.exit` |
| Off-by-one substrings (same as job_LIB's `BatchFile`) | `BatchFile.java` lines 143, 152, 157 | Medium — data truncation bugs |
| `e.printStackTrace()` instead of logger | `ChryslerFileConverter.java` line 116 | Low |
| `ThreadLocal<Log>` anti-pattern | `ChryslerFileConverter.java` lines 22–26 | Low |
| Binary JARs in SCM | `alg/common/`, `BulkCardGen/` | Critical — unauditable supply chain |
| Log4j 1.2.15 JAR committed | `alg/common/log4j-1.2.15.jar` | Critical — CVE-2019-17571 |
| Hibernate 3.2.0.cr5 JAR committed | `BulkCardGen/JobImportFile/BulkCardGen/` | Critical |
| No unit tests | All modules | High |
| Windows-only `.vbs` / `.wsf` scripts | `alg/`, `chrysler/` | High — not container-portable |
| `makeField` silently truncates data beyond max length | `BatchFile.java` `makeField()` method | Medium — data loss without warning |

## Gen-3 Migration Requirements

1. Replace file-based ETL with event-driven REST API ingestion (client submits JSON or CSV via API).
2. Replace per-client converter modules with configurable transformation rules (or client-specific adapters backed by a rules engine).
3. Remove all binary JARs from source control; manage all dependencies through Maven coordinates.
4. Replace Windows scripts with platform-independent implementations (Java, Python, or shell scripts).
5. Replace `System.exit()` calls with proper exception propagation.
6. Add structured logging (ECS/JSON) with OpenTelemetry correlation.
7. Add input validation with schema-validated DTO models.
8. Implement TLS/encryption for file transit; use Azure Blob Storage with managed identity instead of filesystem paths.
9. Add unit and integration tests.

## Code-Level Risks (File:Line References)

| Risk | File | Line |
|---|---|---|
| `System.exit(-1)` in library code | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 116 |
| `System.exit(rc)` in library code | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 88 |
| `System.exit(1)` in library code | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 81 |
| `ecountId.substring(16)` truncation bug (should be `substring(0,16)`) | `Common/src/main/java/com/ecount/jobintegration/common/BatchFile.java` | 143 |
| Log4j 1.2.15 critical CVE JAR in SCM | `alg/common/log4j-1.2.15.jar` | N/A — binary |
| `e.printStackTrace()` without logger | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 116 |
| Silent data truncation in `makeField` | `Common/src/main/java/com/ecount/jobintegration/common/BatchFile.java` | 36–40 |
| `otherAreaCode`/`otherPhoneNumber` reads same field as home phone (copy-paste bug) | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 469–470 |
