# card-enrollment-maricopa_LIB — Data Architect View

## Data Stores

| Store | Reference | Purpose |
|---|---|---|
| eCount Core Database (RDBMS) | `appContext.xml` bean `EcountCoreDataSource`, line 20–25 | Primary operational database; source of account records |
| Director Configuration Service | `appContext.xml` bean `directorDataSourcesFactory`, line 16–18 | Supplies the JDBC DataSource configuration dynamically via a "Director" service at `${director.address}` |
| Properties files (flat file config) | `appContext.xml` lines 8–9 — `D:/c-base/config/processes/cardenrollment/cardenrollment.properties` and `d:/c-base/config/director-client.properties` | Holds runtime configuration including database agent name, database alias, and director address |
| Log4j XML config (flat file) | `EnrollmentProcessMain.java` line 14 — `D:\c-base\config\processes\cardenrollment\log4j.xml` | Controls logging output destinations and levels |

There is no local embedded data store. All persistent state lives in the eCount Core database, accessed exclusively through a Spring-managed `DataSource` bean.

## Schema & Tables

The library does not define or manage its own schema. It consumes a single database object:

| Object | Type | Reference | Columns Read |
|---|---|---|---|
| `Get_MaricopaDDA_With_No_Card` | Stored Procedure | `GetCardIdsList.java` line 18 | `accountid` (VARCHAR — mapped via `rs.getString("accountid")` at line 38) |

The stored procedure returns a result set mapped by the inner class `AccountList implements RowMapper` in `GetCardIdsList.java` (lines 35–39). Only the `accountid` column is consumed; all other columns returned by the procedure (if any) are discarded.

The procedure is registered as a Spring `StoredProcedure` subclass with a single `SqlReturnResultSet` named `"transactions"` (line 22–23), meaning the result set key in the output map is the string `"transactions"`.

## Sensitive Data Handling

**Critical concern**: The column read from the database is named `accountid` and the Java variable is later used as `accountNumber` in `EnrollmentHelper.java` line 53. The value is then passed directly to:
- `new Account(accountNumber)` (line 76) — passed to the eCount Core API
- `logger.info("Processing Account " + accountId)` in `EnrollmentProcessMain.java` line 49
- `logger.info("Issue Plastic Successfully for Account " + accountId)` line 54
- `logger.error("Error Issuing Plastic for Account Id " + accountId)` line 57

If `accountid` is a PAN, a card device ID traceable to a PAN, or any other Primary Account Data element, logging it in clear text violates PCI DSS v4.0.1 Requirement 3.3.1 (do not retain SAD) and Requirement 10.3 (protect audit logs). The actual sensitivity of this field must be confirmed with the database/data team. If it is an internal opaque device ID with no cardholder data content, risk is lower but should still be validated.

There is no masking, tokenization, or encryption of the `accountid` value at any layer in this library.

## Encryption & Protection

- **In transit**: The JDBC connection to the eCount Core database is DataSource-managed by the Director service. No TLS/SSL parameters are visible in this library's configuration. Whether the JDBC URL enforces SSL is opaque and not verifiable from this source alone.
- **At rest**: Not applicable to this library — no data is written or stored locally.
- **Configuration secrets**: The `settings.xml` file (`.mvn/wrapper/settings.xml`) contains **plaintext credentials** for multiple servers:
  - `nexus-qa`: username `deployment`, password `dwil15?` (line 38–40)
  - `ecount.release`: username `deployment`, password `d3v0nly` (line 41–45)
  - `ecount.snapshot`: username `deployment`, password `d3v0nly` (line 46–50)
  - `wirecard-mavenproxy-repository`: username `acmng`, password `acmng` (line 33–36)
  
  These are committed to source control, which is a critical secret-management failure and violates PCI DSS Requirement 8 (manage identifiers and authentication) and internal SDLC security policies.
- **Log file security**: The log4j configuration path is hardcoded to a Windows local path (`D:\c-base\config\processes\cardenrollment\log4j.xml`). Log file access control is not managed by this library.

## Data Flow

```
[eCount Core DB]
      |
      | JDBC call via Spring StoredProcedure
      v
[Get_MaricopaDDA_With_No_Card stored proc]
      |
      | ResultSet: column "accountid"
      v
[GetCardIdsList.AccountList.mapRow() → Collection<String>]
      |
      | returned via IAccountIdDAO.getAccountIds()
      v
[EnrollmentHelper / EnrollmentProcessMain — in-memory list]
      |
      | accountId string passed to IDeviceManager.issuePlastic()
      v
[eCount Core API (DeviceManagerImpl) — writes card issuance record]
      |
      | accountId strings written to log file
      v
[Log4j log file on local filesystem: D:\c-base\config\processes\cardenrollment\]
```

No data flows outbound over HTTP/REST/SOAP from this library directly. All integration is via in-process Java API calls to the eCount Core/xPlatform libraries.

## Data Quality & Retention

- **No data validation**: The `accountid` string returned by the stored procedure is not validated for format, length, or non-null before being passed to the API. A null or malformed value would cause an unchecked exception within `issuePlastic`.
- **No deduplication**: If the stored procedure returns the same `accountid` twice, it will be processed twice.
- **No write-back / status update**: The Java layer does not update the database after successful or failed issuance. The stored procedure defines the eligibility boundary, and without a post-processing status update, the same records could be re-selected on the next run.
- **Retention**: No retention policy is implemented or referenced. Log files accumulate until externally purged. The `DEFAULT_RETRY_COUNT` constant (value `3`, `EnrollmentHelper.java` line 37) is declared but never used — retry logic was never implemented.

## Compliance Gaps

| Gap | Regulation / Standard | Evidence |
|---|---|---|
| Plaintext passwords committed to source control in `.mvn/wrapper/settings.xml` | PCI DSS v4.0.1 Req 8.3, Req 12.3 | Lines 33–50 of `settings.xml` |
| Account identifiers potentially logged in clear text | PCI DSS v4.0.1 Req 3.3.1, Req 10.3.3 | `EnrollmentProcessMain.java` lines 49, 54, 57 |
| No post-issuance audit record written to database | Reg E dispute resolution; SOC 1/2 control evidence | Absence of any write/update operation in the entire codebase |
| No encryption-in-transit enforcement for DB connection | PCI DSS v4.0.1 Req 4.2 | `appContext.xml` — DataSource provided externally with no TLS parameters |
| Nexus/artifact repository URL references legacy Wirecard infrastructure (`d-na-stk01.nam.wirecard.sys`) | Supply-chain security; PCI DSS Req 6.3 | `settings.xml` lines 13, 92, 120 |
