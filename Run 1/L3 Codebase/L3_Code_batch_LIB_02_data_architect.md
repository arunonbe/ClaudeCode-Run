# batch_LIB — Data Architect View

## Data Stores

batch_LIB accesses **seven distinct databases**, all provisioned at runtime via the `DirectorConfiguredDBCPdatasourceCreator` factory (`data-source-context.xml`). No connection strings are hard-coded in source; they are resolved through the Director service discovery component. The logical database identifiers are:

| Spring Bean ID | Config Key | Usage |
|---|---|---|
| `ecountDataSource` | `database.ecountcore` | Primary ecount platform DB — member accounts, transactions, claim data, auto-claim records |
| `ecountCoreDS` | `database.ecountcore` (eCountCoreAgent) | Same ecount DB via a different agent credential |
| `ecountcoreDataSource` | `database.ecountcore_process` | Spring Batch job repository |
| `batchRepoDataSource` | `database.batchrepository` | Spring Batch repository (job/step execution metadata) |
| `cbaseappDS` / `CbaseappDataSource` | `database.cbaseapp` | cbase application data (member profiles, device data) |
| `notificationsvcDS` | `database.notificationsvc` | Notification service DB (email audit, returned email records) |
| `jobsvcDataSource` | `database.jobsvc` | Job service DB (ACH transfer records, affiliate/program mapping) |
| `strongboxDS` | `database.strongbox` | Strongbox secrets/credential vault DB |
| `cfReportDataSource` | `database.cf_report` | Client-funded reporting DB |

All databases are Microsoft SQL Server (Hibernate dialect `org.hibernate.dialect.SQLServerDialect` confirmed in `autoClaimProcessBatchjob.xml`, line 207; JDBC driver `com.microsoft.sqlserver.jdbc:sqljdbc:1.1`).

## Schema & Tables

Tables are never DDL-defined in this library (schema-owning services define them). Access is exclusively via stored procedures and `JdbcTemplate` queries. Key stored procedures identified:

| Stored Procedure | Database | Job |
|---|---|---|
| `auto_claim_process_count_extract` | ecountDataSource | Auto Claim |
| `auto_claim_process_extract_transaction` | ecountDataSource | Auto Claim |
| `core_profile_global_deposit_file_update` | ecountDataSource | Auto Claim status update |
| `dbo.payout_transfer_details_fetch` | ecountDataSource | PayPal/Venmo Choice Recurring |
| `InsertPaypalTransactionStatus` (SP object) | ecountDataSource | PayPal payout |
| `GetPaypalTransactionSP` (SP object) | ecountDataSource | PayPal refund check |
| Multiple ECS settlement/auth stored procs | ecountDataSource | ECS jobs |

Additional DAO patterns identified:
- `AccountDataCountDAO` / `AccountDataGetFileNamesDAO` — JDBC queries against account data tables.
- `AutoClaimAffiliateDetailsDaoImpl` — Hibernate (`AnnotationSessionFactoryBean`) accessing `AffiliatePartnerDetail` and `ProgramMapDetail` entities in `jobsvcDataSource`. Entities use `@Entity` / `@Table` annotations (Hibernate 3).
- `PaymentHubCheckIssuanceUserProfileDAOImpl` — reads/inserts user profile option name.
- `PaypalSettlementFileInsertSQL`, `PaypalSettlementAccountInsertSQL`, `PaypalSettlementFileMetaDataInsertSQL` — named SQL insert objects for PayPal settlement file parsing results.
- `CbtsPendingConfirmationStatusPreparedStatementSetter` — CBTS pending confirmation inserts.
- ECS settlement DAO (`ECSSettlementPostingDAO`) — `processATPTPosted`, `processATGTPosted`, `processPostATPT` stored procedure calls.

## Sensitive Data Handling

The following sensitive data fields are present in DTO classes read from and written to the database:

| Field | DTO Class | Sensitivity |
|---|---|---|
| `memberId` | `AutoClaimTransactions`, `BalanceSyncVO`, `PaymentHubAutoCardMember`, numerous others | PII — cardholder identifier |
| `ddaNumber` | `AutoClaimTransactions`, `AltoBacsPayment`, `PayPalChoiceRecurringDetails` | Account number (DDA) |
| `last4` | `PushtodebitTransactionVo` | Truncated PAN — PCI DSS in-scope |
| `bin` | `PushtodebitTransactionVo` | Card BIN — PCI DSS in-scope |
| `PAR` | `PushtodebitTransactionVo` | Payment Account Reference — PCI DSS in-scope |
| `MAC` | `PushtodebitTransactionVo` | Message Authentication Code |
| `cvv2` | `PushtodebitTransactionVo` | SAD — PCI DSS Requirement 3.2.1 prohibits storing post-auth |
| `ofacCode` / `corrOfacCode` | `PushtodebitTransactionVo` | OFAC screening result |
| `firstName`, `lastName` | `PushtodebitTransactionVo` | PII |
| `fromAddress`, `toAddress`, `bodyContent` | `EmailMessageVO` | PII — cardholder email and content |
| `notificationId`, `messageSubscriberId` | `EmailMessageVO` | Internal notification correlation IDs |
| `paypalEmailID` / `payorID` | `PayPalChoiceRecurringDetails` (via `PaypalChoiceOptionDetailsDAO`) | PII — PayPal account linkage |
| `clientSecret` | `MSExchangeEmailReaderDelegateImpl` | Secret — OAuth client credential for Microsoft Exchange |
| `emailAccountPassword` | `MSExchangeEmailReaderDelegateImpl` | Secret — Exchange mailbox password |

**Critical finding**: `cvv2` is a named field in `PushtodebitTransactionVo` (line 33) and is imported from the TabaPay push-to-debit settlement file. PCI DSS Requirement 3.2.1 prohibits storing CVV2 after authorization. If this field is persisted to the database by `PushtodebitTransactionItemWriter`, it constitutes a PCI DSS violation.

## Encryption & Protection

- **Strongbox**: `strongboxImpl:1.0.2` is a declared dependency and `strongboxDatabase` is provisioned as a data source bean (`data-source-context.xml`, line 77). This suggests secrets are accessed from a centralized vault, but the code does not show explicit Strongbox API calls in the reviewed batch processors — it may be used by lower-level service dependencies.
- **Database credentials**: No credentials are present in source code. All connections go through the Director service discovery factory (`DirectorConfiguredDBCPdatasourceCreator`), which retrieves credentials from the Director agent at runtime.
- **OAuth for Exchange**: `MSExchangeEmailReaderDelegateImpl` (lines 128–134) uses `ConfidentialClientApplication` (MSAL4J) with `clientSecret` to obtain an OAuth bearer token for Microsoft EWS — a modern pattern. However, `clientSecret` is injected via a Spring property file at `D:\c-base\config\batch\returnedemailbatch\ReturnedEmailBatch.properties`.
- **No field-level encryption** of PII or payment data is evident in the batch library itself. Encryption at the DB/storage layer is assumed but cannot be confirmed from this codebase.
- **TLS**: HTTP calls in `ClaimableChoiceAPIClient` use `org.javalite.http.Http.post()` — no explicit TLS certificate validation override found, but no `trustAll` or `hostnameVerifier` bypass is present either.

## Data Flow

```
External Files (PACS/ARUCS/PayPal/TabaPay CSV) 
    --> File System (D:\c-base\...) 
    --> Perl/VBS pre-processor scripts 
    --> SQL Server (direct load) 
    --> Spring Batch Reader (StoredProcedureItemReader / FlatFileItemReader)
    --> Processor (business logic, ecount core calls)
    --> Writer (JdbcTemplate / StoredProcedure updates)
    --> File System (output reports) or downstream DB tables
```

Notification flow:
```
SQL Server (notification_svc DB) 
    --> Spring Batch Reader 
    --> NotificationManager.deliver() 
    --> Email / notification channel
```

Returned email flow:
```
Microsoft Exchange (EWS / Office 365) 
    --> MSExchangeEmailReaderDelegateImpl (MSAL4J OAuth) 
    --> EmailMessageVO 
    --> notificationsvcDS (insert)
```

## Data Quality & Retention

- **Duplicate detection**: `PushtodebitTransactionItemProcessor` maintains an in-memory `HashSet<String>` of `importFileId_referenceId` keys per job step execution. This is not durable — a restart would reset the set.
- **Infinite-loop guard**: Execution counts are compared across runs in Spring Batch `ExecutionContext` to detect stalled processing.
- **Job execution metadata**: Stored in `batchRepoDataSource` (`database.batchrepository`) — standard Spring Batch tables (`BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, etc.).
- **Job status tracking**: Several jobs maintain their own custom job instance tables (e.g., `SQLInsertClaimExpirationJobStatus`, `SQLInsertClaimableChoiceExpirationJobStatus`, `SQLInsertEmailReaderJobStatus`) to track run windows and prevent reprocessing.
- **Retry on deadlock**: `SpringBatchCommon.xml` configures `batchRetryPolicy` with `maxAttempts=5` for `DeadlockLoserDataAccessException` and `DataAccessResourceFailureException`.
- **No explicit data retention policy** is implemented in the batch code; retention is governed by downstream database policies not visible here.

## Compliance Gaps

1. **CVV2 in PushtodebitTransactionVo**: The field `cvv2` (line 33, `PushtodebitTransactionVo.java`) is read from the TabaPay file and potentially persisted. PCI DSS Requirement 3.2.1 explicitly prohibits storing CVV2 after authorization. **This requires immediate review with the Security and Compliance teams.**

2. **Email body content persisted**: `EmailMessageVO.bodyContent` captures the raw HTML body of bounced notification emails. This may contain cardholder PII beyond what is minimally needed. GDPR Article 5(1)(c) data minimisation principle may apply.

3. **Client secret in properties file**: The Microsoft Exchange OAuth `clientSecret` is stored in a flat file on disk (`D:\c-base\config\batch\returnedemailbatch\ReturnedEmailBatch.properties`). This does not meet Strongbox or secrets-manager standards.

4. **Email account passwords in properties**: `emailAccountPassword` is injected as a plain-text Spring property string, stored in the same config file on disk.

5. **No PAN masking in logging**: Log statements in `AutoClaimProcessHelper` (line 132) log `echeck_id`, `payment_id`, `certificate_id` at INFO level. DDA numbers and member IDs are logged throughout multiple processors. These may appear in plaintext log files.

6. **Hibernate second-level cache**: `autoClaimProcessBatchjob.xml` enables Hibernate second-level cache (`use_second_level_cache=true`) with EHCache for `AffiliatePartnerDetail` and `ProgramMapDetail`. Cached data may include program-level sensitive configuration that persists across JVM sessions.
