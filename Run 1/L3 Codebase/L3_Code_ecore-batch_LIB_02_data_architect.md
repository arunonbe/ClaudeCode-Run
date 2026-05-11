# ecore-batch_LIB — Data Architect View

## Data Stores

### Primary Data Source: ecountcoreDataSource
- Factory: `DirectorConfiguredDBCPdatasourceCreator` using `${director.address}` and `${springbatch-agent}`/`${database}` properties
- Resolved at runtime from Director service (eCount's service directory / config server)
- Used by all item readers (StoredProcedureItemReaders calling eCount Core stored procedures)
- Underlying database: EcountCore (SQL Server — on `p-db02-ha.nam.wirecard.sys\db02` per DB07 config scripts)

### Batch Repository: batchRepoDataSource
- Factory: same `DirectorConfiguredDBCPdatasourceCreator`
- `${batchrepodatabase}` property resolves to Spring Batch metadata database
- Stores Spring Batch job execution history: `BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION`, etc.
- `isolation-level-for-create="SERIALIZABLE"` — Spring Batch uses serializable isolation for job instance creation to prevent duplicate runs

### External Service Data Sources (via API calls, not JDBC)
| Service | Data Retrieved | Used In |
|---|---|---|
| StrongboxServiceHelper | Bank account details (routing number, account number, bank name) | ACH notifications |
| EcountCoreServiceHelper (eMember) | First name, last name, email, enrollment program | ACH and IEFT notifications |
| ProfileServiceHelper | Program labels (product name, URL, brand name, customer service phone, payment_selection) | ACH and IEFT notifications |
| IEFTJournalInquiry | IEFT journal: beneficiaryName, country, forexRate, destCurrency, adjustedAmount, returnDate | IEFT notifications |
| RequestContext (cbase) | Agent context for service calls | All service helpers |

## Schema / Tables / Stored Procedures
(Actual SP names are resolved from properties files at runtime via placeholders)

| Placeholder | Used By | Purpose |
|---|---|---|
| `${eventach.sp.ach_event_service_batch_count}` | eventACHBatchJob count reader | Count pending ACH events |
| `${eventach.sp.ach_event_service_batch}` | eventACHBatchJob item reader | Retrieve ACH event instances |
| `${core_transfer.sp.core_transaction_service_batch_count}` | coreTransferBatchJob count reader | Count pending core transfers |
| `${core_transfer.sp.core_transaction_service_batch}` | coreTransferBatchJob item reader | Retrieve core transactions |

Column mappings from constants:
- `transfer.id`, `phase_code`, `core_transaction_count` — CoreTransaction
- `trigger_id`, `event_id`, `event_name`, `event_parameters.reference`, `event_parameters.amount`, `event_parameters.created`, `event_parameters.memberid` — EventInstance
- `ach_count`, `ieft_count` — event count columns
- `rule_id`, `action_id`, `status`, `message`, `type`, `script_url`, `script_procedure`, `script_timeout`, `parameters`, `member.id` — EventActionDispatch

## Sensitive Data in Processing
| Data Element | Class | Handling | Risk |
|---|---|---|---|
| Bank account number | EventActionDispatch / StrongboxServiceHelper | Truncated to last 4 digits in email output | PCI/GLBA — correctly masked |
| Bank routing number | EventActionDispatch / StrongboxServiceHelper | Full routing number sent in email | GLBA — routing numbers are less sensitive than account numbers but still financial data |
| Member email address | EventInstance / EcountCoreServiceHelper | Used as recipient and `recipientFriendlyName` | CCPA/GLBA PII |
| First name / last name | EcountCoreServiceHelper | Included in email notification body | PII |
| Transfer amount | EventInstance.amount | Amount/100.0 (stored as integer cents) | Financial |
| Program ID | memberData | Used as `affiliateId` (substring 4-8 of programId) | Internal identifier |
| IEFT forex rate, dest currency, adjusted amount | IEFTJournal | Included in email | Financial |
| IEFT beneficiary name | IEFTJournal.beneficiaryName | Included in email | PII (third-party beneficiary) |
| Promotion ID | MemberInquiryExtendedResult.addenda | Used for IDD notification routing | Internal |

**Key PII risk**: Member email, first name, last name, and bank account details are held in memory during batch processing. If the JVM heap is captured in a heap dump or crash, this data could be exposed.

## Encryption
- Database connections managed by `DirectorConfiguredDBCPdatasourceCreator` using `commons-dbcp` 1.2.2 — connection pool; TLS configuration depends on the Director service configuration and JDBC URL, not visible in this repo.
- No explicit TLS or encryption configuration in Spring XML context files.
- No at-rest encryption (data resides in EcountCore SQL Server — TDE status unknown from this repo).
- StrongboxServiceHelper retrieves bank credentials via the `RepositoryService.Read` API — the strongbox service is a credential store; its transport security is not visible in this repo.

## Data Quality / Retention
- Spring Batch metadata tables (BATCH_ prefix) retain job execution history — no purge policy configured in this repo.
- `isolation-level-for-create="SERIALIZABLE"` prevents duplicate job instances — a data integrity control.
- Infinite loop detection compares consecutive counts in `ExecutionContext` — a data quality guard on the processing pipeline.
- Exception threshold provides a circuit breaker if data quality issues cause repeated failures.

## Compliance Gaps
1. **Routing number in email** — full bank routing numbers are included in ACH notification emails; GLBA data minimization best practice suggests routing number should also be masked or omitted from customer-facing notifications.
2. **No heap/memory dump protection** — PII and financial data in Java object graph; no evidence of secure memory handling (zeroing sensitive arrays).
3. **Logging of PII** — `_log.info` statements log `registration.email_address`, `registration.first_name`, `registration.last_name` in `EcountCoreServiceHelperImpl.java:80-82` — PII in application logs is a CCPA/GLBA concern.
4. **StrongboxServiceHelper logs reference ID** — `_log.info("Calling StrongBox.RepositoryService.Read to retrieve bank info for reference id:"+reference)` — the reference ID for bank credentials is logged; severity depends on what `reference` contains.
5. **Spring Batch metadata retention** — no job execution log purge; tables may grow indefinitely.
