# citi-direct-file-process_LIB — Data Architect View

## Data Stores

| Store | Type | Details |
|---|---|---|
| EcountCore | SQL Server (MSSQL) | Operational source database; accessed via JDBC using the jTDS driver (`net.sourceforge.jtds:jtds:1.2.2`, `pom.xml` line 35). Database name is `EcountCore` (`etlContext.properties` line 3). |
| CitiDirect output file | Filesystem flat file | Fixed-length text file written to a local path configured in `etlContext.properties` (`CitiDirectFilePath=d:/c-base/runtime/citidirectfile/`). Filename is supplied at runtime and stamped with `_yyyyMMddkkmmss`. |
| newAccountFileTemplate.xml | Classpath XML resource | Template defining the file layout; loaded from the same directory as `CitiDirectFilePath` at runtime (`CitiDirectAccountFile.java` line 128-130). |
| citidirect.log | Rolling log file | Log4j `RollingFileAppender`, max 100 KB, 1 backup (`log4j.properties` lines 9-12). |
| Director service | HTTP endpoint | `http://ecappdev/service/dispatch.asp` — plain HTTP, non-TLS. Provides DBCP data-source configuration by agent+database key. |

## Schema & Tables

No DDL is present in the repository. The only observable schema evidence is the stored procedure call and the result-set column names mapped in `CitiDirectFileMapper.processRowIntoRecord()`:

```
Stored procedure: core_citi_direct_process_extract  (CitiDirectAccountFile.java line 23)

Result set columns consumed:
  preformatCode       VARCHAR  (safeGetString)
  transactionAmount   VARCHAR  (safeGetString)
  country             VARCHAR  (safeGetString, 2-char or 3-char ISO country code)
  file_date           DATE     (rs.getDate)
```

The stored procedure is invoked as `exec core_citi_direct_process_extract` with no parameters. The proc is presumed to reside in `EcountCore` on SQL Server. No additional tables, views, or indexes are evidenced in this library.

## Sensitive Data Handling

| Field | Classification | Handling |
|---|---|---|
| `transactionAmount` | Financial — payment instruction value | Written in plaintext to the output flat file; no masking or encryption applied. |
| `preformatCode` | Potentially account/card identifier | Written in plaintext; nature of this field must be confirmed. If it is a card token or partial PAN derivative, PCI DSS scope applies. |
| `country` | Personal data (residence country) | Written to file; GDPR/PIPEDA data subject location attribute. |
| `file_date` | Operational date | Not personally sensitive. |

No PAN, CVV, PIN, SSN, or full bank account numbers are observed in the field set. However, the stored procedure `core_citi_direct_process_extract` could return additional columns that this mapper does not capture — that is not verifiable from this library alone.

## Encryption & Protection

- **At-rest encryption**: None implemented in this library. The output file is written as plaintext to a local filesystem path via `BufferedWriter`/`FileWriter` (`CitiDirectFileProcess.java` lines 81-83). Whether the host OS or a downstream process encrypts the file is outside this codebase.
- **In-transit encryption**: None implemented. The Director service is contacted over plain HTTP (`http://ecappdev/...`). The JDBC connection via jTDS uses default (unencrypted) SQL Server connectivity unless the connection string from the Director service specifies `ssl=require`.
- **File transfer to Citibank**: No SFTP, FTPS, or PGP encryption logic exists in this library. The delivery of the generated file to Citibank is entirely absent from this codebase.
- **Log data**: Error messages including partial exception detail are written to `citidirect.log`. If exception stack traces expose field values, sensitive data could appear in logs.

## Data Flow

```
SQL Server (EcountCore)
  └─ exec core_citi_direct_process_extract
       │
       ▼ ResultSet (preformatCode, transactionAmount, country, file_date)
CitiDirectFileMapper.processRowIntoRecord()
       │
       ▼ java.util.Hashtable (account)
CitiDirectAccountFile.appendNewBatchAccountRecordToFile()
       │  Applies newAccountFileTemplate.xml layout
       ▼
FixedLengthPrintWriter
       │  Fixed-length ASCII text
       ▼
Local filesystem: <CitiDirectFilePath>/<filename>_<timestamp>.txt
       │
       ▼ (out of scope for this library)
Citibank Direct (file ingestion)
```

All transformations are stateless per-row; no intermediate staging table or message queue is used.

## Data Quality & Retention

1. **No null-safety for `transactionAmount` and `country`** — `CitiDirectFileMapper` uses `safeGetString()` which returns `""` on null (line 36-44). An empty `transactionAmount` field written to the payment file would produce a malformed zero-length payment instruction.
2. **`file_date` null handling absent** — `rs.getDate("file_date")` (line 32) is called directly without null protection; a null date throws `NullPointerException` at format time in `CitiDirectAccountFile.getFieldValue()` (line 416).
3. **Silent field truncation** — values longer than the template-defined field `length` are silently truncated by `FixedLengthPrintWriter` (e.g., `leftJustifyWithBlanks` lines 126-130); no data quality alert is raised.
4. **Log retention** — log is capped at 100 KB with 1 backup. For a payment file generation process, this is inadequate for audit or dispute purposes. FFIEC and internal policy likely require longer retention.
5. **No record count trailer** — the file has no header or trailer record. Downstream reconciliation with Citibank is entirely dependent on out-of-band confirmation.
6. **All field values uppercased** — `CitiDirectAccountFile.getFieldValue()` returns `res.toUpperCase()` (line 428) for all value types, including `preformatCode` and `transactionAmount`. This may corrupt numeric or case-sensitive values.

## Compliance Gaps

| Gap | Regulation | Evidence |
|---|---|---|
| Plaintext financial data in output file | PCI DSS v4.0.1 Req 3 | `CitiDirectFileProcess.java` lines 81-83; `FixedLengthPrintWriter` writes raw strings |
| Plain HTTP to Director service | PCI DSS v4.0.1 Req 4, TLS 1.2 minimum | `etlContext.properties` line 1: `http://ecappdev/...` |
| No file integrity check (hash/MAC) | PCI DSS v4.0.1 Req 10, NACHA | No checksum generation in any class |
| No encryption of flat file | PCI DSS v4.0.1 Req 3.5 (if scope confirmed) | `FileWriter` used directly |
| Insufficient log retention (100 KB) | FFIEC, SOC 2 CC7 | `log4j.properties` line 11 |
| No audit record of who initiated the run | SOC 2, internal audit | No user identity captured in logs |
