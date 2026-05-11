# ecore-batch_LIB — Business Analyst View

## Business Purpose
A **Java Spring Batch library** that implements the batch processing engine for eCount Core — the legacy prepaid card platform. The library orchestrates asynchronous payment and financial transaction processing, including ACH (Automated Clearing House) withdrawals, IEFT (International Electronic Funds Transfer) withdrawals, core transaction processing (commit/cancel), and device (card) management. When events occur in the eCount core system (e.g., an ACH withdrawal is initiated, completed, or failed), this batch library detects those events and triggers the corresponding downstream actions — including cardholder email notifications.

**Authored by:** OFSS (Oracle Financial Services Software) — offshore development partner, initial development June 2010.

## Capabilities
| Batch Job | Business Function |
|---|---|
| `eventACHBatchJob` | Processes pending ACH event notifications: reads outstanding ACH events from core, calls notification service to send emails to cardholders |
| `eventACHJobEndBatchJob` | End-of-cycle cleanup for ACH batch events |
| `eventIEFTBatchJob` | Processes IEFT (international wire/transfer) event notifications with similar pattern to ACH |
| `coreTransferBatchJob` | Processes core financial transfers (COMMIT or CANCEL phase codes); calls eCount Core transfer service for each pending transaction |
| `coreDeviceJob` | Manages prepaid card/device records — card creation and state management |

## Key Entities
| Entity | Class | Notes |
|---|---|---|
| EventInstance | `dto.eventach.EventInstance` | An ACH event to be processed: triggerId, eventId, eventName, eventReference, amount, created, memberId |
| EventRule | `dto.eventach.EventRule` | Rule governing how an event is handled |
| EventActionDispatch | `dto.eventach.EventActionDispatch` | Dispatched action for an event: type, scriptUrl, scriptProcedure, parameters, memberId |
| CoreTransaction | `dto.processcoretransfer.CoreTransaction` | A core financial transfer: Transfer object (from cbase lib) + phaseCode (1=COMMIT, 2=CANCEL) |
| CoreDeviceInfo | `dto.device.CoreDeviceInfo` | Prepaid card/device information |
| IEFTJournal | `dto.eventieft.IEFTJournal` | IEFT transaction journal: beneficiaryName, country, forexRate, destCurrency, adjustedAmount, returnDate, returnedCreditAmount, returnReasonCode |
| Member | (com.cbase.business.core.value.Member) | Cardholder member record |

## Business Rules
1. ACH event processing uses a **count-first pattern**: the batch first counts pending events; if zero, the job ends with "NO RECORDS FOUND". If the count has not changed between cycles, the job exits with "RECORDS FOUND:INFINITELOOP" to prevent infinite processing.
2. An **exception threshold** controls how many processing failures are tolerated before the job exits with "EXCEPTION THRESHOLD" — configured externally via `eventach_exception_threshold` / `core_transfer_exception_threshold` properties.
3. Core transfers have two phase codes: **1 = COMMIT** (finalize) and **2 = CANCEL** (reverse). Both are processed by `coreTransferBatchJob`.
4. ACH notifications include masked bank account number (last 4 digits only): `bankAccountNumber.substring(length-4, length)` — a PCI/GLBA data minimization control.
5. IEFT notifications include IDD (International Direct Deposit) reject flow handling: if a program has `payment_selection` label enabled and fxtransfer+cardlessFx flags are true, the notification uses the IDD reject template instead of the standard IEFT failed template.
6. Email notifications are delivered via `NotificationManagerImpl` with `setShouldValidate(false)` — validation bypassed.
7. Device job processes card records through `CoreDeviceProcessor` and `CoreDeviceWriter`.

## Data Flows
```
eCount Core DB (via ecountcoreDataSource)
    |
    v [StoredProcedureItemReader — reads pending events/transactions]
Spring Batch partitioned step (parallelism via SimpleAsyncTaskExecutor)
    |
    v [Processor: EventACHProcessor / CoreTransactionProcessor]
    |
    +--> StrongboxServiceHelper (bank account data retrieval)
    +--> EcountCoreServiceHelper (eMember inquiry — cardholder data)
    +--> ProfileServiceHelper (program label lookup)
    +--> NotificationServiceHelperImpl (email notification delivery)
    |
    v [Writer: EventACHWriter / CoreTransactionWriter]
eCount Core DB (stored proc dispatch: eventActionDispatchBegin / End)
```

## Compliance Relevance
- **NACHA / Reg E** — ACH event processing; notification of ACH withdrawal outcomes to cardholders is a Reg E obligation (error resolution notice, transaction confirmation).
- **GLBA** — cardholder email notifications include financial information (amounts, bank account last 4 digits).
- **PCI DSS Req 3** — bank account number is masked to last 4 digits in email output (correctly implemented in `NotificationServiceHelperImpl`).
- **CCPA** — member email and name retrieved and included in notifications; cardholder PII in transit.

## Risks (Business)
1. **Infinite loop detection** — business logic uses remaining-count comparison across cycles to detect infinite loops; if the count decreases slowly (not stalls completely), infinite loop may not be detected.
2. **Exception threshold is a hard stop** — if the threshold is exceeded, remaining transactions are left unprocessed; Finance must be notified of partial batch runs.
3. **IEFT IDD reject flow** — the complex IDD logic (FX transfer + cardless FX flags) was added as a late change; test coverage for this path should be verified.
4. **`setShouldValidate(false)` on notifications** — bypassing notification validation could result in malformed or undeliverable emails without error.
5. **OFSS/offshore author** — original code by Oracle Financial Services Software offshore team (2010); no current named owner in Onbe.
