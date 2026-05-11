# Data Architect Analysis: request_LIB

## Data Stores
| Store | Type | Purpose |
|---|---|---|
| SQL Server (`ecountcore` / `ecountbatchjobrepository` databases) | Relational DB | Requests, actions, action results, request activities, processor config, processor control, SMS queue |
| SQL Server (`nexpay_claimable` or shared DB) | Relational DB | Claimable payment records, ACH transfer detail, claim code issuance info |
| SMS queue table | Relational DB (same SQL Server) | Queued SMS messages for async delivery |
| CRCP service | Remote HTTP service | Notification delivery |
| Shared SMS service | Remote HTTP service | SMS delivery via `SharedServiceConnector` |

## Schema / Tables
Inferred from JDBC DAO class names and stored procedure names:

### Request Schema
| Table / SP | Purpose |
|---|---|
| `request` (or similar) | Core request records; `JdbcRequestDao` |
| `request_activity` | Request state transition log; `JdbcRequestActivityDao` |
| `action` | Action records per request; `JdbcActionDao` |
| `action_result` | Action outcomes; `JdbcActionResultDao` |
| `request_processor_config` | Processor configuration; `JdbcRequestProcessorConfigDao` |
| `request_processor_control` | Processor runtime state; `JdbcRequestProcessorControlDao` |

### Action-Specific Tables (per action type)
Each action type has its own JDBC DAO operations class, implying distinct tables or stored procedures:
- AddFunds, InstantIssueAddFunds, IssueCard, IssueSecondaryCard, LinkCard, BulkOrder
- RegisterUser, UpdateUserRegistration, **UpdateUserSecureProfile** (SSN/DOB)
- StopPayment, Withdraw, UpdateAccountStatus, UpdateInventory, UpdateMemberAddenda, SendNotification

### Claimable Payment Schema
| Class | Purpose |
|---|---|
| `CreateClaimablePaymentSP` | Stored procedure for claimable payment creation |
| `ACHTransferDetailCreateAPISP` | Stored procedure for ACH transfer detail |
| `InsertClaimCodeIssuanceInfo` | Stored procedure for claim code issuance |
| `GetPaymentExpiryDate` | Stored procedure for payment expiry |
| `JdbcClaimablePaymentAddendaDao` | DAO for claimable payment addenda |

### SMS Schema
| Class | Purpose |
|---|---|
| `SmsConfigDao` | SMS configuration lookup |
| `SmsQueueDao` | SMS queue persistence |

## Sensitive Data Handled
| Data Element | Classification | Risk |
|---|---|---|
| SSN (`SecureProfile.ssn` / `federal_id`) | PII — GLBA/CCPA/GDPR sensitive | Stored in database via `UpdateUserSecureProfileJdbcDaoOperations` |
| Date of birth (`SecureProfile.dob`) | PII | Stored in database |
| Cardholder address | PII | Via `Registration` / `Address` in action payloads |
| Cardholder name | PII | Part of registration actions |
| Phone number | PII | Part of registration and notification actions |
| Email address | PII | Part of notification actions |
| Payment amounts (`FundsValue`) | Financial | Stored with action records |
| ACH transfer details | Financial — NACHA sensitive | Stored via `ACHTransferDetailCreateAPISP` |

## Encryption
- No application-level encryption of sensitive fields is visible within this library.
- SSN and DOB are handled as plain strings/dates in `SecureProfile` and stored via JDBC operations.
- Encryption at rest for these fields depends entirely on SQL Server column-level encryption or TDE configuration managed outside this library.
- XStream serialisation (`XStreamFactory`, `Symbol`, `SymbolFactory`) is used for some domain objects — serialised XML may contain sensitive data if logged or stored in log files.

## Data Flow
```
Caller (web app / batch processor)
  --> RequestManager.submitRequest() / processRequest()
        --> RequestManagerImpl / RequestProcessorImpl
              --> RequestDao / ActionDao (JdbcRequestDao, JdbcActionDao)
                    --> SQL Server stored procedures
              --> TypeRoutingActionHandler
                    --> [Action-specific handler] (IssueCardActionHandler, AddFundsActionHandler, etc.)
                          --> PaymentServiceDelegate --> payment-service_SVC
                          --> InventoryMgmt service
                          --> Profile/Director clients
                          --> SmsNotificationService --> SMS queue DB --> Shared SMS service
                          --> CrcpNotificationService --> CRCP HTTP endpoint
              --> ActionResultDao --> SQL Server
```

## Data Quality / Retention
- Request and action activities are persisted at each state transition — provides natural audit trail.
- No explicit data retention policy within the library; data lifecycle managed by external processes.
- `RequestManagerImpl` and `RequestProcessorImpl` implement synchronisation (`RequestSynchronizerImpl`, `ActionSynchronizerImpl`) to prevent concurrent processing of the same request.
- `GetPaymentExpiryDate` stored procedure indicates expiry-based lifecycle management for claimable payments.

## Compliance Gaps
1. **SSN stored without application-level encryption**: `SecureProfile.ssn` is a plain String written to the database. GLBA requires appropriate safeguards; encryption at column level should be verified at the database layer.
2. **XStream serialisation of sensitive objects**: If `Symbol`/domain objects containing sensitive data are serialised and logged, PII or SSN could appear in log files.
3. **No explicit PAN handling**: Actions involving card issuance (`IssueCardAction`) may carry PAN data through the system; no PAN masking or tokenisation logic is visible in this library.
4. **ACH transfer details**: Stored via `ACHTransferDetailCreateAPISP`; NACHA rule compliance for ACH data protection must be verified at the stored procedure level.
5. **Thread-local processor state** (`SasiRequestProcessorThreadLocal`): Thread locals in thread pools can cause data leakage between requests if not properly cleared.
