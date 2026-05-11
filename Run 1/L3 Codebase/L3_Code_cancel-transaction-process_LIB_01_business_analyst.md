# cancel-transaction-process_LIB — Business Analyst View

## Business Purpose

This library implements a **batch cancellation process for pending prepaid card transfers**. Its purpose is to identify transfers that have remained in a PENDING state beyond a configurable age threshold and to invoke the downstream Core (ecount/cbase) cancellation service to resolve them. It operates as a scheduled, headless Java process within the Citi/Northlane prepaid card platform and is a critical housekeeping component in the disbursements lifecycle.

The process supports a **dry-run mode** (`-dryRun` flag) that simulates cancellation without writing to the Core system, used for audit and testing.

---

## Business Capabilities

1. **Stale-transfer detection** — Queries the Core database for pending transactions within a configurable date range (default: between 2 days and 1 day ago, controlled by `cancelAge` and `fromCancelAge` in `ProcessRunData`).
2. **Bulk cancellation** — Iterates over all retrieved pending transfers and calls `ITransferManager.cancel(transfer)` for each via `TransferHelper.cancelTransaction()`.
3. **Debit audit update** — After each successful cancellation, updates an audit record via the `card_balance_debit_update_job` stored procedure (`UpdateDebitAuditInfo`).
4. **Program-scoped execution** — Supports include/exclude lists of Program IDs so that specific programs can be targeted or exempted from the cancellation run.
5. **Targeted single-transfer cancellation** — The `-transfer <UUID>` command-line switch allows a single transfer to be specified (note: as-coded in `Controller.validateParameters()`, passing a `transferId` throws `IllegalArgumentException("Bad boy.")` — this logic appears incomplete or intentionally disabled).
6. **Concurrent execution** — Supports a configurable `ThreadPoolExecutor` for parallel cancellation tasks (`CancelTask` implements `Runnable`).
7. **Retry-on-failure** — Each cancel task retries up to `maxTry` times with a randomised sleep between `minSleepTime` and `maxSleepTime` milliseconds.
8. **JMX runtime monitoring** — Exposes task counts (total, failed, incomplete, finished, retry) and management operations (force-terminate, terminate single task) via JMX through `ControllerJMXExporter` and `appCtx-jmx.xml`.

---

## Business Entities

| Entity | Class / Artifact | Description |
|---|---|---|
| Transfer | `TransferDTO` | The unit of work — a pending financial transfer on a prepaid account |
| Program | `TransferDTO.programId` / `ProcessRunData.includeProgramIds` | The prepaid program the cardholder belongs to |
| Account | `TransferDTO.accountId` mapped from `dda_number` column | The DDA (demand deposit account / prepaid card account) |
| Transaction Type | `TransactionType` | Source/facility integer pair identifying the payment rail or instrument type |
| Transfer State | `TransferState` (enum) | UNKNOWN, PENDING (0), COMMITTED (1), CANCELLED (2) |
| Transaction Phase | `TransactionPhase` (enum) | UNKNOWN, PENDING (1), COMMITTED (0), CANCELLED (2) — note inverted numeric mapping vs TransferState |
| Process Run | `ProcessRunData` | Runtime parameters for a single execution: date range, limits, program filters, retry config |
| Cancel Task | `CancelTask` | Runnable unit of work representing one transfer cancellation attempt |

---

## Business Rules & Validations

All rules are enforced in `Controller.validateParameters()` and `Controller.populateParameters()` unless noted otherwise.

1. **Date range is mandatory.** Both `fromDate` and `toDate` must be non-null before processing. If neither is provided via CLI, they are auto-calculated using `cancelAge` (default 2 days) and `fromCancelAge` (default 1 day) offsets from the current time.
2. **From date must be strictly before to date.** `fromDate.getTime() >= toDate.getTime()` throws `IllegalArgumentException`.
3. **At least one transaction type must be configured.** An empty `transactionTypes` list throws `IllegalArgumentException`.
4. **Include and exclude program lists are mutually exclusive.** Providing both simultaneously throws `IllegalArgumentException`.
5. **Transfer ID CLI switch is disabled.** Passing `-transfer` currently triggers `IllegalArgumentException("Bad boy.")` in `validateParameters()`, indicating the single-transfer mode is intentionally blocked or was never completed.
6. **Transaction limit guard.** `ProcessRunData.limitTransactions` defaults to 101. The stored procedure `core_pending_transactions_inquiry` receives this as `limit_trans`; if the result set exceeds the limit, a `DataLimitException` (error code 2) is thrown and processing halts.
7. **Transfer state/phase sync check.** In `TransferHelper.cancelTransaction()`, if `TransferState` and `TransactionPhase` names do not match, a `StatePhaseOutOfSyncStateException` is thrown and the task is marked FAILED without retry.
8. **End-state idempotency.** Transfers already in COMMITTED or CANCELLED state throw `TransferInEndStateException`, which is treated as a non-error FINISHED outcome in `CancelTask`.
9. **Core error code 14023 mapped.** `CoreErrorType.TRANSFER_IN_END_STATE` (code 14023) from the Core API is caught and treated as a normal end-state, not a failure.
10. **Single-run guard.** `Controller.started` flag prevents the controller from being executed twice within the same JVM session.
11. **Retry cap.** Each `CancelTask` retries up to `maxTry` iterations; failed tasks contribute to the `countFailedTasks` tally, and a non-zero count causes a terminal `ProcessException` after the pool drains.

---

## Business Flows

```
Start
  |
  v
Parse CLI args (-config, -log, -from, -to, -transfer, -dryRun)
  |
  v
Load Spring context (cancelTransactionProcessContext.xml)
  |
  v
Populate date range (if not given via CLI, derive from cancelAge offsets)
  |
  v
Validate parameters (Controller.validateParameters)
  |
  v
For each TransactionType (source/facility pair):
    |
    v
    Query DB: core_pending_transactions_inquiry(programId=null, source, facility, startDate, endDate, limitTrans)
    --> Returns list of TransferDTO
  |
  v
Filter by includeProgramIds / excludeProgramIds
  |
  v
For each TransferDTO (single-threaded or via ThreadPoolExecutor):
    |
    v
    CancelTask.run()
      |
      +--> If dryRun: log only, mark FINISHED
      |
      +--> Else: TransferHelper.cancelTransaction(transfer)
      |          |
      |          +--> Validate TransferState == TransactionPhase name
      |          +--> If COMMITTED or CANCELLED: throw TransferInEndStateException -> FINISHED
      |          +--> If PENDING: call ITransferManager.cancel(transfer) via eCore
      |               |
      |               +--> On CoreBusinessException code 14023: FINISHED
      |               +--> On other CoreBusinessException: CoreCancelFailedException -> FAILED (no retry)
      |               +--> On success: mark FINISHED, call updateDebitAuditInfo(transferId)
      |
      +--> On ProcessException: retry up to maxTry with random sleep
      +--> On StatePhaseOutOfSyncStateException: FAILED (no retry)
  |
  v
Summarise: count FAILED / INCOMPLETE / FINISHED / RETRY
  |
  +--> countFailedTasks > 0 -> throw ProcessException -> exit code 1
  +--> countIncompleteTasks > 0 -> throw ProcessException -> exit code 1
  +--> All FINISHED -> exit code 0
```

---

## Compliance & Regulatory Concerns

- **Prepaid card financial adjustments.** Cancelling a pending transfer reverses a debit or credit on a prepaid card account. Each cancelled transfer must be auditable; the `card_balance_debit_update_job` stored procedure writes an audit record post-cancellation, supporting requirements under **Reg E** (electronic fund transfer error resolution) and internal audit trail obligations.
- **Program-level scoping.** The include/exclude program filter provides the ability to restrict cancellation to specific programs, which is important for client-specific contractual constraints.
- **Dry-run capability.** The `-dryRun` flag allows compliance-safe simulation of the batch before live execution, supporting change-management controls.
- **No PAN or SAD in data model.** The `TransferDTO` does not contain PANs, CVVs, or PINs. The `accountId` field maps from `dda_number` (a DDA number — a potential account identifier), which should be masked or tokenised in logs. No masking is present in the code.
- **Logging of financial identifiers.** `CancelTask` logs `transfer_id` and `transferHelper` logs `transfer_id` at INFO/WARN level. The `FormatLogFactory` does not sanitise output; `dda_number`/`accountId` is not logged in the current code, but the `TransferDTO` carries it in memory.
- **Batch transaction limit.** The hard default limit of 101 transactions per query invocation (`ProcessRunData.limitTransactions`) limits blast radius but may cause operational gaps if more than 101 transfers are pending and the process is not re-run iteratively.

---

## Business Risks

1. **Disabled single-transfer mode.** The `-transfer` CLI switch is parsed but blocked at validation (`"Bad boy."`). This means targeted re-processing of individual failed transfers is not possible without changing code.
2. **Default transaction limit of 101.** If the pending queue grows beyond 101 per transaction type, the process throws `DataLimitException` and halts rather than processing in batches. This represents an operational gap for high-volume programs.
3. **No batch idempotency tracking.** There is no run-completion record written to the database; if the process crashes mid-run, already-cancelled transfers may be re-queried on the next run (Core's end-state detection prevents double-cancellation, but it still incurs unnecessary API calls).
4. **No alerting or notification.** Failures are logged and a non-zero exit code is returned, but there is no built-in alerting mechanism. Monitoring depends entirely on external job-scheduling infrastructure detecting the exit code.
5. **Program filter interaction with transfer limits.** Filtering by program is done post-query in application code. If many transfers match the query but most are excluded by program filter, the 101-record limit may prevent the desired transfers from being returned.
