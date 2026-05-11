# check-issuance_LIB — Data Architect View

## Data Stores

The library interacts with a single relational database accessed through two logical Spring `DataSource` beans declared in `appContext.xml`:

| Bean ID | Purpose | Runtime Config Property |
|---|---|---|
| `EcountCoreDataSource` | Primary application database — all check issuance read/write | `${ecountcore.database}` with agent `${ecount.agent}` |
| `JobsvcDataSource` | Declared in `appContext.xml` (lines 23–30) but not wired to any DAO in this library | `${jobsvc.database}` |

Both data sources are created via `DirectorConfiguredDBCPdatasourceCreator` (`com.ecount.Core2.system.dal.ds`) using a Director service address (`${director.address}`), indicating connection parameters are resolved at runtime via an internal service registry rather than being fully embedded in config files.

The JDBC driver in `pom.xml` (line 104) is `net.sourceforge.jtds:jtds:1.2.4`, confirming the target RDBMS is **Microsoft SQL Server**.

## Schema & Tables

No DDL files are present in the repository. The schema is inferred entirely from stored procedure signatures and result-set mappings.

### Stored Procedures (all in `EcountCoreDataSource`)

| Stored Procedure | Class | Operation | Parameters |
|---|---|---|---|
| `check_process_create_records` | `CreateCheckIssuanceRecords.java` | Populate work queue; returns count | OUT: `check_records_count` (INTEGER) |
| `check_process_transaction_auto_post` | `CheckIssuanceTransactionsList.java` | Fetch batch of pending records | IN: `count` (INTEGER), `check_type` (INTEGER); returns result set |
| `check_process_transaction_auto_post_status_upd` | `CheckIssuanceUpdTransaction.java` | Update transaction status | IN: `transaction_uuid`, `old_transaction_uuid`, `dda_number` (VARCHAR), `status`, `error_code`, `retry_count` (INTEGER), `error_desc` (VARCHAR) |
| `check_process_transaction_refundcheck_stop_extract` | `citiCPSStopRefundCheck.vbs` line 94 | Export stop-refund records via BCP | None declared (BCP queryout) |

### Inferred Table/View Columns (from `CheckIssuanceTransactionsList.java` result-set mapper)

The SP `check_process_transaction_auto_post` returns:

| Column | Java Field | Type |
|---|---|---|
| `transaction_uuid` | `transaction_uuid` | String (UUID) |
| `dda_number` | `dda_number` | String |
| `dda_device_id` | `ddaDeviceId` | String |
| `ecard_device_id` | `ecardDeviceId` | String |
| `total_amount` | `total_amount` | Integer (cents) |
| `echeck_flag` | `echeck_flag` | Integer |
| `addfunds_flag` | `addfunds_flag` | Integer |
| `businessdays_flag` | `businessdays_flag` | Integer |
| `voidChkAmt` | `voidChkAmt` | Integer (cents) |
| `voidChkRefundAmt` | `voidChkRefundAmt` | Integer (cents) |
| `member` | `member` | String |
| `post_chk_flag` | `post_chk_flag` | Boolean |
| `status` | `status` | Integer (0=new, 1=in-progress, 2=complete) |
| `error_code` | `error_code` | Integer |
| `default_enrollment` | `defaultEnrollment` | Integer |
| `retry_count` | `retryCount` | Integer |
| `is_issuance` | `isIssuance` | Integer |
| `is_enrollment` | `isEnrollment` | Integer |
| `payment_id` | `paymentId` | String |
| `source` | `source` | Integer (255=reissuance) |
| `validity` | `validityDays` | Integer |
| `check_type` | `checkRequestType` | Integer (0=auto, 1=manual) |

### File-Based Data (Citi CPS)

The `citi-cps-checks.fmt` BCP format file defines the outbound check issuance file to Citi with 27 pipe-delimited (`~|`) fields including cardholder name, address, check amount, check ID, and expiration date.

The `citi-cps-stop-refund-checks.fmt` defines the stop-refund file with 4 fields: `account_number`, `amount`, `check_number`, `check_issue_date`.

## Sensitive Data Handling

| Data Element | Sensitivity | Where Present | Protection Status |
|---|---|---|---|
| `dda_number` | High — DDA account identifier | `CheckIssuanceData`, DB columns, BCP file | No masking observed in code; logged at `debug` level (`CheckIssuanceHelper.java` lines 279, 412, 476, 494, 504, 567) |
| `account_number` (Citi file) | High — up to 17 chars, likely a card/account number | `citi-cps-checks.fmt` col 9 | Transmitted in pipe-delimited plaintext file |
| `first_name`, `last_name` | PII | `citi-cps-checks.fmt` cols 18–19 | Transmitted in plaintext |
| Full mailing address | PII | `citi-cps-checks.fmt` cols 21–26 | Transmitted in plaintext |
| DB password | Credential | `citiCPSStopRefundCheck.vbs` lines 78, 95 | Read from INI file; passed as `-P` on BCP command line — plaintext |
| `member` (member ID) | Internal identifier | `CheckIssuanceData`, DB, log output | No masking |
| `transaction_uuid` | Internal transaction identifier | All layers | Logged at info/debug level — acceptable |

## Encryption & Protection

- **No application-level encryption** is implemented in the Java library. There is no use of Java Cryptography Architecture (JCA), Bouncy Castle, or any cipher utilities anywhere in the source.
- The CDP process `CITISTOPREFUNDCHECK.cdp` includes a commented/conditional step `STEP05` that calls `PGM=ENCRYPT` with `ENCRYPT.VBS` — however, in `citiCPSStopRefundCheck.vbs`, the GPG encryption command is entirely commented out (lines 153–158: `'--PKZIP = "gpg --encrypt..."`). **Encryption of the stop-refund file is disabled.**
- The `citi-cps-checks.fmt` check issuance file format shows no reference to encryption or PGP wrapping in this codebase.
- Database connections use DBCP connection pooling (`DirectorConfiguredDBCPdatasourceCreator`) — TLS/SSL configuration is not controlled from this library.
- Log4j rolling file appender writes to `D:/c-base/log/CheckIssuance/checkissuance.log` — no log-level filtering prevents `dda_number` from appearing in log files (root logger is set to `debug` in `src/log4j.properties` line 1; `src/main/resources/log4j.properties` sets it to `debug` as well).

## Data Flow

```
SQL Server (EcountCoreDataSource)
    │
    ├─[SP: check_process_create_records]──► Populates work queue table
    │
    ├─[SP: check_process_transaction_auto_post(count, check_type)]
    │       └─► CheckIssuanceResponse (collection of pending records)
    │               └─► RequestProcessorThread
    │                       ├─► DeviceInfoManager.getAccountDetails()  ──► ecount Core API (RPC)
    │                       ├─► TransferManager.simpleFeeInquiry()     ──► ecount Core API (RPC)
    │                       ├─► TransferManager.transferDDAToOperator() ──► ecount Core API (RPC)
    │                       └─► [SP: check_process_transaction_auto_post_status_upd]
    │
    └─[SP: check_process_transaction_refundcheck_stop_extract]  (via BCP in VBS)
            └─► pipe-delimited .dat file
                    └─► citiReportParser.pl (createStopRefundCheck)
                            └─► formatted stop-refund file
                                    └─► Sterling Connect:Direct (NDM)
                                            └─► Citi Mainframe MVS dataset
```

## Data Quality & Retention

- **No data validation** of incoming SP result fields is performed in Java — values are mapped directly from `ResultSet` to `CheckIssuanceData` fields without null checks or range validation.
- **Amounts are stored as integers (cents)** — no decimal/precision issues, but there is no explicit currency field; USD is assumed implicitly.
- The `retryCount` field tracks processing attempts per transaction. There is no TTL or expiration logic in the Java code; expiry is managed via the `validityDays` field supplied by the database.
- **No archival or purge logic** is present in this library. Retention policy for processed records is enforced entirely at the database tier.
- The `errorDesc` field is a free-text VARCHAR used for diagnostic messages — contains internal error codes and stack trace excerpts logged in plain text (e.g., `"TRANSACTION REACHED MAX RETRY COUNT AND CANCELLED"`).

## Compliance Gaps

1. **DDA number logged at debug level** — `dda_number` appears in multiple `logger.debug()` calls (`CheckIssuanceHelper.java` lines 279, 403, 476) and `logger.error()` calls (line 411, 494). With root logger set to `debug`, these are written to the rolling log file. PCI DSS Req 3.3.1 prohibits storage of SAD; DDA numbers may constitute sensitive account data depending on context.
2. **Plaintext DB credentials in VBS/INI** — `citiCPSStopRefundCheck.vbs` reads and uses DB password from a plaintext INI file and passes it as a command-line argument. This violates PCI DSS Req 8.3.1 and Req 6.3 (protect credentials).
3. **Encryption of outbound Citi file is disabled** — The GPG encryption step in `citiCPSStopRefundCheck.vbs` is commented out. Outbound files containing account numbers may be transmitted in plaintext. Violates PCI DSS Req 4.2.1.
4. **No field-level masking** — Cardholder name and address fields are written to files and logs without masking. PCI DSS Req 3.3 and GLBA require that PII be protected in transit and at rest.
5. **Old transaction UUID retained** — `CheckIssuanceTransactionsList.java` line 87 sets `old_transaction_uuid` to the same value as `transaction_uuid` (`rs.getString(TRANSACTION_UUID)`). This appears to be a mapping defect — the old UUID is never separately populated from the DB.
6. **No explicit query timeout on update SP** — `CheckIssuanceUpdTransaction` constructor (line 29) has the `setQueryTimeout()` call commented out. Long-running updates could hold DB locks indefinitely.
