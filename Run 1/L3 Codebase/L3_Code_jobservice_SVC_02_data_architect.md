# Data Architect View — jobservice_SVC

## 1. Data Architecture Overview

`jobservice_SVC` is a **SQL Server-backed, Spring XML-configured service** that manages the lifecycle of batch payment jobs and their constituent actions. Its data architecture is rooted in the `jobsvc` database (job management and action queue) and `cbaseapp` database (cardholder core data). The service does not use an ORM — it relies on raw JDBC via stored procedures, a legacy pattern consistent with its ~2010 origins.

## 2. Primary Data Stores

### 2.1 jobsvc Database (SQL Server)

The primary operational store for all job and action data. Accessed via `JobSvcDataSource` (bean aliased as `jobsvcDS`), sourced from `appCtx-jobsvc-ds.xml` in the classpath.

Key logical entities (inferred from XML context files and Java service methods):

| Logical Table / Object | Purpose | Sensitivity |
|---|---|---|
| `job_file` | Job file lifecycle record (status, dates, agent, format) | Business data |
| `job_batch` | Batch grouping for a job file | Business data |
| `job_action` | Individual action record within a batch (one per recipient record) | PII (partnerUserId, action type) |
| `job_action_error` | Error details for failed actions | PII adjacent |
| `job_fee` | Computed fee records for client billing | Financial |
| `job_account_map` | Temporary mapping of client partnerUserId to internal eMember/eCount IDs | PII (external → internal ID mapping) |
| `job_profile` | Job processing profile configuration | Configuration |
| `job_notification` | Notification records created for processed recipients | PII adjacent |
| Job file (Repository Service) | Physical batch file stored in Repository Service filesystem | PII / Financial |

Access pattern: All database interactions go through **Director-service** for data source resolution. The Director service dynamically resolves JNDI/JDBC data sources at runtime based on agent/program configuration, rather than hardcoded connection strings.

### 2.2 cbaseapp Database (SQL Server)

The cardholder core database, accessed via `CbaseappDataSource`. The Job Agent action handlers call `AccountService` and `PaymentService` methods that ultimately read/write to `cbaseapp` for:
- Cardholder account creation (RegisterUser, ExtendedRegisterUser)
- Card issuance (IssueCard)
- Fund loading (AddFunds)
- Withdrawal initiation (Withdraw)
- Profile updates (UpdateUser, ExtendedUpdateUser)

`cbaseapp` is the primary PCI DSS Cardholder Data Environment (CDE) database in the legacy platform.

## 3. Data Flows

### 3.1 Inbound (File Intake)
```
Client → Repository Service → file stored
    ↓
JobManager.loadJobFileChecker()
    → job_file record created (status: loading)
    → file parsed / structural validation
    → individual job_action records created (one per batch file row)
    → job_file status updated (validated / failed_structural_validation)
```

### 3.2 Execution (Action Processing)
```
JobManager.runJob() → JMS topic publish (JOB_EXECUTION_QUEUE)
    ↓
JobAgent.process() → polls job_action table
    → checks out action record (status: Processing)
    → dispatches to typed ActionHandler (RegisterUser, AddFunds, etc.)
        → AccountService / PaymentService XmlRPC call
        → cbaseapp write (account, card, funds)
    → updates job_action (status: Completed / Failed)
    → when all actions complete → JobManager.endJob() → job_file archived
```

### 3.3 Reply Files (Output)
```
JobManager.archiveJob()
    → reads completed/failed job_action records from jobsvc DB
    → generates confirmation reply file (successful records)
    → generates exception file (failed records)
    → stores reply files in Repository Service
    → job_file status: Archived
```

## 4. JMS Messaging Architecture

The service supports **four JMS providers**, selected at build time via Maven filter profiles:

| Profile | Provider | Configuration File |
|---|---|---|
| `activemq` | Apache ActiveMQ | `activemq/` filter |
| `ibmmq` | IBM MQ | `ibmmq/` filter |
| `tibcojms` | TIBCO JMS (via `.properties` file at `CBASE_HOME_URL`) | `tibcojms/` filter |
| `weblogicjms` | Oracle WebLogic JMS | `weblogicjms/` filter |

The active JMS provider is compiled into the WAR. The property placeholder reads JMS configuration from `${CBASE_HOME_URL}/config/service/prepaidJMS/tibcojms.properties`. This indicates the production environment uses TIBCO JMS for job queue messaging.

## 5. Sensitive Data

### 5.1 PII in Job Actions

Each `job_action` record contains:
- `partnerUserId` — the client's external reference for the recipient (could be SSN, employee ID, etc.)
- Action type
- Action-specific parameters (name, amount, address — varies by action type)

The `job_account_map` table explicitly maps `partnerUserId` values to internal `eMemberId`/`eCountId` values. If `partnerUserId` is an SSN, Tax ID, or other government identifier (common in healthcare/insurance disbursement programs), this mapping table contains sensitive PII.

### 5.2 Financial Data

`job_file` and `job_action` records contain disbursement amounts and action types. Fund load amounts are stored in `job_action`. These are financial records subject to NACHA, Reg E, and SOC 1 audit scope.

### 5.3 No Direct PAN Storage

The Job Service does not store PANs in the `jobsvc` database. Card numbers are issued by the Account Service and stored in `cbaseapp`. The Job Agent calls Account Service to issue cards but does not receive or log PANs.

## 6. SQL Timeout Configuration

The `JobDataSources.xml` configures a `SqlTimeoutManager` bean:
```xml
<property name="defaultTimeout" value="600" />    <!-- 600 seconds = 10 minutes -->
<property name="fdrProcDefaultTimeout" value="600" />
```
A 10-minute SQL timeout is very long and reflects the batch processing nature of the service. Queries that process large job files may legitimately run for minutes. This is acceptable for batch but would be unacceptable for a real-time API.

## 7. Encryption and Data Protection

- **In transit**: Director-client configuration connects to `https://` endpoints (director service). JMS connections depend on the provider configuration (TLS/SSL configurable per provider).
- **At rest**: SQL Server encryption at rest is a database-level concern not visible in the application code. No application-level encryption of stored data is implemented.
- **No field-level encryption**: Sensitive fields in `job_action` (amounts, action parameters) are stored in plaintext. PAN is not stored, but action parameters may contain PII.

## 8. Compliance Gaps

| Gap | Standard | Detail |
|---|---|---|
| No structured audit log for data access | PCI DSS Req 10.2 | No evidence of application-level audit logging for reads of job action data |
| 10-minute SQL timeout | Operational | Long-running transactions may hold database locks, impacting concurrent job processing |
| JMS queue durability | Reg E | Job actions in the JMS queue that have not been written to the database are at risk of loss on server restart |
| partnerUserId sensitivity unknown | GLBA / CCPA | May contain SSN-equivalent identifiers depending on the client program |
| No data retention policy visible | GDPR / CCPA | Job file records, action records, and account maps accumulate without a visible retention / archival policy in the code |
