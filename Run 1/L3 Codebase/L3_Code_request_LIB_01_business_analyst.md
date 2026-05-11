# Business Analyst Analysis: request_LIB

## Business Purpose
request_LIB is a foundational Gen-1 Java library that implements the core request/action processing engine for the Onbe prepaid card platform. It provides the domain model, persistence layer, and execution engine for all cardholder lifecycle operations — from card issuance and fund loading to account status updates and withdrawal processing.

The library represents the central workflow orchestration layer of the legacy platform: requests are created, submitted, and processed through a state machine with activities, actions, and results — all persisted to the database and processed asynchronously.

## Capabilities
1. **Request Lifecycle Management**: Create, save, submit, cancel, and correct requests.
2. **Action Execution**: Execute typed actions (IssueCard, AddFunds, RegisterUser, StopPayment, Withdraw, etc.) against the payment and inventory systems.
3. **Action Result Persistence**: Record outcomes of each action for audit and retry purposes.
4. **Request Activity Tracking**: Track all state transitions (Save, Submit, Process, Cancel, Correct) with associated activities and timestamps.
5. **Processor Configuration**: Load and manage processor configuration controlling request routing and processing behaviour.
6. **Processor Control**: Manage processor start/stop/pause state (RequestProcessorControl).
7. **SMS Notification**: Queue and send SMS notifications as part of request processing.
8. **CRCP Notification**: Send notifications via CRCP (Customer Resource Communications Platform) service.
9. **Claimable Payment Processing**: Create and manage claimable payment records with ACH transfer detail.
10. **Claim Code Issuance**: Record claim code issuance metadata.
11. **Symbol/XStream Serialisation**: XML serialisation of domain objects via XStream.
12. **Config Caching**: Cache program processor configuration to avoid repeated database lookups.

## Key Business Entities
| Entity | Description |
|---|---|
| Request | Root aggregate: id, status, memo, definition reference, activity log |
| RequestDefinition / RequestCatalogEntry | Definition of a request type |
| RequestStatus | Enum: PENDING, SUBMITTED, PROCESSING, COMPLETED, CANCELLED, ERROR, etc. |
| Action | An operation within a request (typed: IssueCard, AddFunds, etc.) |
| ActionType | Enum of all supported action types |
| ActionResult | The outcome of executing an action |
| ActionStatus | Status of an action |
| ActionMemo / ActionSecureMemo | Notes attached to an action |
| RequestActivity | State transition event on a request |
| RequestActivityType | Enum: Save, Submit, Process, Cancel, Correct |
| Registration | Cardholder registration data |
| SecureProfile | Sensitive identity data: SSN + date of birth |
| Address | Cardholder address |
| FundsValue | Monetary value for fund operations |
| NotificationValue | Notification delivery details |
| ClaimablePaymentAddenda | Payment addenda for claimable payment types |
| RequestProcessorConfig | Configuration controlling how requests are processed by a processor |
| RequestProcessorControl | Runtime control of a request processor (start/stop/pause) |

## Supported Action Types
`IssueCard`, `IssueSecondaryCard`, `AddFunds`, `InstantIssueAddFunds`, `RegisterUser`, `UpdateUserRegistration`, `UpdateUserSecureProfile`, `UpdateAccountStatus`, `BulkOrder`, `LinkCard`, `StopPayment`, `Withdraw`, `UpdateInventory`, `UpdateMemberAddenda`, `SendNotification`

## Business Rules
- No snapshot (non-release) dependencies allowed in released builds (enforced by `maven-enforcer-plugin:requireReleaseDeps`).
- Request IDs are string-based identifiers used as equals keys.
- `SecureProfile` carries SSN (`federal_id`) and date of birth — both PII/sensitive data elements.
- SASI (Stand-Alone Submission Interface) request processing uses a thread-local for processor state: `SasiRequestProcessorThreadLocal`.
- Inventory journal activities track card status changes and account activity types.
- SMS notifications support queuing via `SmsQueueService` for asynchronous delivery.
- Claimable payment creation involves an ACH transfer detail API stored procedure call.

## Business Flows
### Request Submission Flow
1. Caller creates a `Request` object with one or more `Action` objects.
2. Caller invokes `RequestManager.submitRequest(...)` (via `RequestManagerImpl`).
3. `SubmitRequestActivityHandler` persists the state transition.
4. `RequestDao` and `ActionDao` persist the request and actions to the database.

### Request Processing Flow
1. `RequestProcessorImpl` picks up submitted requests (typically via a job/scheduler).
2. For each request, `ActionProcessorImpl` routes each action to its typed handler (via `TypeRoutingActionHandler`).
3. Each action handler (e.g., `IssueCardActionHandler`, `AddFundsActionHandler`) calls the downstream service (payment service, inventory service, etc.).
4. Action results are persisted via `ActionResultDao`.
5. Notifications (SMS, CRCP) are sent as part of action processing.

## Compliance Relevance
- `SecureProfile` contains SSN (`federal_id`) and date of birth — GLBA/CCPA/GDPR sensitive data elements.
- `UpdateUserSecureProfileAction` and `UpdateUserSecureProfileJdbcDaoOperations` update SSN/DOB in the database — these operations are subject to strict access control and audit requirements.
- Claimable payment and ACH transfer operations are subject to NACHA and Reg E compliance.
- Inventory journal tracking supports audit trail requirements.

## Risks (Business Perspective)
- **SSN persistence**: `SecureProfile.ssn` field is mapped to/from the database via JDBC DAOs; SSN at rest must be encrypted (PCI DSS Requirement 3 equivalent for GLBA data).
- **Wide action surface**: 15 action types all routed through this library; a bug in the routing or persistence layer affects all cardholder operations.
- **Thread-local SASI state**: `SasiRequestProcessorThreadLocal` could leak state between requests if thread pooling is used.
