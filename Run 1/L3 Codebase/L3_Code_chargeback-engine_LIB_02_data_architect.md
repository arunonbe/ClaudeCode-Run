# chargeback-engine_LIB — Data Architect View

## Data Stores

Three distinct data stores are used. All are relational SQL databases accessed via Spring `JdbcTemplate`.

| Logical Name | Bean ID | DAO Class | Connection Source | Properties Key |
|---|---|---|---|---|
| Core (ecount card accounts) | `coreDataSource` | `CoreGenericDAO` | Director service (DBCP-managed) | `core_agent=b2ctest`, `core_database=ecountcore` |
| Reporting / Vendor | `vendorDataSource` | `ReportingGenericDAO` | Director service (DBCP-managed) | `vendor_agent=b2ctest`, `vendor_database=vendor` |
| ODS (FDR card processor) | `ODSDataSource` | `FDRODSChargebackDAO` | Apache DBCP via JDBC-ODBC bridge | `ods.url=jdbc:odbc:mcyc` |

- **Core** and **Reporting** data sources are provisioned through a proprietary `DirectorConfiguredDBCPdatasourceCreator` factory bean (`com.ecount.Core2.system.dal.ds.DirectorConfiguredDBCPdatasourceCreator`) declared in `ChargebackProcess.xml` lines 12-14. The Director service at `http://ppamwdcddcor1:80/service/dispatch.asp` resolves agent+database name to actual JDBC connection parameters at runtime.
- **ODS** connects via `sun.jdbc.odbc.JdbcOdbcDriver` to a local ODBC DSN named `mcyc` (two commented-out alternatives: `CBasclntCatM`, `mcycase`), configured directly in properties with hardcoded credentials.

---

## Schema & Tables

No DDL or schema files are present in the repository. All database interaction occurs exclusively through stored procedures. The procedures inferred from code are:

| Procedure | Database | Called From | Purpose |
|---|---|---|---|
| `chargeback_process_begin` | Reporting/Vendor | `ChargebackMain.java` line 62 | Starts a new process run; returns `process_id` |
| `chargeback_process_service <process_id>` | Reporting/Vendor | `ChargebackMain.java` line 84 | Streams all chargeback rows to be processed |
| `chargeback_process_callback <chargeback_id>, '<result>'` | Reporting/Vendor | `ChargebackHelper.java` line 42 | Records ODS outcome per chargeback record |
| `chargeback_process_end <process_id>, <status>` | Reporting/Vendor | `ChargebackMain.java` lines 119, 121 | Marks process complete with status 2 (OK) or 3 (error) |
| `chargeback_process_core_callback '<comment>', <fee_amount>, '<dda_number>'` | Core | `ChargebackHelper.java` line 60 | Applies fee, blocks account, queues comment |
| ODS query (dynamic, per chargeback row) | FDR ODS | `ChargebackHelper.java` line 35 | Submits individual chargeback to card processor |

**Row structure** returned by `chargeback_process_service`: Inferred from field references in `ChargebackHelper.java` and `ChargebackProcessor.java`:

| Column | Type | Usage |
|---|---|---|
| `chargeback_id` | INTEGER | Chargeback record identifier |
| `query` | VARCHAR/CLOB | Pre-built SQL/RPC string to execute against FDR ODS |
| `description` | VARCHAR | Human-readable chargeback description; embedded in account comment |
| `fee_amount` | INTEGER | Fee to apply; zeroed on ODS failure |
| `dda_number` | VARCHAR | Demand deposit account number; passed to core callback |

---

## Sensitive Data Handling

| Data Element | Sensitivity | Handling |
|---|---|---|
| `dda_number` | High (account identifier, potentially in PCI scope for prepaid) | Passed as inline string literal in stored-procedure call; no masking, no parameterisation |
| `fee_amount` | Medium | Integer; no special handling required |
| `description` | Medium | Contains chargeback description; single-quote stripped before SQL interpolation only |
| ODS username (`CBASEAPP`) | Credential | Stored plaintext in `ChargebackProcess.properties` line 13, committed to git |
| ODS password (`ECOUNT`) | Credential | Stored plaintext in `ChargebackProcess.properties` line 14, committed to git |
| Nexus password (`dwil15?`) | Credential | Stored plaintext in `.mvn/wrapper/settings.xml` line 39 |
| ecount release password (`d3v0nly`) | Credential | Stored plaintext in `.mvn/wrapper/settings.xml` lines 46, 50 |
| Wirecard proxy password (`acmng`) | Credential | Stored plaintext in `.mvn/wrapper/settings.xml` line 37 |
| `query` column | High — may contain account-level identifiers | Executed verbatim against ODS without sanitisation beyond quote-stripping |

There is **no evidence** of encryption, tokenisation, or masking applied to any data element within this codebase. The `dda_number` is written directly into a log comment and a stored-procedure call string.

---

## Encryption & Protection

- **Data at rest**: Not managed by this library. No encryption APIs, key management, or vault references are present.
- **Data in transit (Core / Reporting)**: TLS is implicitly delegated to the Director service's DBCP connection factory; not verifiable from this code.
- **Data in transit (ODS)**: `sun.jdbc.odbc.JdbcOdbcDriver` + `jdbc:odbc:mcyc` — transport security depends entirely on the ODBC DSN configuration on the host OS. The JDBC-ODBC bridge itself does not provide TLS. This is a significant gap for a connection that carries card-processor interactions.
- **Credentials**: All passwords are cleartext in committed configuration files. No environment-variable injection, secrets manager, or vault integration is present. `GITHUB_TOKEN` is the one exception — it is referenced as `${env.GITHUB_TOKEN}` in `settings.xml` line 54 — but ODS and database credentials are not similarly externalised.

---

## Data Flow

```
[Reporting DB]
    chargeback_process_begin  --> process_id (integer)
    chargeback_process_service --> stream of rows:
        { chargeback_id, query, description, fee_amount, dda_number }
        |
        |-- query string -------> [FDR ODS via ODBC]
        |                             --> result: "OK - <CB_PRCS_ID>" | "ERROR - <msg>"
        |
        |-- (chargeback_id, result) --> chargeback_process_callback [Reporting DB]
        |
        |-- (comment, fee_amount|0, dda_number) --> chargeback_process_core_callback [Core DB]

    chargeback_process_end (process_id, 2|3) [Reporting DB]
```

Data originates in the Reporting/Vendor database (chargeback cases to process), flows out to FDR ODS, and results flow back into both the Reporting and Core databases. No data is written to disk or external files beyond the log file `chargeback_engine.log`.

---

## Data Quality & Retention

- **No retry logic**: If an ODS call fails, the error is logged and `fee_amount` is zeroed; the record is not re-queued. A failed chargeback results in a `chargeback_process_callback` with `"ERROR - <msg>"` and the process moves on.
- **No dead-letter handling**: Failed records are not moved to an error queue or separate table by this library; that responsibility lies with the stored procedures.
- **Log retention**: `log4j.xml` configures `RollingFileAppender` with `MaxFileSize=10000KB` and `MaxBackupIndex=10` (max ~100 MB total log retention). The log file is named `chargeback_engine.log` and is not time-stamped, so it overwrites on each fresh deployment run (Append is commented out).
- **Result truncation**: CLOB columns are truncated to 8000 characters (`ChargebackProcessor.java` line 75). This affects any large text fields in the result set.
- **No data validation** of incoming row fields beyond null-skipping (`ChargebackProcessor.java` line 45).

---

## Compliance Gaps

| Gap | Regulation | Detail |
|---|---|---|
| Plaintext credentials in source control | PCI DSS v4.0.1 Req 8.3, Req 6.3 | `ods.password=[REDACTED — rotate immediately]` in `ChargebackProcess.properties`; multiple passwords in `settings.xml` |
| No parameterised queries | PCI DSS v4.0.1 Req 6.2 (secure coding) | All stored-procedure calls built via string concatenation |
| ODS transport encryption not enforced | PCI DSS v4.0.1 Req 4.2 | JDBC-ODBC bridge with no TLS configuration |
| No audit trail of chargeback lifecycle events | Reg E §205.11, PCI DSS Req 10 | The library logs to a rolling file but no structured audit record is written to a database |
| DDA number passed in cleartext SQL string | PCI DSS Req 3 (protect stored data) | `dda_number` embedded inline in stored-procedure call at `ChargebackHelper.java` line 60 |
| Non-volatile shared boolean `has_errors` | Data integrity | `Context.java` line 25 — race condition under concurrent thread writes |
