# Data Architect View — jobservice_common_LIB

## Data Model Role

This library is purely a **data model and interface definition library** — it contains no database access code, no DAO implementations, and no Spring data configuration. Its role is to define the canonical Java object representations that all services use when communicating job state. There are no data stores accessed directly by this library.

## Value Object Catalog and Data Fields

### `Job.java` — Primary Business Entity

The `Job` class is the central value object representing a batch job submission. Inferred fields from usage across the codebase:
- `job_id` (int) — system-generated unique identifier
- `file_id` (String) — client-provided file identifier
- `file_name` (String) — original uploaded filename
- `program_id` (String) — client program identifier
- `affiliate_id` (int) — client affiliate identifier
- `job_status_id` (int) — current status code
- `received_dt` (Date) — when the file was received
- `owner` (Member reference) — submitting member
- `request_file` (ECountFile reference) — the physical file in the repository
- `statistics` (JobStatistics) — action counts

### `JobAction.java` — Individual Disbursement Record

Represents a single action within a batch (e.g., one payment, one card issuance). Critical fields:
- `action_id` (int) — action record identifier
- `action_code` (int) — type of action (e.g., `JOB_ACTION_CODE_REGISTER_USER = 10` from `JobServiceConstants.java` line 108)
- `status_id` (int) — current action status
- `amount` (BigDecimal) — disbursement amount (if applicable)
- Various keys: `emember_id`, `ecount_id`, `device_id`, `payment_id`, `certificate_id`, `claim_code`

The constants in `JobServiceConstants.java` define all the key names used in action records:
- `EMEMBER_ID_KEY = "emember_id"` (line 43)
- `ECOUNT_ID_KEY = "ecount_id"` (line 44)
- `COMPLETED_EVENT_ID_KEY = "completed_event_id"` (line 45)
- `DEVICE_ID_KEY = "device_id"` (line 46)
- `EXP_MONTH_KEY = "exp_month"` (line 47) — card expiration month
- `EXP_YEAR_KEY = "exp_year"` (line 48) — card expiration year
- `CARD_TYPE_KEY = "card_type"` (line 49)
- `TX_ID_KEY = "tx_id"` (line 53) — transaction ID
- `ECHECK_ID_KEY = "echeck_id"` (line 55)
- `PAYMENT_ID_KEY = "payment_id"` (line 56)
- `CLAIM_CODE_KEY = "claim_code"` (line 57)
- `CERTIFICATE_ID_KEY = "certificate_id"` (line 58)
- `IBAN_NUMBER_KEY = "iban_number"` (line 64) — international bank account number (GDPR-sensitive)

### Sensitive Data Indicators in the Data Model

The value objects in this library carry **references to sensitive data identifiers**, not the sensitive data themselves. However, the semantics are critical for understanding the CDE scope:

| Field Key | Sensitivity Level | Regulatory Scope |
|---|---|---|
| `device_id`, `card_type`, `exp_month`, `exp_year` | Card-adjacent identifiers | PCI DSS — in-scope; these reference card objects in the account service |
| `echeck_id`, `iban_number` | ACH/banking reference | NACHA, Reg E — sensitive financial identifiers |
| `emember_id`, `ecount_id` | Member identity | GLBA/CCPA — personally identifiable |
| `payment_id`, `certificate_id` | Payment instrument references | PCI DSS |
| `claim_code` | Claim redemption code | Commercially sensitive |
| `tx_id` | Transaction reference | Audit trail required under PCI DSS Req 10 |
| `VIRTUAL_EXPRESS_URL` (line 67) | Virtual card delivery URL | Contains payment credential delivery path |

The `VIRTUAL_EXPRESS_URL` constant (line 67) is particularly sensitive — it represents the URL through which a virtual card's credentials are delivered to the recipient. This URL, if logged in cleartext, could expose card credentials through log files.

### `JobFee.java` — Fee Assessment Record

Contains financial computation data for fee collection:
- Fee type identifiers
- Fee amounts
- Program fee configuration references

This is relevant to Onbe's billing system — fee records feed into client invoicing and reconciliation.

### `JobStatistics.java` — Aggregate Counts

Critical operational data object used by `job-order-synchronization_LIB` to determine whether a job archived "with errors" or cleanly:
- `actionFailed` (int) — count of failed individual actions
- `actionSuccess` (int)
- `actionSkipped` (int)

The `hasErrors()` method in `JobOrderSynchronizer` queries this object to determine whether an archived job should be marked `PROCESSED` or `PENDING_CORRECTION` in the Order Service.

### `StructureValidationErrorLevels.java`

Defines error severity levels for file structure validation — used to determine whether a structural error is fatal (job rejected) or a warning (job can proceed with exceptions).

## Interface Definitions and Their Data Contracts

### `IJobManager.java`

Defines the contract for all job lifecycle operations. The method signatures expose data types from this library, making it the **contract between the front-end services and the job execution back-end**. Key data inputs and outputs:
- Input: `Member caller`, `int jobId` for most state transitions
- Input: `String agentPackage` for validation (ETL agent package selection)
- Output: `Job[]`, `JobProcess[]`, `JobBatch`, `JobAction`, `JobActionAmountSummary[]`, `JobJobStatus[]`, `JobBatchInfo[]`, `JobPromotion[]`

### `IJobAgent.java`

Defines the contract for the Job Agent — the component that executes individual actions within a running job. Single method:
```java
void runProcess(String execAgent, String memberId, String jobAgentName, boolean isBatch)
```

### `IJobFileManager.java`

Contract for file lifecycle operations (load, validate, complete, create reply files). Data types: `ECountFile`, `Member`, `String agentPackage`.

### `IJobProfileManager.java`

Contract for program profile management (the per-program ETL configuration). Data types: `JobServiceProgramProfile`, `JobProfileManagerInput`.

## File Status Mapping — `JobServiceConstants.FILE_STATUS_MAP`

A static `HashMap<String, String>` defined at lines 122–139 maps internal job status strings to client-visible status strings displayed in status reports:

```java
FILE_STATUS_MAP.put("loading", "Received");
FILE_STATUS_MAP.put("failed_structural_validation", "Structure Failed");
FILE_STATUS_MAP.put("Processing", "Processing");
FILE_STATUS_MAP.put("Archived", "Processing Complete");
FILE_STATUS_MAP.put("Completed with Errors", "Content Failed");
// ...
```

This mapping is the **source of truth for client-facing status language**. Changes to this map affect all status reports delivered to clients.

## Data Retention Notes

As a library, this component itself stores no data. The data objects it defines are persisted by `jobservice_SVC` into the `jobsvc` SQL Server database. Retention of action records (`job_action` table, implicit from `JobAction` value object) is subject to:
- PCI DSS Req 10.7: 12-month online, 3-month immediately available
- NACHA: 2 years for ACH entry records
- SOC 1: As defined in client service agreements (typically 7 years)
