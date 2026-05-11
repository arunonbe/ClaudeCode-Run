# chargeback-engine_LIB — Business Analyst View

## Business Purpose

`chargeback-engine_LIB` is a batch automation library that processes prepaid-card chargebacks without manual intervention. It coordinates three distinct systems — a card-processing ODS (identified in properties as "FDR" / First Data Resources), an internal reporting/vendor database, and the core ecount card-account system — to execute chargeback disputes end-to-end: submit the dispute to the card processor, record the outcome, apply a fee to the cardholder account, and queue a comment on the account record.

The library is packaged as a runnable JAR (`jar-with-dependencies`) and is intended to be invoked as a scheduled batch job. The comment authored in `ChargebackHelper.java` (line 10) states: "Call FDR, update our database, and update ECountCore."

---

## Business Capabilities

| Capability | Where Implemented |
|---|---|
| Chargeback batch initiation | `ChargebackMain.java` — calls `exec chargeback_process_begin` stored procedure |
| Multi-record parallel chargeback processing | `ChargebackProcessor.java` (RowCallbackHandler) + `ThreadPoolExecutor` in `ChargebackMain.java` |
| Dispute submission to card processor (FDR ODS) | `FDRODSChargebackDAO.java` — executes a query string received in the `query` column; returns `CB_PRCS_ID` on success |
| Outcome recording (reporting/vendor DB) | `ChargebackHelper.java` line 42 — `exec chargeback_process_callback <chargeback_id>, '<result>'` |
| Fee application and account comment (core DB) | `ChargebackHelper.java` line 60 — `exec chargeback_process_core_callback '<comment>', <fee_amount>, '<dda_number>'` |
| Fee suppression on failure | `ChargebackHelper.java` lines 55-57 — sets `fee_amount` to `0` when ODS returns an error |
| Process lifecycle management | `ChargebackMain.java` — calls `chargeback_process_end` with status `2` (success) or `3` (error) |
| Manual process_id override | `ChargebackMain.java` lines 49-54 — accepts `process_id` as command-line argument |

---

## Business Entities

| Entity | Source Evidence |
|---|---|
| Chargeback record | `ChargebackProcessor.java` — row retrieved via `exec chargeback_process_service <process_id>`; stored in `Hashtable<String,Object>` |
| `chargeback_id` | `ChargebackHelper.java` line 42 — key in the chargeback record map |
| `dda_number` | `ChargebackHelper.java` line 60 — demand deposit account identifier passed to core callback |
| `fee_amount` | `ChargebackHelper.java` lines 55-57, 60 — numeric fee applied or zeroed-out |
| `description` | `ChargebackHelper.java` lines 51, 57 — human-readable description embedded in account comment |
| `query` | `ChargebackHelper.java` line 35 — pre-built SQL/RPC query string fetched from the reporting DB and forwarded to the ODS |
| Process run | `ChargebackMain.java` — `process_id` integer returned by `chargeback_process_begin` |
| `CB_PRCS_ID` | `FDRODSChargebackDAO.java` line 56 — identifier returned by FDR ODS on successful chargeback |

---

## Business Rules & Validations

1. **Process gate**: `chargeback_process_begin` must return a non-negative `process_id`; a negative value causes immediate `System.exit(1)` (`ChargebackMain.java` lines 73-76). This prevents duplicate or overlapping runs.
2. **Fee suppression on ODS failure**: If the FDR ODS does not return a string starting with `"OK"`, `fee_amount` is forced to `0` before the core callback (`ChargebackHelper.java` lines 53-57). No fee is charged unless the processor confirms the chargeback.
3. **Comment categorisation**: Successful disputes produce comment `"No authorization chargeback: <description>"`; failed disputes produce `"Automatic chargeback failed: <result> <description>"` (`ChargebackHelper.java` lines 51, 57).
4. **Error propagation**: Any `DataAccessException` in either callback sets the shared `Context.has_errors` flag, which causes `chargeback_process_end` to be called with status `3` (error) and the JVM to exit with code `1`.
5. **Thread-pool drain**: The main thread calls `threadPool.awaitTermination(threadTerminationWaitSecs, ...)` — default 3600 seconds — before writing the end-process record, ensuring all chargeback records are attempted before finalisation.
6. **Single-quote sanitisation**: Raw `replace("'", "")` applied to ODS result and description strings before interpolating into SQL calls (`ChargebackHelper.java` lines 35, 51, 57). This is the only input-cleaning step present.

---

## Business Flows

```
BATCH START
    |
    v
chargeback_process_begin  (Reporting DB)
    |
    +-- returns process_id
    v
chargeback_process_service <process_id>  (Reporting DB)
    |  (streams rows; each row is one chargeback to process)
    |
    For each row (parallel, up to threadpoolsize=20 threads):
        |
        v
        FDR ODS: execute <query>  (ODS via ODBC)
            |
            +-- OK  --> result = "OK - <CB_PRCS_ID>"
            +-- ERR --> result = "ERROR - <cause message>"
        |
        v
        chargeback_process_callback <chargeback_id>, '<result>'  (Reporting DB)
        |
        v
        [if OK]  fee = original fee_amount
        [if ERR] fee = 0
        |
        v
        chargeback_process_core_callback '<comment>', <fee>, '<dda_number>'  (Core DB)
BATCH END
    |
    v
chargeback_process_end <process_id>, 2|3  (Reporting DB)
```

---

## Compliance & Regulatory Concerns

### Reg E — Electronic Fund Transfer Act
- **Chargeback automation without cardholder acknowledgement log**: The engine submits "no-authorization" chargebacks automatically. Reg E §205.11 requires investigation and provisional credit workflows. There is no evidence of a provisional credit step, investigation timer, or cardholder notification within this codebase. These likely exist in the upstream stored procedures, but the library itself provides no audit trail of the Reg E lifecycle.
- **Error resolution comment**: The account comment `"No authorization chargeback: <description>"` is the only cardholder-facing artefact produced here. If this comment is the sole record of dispute initiation, it is insufficient for the 10-business-day investigation window documentation required under Reg E.

### PCI DSS
- **Credentials in plaintext**: `ChargebackProcess.properties` (lines 13-14) contains `ods.username=CBASEAPP` and `ods.password=[REDACTED — rotate immediately]` in cleartext. This is a direct PCI DSS v4.0.1 Requirement 8 violation (protect individual authentication credentials).
- **Additional credentials in settings.xml**: `.mvn/wrapper/settings.xml` (lines 37-50) contains hardcoded plaintext passwords for Nexus and ecount release repositories (`acmng`, `dwil15?`, `d3v0nly`). These are checked into source control.
- **DDA number in SQL string**: `dda_number` is passed directly into a stored-procedure call string. If DDA numbers are considered account data in scope for PCI DSS (applicable to prepaid products), this is relevant to CDE data-handling controls.
- **No encryption of data in transit to ODS**: The ODS connection uses `sun.jdbc.odbc.JdbcOdbcDriver` with `jdbc:odbc:mcyc` — a local ODBC DSN — with no TLS configuration visible. Whether the underlying ODBC DSN encrypts the transport is externally managed and not auditable from this code.

### NACHA / ACH
- No ACH-specific logic found. All processing targets FDR (card processor).

### OFAC
- No sanctions screening or watchlist check present in this library. Expected to be handled upstream.

---

## Business Risks

| Risk | Severity | Evidence |
|---|---|---|
| Plaintext ODS password in source control | Critical | `ChargebackProcess.properties` lines 13-14 |
| Plaintext Nexus/repo passwords in settings.xml | High | `.mvn/wrapper/settings.xml` lines 37-50 |
| No idempotency guard beyond `process_id` gate | High | If `chargeback_process_begin` is called twice concurrently, both calls could obtain different valid IDs, potentially double-charging cardholders |
| SQL injection via `dda_number` and `description` | High | `ChargebackHelper.java` line 60 — only `'` is stripped; no parameterised queries used anywhere |
| Fee silently zeroed on ODS error — no alerting | Medium | `ChargebackHelper.java` lines 53-57 — log.debug only; business may not know a chargeback dispute was not filed |
| No Reg E provisional credit or notification artefact | Medium | No cardholder notification, no investigation-window tracking |
| Java 6 / Spring 2.5.6 EOL stack in production | High | `pom.xml` lines 54-55, 26-28 — both are long past end of security support |
| Thread-safe flag `has_errors` is not volatile or AtomicBoolean | Medium | `Context.java` line 25 — plain `boolean has_errors`, written from multiple worker threads |
