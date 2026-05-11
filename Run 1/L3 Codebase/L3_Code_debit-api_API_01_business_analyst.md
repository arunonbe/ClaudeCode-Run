# Business Analyst Report — debit-api_API

## 1. Business Purpose
debit-api_API is the **prepaid debit card transaction processing web service** for the Onbe (formerly Citi Prepaid / Wirecard) platform. It exposes a SOAP/WSDL endpoint that allows downstream callers to initiate, confirm, or reverse debit transactions against prepaid card accounts held in the ECount Core (cbase) ledger system. The service operates as a B2B integration layer between order-management systems, partner integrations, and the internal card-account ledger.

Deployment name: `debitapiws`  
SOAP endpoint path: `/services/DebitService`  
Spring Boot artifact version: `3.1.4-SNAPSHOT`

---

## 2. Capabilities

| Capability | Entry Class | Description |
|---|---|---|
| Begin Debit | `BeginDebitController` / `BeginDebitService` | Reserves funds on a prepaid card; creates a PENDING transfer in Core |
| Commit Debit | `CommitDebitController` / `CommitDebitService` | Finalises a pending debit; moves transfer to COMMITTED state |
| Cancel Debit | `CancelDebitController` / `CancelDebitService` | Voids a pending debit; moves transfer to CANCELLED state |
| Get Status | `GetStatusDebitController` / `GetStatusDebitService` | Returns current transfer state (PENDING / COMMITTED / CANCELLED / UNKNOWN) |
| Inquiry | `InquiryController` / `InquiryService` | Fetches supplemental data (balance, refill info, transaction history) without altering state |

All five operations are assembled by `DebitWebServiceHandlerImpl` (ws module) and exposed through the `IDebitWebService` interface. AOP interceptors `GlobalRequestIDInterceptor` and `AuditMethodInterceptor` wrap every call.

---

## 3. Key Business Entities

| Entity | Class / Source |
|---|---|
| Program | `BeginDebitRequest.program_id` (line 27); hardcoded list `["04014096","04019215"]` in `DebitApiConfig.java` |
| Partner User | `Request.partner_user_id` — external caller's user reference |
| Account | `Request.account_id`; resolved to internal `AccountDefinitionDDA` via `AccountHelper` |
| Transfer | `TransferDefinition` + `TransactionDefinition[]`; identified by `transfer_id` |
| Transaction (idempotency key) | `Request.transaction_id` — partner-supplied unique ID stored in addenda `PARTNER_PAYMENT_ID` |
| Amount | `long amount` (cents, USD); `CurrencyCodes.UNITED_STATES_DOLLAR` enforced |
| Member | `Member` GUID; prod value `42BA18D5-9879-494B-9B4C-D8C9D2D1CC75` from app-config/prod |
| Agent | String `B2C` (prod) / `B2CSTAGE` (QA/staging) — controls Director credential lookups |

---

## 4. Business Rules

1. **Transaction state machine**: Begin → Commit | Cancel. Attempting to commit an already-committed transaction raises `TRANSACTION_ALREADY_COMMITED`; `BeginDebitService.doExecute` (line 42) and `CommitDebitService.doExecute` (line 21) both enforce this.
2. **Insufficient funds** (`CoreType.INSUFFICIENT_FUNDS`): surfaces as `ServiceFailureException.INSUFFICIENT_FUNDS`; the Core system now internally cancels failed begins (`BeginDebitService`, line 149 comment).
3. **Velocity controls**: min/max per-transaction amount, max daily and monthly amounts checked against `TransactionStrategy.velocities` in `BeginDebitService.validateAmountPerTran` (lines 233–266).
4. **Negative balance**: Allowed when `beginDebitInput.isAllowNegativeBalance()` is true; sets `transferDefinition.facility = "job"` (`BeginDebitService`, lines 79–86).
5. **Account must be active** before commit or cancel (`CommitDebitService` line 45, `CancelDebitService` line 47).
6. **Program allow-list**: Only programs in `DebitApiConfig.programList` (`04014096`, `04019215`) are accepted.
7. **Addenda slots**: `AddendaType` enum supports `PARTNER_PAYMENT_ID`, `PROMOTION`, `CZ_USER_ID`, `ADDENDA_1`–`ADDENDA_5`.

---

## 5. Business Flows

### 5.1 Standard Debit Flow
```
Client → POST /services/DebitService (beginDebitRequest)
  → GlobalRequestIDInterceptor (assigns global request ID)
  → DebitWebServiceHandlerImpl.beginDebit()
  → BeginDebitController.execute()
  → Validator.validate()
  → AuditHelper.preProcess()
  → BeginDebitService.doExecute()
    → AccountHelper.getMemberId() [RequestDataSource]
    → AccountHelper.getAccountDeviceId() [cbase via ECoreDevice/ECoreMember]
    → TransferManagerImpl.begin() → ECoreTransfer (Core2 XML-RPC)
  → AdditionalInfoHelper (balance/refill optional)
  → AuditHelper.postProcess()
  → Response marshalled to SOAP XML

Client → POST /services/DebitService (commitDebitRequest / cancelDebitRequest)
  [same chain; CommitDebitService calls TransferManagerImpl.commit/cancel]
```

---

## 6. Compliance Relevance

- **PCI DSS**: Service processes card account IDs and amounts; no PAN/CVV in transport layer (card numbers are internal device IDs). Credentials resolved via Azure Key Vault (not in code). Addenda fields could carry sensitive data if callers mispopulate them — no explicit redaction on logs observed.
- **Reg E**: Debit error resolution supported through Cancel flow; idempotency key (`transaction_id`) supports re-presentment handling.
- **UDAAP**: Velocity limits and insufficient-funds handling protect cardholders from overdraft via `validateAmountPerTran`.
- **Audit trail**: `DebitAuditInfoDao` writes pre/post audit records to `CbaseappDataSource`; `AuditMethodInterceptor` records statistics.

---

## 7. Risks

| Risk | Severity | Detail |
|---|---|---|
| Log leakage of account/member IDs | Medium | `BeginDebitService` logs `account_device_id` and `operator_device_id` at INFO level (lines 116–118) — may appear in log aggregators |
| `allow-circular-references: true` in application.yml | Medium | Spring circular-ref override active; indicates unresolved design debt and can mask startup errors |
| Hardcoded program IDs | Low-Medium | `DebitApiConfig` line 16 hard-codes program IDs `04014096`, `04019215`; a new program requires a code change and redeploy |
| No SOAP authentication observed | High | No WS-Security or bearer token requirement visible in `server-config.wsdd` or `DebitApiWsConfig`; relies on network perimeter only |
| Maven compiler target 1.7 mismatch in TESTING_AUTO | Low | Test repo still targets Java 1.7 (`pom.xml`); runtime is Java 21 in API |
| ECount Core connectivity single point of failure | High | All debit operations synchronously depend on Core2 XML-RPC; no circuit breaker pattern observed |
