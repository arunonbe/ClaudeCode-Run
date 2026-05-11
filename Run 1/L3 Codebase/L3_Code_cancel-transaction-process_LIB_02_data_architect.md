# cancel-transaction-process_LIB — Data Architect View

## Data Stores

Two distinct relational databases are accessed, configured via Spring XML dependency injection with the `DirectorConfiguredDBCPdatasourceCreator` factory (ecount Director-managed connection pool):

| Logical Name | Spring Bean ID | Property Key | Purpose |
|---|---|---|---|
| Core (ecount) DB | `coreDataSource` | `${ecountcore.database}` | Source of pending transfer records; queried via `core_pending_transactions_inquiry` stored procedure |
| CBase App DB | `cbaseappDataSource` | `${cbaseapp.database}` | Target for debit audit updates; written via `card_balance_debit_update_job` stored procedure |

Both data sources are managed by `DirectorConfiguredDBCPdatasourceCreator` (`com.ecount.Core2.system.dal.ds`) with the `director.address` property pointing to the ecount Director service for dynamic database configuration. Connection pooling is provided by Apache Commons DBCP (`commons-dbcp:1.2.2`, `commons-pool:1.4`).

---

## Schema & Tables

No DDL files are present in the repository. Schema evidence is derived entirely from DAO code.

### Core DB — Read Access

**Stored procedure: `core_pending_transactions_inquiry`** (called as a function; `setFunction(true)` in `CorePendingTransactionsInquiry.java`)

Input parameters (from `CorePendingTransactionsInquiry` constructor, lines 43–49):

| Parameter | SQL Type | Source |
|---|---|---|
| `program_id` | VARCHAR | `PendingTransactionGroupParameter.programId` (always `null` in current code — `Controller.java` line 75) |
| `source` | INTEGER | `TransactionType.source` |
| `facility` | INTEGER | `TransactionType.facility` |
| `start_date` | TIMESTAMP | `ProcessRunData.fromDate` |
| `end_date` | TIMESTAMP | `ProcessRunData.toDate` |
| `limit_trans` | INTEGER | `ProcessRunData.limitTransactions` (default 101) |

Output result set columns mapped in `CorePendingTransactionsInquiry.mapRow()` (lines 100–111):

| Column Name | Java Field | Java Type |
|---|---|---|
| `program_id` | `TransferDTO.programId` | String |
| `dda_number` | `TransferDTO.accountId` | String |
| `amount` | `TransferDTO.amount` | long |
| `created` | `TransferDTO.created` | Date |
| `device_id` | `TransferDTO.deviceId` | String |
| `facility` | `TransferDTO.facility` | int |
| `phase` | `TransferDTO.phase` | int |
| `source` | `TransferDTO.source` | int |
| `transaction_id` | `TransferDTO.transactionId` | String |
| `transaction_state` | `TransferDTO.transactionState` | int |
| `transfer_id` | `TransferDTO.transferId` | String |
| `transfer_state` | `TransferDTO.transferState` | int |

Return value parameter: `RETURN_VALUE` (INTEGER); code 0 = success, code 2 = limit exceeded (`DataLimitException`).

### CBase App DB — Write Access

**Stored procedure: `card_balance_debit_update_job`** (`UpdateDebitAuditInfo.java`, line 31)

| Parameter | SQL Type | Source |
|---|---|---|
| `transfer_id` | VARCHAR | `TransferDTO.transferId` |

No output parameters or result sets are declared; the procedure is called for its side-effect only (updating audit/state in the CBase application database).

---

## Sensitive Data Handling

| Field | Sensitivity | Handling |
|---|---|---|
| `dda_number` (mapped to `accountId`) | Account identifier — potentially a prepaid card DDA number | Stored in `TransferDTO` in-memory; **never logged** by any DAO or helper class in the current code. Not masked. |
| `transfer_id` | Financial transaction identifier (UUID) | Logged extensively at INFO/WARN/ERROR level (e.g., `CancelTask` lines 80, 93–100, `CorePendingTransactionsInquiry` line 113). |
| `amount` | Transaction amount (long, likely minor currency units) | Held in `TransferDTO`; not logged in any identified log statement. |
| `program_id` | Program identifier | Logged indirectly via `TransactionType` (source/facility), not by name. |
| `device_id` | Device identifier associated with the transaction | In `TransferDTO`; not logged. |

**Critical observation:** The `dda_number` column is mapped to `accountId` in `TransferDTO`. In prepaid card environments, a DDA number is a sensitive account identifier. No tokenisation, masking, or encryption is applied before the value is held in the JVM heap. This may constitute a PCI DSS or Reg E concern depending on whether the DDA number is itself a payment account number (PAN) or a surrogate.

---

## Encryption & Protection

- **No field-level encryption** is present in any DAO, DTO, or helper class.
- **Database credentials** are not hardcoded in any XML or Java file; they are resolved at runtime through the ecount Director service via `DirectorConfiguredDBCPdatasourceCreator`. This is an indirect credential management mechanism — the security properties of the Director service are not visible in this repository.
- **Transport encryption** (TLS for JDBC connections) is not configured in the `dataSource.xml`; it relies entirely on the Director-managed DBCP configuration.
- **No secrets in source code** were identified in any scanned file.

---

## Data Flow

```
[Core DB]
    |
    | core_pending_transactions_inquiry(source, facility, startDate, endDate, limitTrans)
    | Returns: transfer_id, dda_number, amount, phase, transaction_state, transfer_state, ...
    v
[TransferDTO list in JVM heap]
    |
    | filtered by program include/exclude list
    v
[CancelTask per TransferDTO]
    |
    | TransferHelper.cancelTransaction(dto)
    | --> Reads: transferId, transferState, phase from DTO
    | --> Calls: ITransferManager.cancel(Transfer{id=transferId}) -- eCore/Core API (not DB direct)
    v
[Core API / eCore (com.cbase.business.core.impl.TransferManagerImpl)]
    |
    | On success:
    v
[CBase App DB]
    |
    | card_balance_debit_update_job(transfer_id)
    v
  Audit record updated
```

The process does **not** write to the Core DB directly; all state transitions in the Core system are performed through the `ITransferManager` service API.

---

## Data Quality & Retention

- **`program_id` is always NULL** when calling `core_pending_transactions_inquiry` (hardcoded `parameter.programId = null` in `Controller.java` line 75). This means the stored procedure receives no program filter at the database level; filtering is performed in-application after retrieval.
- **Limit of 101 records per query.** If more than 101 pending transactions exist for a source/facility combination within the date window, a `DataLimitException` is thrown and processing halts. No pagination or cursor-based retrieval exists.
- **Numeric state encoding inconsistency:** `TransferState.PENDING = 0`, `TransferState.COMMITTED = 1`, `TransferState.CANCELLED = 2`. However, `TransactionPhase.PENDING = 1`, `TransactionPhase.COMMITTED = 0`, `TransactionPhase.CANCELLED = 2`. The integer-to-enum mapping is asymmetric between these two types, which represents a data quality risk: the state/phase sync check in `TransferHelper` compares enum *names* (not codes), so a transfer with `transfer_state=0` (PENDING) and `phase=1` (also PENDING) would pass the check correctly — but the inverted numeric encodings could be confusing and bug-prone for future maintainers.
- **No data retention policy** is implemented in this library. The process consumes and cancels data but does not delete or archive records.

---

## Compliance Gaps

1. **`dda_number` is not masked in logs or masked in-memory.** If this value maps to any portion of a prepaid PAN, PANs must never be stored unprotected (PCI DSS Requirement 3.3). Confirm with the security team whether `dda_number` is a full or partial PAN.
2. **No database query audit trail.** The process reads from and writes to the database but does not record its own execution (start time, end time, records processed, user context) in any audit table within this codebase.
3. **Connection pool configuration not visible.** DBCP pool parameters (max connections, timeout, eviction) are delegated entirely to the Director service. This makes it difficult to validate connection limits are appropriate for PCI DSS-compliant resource management.
4. **No input validation on stored procedure parameters.** Date range and limit values are passed directly from `ProcessRunData` to the stored procedure without bounds checking beyond the basic null/order validation in `Controller.validateParameters()`.
