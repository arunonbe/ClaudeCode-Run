# client-rewards_LIB — Solution Architect View

## Technical Architecture

### Module Structure
```
client-rewards (parent POM)
├── client-inputfile          (JAR, main: ReadInputFile)
│   ├── ReadInputFile         — entry point, file scan, JAXB parse, Spring boot
│   ├── ReadInputFileService  — service layer
│   ├── InputDAO              — transaction orchestrator
│   ├── CreateClientRewardsFileSP       — SP wrapper: dbo.create_client_rewards_file
│   ├── CreateClientRewardsFileStatusSP — SP wrapper: dbo.create_client_rewards_file_status
│   ├── CreateClientRewardsCustomerInfoSP — SP wrapper: dbo.create_client_rewards_customer_information
│   ├── FileExtension         — FilenameFilter for .xml
│   ├── generated/Inputfile   — JAXB-generated from Inputfile.xsd
│   ├── generated/Userinfo    — JAXB-generated from Inputfile.xsd
│   ├── generated/reply/Replyfile — JAXB-generated from Replyfile.xsd
│   └── util/ClientRewardProperties, IClientRewardsConstants
│
├── client-requestfile        (JAR, main: RequestFileBuilder)
│   ├── RequestFileBuilder    — entry point, Spring boot, orchestrator
│   ├── CreateRequestFile     — builds RequestFileVO / BatchVO / AccountCreationVO
│   ├── ClientRewardsRequestFileServiceImpl — service layer
│   ├── ClientRewardsRequestFileDAO — DAO, transaction management
│   ├── GetRewardsCustomerInformationSP — SP wrapper + RowMapper
│   ├── GetRewardsFileHeaderSP          — SP wrapper + RowMapper
│   ├── UpdateClientRewardsStatusSP     — SP wrapper
│   └── DTOs: ClientRewardsFileDTO, ClientRewardsCustomerInformationDTO, ClientRewardsFileStatusDTO
│
└── client-expire-records     (JAR, main: ExpireRecords)
    ├── ExpireRecords         — entry point
    ├── ExpireRecordsServiceImpl
    ├── ExpireRecordsDAO
    └── UpdateExpireRecordsSP — SP wrapper: dbo.update_client_rewards_customer_information
```

### Technology Stack
| Layer | Technology | Version | Status |
|---|---|---|---|
| Language | Java | 1.5 source/target | EOL |
| Framework | Spring Framework | 2.0.8 | EOL |
| XML binding | JAXB RI | 2.0EA3 (`com.sun.xml`) | EOL/non-standard |
| JDBC | jTDS | 1.2 | EOL (last release 2012) |
| Connection pool | Apache DBCP | 1.2.2 (via Director) | EOL |
| Logging | Log4j | 1.2.13 | EOL; multiple CVEs |
| Build | Maven | 3.9.1 (wrapper) | Current |
| Database | Microsoft SQL Server | Unknown version | Via `cbaseapp` |
| OS (deploy) | Windows (implied) | — | `D:\c-base\` paths, `.bat` file |

---

## API Surface

**This library exposes no public API.** It is a batch-only component.

### Internal service interfaces
```java
// client-inputfile
public interface IReadInputFileService {
    public void setInputfile(Inputfile inputFileDTO, int fileStatus,
                              ClientRewardProperties clientRewardProperties);
}

// client-requestfile
public interface IClientRewardsRequestFileService {
    public List<ClientRewardsFileDTO> getClientRewardsFileInfo();
    public boolean updateClientRewardsProcessed(
        List<ClientRewardsFileDTO> clientRewardsFileDTOList, String partnerId);
}

// client-expire-records
public interface IExpireRecordService {
    public void expireRecords();
}
```

### Stored Procedure contract (inferred from SP wrapper classes)
| SP Name | Module | In Params | Out Params |
|---|---|---|---|
| `dbo.create_client_rewards_file` | inputfile | file_name, program_id, promotion_id, partner_id, batch_description, created_date | id (INTEGER) |
| `dbo.create_client_rewards_file_status` | inputfile | file_id, status, comment, updated_date | id (INTEGER) |
| `dbo.create_client_rewards_customer_information` | inputfile | file_id, firstname, middlename, lastname, suffixname, email, address1, address2, city, state, postal_code, country, home_phone, business_phone, mobile_phone, amount, expired, status, created_date, updated_date | id (INTEGER) |
| `dbo.get_rewards_customer_information` | requestfile | status (BIT) | ResultSet (all customer fields + partner/program/promotion/batch) |
| `dbo.get_rewards_file_header` | requestfile | status (BIT), fileIds (VARCHAR) | ResultSet (file header fields) |
| `dbo.update_client_rewards_status` | requestfile | status (VARCHAR), rewards_ids (VARCHAR) | updateSuccess (BIT) |
| `dbo.update_client_rewards_customer_information` | expire-records | (none) | (none — side effect only) |

---

## Security Posture

### Authentication & Authorisation
- **None in application code**. No caller authentication is performed on the batch JAR entry points.
- Database authentication is delegated to the Director service. Credential type (Windows auth vs. SQL auth) is not visible in code; the `b2ctest` agent name suggests SQL authentication.
- No role-based access control within the application.

### Input Validation
- **XML schema validation** is performed via JAXB + XSD before any DB write (`ReadInputFile.parseValidateInputFile()`, lines 229–257). This is the only meaningful validation gate.
- **No SQL injection risk**: all DB interactions use parameterised stored procedures via Spring's `StoredProcedure` base class.
- **Phone number normalisation** strips non-digit characters (`formatStrPhoneNumber()`), which is defensive but not security-driven.
- **Amount validation** at XSD layer only: `xs:maxInclusive value="1000000000"` — no business-layer validation.

### Secrets Management
- **No secrets management framework**. Properties files checked into source control contain:
  - `agent=b2ctest` (credential for Director/DB auth)
  - `database=cbaseapp_jdbc`
  - `member_id = {AE6BBCC6-52DD-41E9-9298-A270BEC19DE3}` (GUID used as caller identity for JobSvc)
  - `director.address=http://ECIFLEXAPPDEV/service/dispatch.asp` (unencrypted HTTP)
- The commented-out `DriverManagerDataSource` bean in `applicationContext.xml` contains hardcoded credentials (`b2ctest`/`b2ctest`) — these were not deleted, only commented.

### Transport Security
- Director service is called over **plain HTTP** (`http://ECIFLEXAPPDEV/...`).
- No evidence of TLS on the JDBC connection.
- No evidence of SFTP or PGP on input file delivery.

### PII Exposure
- PII is logged at `debug` level in `ReadInputFile.displayRecords()` (lines 266–294). Although this method is commented out in the call chain (`//displayRecords(inputfile)`), it could be re-enabled accidentally.
- `log4j.rootLogger=debug` means all debug output is captured — if `displayRecords()` were enabled, full PII would appear in `Client_Rewards_log.log`.
- No masking of PII in log statements throughout the codebase.

---

## Technical Debt

### Critical
1. **EOL frameworks throughout** — Spring 2.0.8, Log4j 1.2.13, JAXB 2.0EA3, Java 1.5, jTDS 1.2. All carry unpatched CVEs and have no vendor support.
2. **Secrets in source control** — `agent`, `database`, `member_id`, plaintext credentials in `.properties` files committed to Git.
3. **Source files not deleted after archive** — `deleteFile()` is commented out in `ReadInputFile.moveFile()` (line 423). PII-containing input files accumulate on filesystem.

### High
4. **No meaningful test coverage** — All three `AppTest.java` files contain only `assertTrue(true)` (Maven archetype scaffolding). Zero functional tests.
5. **Partner ID failure is silent** — `CreateClientRewardsFileSP.getPartnerID()` catches `Throwable` and returns `0`, allowing reward files to be inserted with `partner_id=0` without any error or abort (lines 97–100).
6. **`@SuppressWarnings("unchecked")` on raw collection operations** — Raw `Map` and `List` types used throughout all SP wrapper classes, bypassing generics type safety (e.g., `CreateClientRewardsCustomerInfoSP.execute()` lines 61–101, `InputDAO.executeBatch()` lines 29–30).
7. **Date format bug** — `GetRewardsFileHeaderSP` line 101 uses `"mm-dd-yyyy"` where `mm` = minutes; correct pattern is `"MM-dd-yyyy"`. This silently corrupts all `createdDate` fields on `ClientRewardsFileDTO`.

### Medium
8. **Duplicate dependency declarations** — `client-expire-records/pom.xml` declares `jaxb-impl`, `jaxb-api`, `jaxb-xjc` twice each (lines 130–143 and 151–164).
9. **Inconsistent `xPlatform` version** — `client-inputfile` uses `1.0.14`; `client-expire-records` uses both `1.0.12-SNAPSHOT` and `1.0.8-SNAPSHOT` in the same POM.
10. **`vssver2.scc` binary files committed** — Visual SourceSafe artefacts present in multiple `resources/` directories; unrelated to project functionality.
11. **Hardcoded `D:\c-base\` paths** — Makes the application unrunnable on any system without replicating a specific Windows directory structure.
12. **All three modules log to the same file** — `D:/c-base/log/Client_Rewards_log.log` is shared; concurrent execution produces interleaved, uncorrelated output.
13. **`xstream` dependency declared but not imported in production code** — `com.thoughtworks.xstream:xstream:1.2.1` is in root `dependencyManagement` and `GetRewardsFileHeaderSP` imports it, but it is not used in any SP result mapping. Known deserialization vulnerabilities.

### Low
14. **`App.java` stub class** in `client-inputfile` — `com.ecount.service.rewards.client.App` just prints "Hello World!" (Maven archetype leftover).
15. **`CreateRequestFile` vs `RequestFileBuilder` separation** — `RequestFileBuilder` is the main class but merely delegates to `CreateRequestFile`; the split provides no architectural value.
16. **No file lock / mutex** on input folder scanning — `getInputFileList()` reads the directory without locking.
17. **printStackTrace() in production code** — Used in at least 8 locations across `ReadInputFile`, `CreateClientRewardsFileSP`, `RequestFileBuilder`; should use structured logging only.

---

## Gen-3 Migration Requirements

To migrate this library to a Gen-3 architecture, the following work is required:

### Must-Have
1. **Replace all EOL dependencies**: Spring Boot 3.x, Log4j2 (or SLF4J/Logback), Jakarta XML Binding 4.x, HikariCP, Microsoft JDBC Driver.
2. **Externalise secrets**: Move `agent`, `database`, member GUID to a secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault). Remove from source control.
3. **Replace Director DataSource**: Implement standard Spring Boot datasource autoconfiguration with explicit connection properties from secrets manager.
4. **Replace JobSvc/ProfileManager**: Implement `partner_id` resolution via a Gen-3 programme configuration service or database lookup — remove `com.cbase.*` and `xPlatform` dependencies.
5. **Replace `requestfile-impl` dependency**: Wire to Gen-3 payment disbursement API (REST or event-driven) rather than the internal XML file builder.
6. **Implement file deletion after archiving**: Fix the commented-out `deleteFile()` call or replace with an atomic move.
7. **Implement structured logging with correlation IDs**: Replace Log4j 1.x with SLF4J/Logback or Log4j2; add MDC with batch run ID.

### Should-Have
8. **Containerise**: Package as Docker image; externalise all `D:\c-base\` paths via environment variables or Spring Boot configuration.
9. **Write integration/unit tests**: Cover all three processing flows with test coverage for error cases (duplicate file, SP failure, XSD validation failure, empty input folder).
10. **Replace file-based client integration with event-driven**: Replace XML file drops with S3/Azure Blob trigger or Kafka topic for inbound client data.
11. **Add metrics instrumentation**: Micrometer for records processed, files loaded, error counts, processing latency.
12. **Fix date format bug**: `GetRewardsFileHeaderSP` line 101 `"mm-dd-yyyy"` → `"MM-dd-yyyy"`.

### Nice-to-Have
13. **Regenerate JAXB classes**: From `Inputfile.xsd` and `Replyfile.xsd` using current Jakarta XML Binding tooling; remove JAXB 2.0EA3 `com.sun.xml` dependency.
14. **Replace raw types with generics**: Remove all `@SuppressWarnings("unchecked")` by adopting typed Spring JDBC `RowMapper<T>` and parameterised `Map<String, Object>`.

---

## Code-Level Risks

| Risk | File | Line(s) | Detail |
|---|---|---|---|
| PII retained on filesystem | `ReadInputFile.java` | 423 | `deleteFile()` commented out — input file not removed after archive copy |
| Silent partner_id=0 on error | `CreateClientRewardsFileSP.java` | 97–100 | `catch(Throwable)` returns `partnerID=0`; reward record inserted with invalid partner |
| Date format bug corrupts created_date | `GetRewardsFileHeaderSP.java` | 101 | `"mm-dd-yyyy"` (minutes) instead of `"MM-dd-yyyy"` (months) |
| address2 overwrites address1 | `GetRewardsCustomerInformationSP.java` | 96 | `setAddress1(rs.getString("address2"))` — address2 stored in address1 field of DTO |
| Raw unchecked Map operations | Multiple SP classes | — | `Map in = new HashMap()` without generics; type errors at runtime only |
| XStream import with no use | `GetRewardsFileHeaderSP.java` | 29 | `import com.thoughtworks.xstream.XStream` imported but unused; XStream 1.2.1 has known RCE vulnerabilities if instantiated |
| Batch update with string-built ID list | `ClientRewardsRequestFileDAO.java` | 159–200 | `rewardsIds` built via `StringBuffer` concatenation of integer IDs passed to SP as VARCHAR — no SQL injection risk (SP parameter) but fragile if IDs contain unexpected chars |
| No null check on SP OUT param | `CreateClientRewardsCustomerInfoSP.java` | 101 | `return (Integer)map.get("id")` — NullPointerException if SP does not return `id` |
| No null check on SP OUT param | `CreateClientRewardsFileSP.java` | 63 | `return (Integer)map.get("id")` — same pattern |
| Spring context loaded in constructor | `ReadInputFile.java`, `RequestFileBuilder.java`, `ExpireRecords.java` | constructor | Loading `ClassPathXmlApplicationContext` in constructor means any constructor failure during static init leaves app in undefined state |
| `System.exit(0)` on IOException | `ReadInputFile.java` | 145, 150, 154, 156 | Abrupt JVM termination; no cleanup, no final logging, no alerting |
