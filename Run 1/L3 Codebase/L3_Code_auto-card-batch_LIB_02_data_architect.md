# auto-card-batch_LIB — Data Architect View

## Data Stores

| Store ID | Purpose | Spring Bean | Driver / Technology |
|---|---|---|---|
| `ecountcoreDataSource` | Operational data: transaction journal, auto-card SPs | `data-source-context.xml` lines 11–16 | Microsoft SQL Server (`com.microsoft.sqlserver.jdbc:sqljdbc:1.1`) via DBCP |
| `batchRepoDataSource` | Spring Batch job repository metadata | `data-source-context.xml` lines 18–23 | Same SQL Server driver; separate database (`ecountbatchjobrepository`) |

Both data sources are created at runtime by `DirectorConfiguredDBCPdatasourceCreator` (`com.ecount.Core2.system.dal.ds`), fetching connection parameters from a Director service at runtime rather than from static properties. This means JDBC URLs, usernames, and passwords are not present in this repository; they are resolved from the Director configuration service (`director.address` property).

## Schema & Tables

### Application Table: `autocard_creation_transaction_journal`
Source: `autocardbatch.properties` (line 12) and `AutoCardProcessJob.xml` (line 182).

| Column (property key) | Type (inferred) | Purpose |
|---|---|---|
| `id` | INTEGER | Primary key / surrogate row identifier |
| `memberid` | VARCHAR | Member identifier — foreign key to member master |
| `status` | VARCHAR(1) | Processing status: N/P/C/I/F/R |
| `created` | DATE | Record creation date |
| `is_issuance` | INTEGER (0 or 1) | Flag: 0 = needs enrollment, 1 = issuance only |

The UPDATE statement is: `UPDATE autocard_creation_transaction_journal SET status = ? WHERE memberid = ?` (constructed dynamically in `AutoCardProcessJob.xml`, line 182, using `${autocard.table}`, `${autocard.table.status.column}`, `${autocard.table.memberid.column}`).

### Stored Procedures (SQL Server, `dbo` schema)

| SP Name | Property Key | Purpose | Parameters |
|---|---|---|---|
| `dbo.auto_card_creation_order_load` | `autocard.sp.autocard_order_load` (note: key in properties file is `auto_card_creation_order_load`) | Load eligible records into journal | None declared in reader config |
| `dbo.autocard_get_count` | `autocard.sp.autocard_get_count` | Returns `totalcount` column — count of pending records | None |
| `dbo.autocard_get_record` | `autocard.sp.autocard_get_record` | Returns paginated `AutoCardMember` rows | `count` (INTEGER) = `autocard.pagesize` |
| `dbo.check_threshold_program_virtual_card` | (inline, `ThresholdProgramVirtualCardSP.java` line 25) | Returns virtual card count for a given program/DDA | `product` (TINYINT), `brand` (TINYINT), `affiliate` (SMALLINT), `dda_number` (VARCHAR), OUT `countValue` (INTEGER) |

### Spring Batch Repository Tables
Prefix `BATCH_` in database `ecountbatchjobrepository`. Standard Spring Batch 2.1 schema: `BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_JOB_EXECUTION_PARAMS`, `BATCH_STEP_EXECUTION`, `BATCH_STEP_EXECUTION_CONTEXT`, `BATCH_JOB_EXECUTION_CONTEXT`.

## Sensitive Data Handling

| Data Element | Where Used | Sensitivity | Observed Protection |
|---|---|---|---|
| `memberid` (VARCHAR) | `AutoCardMember.memberid`, SQL UPDATE, log debug output (`AutoCardCreateWriter.java` line 63) | PII — member account identifier | None — logged in plaintext at DEBUG level |
| `dda_number` (VARCHAR) | `ThresholdProgramVirtualCardSP.execute()` line 49 — passed as SP parameter; substring extracted at `CardCreateService.issueCard()` line 136–137 | Sensitive financial identifier (DDA / account number) | None — not masked, not encrypted, passed as plain VARCHAR |
| `ecard.getDda().getNumber()` | `CardCreateService.issueCard()` line 136 | DDA account number retrieved from eCard object | Not logged, but stored in local variable and passed to SP without masking |
| Job execution context values | Spring Batch `BATCH_JOB_EXECUTION_CONTEXT` (serialised to DB) | Transaction counts — low sensitivity | None required |

**Critical finding**: `memberid` is logged at DEBUG level in `AutoCardCreateWriter.write()` (line 63: `_log.debug(cardMember.getId() + "member id :: " + cardMember.getMemberid() + ...)`). Log level is set to `debug` globally (`log4j.properties` line 1: `log4j.rootLogger=debug`), meaning PII is written to log files in all environments where this default config is active.

## Encryption & Protection

- **No encryption at the application layer** is implemented or configured in this codebase. There is no use of JCE, Jasypt, or any cryptographic library.
- **Connection credentials** are not in this repository; they are resolved at runtime via the Director service. This is the only credential-protection mechanism present.
- **Log files** are written to `D:/c-base/log/autocardtest.log` with DEBUG level enabled globally. No log sanitisation or masking is applied before writing.
- **Transport security**: JDBC connections to SQL Server are managed by the Director-configured DBCP pool. TLS enforcement for the JDBC connection is not configurable from this codebase.
- **Maven settings credentials** (`settings.xml` lines 37–54): Plaintext passwords for Nexus (`nexus-qa`), ecount release/snapshot repos (`deployment` / `d3v0nly`, `d3v0nly`), and wirecard proxy (`acmng`/`acmng`) are committed to the repository. This is a critical secret-exposure risk.

## Data Flow

```
[Director Service] ──(connection params)──> [DirectorConfiguredDBCPdatasourceCreator]
                                                     │
                          ┌──────────────────────────┴──────────────────────┐
                          ▼                                                   ▼
               [ecountcoreDataSource]                           [batchRepoDataSource]
                          │                                                   │
         ┌────────────────┼─────────────────────┐              [BATCH_* tables]
         ▼                ▼                     ▼
  SP: autocard_    SP: autocard_        autocard_creation_
  get_count        get_record           transaction_journal
         │                ▼                     ▲
         │         [AutoCardMember VO]          │
         │                │                    │
         │                ▼                    │
         │         [CardCreateService]         │
         │          ├─ IDeviceManager          │
         │          │   (eCore/FDR API)        │
         │          ├─ AppProfileUserEnrollment│
         │          │   (profile system)       │
         │          └─ ThresholdProgramVirtual ┘
         │              CardSP (ecountcoreDS)  │
         │                                    │
         └──> [AutoCardCountWriter]            │
              (StepExecutionContext)           │
                                              │
                                    [AutoCardDaoImpl.updateStatus()]
```

## Data Quality & Retention

- **Idempotency**: The count step (`autocard_get_count`) and record retrieval SP (`autocard_get_record`) implicitly filter for unprocessed records (status `N` or `P` assumed). No explicit WHERE clause is visible in this repo; it is encapsulated in the SPs.
- **Pagination**: `autocard.pagesize = 5` — only 5 records are fetched per partition step. `autocard.gridsize = 5` — 5 parallel partition threads. Maximum 25 records processed per job iteration.
- **Infinite-loop detection**: Three successive run counts are compared (`AutoCardCountSavingListener.isInfinite()`). If current == previous == previousprevious (and all > 0), the job exits with `RECORDS FOUND:INFINITELOOP`.
- **Retention policy**: No data retention, archival, or purge logic exists in this codebase. The transaction journal table accumulates records indefinitely unless purged externally.
- **Spring Batch metadata**: `BATCH_*` tables retain full job/step execution history. No cleanup job is configured.

## Compliance Gaps

| Gap | Detail | Relevant Standard |
|---|---|---|
| PII in debug logs | `memberid` written to log file at DEBUG level globally (`AutoCardCreateWriter` line 63, `log4j.properties` line 1) | PCI DSS Req 10, CCPA, GDPR |
| DDA number unmasked in SP call | `dda_number` passed as plain VARCHAR to `check_threshold_program_virtual_card` (`ThresholdProgramVirtualCardSP` line 49) | PCI DSS Req 3 |
| Plaintext credentials in SCM | `settings.xml` contains deployment passwords and a Wirecard proxy credential in plaintext | PCI DSS Req 8, NIST CSF PR.AC |
| No at-rest encryption | Application data in `autocard_creation_transaction_journal` and batch repo — no column-level or tablespace encryption enforced at app layer | PCI DSS Req 3.5 |
| No log sanitisation | No PII masking before log write | GLBA, CCPA |
| No data retention/purge | Transaction journal and BATCH_* tables grow unbounded | Internal data governance |
