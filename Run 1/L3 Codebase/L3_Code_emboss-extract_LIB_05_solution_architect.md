# 05 Solution Architect — emboss-extract_LIB

## All Classes and Methods

### `com.ecount.process.emboss.extract.Extractor`
File: `src/main/java/com/ecount/process/emboss/extract/Extractor.java`

| Method | Purpose |
|---|---|
| `main(String[] args)` | Entry point; reads `vendorId` from args[0]; calls `initializeContext()` and `createStaxXML(vendorId)`; exits with stored-procedure return code |
| `createStaxXML(Integer vendorId)` | Orchestrates the three-step workflow: insert file record → extract queue data → update file record |
| `initializeContext()` | Loads Spring `ClassPathXmlApplicationContext` from `appContext-emboss.xml` |
| `getOutputFileName(String outputFilePath, String vendorName)` | Constructs the output file path; FDR → `{path}{VendorName}_{yyyyMMddhhmmss}.xml`; PSX → `{path}{VendorName}{yyDDDHH}.xml` |
| `getOutputFileName(String vendorName)` | Overload; constructs filename without path prefix |
| `createExtractData()` | Test-data factory (unused in production path); creates 10 synthetic `EmbossExtractData` records |
| `logInfo(String)` | Conditional logging helper |

### `com.ecount.process.emboss.dao.CallCoreProcessEmbossQueueExtract`
File: `src/main/java/com/ecount/process/emboss/dao/CallCoreProcessEmbossQueueExtract.java`

| Method | Purpose |
|---|---|
| `CallCoreProcessEmbossQueueExtract(DataSource ds)` | Constructor; registers SP `dbo.core_process_emboss_queue_extract`; declares RS return, integer return code, `vendor_id` and `file_id` input parameters |
| `execute(Integer vendorId, Integer fileId, XMLStreamWriter)` | Calls the SP, streams rows through `EmbossExtractRowCallbackHandler`, writes XML header and trailing elements |

#### Inner class `EmbossExtractRowCallbackHandler`

| Method | Purpose |
|---|---|
| `processRow(ResultSet rs)` | Reads each result-set row; on first row writes the XML `<embossfile>` header; groups rows by `request_id` to aggregate variable fields |
| `mapRow(ResultSet rs, EmbossExtractData)` | **Maps 30+ columns from the result set including `card_number`, `card.exp_month`, `card.exp_year`, `first_name`, `last_name`, `emboss_name`** |
| `mapVariableField(ResultSet rs, EmbossExtractData)` | Maps `carrier-variable-field1` through `carrier-variable-field20` |
| `processRecord(EmbossExtractData)` | Writes one `<request>` XML element to the stream |
| `getRowCount()` | Returns total rows processed |
| `getLastRecord()` | Returns the last `EmbossExtractData` (written after SP completes) |
| `trimData(String)` | Null-safe trim |
| `trimTrailingZeroes(String)` | Formats `cardValue` as 2 decimal places using `BigDecimal` |

### `com.ecount.process.emboss.builder.StaxEmbossExtractBuilder`
File: `src/main/java/com/ecount/process/emboss/builder/StaxEmbossExtractBuilder.java`

| Method | Purpose |
|---|---|
| `createEmbossFileNode(XMLStreamWriter, String docNS, int dataListSize, int fileId)` | Writes `<embossfile>` root element with `fileid`, `requestcount`, and `xmlns` attributes |
| `createRequestNode(XMLStreamWriter, EmbossExtractData)` | **Writes all fields including `<cardnumber>` (FULL PAN) and `<cardexpiration>` as plaintext XML** |
| `formatCardExpiration(String)` | Zero-pads the expiration to 6 characters (MMYYYY) |

### `com.ecount.process.emboss.dao.InsertEmbossFile`
File: `src/main/java/com/ecount/process/emboss/dao/InsertEmbossFile.java`

| Method | Purpose |
|---|---|
| `InsertEmbossFile(DataSource ds)` | Constructor; registers SP `dbo.core_process_emboss_file_insert` with `file_id` out parameter |
| `execute()` | Calls SP and returns the generated `file_id` |

### `com.ecount.process.emboss.dao.UpdateEmbossFile`
File: `src/main/java/com/ecount/process/emboss/dao/UpdateEmbossFile.java`

| Method | Purpose |
|---|---|
| `UpdateEmbossFile(DataSource ds)` | Constructor; registers SP `dbo.core_process_emboss_file_update` |
| `execute(Integer file_id, Integer request_count, String file_name)` | Updates the emboss-file record with final count and file name |

### `com.ecount.process.emboss.dao.data.EmbossExtractData`
See `02_data_architect.md` for full field inventory. Pure JavaBean with 60+ getter/setter pairs.

### `com.ecount.process.emboss.dao.data.EmbossQueueExtractOutput`
| Field | Purpose |
|---|---|
| `dataListSize` | Total number of card records in the extract |
| `returnCode` | Stored-procedure return code (0 = success, 100 = empty result) |

### `com.ecount.process.emboss.builder.EmbossExtractBuilder`
Interface defining the builder contract (implemented by `StaxEmbossExtractBuilder`). Presumably declares `createRequestNode` and `createEmbossFileNode`.

### `com.ecount.process.emboss.exception.EmbossQueueExtractException`
| Method | Purpose |
|---|---|
| `getCode()` | Returns the stored-procedure error code for use as JVM exit code |

### Utility classes

| Class | Key Methods | Purpose |
|---|---|---|
| `StaxXMLUtil` | `getXMLStreamWriter(String filePath)`, `writeStartDocument()`, `writeTextData()`, `writeNewLine()` | StAX XML writer utilities |
| `XMLUtil` | DOM-based XML utilities (appears to be an older/unused variant) | — |
| `StringUtils` | `hasData(String)` | Null/empty string check |

## CRITICAL Security Vulnerabilities

### 1. Full PAN Written in Plaintext to File (P0 — PCI DSS Showstopper)
- **Location**: `StaxEmbossExtractBuilder.createRequestNode()` line 61: `StaxXMLUtil.writeTextData(xmlStreamWriter, "cardnumber", data.getCardNumber())`
- **Description**: The full PAN is written as a plaintext XML text node to the output file. There is no encryption, tokenisation, or masking applied within the library.
- **PCI DSS**: Req 3.5.1 requires that PANs be rendered unreadable anywhere they are stored (AES-256, HSM-based encryption, or tokenisation). If the output file is the "storage", this is a direct violation.
- **Remediation**: Before writing `<cardnumber>`, apply at minimum PGP encryption to the entire file using the card bureau's public key (standard industry practice for emboss files). Alternatively, integrate with an HSM to produce an encrypted card block.

### 2. Hardcoded Credentials in Source Control (P0 — PCI DSS Req 8.6.3)
- **Location**: `src/conf/dev/embossContext.properties` lines 3–4 and `src/conf/prod/embossContext.properties` lines 3–4
- **Credentials**: `username=andrewc`, `password=andrewc`
- **Description**: Database credentials are committed to the Git repository in plaintext. This violates PCI DSS Req 8.6.3 (no shared/group credentials) and is a supply-chain security risk.
- **Remediation**: Remove all credential values from property files. Retrieve credentials at runtime from Azure Key Vault, AWS Secrets Manager, or Director.

### 3. Log4j 1.2.8 in `lib/` (P1 — Critical CVE)
- **Location**: `lib/log4j-1.2.8.jar`
- **Description**: An older version than even the `1.2.15` used by `ecount-host-log4j_LIB`. Carries CVE-2019-17571 (CVSS 9.8 — RCE via deserialization), CVE-2022-23302, CVE-2022-23305, CVE-2022-23307.
- **Remediation**: Remove the `lib/` binary JAR. Declare the dependency in Maven and upgrade to Log4j 2 or Logback.

### 4. Spring Framework 2.0 (P1 — Critical)
- **Location**: `pom.xml` lines 25–28
- **Description**: Spring 2.0 is end-of-life since approximately 2009. Known vulnerabilities exist. Spring XML bean configuration (DTD-based `spring-beans.dtd`) is a deprecated and less-secure configuration style compared to annotation-driven or Java-based configuration.
- **Remediation**: Upgrade to Spring Boot 3.x.

### 5. Java 1.5 Compiler Target (P2 — High Technical Debt)
- **Location**: `pom.xml` lines 57–60
- **Description**: Java 5 compatibility mode. Modern JVMs can run Java 5 bytecode, but the code loses access to all post-Java-5 security APIs (TLS improvements, secure random enhancements, etc.).
- **Remediation**: Upgrade to Java 21 compiler target.

### 6. `DriverManagerDataSource` (No Connection Pooling) (P3 — Medium)
- **Location**: `appContext-emboss.xml` lines 12–26
- **Description**: Spring's `DriverManagerDataSource` creates a new physical connection for every request. For a batch job processing thousands of cards, this is a performance issue and can exhaust database connections.
- **Remediation**: Replace with `HikariCP` or `BasicDataSource`.

### 7. Bug in Variable Field Mapping — `carrier-variable-field14` (P4 — Medium)
- **Location**: `CallCoreProcessEmbossQueueExtract.java` line 253
- **Description**: `carrier-variable-field14` maps to `setVariableTextId1()` instead of `setVariableTextId14()`. This causes field 14 data to silently overwrite field 1 data.
- **Remediation**: Change `eeData.setVariableTextId1(fValue)` to `eeData.setVariableTextId14(fValue)`.

## Remediation Priority Summary

| Finding | Priority | Action |
|---|---|---|
| Plaintext PAN in output file | P0 — Critical | Implement PGP encryption with bureau public key before file write |
| Hardcoded credentials in source | P0 — Critical | Remove credentials; use secrets manager |
| Log4j 1.2.8 CVEs | P1 — Critical | Replace with Log4j 2 or Logback |
| Spring 2.0 (EOL) | P1 — Critical | Upgrade to Spring Boot 3.x |
| Java 1.5 target | P2 — High | Upgrade to Java 21 |
| No connection pooling | P3 — Medium | Add HikariCP |
| field14 mapping bug | P3 — Medium | One-line fix |
