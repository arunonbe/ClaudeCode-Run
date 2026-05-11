# Solution Architect View — fdr-batch-reports-processing_LIB

## Complete Class/Method Inventory

### Package: `com.ecount.batch.fdr.reports`

**`FDRBatchReportsMain`** — Entry point and orchestrator
- `main(String[] args)`: Parses optional config path arg, initializes, runs pre-processing SPs, processes three report types in sequence, runs post-processing SPs, cleans up.
- `initialize(String[] args)`: Loads config, configures Log4j.
- `executePreProcessingStoredProcedures()`: Iterates enabled pre-processing SPs and calls `DBStoredProcedureExecuter.execute()`.
- `executePostProcessingStoredProcedures()`: Iterates enabled post-processing SPs and calls `DBStoredProcedureExecuter.execute()`.
- `getReportReader(Reports, config, logger)`: Delegates to `ReportReaderFactory.getReader()`.
- `processReport(Reports, IFDRReportReader)`: Dispatches to forward-only or set-mode processing.
- `processReportDataReadforwardMode(Reports, IFDRReportReader, IReportProcessor)`: Streams records one-at-a-time through the processor; calls `markAsRead()` on completion.
- `processReportDataSetMode(Reports, IFDRReportReader, IReportProcessor)`: Loads full dataset into memory, processes, then marks as read.
- `cleanup()`: Logs runtime duration.

**`FDRBatchAddFundsReportProcessor`** — Processes Add Funds report data
- Constructor: Accepts `IFDRReportProcessorConfig`, `Logger`.
- `process(ImportedReportData)`: Full-set mode. Connects to DB, exports all records, removes duplicates, calls post-processing SP.
- `process(IFDRReportForwardOnlyReader)`: Forward-only streaming mode. Connects to DB, iterates reader, exports each record, removes duplicates, calls post-processing SP.
- `connectToTargetDB()`: Opens jTDS JDBC connection to target DB; prepares INSERT statement.
- `exportItem(AddFundsReportItem)`: Executes parameterized INSERT for one record.
- `exportIntoTrargetTable(ImportedReportData)`: Iterates report data and calls `exportItem()`.
- `removeDuplicates()`: Executes batch DELETE to remove already-processed rows and intra-batch duplicates.
- `removeNewRowsAlreadyProcessed(Statement)`: Builds and adds DELETE for rows that match an already-processed row (by member_id, journal_tx_group, amount).
- `removeDuplicateNewRows(Statement)`: Builds and adds DELETE for intra-batch duplicates (same member_id, journal_tx_group, amount, keep lowest ID).
- `executePostProcessingStoredProcedure()`: Calls configured stored procedure(s) via `CallableStatement`.
- `closeConnections()`: Closes statement and connection.
- `getFriendlyName()`: Returns `"Batched-Add-Funds Processor"`.

**`FDRBatchNewAccountReportProcessor`** — Processes New Account report data
- Constructor: Accepts `IFDRReportProcessorConfig`, `Logger`.
- `process(ImportedReportData)`: Full-set mode. Connects, writes to destination, calls post SP.
- `process(IFDRReportForwardOnlyReader)`: Forward-only mode. Connects, iterates, exports, calls post SP.
- `connectToTargetDB()`: Opens jTDS JDBC connection; prepares INSERT for `job_fdr_batch_creation_report`.
- `exportItem(AccountCreationReportItem)`: Executes parameterized INSERT for one record.
- `writeToDestinationTable(ImportedReportData)`: Iterates report data, calls `exportItem()`.
- `executePostProcessingStoredProcedure()`: Calls configured SP via `CallableStatement`.
- `closeConnections()`: Closes statement and connection.
- `getFriendlyName()`: Returns `"Batched-New-Accounts Processor"`.

**`FDRDatabaseNewAccountCreationReportReader`** — Reads new account data from DB
- Constructor: Accepts `IFDRReportProcessorConfig`, `Logger`.
- `read(Reports)`: Full-set mode. Opens connection, queries, processes result set into `ImportedReportData`.
- `start(Reports)`: Forward-only mode initialization. Opens connection and result set.
- `hasMoreElements()`: Returns `rfRs.next()`.
- `getNext(IReportItem)`: Returns next `AccountCreationReportItem` from result set.
- `getReportItemFromResultSet(ResultSet, IReportItem)`: Reads `cardId`, `insertionDate`, `successful`, `message`, `deviceId` from result set row.
- `markAsRead(ImportedReportData)`: Updates `exported_date` on source table.
- `markAsRead(int)`: Updates `exported_date` on source table (forward-only mode).
- `markAsProcessed(Connection, int)`: Executes UPDATE query to set `exported_date = NOW()` for unprocessed rows.
- `close()`: Closes all JDBC resources.
- `getResultSet(Connection)`: Selects between file-based or dynamic query.
- `getResultSetByQueryFile(Connection)`: Executes SQL from external query file.
- `getResultSetDynQuery(Connection)`: Builds and executes dynamic SELECT with INNER JOIN on `core_device_ecard`.
- `openDBConnection()`: Opens jTDS JDBC connection using config properties.
- `getFriendlyName()`: Returns `"FDRDatabaseNewAccountCreationReportReader"`.

**`FDRDatabaseBatchAddFundsReportReader`** — Reads add-funds data from DB
- Constructor: Accepts `IFDRReportProcessorConfig`, `Logger`.
- `read(Reports)`: Full-set mode. Opens connection, queries, processes result set.
- `start(Reports)`: Forward-only mode initialization.
- `hasMoreElements()`: Returns `rs.next()`.
- `getNext(IReportItem)`: Returns next `AddFundsReportItem`.
- `getReportItemFromResultSet(IReportItem)`: Reads `txGroupId`, `amount`, `member_id` from result set row.
- `processResultSet(ImportedReportData)`: Iterates result set into `ImportedReportData`.
- `getResultSetFromDynQuery()`: Builds dynamic SELECT joining `fdr_dda_account_journal` to `core_transaction_journal`.
- `getResultSetFromFileQuery()`: Executes SQL from `batch_add_funds.sql`.
- `getSourceDDAJournalHistoryDaysToConsider()`: Calculates a `Timestamp` X days in the past.
- `openDatabaseConnection()`: Opens jTDS JDBC connection.
- `closeConnections()`: Closes all JDBC resources.
- `markAsRead(ImportedReportData)`: No-op (not required for this report).
- `markAsRead(int)`: No-op.
- `close()`: Calls `closeConnections()`.
- `queryFromFile()`: Returns true if query file exists.
- `getFriendlyName()`: Returns `"(FDRDatabaseBatchAddFundsReportReader)"`.

**`BatchedActionsStatusReader`** — Reads message queue status data
- (Inferred from config; reads from `job_batch_completed_actions_messages` view)

**`BatchedActionsStatusProcessor`** — Processes message status data
- (Inferred from config; writes to `batch_message_status` in `cbaseapp`)

**`DBStoredProcedureExecuter`** — Utility to execute a stored procedure
- `execute(ProcessingStoredProcedure)`: Opens JDBC connection, calls SP via `{ call <name>() }`, returns success/failure.

**`ReportReaderFactory`** — Factory for readers
- `getReader(Reports, config, logger)`: Returns appropriate reader for each report type.

**`ReportProcessorsFactory`** — Factory for processors
- `getReportProcessor(Reports, config, logger)`: Returns appropriate processor for each report type.

### Interfaces
- `IFDRReportReader`: `read(Reports)`, `markAsRead(ImportedReportData)`.
- `IFDRReportForwardOnlyReader`: `start(Reports)`, `hasMoreElements()`, `getNext(IReportItem)`, `markAsRead(int)`, `close()`, `getFriendlyName()`.
- `IReportProcessor`: `process(ImportedReportData)`, `process(IFDRReportForwardOnlyReader)`, `getFriendlyName()`. Inner enum `Reports` = `{FDR_BATCH_NEW_ACCOUNT, FDR_BATCH_ADD_FUNDS, MESSAGE_QUEUE_UPDATES}`.

### Value Objects (package `value`)
- `AddFundsReportItem`: `txGroupId`, `amount`, `memberId`.
- `AccountCreationReportItem`: `cardId`, `deviceId`, `insertionDate`, `successful`, `message`.
- `ActionMessageStatus`: `messageId`, `actionSuccessful`.
- `ImportedReportData`: List container for `IReportItem` instances.
- `IReportItem`: Marker interface.

### Config Objects (package `config`)
- `PropertiesFileConfiguration`: Singleton; loads all config from `.properties` file. Implements `IFDRReportProcessorConfig`.
- `FDRBatchAddFundsDBMapping`: POJO holding all Add Funds DB connection params and field names.
- `FDRNewAccountCreateReportDBMapping`: POJO holding all New Account DB connection params and field names.
- `BatchedActionsStatusDBMapping`: POJO holding all Message Status DB connection params and field names.
- `ProcessingStoredProcedure`: POJO holding SP name, DB connection params, enabled flag.
- `IFDRReportProcessorConfig`: Interface exposing all mapping objects and SP lists.

## Security Vulnerabilities — CRITICAL

### VULN-1: Passwords Logged at DEBUG Level (CRITICAL)
**Files**: `FDRBatchAddFundsReportProcessor.java` line 225, `FDRBatchNewAccountReportProcessor.java` line 156, `FDRDatabaseNewAccountCreationReportReader.java` line 481, `FDRDatabaseBatchAddFundsReportReader.java` line 272  
**Detail**: The JDBC connection URL including username AND password is logged: `"trying to open DB connection to " + connectionString.toString()`. The connection string is `jdbc:jtds:sqlserver://server:port/db;instance=X;user=Y;password=Z`.  
**PCI DSS**: Violates Requirement 3 (protect stored account data) and Requirement 8.  
**Priority**: P0 — Immediate fix required.

### VULN-2: Log4j 1.x (CRITICAL — CVE-2019-17571)
**File**: `pom.xml` line 11, `log4j:log4j:1.2.14`  
**Detail**: Log4j 1.x is end-of-life since 2015. CVE-2019-17571 allows remote code execution via a malicious serialized object sent to the SocketServer (not used here, but the dependency itself is vulnerable).  
**Priority**: P0.

### VULN-3: jTDS 1.2.2 (HIGH — EOL Driver)
**File**: `pom.xml` line 18  
**Detail**: jTDS is no longer maintained. The recommended replacement is `com.microsoft.sqlserver:mssql-jdbc`. jTDS 1.2.2 has known issues with SQL Server 2012+ features and lacks TLS 1.2 support in older configurations.  
**Priority**: P1.

### VULN-4: Plaintext Credentials in Properties File (HIGH)
**File**: `FDRBatchReportsProcessor.properties` lines 17–19, 25, 66, 117–118  
**Detail**: Database passwords stored in plaintext in a config file on the filesystem.  
**Priority**: P1 — Replace with secrets management (e.g., Azure Key Vault).

### VULN-5: `PropertiesFileConfiguration` is a non-thread-safe Singleton (MEDIUM)
**File**: `PropertiesFileConfiguration.java` line 206–213  
**Detail**: The `getInstance()` method is not synchronized. In a multi-threaded context (e.g., if this library were used in a Spring Boot context), two threads could create two instances simultaneously.  
**Priority**: P3 (low risk given batch execution model, but a code quality issue).

## Remediation Priority Summary

| Priority | Item |
|----------|------|
| P0 | Remove password from connection string log statement (4 files) |
| P0 | Replace Log4j 1.x with Log4j 2.x or Logback |
| P1 | Replace jTDS with Microsoft JDBC Driver |
| P1 | Move credentials to secrets management |
| P2 | Upgrade Java from 1.5 to 17 |
| P2 | Add OWASP dependency check to Maven build |
| P3 | Fix non-thread-safe Singleton |
| P3 | Replace individual INSERT with batch INSERT for performance |
