# Business Analyst View — jobservice_SVC

## Repository Identity

- **Artifact**: `com.ecount.service.jobservice:jobservice` v4.0.7-SNAPSHOT
- **Parent POM**: `prepaid-parent:6.0.13`
- **Repository name**: `jobservice_SVC`
- **Description**: The central batch-job execution engine for Onbe's prepaid disbursement platform. Historically referred to as "JobManager/JobAgent" or simply "JobService," this service handles all aspects of submitting, validating, authorizing, executing, and archiving bulk payment files on behalf of Onbe clients.

## What This Service Does

`jobservice_SVC` is the operational backbone of Onbe's batch processing capability. When a client (e.g., an insurance carrier, auto manufacturer, or marketplace) wants to disburse payments to thousands of recipients simultaneously, they upload a structured file. This service receives, validates, authorizes, executes, and archives that file. The service is split into two deployable WARs that collaborate:

### JobManager (`service.war` on `JobManager` Tomcat server)
Handles all **control-plane** operations — the lifecycle management of a job. It does not process individual payments directly; it orchestrates the pipeline:

1. **File Intake and Structural Validation** — When a batch file is uploaded via the Repository Service, `loadJobFileChecker()` (JobManagerImpl line 216) is triggered. The file is parsed and validated against the program's expected format using configurable ETL agent packages.
2. **Content Validation** — `jobValidateContent(Member caller, int jobId, String agentPackage)` (JobManagerImpl line 645) runs the field-level validation; invalid records are written to an error file.
3. **Authorization** — `authorizeJob()` (line 161) transitions the job to authorized status. For high-value batches, this requires a dual-authorization (Banker role) step before the job can run. `unAuthorizeJob()` and `denyJob()` provide the complementary rejection paths.
4. **Execution Trigger** — `runJob(Member caller, int jobId, boolean batchProcess, String execAgent)` (line 118) transitions the job to processing state and places it in the execution queue via the configured JMS topic.
5. **Lifecycle Management** — State transitions through the full job lifecycle: `endJob()`, `resetJob()`, `cancelJob()`, `adminCancelJob()`, `archiveJob()`, `archiveJobWithErrors()`, `markJobPendingFunds()`, `markJobPendingFinance()`, `markJobFailed()`, `markJobFailedContent()`.
6. **Report Generation** — After execution or cancellation, reply files (confirmation), exception files (failed records), and error report files (structural failures) are generated and stored in the Repository Service for client retrieval.
7. **Fee Management** — `jobFeesCalcEstimate()` and `jobFeesCalcActual()` compute client billing amounts based on action counts and fee schedules.
8. **Notification Creation** — `jobCreateNotifications()` generates notification records for processed recipients.

### JobAgent (`JobAgentService.war` on `JobAgent` Tomcat servers)
Handles all **data-plane** operations — the actual execution of individual actions within a running job. For every record in a batch, the Job Agent checks out an action from the database and delegates to a typed action handler:

| Action Handler | Business Operation |
|---|---|
| `RegisterUser` | Creates a new cardholder account in the Account Service |
| `ExtendedRegisterUser` | Extended registration with additional profile fields |
| `IssueCard` | Issues a prepaid card to a registered account |
| `AddFunds` | Loads funds onto an existing card (disbursement) |
| `Withdraw` | Withdraws funds from a card |
| `UpdateUser` | Updates cardholder profile data |
| `ExtendedUpdateUser` | Extended profile update |
| `StopPayment` | Places a stop payment on a card |
| `SendNotification` | Sends a notification to a cardholder |
| `SetInventoryLocation` | Sets inventory location attributes for a card |
| `SetLocationCode` | Assigns a card distribution location code |
| `CreateCertificate` | Creates a payment certificate (gift/incentive) |
| `CreateEmailNotifications` | Sends email notification for issued cards |
| `SetUserManagementRequest` | Triggers a security/user-management workflow |

Sources: `JobAgentActionHandlers.xml` (jobagent-war), `JobAgentServiceImpl.java` line 60.

## Key Business Processes

### Straight-Through Disbursement (AddFunds)
The most common batch operation is loading funds onto pre-registered cards. A client submits a file with member IDs and amounts; the Job Agent calls `AddFunds` for each record, invoking the Account Service to credit the card. This is the core disbursement function underlying insurance claim payments, auto manufacturer rebates, and gig-economy payouts.

### Card Issuance (IssueCard)
Clients may submit new-account batches. RegisterUser creates the cardholder record and IssueCard provisions a card number. This is used for new program launches, employee incentive distributions, and refund card programs.

### SPIN Payments (Prize Distribution)
The `jobRandomizeSpinPayments()` and `jobAwardSpinPayments()` methods (JobManagerImpl lines 583–607) implement a probabilistic prize distribution system where disbursement amounts are assigned randomly within a weighted distribution table. Used for sweepstakes, loyalty spin-to-win promotions, and rebate programs with prize tiers.

### Fee Collection
After a job executes, `jobFeesCalcActual()` triggers stored procedures that calculate actual fees based on action counts, program fee schedules, and any fee overrides. These fee records feed into the Great Plains financial reconciliation system.

### Account Mapping
`jobAccountMapSet()`, `jobAccountMapUpdate()`, `jobAccountMapGet()`, `jobAccountMapCleanup()` (JobManagerImpl lines 463–678) maintain a temporary mapping table that resolves client `partnerUserId` values to internal eCount/eMember identifiers during batch processing. This mapping is used when clients provide external user references instead of internal account IDs.

### Autofile Workflow Integration
The `autofile-common` library is loaded in `web.xml` (line 50: `autofileService-client.xml`). This enables the Job Manager to participate in the automated file ingestion workflow where files arriving via SFTP are automatically registered, validated, and queued for processing without manual operator intervention.

### Workflow Service Integration
The JobManager WAR also embeds the full Workflow Manager and Workflow Agent services (lines 39–48 of `web.xml` load `WorkflowManagerService.xml`, `WorkflowAgentService.xml`, etc.). This means a single WAR deployment runs both job management and workflow orchestration in the same JVM, sharing the same Director-configured data sources.

## Client-Facing Status Language

The `JobServiceConstants.FILE_STATUS_MAP` provides the client-visible status labels returned in status report files:
- `loading` → "Received"
- `failed_structural_validation` → "Structure Failed"
- `Processing` → "Processing"
- `Archived` → "Processing Complete"
- `Completed with Errors` → "Content Failed"

Clients consuming the reply files and viewing the Banker UI (`banker_API`) see these mapped values.

## Supported File Package Types

Three ETL processing profiles are supported (from `JobServiceConstants.java`):
1. `FILE_PACKAGE_DEFAULT` — Standard tab-delimited or fixed-width format (most clients)
2. `FILE_PACKAGE_XMLSTRICT` — Strict XML format
3. `FILE_PACKAGE_ECOUNTXML` — eCount XML format (2013 R3A and later)

Each profile activates different ETL agents via `agentPackage` parameter, allowing different client file formats to be processed through a common pipeline.

## Organizational Significance

This service is the operational heart of Onbe's disbursement business. Every dollar disbursed via batch (as opposed to real-time API) passes through this service. Client SLAs for batch processing times, error rates, and reporting delivery are all ultimately governed by this service's performance and reliability. A failure in this service directly prevents client fund distributions and triggers SLA penalties.
