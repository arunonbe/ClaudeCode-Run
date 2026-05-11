# Solution Architect View — job-order-synchronization_LIB

## Complete Class and Method Inventory

### Package `com.ecount.service.jobordersync`

| Class | Purpose |
|---|---|
| `Main` | CLI entry point; bootstraps Spring context from `applicationContext.xml` and invokes `JobOrderSynchronizer.synchronize()` |
| `JobOrderSynchronizer` | Core orchestrator. Manages run windows, retry of failed events, and delegates to `synchronizeEvent()` and `synchronizeJob()` |
| `JobOrderLibrary` | Facade over Order Service HTTP Invoker calls: `jobCreateFileOrder()`, `jobPostJobOrders()`, `jobPostCompletedJobOrders()`, `jobUpdateOrderStatus()` |
| `JobOrderStatusMapper` | Maps `JobStatus` → `OrderStatus` using a constructor-injected `Map`; pure value transformation |
| `JobOrderSyncException` | Unchecked runtime exception for fatal sync failures (e.g., Order Service unavailable) |
| `JobServiceException` | Unchecked exception for job lookup failures in DAO layer |
| `Constants` | Static constants (not detailed in read — likely connection/config keys) |
| `ResourceMessages` | Enum-based parameterized message catalog for all log/error messages |
| `UsageException` | Thrown when CLI arguments are invalid |

### Package `com.ecount.service.jobordersync.dao`

| Interface | Purpose |
|---|---|
| `JobDao` | Contract for all `job_file` and `job_order_sync_event` database operations |
| `OrderDao` | Contract for all `file_order` database/API operations |

### Package `com.ecount.service.jobordersync.dao.jdbc`

| Class | Purpose |
|---|---|
| `JdbcJobDao` | `JobDao` implementation using Spring `JdbcTemplate` |
| `JdbcOrderDao` | `OrderDao` implementation — wraps Order Service HTTP Invoker client |
| `AbstractFileJobInquiry` | Base class for stored-procedure-style queries against `job_file` |
| `FileJobIdInquiry` | Lookup job record by `job_id` |
| `FileJobInquiry` | Bulk lookup by date range (`from_date`, `to_date`) |
| `FileJobStatusInquiry` | Lookup job record checking status |
| `FileOrderInquiry` | Lookup `file_order` by `job_id` or `file_id` |
| `FileOrderUpdateStatus` | Direct DB write to update `file_order` status (used in `forceStatus` mode) |
| `IssueCardCountActualByLocationCode` | Query for card issuance actuals per location — used in order breakdown |
| `JobOrderActualsByJobidBrokendown` | Queries `job_order_actuals` for split-job reconciliation |
| `JobOrderByJobidBrokendown` | Queries `job_order` for split-job reconciliation |
| `JobOrderSyncEventInquiry` | Reads/writes `job_order_sync_event` records |

### Package `com.ecount.service.jobordersync.domain`

| Class | Purpose |
|---|---|
| `FileJob` | Value object representing a `job_file` row |
| `FileOrder` | Value object representing a `file_order` row |
| `JobLocationData` | Card location data for multi-location job breakdown |
| `JobOrder` | Value object for `job_order` rows |
| `JobOrderActual` | Actual outcome quantities per job order |
| `JobOrderActualWithOrigJobId` | JobOrderActual extended with `origJobId` for split-job logic |
| `JobOrderSyncEvent` | Value object for `job_order_sync_event` rows; tracks counts and attempt state |
| `JobOrderWithOrigJobId` | JobOrder extended with `origJobId` for split-job logic |
| `JobStatus` | Enum of all Job Service status codes |
| `OrderStatus` | Enum of all Order Service status codes |

### Package `com.ecount.service.common`

| Class | Purpose |
|---|---|
| `Symbol` | Value object for symbol/program identifiers |
| `SymbolEnum` | Enum of symbol types |

## Key Method Signatures — `JobOrderSynchronizer`

```java
// Main entry point — returns true if all jobs synced with zero failures
public boolean synchronize()

// Single-job synchronization (used with --jobId CLI flag)
public boolean synchronize(int jobId)

// Inner: processes all jobs in a date window, updates the sync event record
private void synchronizeEvent(JobOrderSyncEvent event)

// Inner: processes a single job against its order counterpart
private void synchronizeJob(FileJob job, int jobIndex, JobOrderSyncEvent event)

// Inner: creates a new file_order when none exists
private boolean createOrder(FileJob job, int jobIndex)

// Inner: updates an existing file_order to match Job status
private boolean updateOrder(FileJob job, FileOrder order, int jobIndex)

// Emergency: directly writes order status, bypasses Order Service API
private void forceUpdateOrderStatus(FileJob job, int jobIndex, JobOrderSyncEvent event, RuntimeException ex)

// Checks if job has failed actions (used to determine PENDING_CORRECTION vs PROCESSED)
private boolean hasErrors(FileJob job)
```

## Security Vulnerabilities

### SV-1: No Concurrent-Run Protection (HIGH)
There is no database lock, distributed lock, or file lock preventing two instances of the synchronizer from running simultaneously. If scheduled twice or restarted mid-run, both instances would read the same `job_file` records and make duplicate Order Service calls. This could result in duplicate `jobPostJobOrders` calls, which may create duplicate financial records in the Order Service. **Priority: HIGH** — add a `SELECT ... WITH (UPDLOCK)` on `job_order_sync_event` or a `MERGE` upsert pattern to serialize runs.

### SV-2: Force-Status Bypasses API Validation (MEDIUM)
The `forceUpdateOrderStatus()` method writes directly to the Order Service database via `orderDao.updateFileOrderStatus()`, bypassing any server-side business rule validation. In a PCI-regulated environment, direct DB writes to billing records without API-layer controls is an audit finding. **Priority: MEDIUM** — remove the direct-write path; instead, add a force-override endpoint to the Order Service API that includes audit logging.

### SV-3: `System.exit(3)` Without Cleanup (LOW)
`JobOrderSynchronizer.synchronize()` line 70 calls `System.exit(3)` if the Order Service ping fails. This hard exit does not allow Spring to shut down cleanly, which could leave database connections unclosed or partially written `job_order_sync_event` rows. **Priority: LOW** — replace with exception propagation and graceful shutdown.

### SV-4: No Input Validation on `--jobId` Parameter (LOW)
The `jobId` CLI parameter is passed to `jobDao.getFileJob(jobId)` without range validation or SQL injection protection beyond JDBC parameterization. The existing JDBC PreparedStatement binding is adequate, but the parameter should be validated as a positive integer before use. Source: `Main.java` (inferred) + `JobOrderSynchronizer.java` line 84.

### SV-5: HTTP Invoker Uses Java Object Serialization (HIGH)
The `FileOrderManager` HTTP Invoker client uses Java's built-in serialization over HTTP, which is vulnerable to deserialization attacks if the endpoint is exposed beyond the internal network. PCI DSS Requirement 6.2.4 requires protection of web-facing services against injection attacks including deserialization exploits. **Priority: HIGH** — replace with REST/JSON API.

### SV-6: Hibernate Annotations Dependency on Ancient Version (MEDIUM)
`hibernate-annotations:3.2.0.cr3` (2006) is included as `provided` scope. Even though it may not be active at runtime, it introduces a vulnerable transitive dependency and signals that the codebase may still carry dead annotation-driven ORM code. **Priority: MEDIUM** — remove entirely if not used.

## Technical Debt Summary

| Item | Severity | File | Notes |
|---|---|---|---|
| Spring 2.0 XML beans | HIGH | `applicationContext.xml` | No @Component; full XML rewrite needed for Spring Boot |
| HTTP Invoker deserialization | HIGH | `applicationContext.xml` lines 60–71 | Replace with REST |
| No unit/integration tests | HIGH | entire repo | Zero test coverage; all changes are high-risk |
| Concurrent-run race condition | HIGH | `JobOrderSynchronizer.java` | No locking |
| `System.exit()` in library code | MEDIUM | `JobOrderSynchronizer.java` line 70 | Prevents graceful shutdown |
| `forceStatus` direct DB write | MEDIUM | `JobOrderSynchronizer.java` line 438 | Bypasses Order Service validation |
| Hibernate 3.2.0.cr3 dependency | MEDIUM | `pom.xml` line 95 | Ancient CVE surface area |
| Log4j 1.x (inferred from log4j.properties) | HIGH | `src/main/resources/log4j.properties` | Log4j 1 is EOL; log4shell-adjacent risk if classpath |

## Remediation Priority

1. **Immediate**: Replace HTTP Invoker with REST (SV-5) — blocks Java 17 migration and is a security requirement
2. **Short-term**: Add concurrent-run locking (SV-1)
3. **Short-term**: Add test coverage for `synchronizeJob()` status mapping paths
4. **Medium-term**: Migrate to Spring Boot, remove XML wiring
5. **Long-term**: Remove `forceStatus` DB write path in favour of an Order Service API override endpoint
