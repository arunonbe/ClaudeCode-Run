# om-payment-api — Data Architect View

## Data Architecture Overview

`om-payment-api` is a **multi-database, multi-system data orchestrator**. It does not own its own primary data store — it reads from and writes to four SQL Server databases and two external SOAP/RPC services, acting as a translation and orchestration layer between the modern REST API contract and the legacy eCount Core platform.

## Database Architecture

### Four Data Sources (from `DatabaseConfiguration.java` and `application.yml`)

| DataSource Bean | Database | Server | Purpose |
|---|---|---|---|
| `CbaseappDataSource` | `cbaseapp` | `u-lis-db01.nam.wirecard.sys:2231` | Core application data (accounts, affiliates) |
| `JobSvcDataSource` | `jobsvc` | `u-lis-db01.nam.wirecard.sys:2231` | Job service state |
| `OrderSvcDataSource` | `ordersvc` | `u-lis-db01.nam.wirecard.sys:2231` | Order processing state |
| `ecountcoreDataSource` | `ecountcore` | `u-lis-db02.nam.wirecard.sys:2231` | eCount core account and transaction data |

Three of four databases share the same SQL Server instance (`u-lis-db01`), while `ecountcore` is on a separate instance (`u-lis-db02`). All use SQL Server port 2231 (non-standard; standard is 1433) and the `instanceName` parameter indicates named instances.

### Connection Properties
All datasources share identical security configuration (from `application.yml` lines 20-43):
```
sslProtocol=TLSv1.2;trustServerCertificate=true
```
**Critical finding**: `trustServerCertificate=true` disables TLS certificate validation. While TLS encrypts the channel, this setting makes the connection vulnerable to man-in-the-middle attacks. The certificate should be added to the JVM truststore and `trustServerCertificate=false` enforced.

### Connection Pooling and Timeout
Each datasource has:
- `timeout: 5000` (ms) — connection acquisition timeout (5 seconds)
- `fail-fast: true` — triggers `DatabaseStartupValidator` to verify connectivity on application startup before accepting traffic

The `DatabaseStartupValidator` beans (e.g., `jobSvcDataSourceValidator`, lines 67-73 in `DatabaseConfiguration.java`) use `DatabaseDriver.SQLSERVER.getValidationQuery()` to probe the connection, preventing the application from starting if critical databases are unreachable. This is a sound operational pattern.

### Transaction Management
Each datasource has its own `DataSourceTransactionManager` bean, with `TransactionAwareDataSourceProxy` wrapping the physical datasource. This pattern enables transaction propagation through Spring's transaction synchronization mechanism. However, there are four independent transaction managers — there is **no distributed transaction coordinator**. Operations that span multiple databases (e.g., writing to `cbaseapp` and `jobsvc` in the same business operation) are not atomic across datasources.

## Data Access Layer

### DAO Classes
- `AccountDetailDao` (`dao/AccountDetailDao.java`) — uses `ecountcoreDataSource`; provides `getDdaNumber(deviceId)` and `updateBlockCode(ddaNumber)` for DDA account operations supporting card reissue.
- `CheckActivityDao` (`dao/CheckActivityDao.java`) — provides check transaction history queries.

### External System Data Access
Data access to eCount Core, Citi Debit API, and Director service happens through Spring beans configured in `ECountCoreBeanConfig.java` and `AccountManagementBeanConfig.java`:
- `ECoreDevice`, `ECoreMember`, `ECoreTransfer` — eCount Core RPC objects using `ThreadLocalRequestContextHolder` for request context propagation.
- `DebitService`, `BeginDebitService`, `CommitDebitService`, `CancelDebitService` — Citi Debit API services.
- The `agent` value (`B2CSTAGE` from `application.yml` line 78) identifies the calling system to eCount Core.

## Domain Model

### Key Domain Entities (from `src/main/java/.../model/domain/`)

- **Card** — represents a prepaid card; device ID, PAN, status, delivery preference.
- **Registration** — cardholder demographic data (name, address, phone, email, SSN).
- **AchWithdraw** / **CheckWithdraw** / **VoidCheckWithdraw** — disbursement instrument representations.
- **Addenda** — key-value metadata attached to transactions.
- **Address** — structured address with PO Box detection logic.
- **Load** — represents a fund load event.
- **Link** — card linking metadata.

### PII/SAD Data Fields (High Sensitivity)

The domain model and request DTOs contain:
- SSN — in `Registration` and related request objects (obfuscated in logs per Logbook config).
- Card number (PAN) — returned in `CardInquiryResponse`; 16-digit account number.
- CVV — returned in `CvvInquiryResponse`; Sensitive Authentication Data.
- Date of birth — potentially in registration fields.
- Bank account details — in ACH withdrawal requests.
- Physical addresses — in registration and card delivery requests.

PCI DSS prohibits storage of CVV post-authorization. The `cvvInquiry` endpoint returns CVV — this must only be called from within the CDE by authorized systems and must not result in CVV being logged, stored, or transmitted beyond the intended recipient.

## Object Mapping Architecture

The service uses MapStruct (v1.6.3) for object mapping, with 25+ mapper classes in `src/main/java/.../model/mapper/`. This provides compile-time type-safe mapping between REST API DTOs and eCount/Citi service input/output objects. MapStruct generates code at compile time, avoiding runtime reflection overhead.

Key mappers include:
- `CreateAccountRequestMapper` — maps REST `CreateAccountRequest` to eCount `CreateAccountInput`.
- `WithdrawRequestMapper` / `WithdrawResponseMapper` — maps between REST withdraw types and Citi Debit API objects.
- `CardInquiryResponseMapper` — maps eCount card data to REST response; this mapper handles PAN data.
- `CvvInquiryResponseMapper` — maps CVV data to REST response; this mapper handles SAD.
- `DebitRequestMapper` / `DebitResponseMapper` (in `debitapi/` subpackage) — maps debit transaction objects.

## Audit and Debit Audit Trail

`DebitTransactionServiceImpl.java` maintains an explicit audit trail for debit transactions via `AuditHelper`:
- `insertDebitAuditInfo(transaction_id, BEGIN_PENDING, serviceInput)` — on new transaction start.
- `updateStatusDebitAuditInfo(transactionId, status)` — on completion (BEGIN_SUCCESS, BEGIN_FAILED, COMMIT_SUCCESS, etc.).

This provides a complete state machine audit trail for each debit transaction, supporting reconciliation and dispute resolution. The audit write is in the `finally` block (lines 157-167 in `DebitTransactionServiceImpl.java`), ensuring it executes even if the service call fails.

## Mock/Sandbox Data Model

The `src/main/resources/sandbox/responses/` directory contains 11 JSON mock response files:
- `addFunds-200.json`, `beginDebit-200.json`, `cancelDebit-200.json`, `cardInquiry-200.json`, `commitDebit-200.json`, `createAccount-201.json`, `createBulkOrder-201.json`, `cvvInquiry-200.json`, `linkCard-200.json`, `updateRegistration-200.json`, `withdraw-200.json`

These are used by the `mock` Spring profile for integration testing without live backends. **These files must not contain real PANs, CVVs, or SSNs.** They should use synthetic test data (e.g., BIN `411111`, last 4 `0000`) consistent with PCI DSS sandbox data policies.

## Data Lineage Summary

```
Caller (via REST) → AccountManagementRestController
  → AccountManagementRestHandler
    → CreateAccountService / AddFundsService / WithdrawService / etc.
      → SynchronousOrderProcessor → JobService (jobsvc DB + ordersvc DB)
        → eCount Core (ecountcore DB via ECoreDevice/ECoreMember/ECoreTransfer)
          → Citi Prepaid Account Management API (accountmanagementapi)
          → Citi Debit API (debitapi)

Card data returns:
  eCount Core → CardInquiryService → CardInquiryResponseMapper → REST Response
  (PAN and CVV traverse the full stack; must be in TLS on all hops)
```
