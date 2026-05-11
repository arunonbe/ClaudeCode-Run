# Data Architect Report — debit-api_API

## 1. Data Stores

| Store | DataSource Bean | Purpose | Config Key |
|---|---|---|---|
| cbaseapp | `CbaseappDataSource` (`CbaseAppDataSourceAutoConfiguration`) | Core card account ledger (balances, accounts, members, transfers) | `spring.datasource.cbaseapp.*` |
| jobsvc | `JobSvcDataSource` (`JobSvcDataSourceAutoConfiguration`) | Job/ETL task management; used by `JobManager` | `spring.datasource.jobsvc.*` |
| ordersvc (order) | `OrderDataSource` (`OrderDataSourceAutoConfiguration`) | Order records | `spring.datasource.order.*` |
| ordersvc (request) | `RequestDataSource` (`RequestDataSourceAutoConfiguration`) | Request-processor config; `RequestProcessorConfigDao` reads from here | `spring.datasource.request.*` |

All four are Microsoft SQL Server databases via `mssql-jdbc:12.8.2.jre11`.

### 1.1 Environment-Specific Connection Strings

| Env | Host | Port |
|---|---|---|
| Prod | `p-lis-db03.nam.wirecard.sys` (cbaseapp) / `p-lis-db01.nam.wirecard.sys` (others) | 2231 |
| QA/Staging | `q-lis-db01.nam.wirecard.sys` / `u-lis-db01.nam.wirecard.sys` | 2231 |

`trustServerCertificate=true` is set on all connection strings — TLS certificate validation is disabled.

---

## 2. Schema Notes (Inferred from Code)

### 2.1 cbaseapp
Supports the CBase/ECount Core object model:
- **Member** (GUID primary key — e.g., prod `42BA18D5-9879-494B-9B4C-D8C9D2D1CC75`)
- **AccountDefinitionDDA** — card account with `dda.accessLevel` and internal device ID
- **Transfer** — monetary transfer record with state (PENDING/COMMITTED/CANCELLED)
- **TransactionDefinition** — two legs per transfer (OPERATOR credit, ECARD debit)
- **Addenda** — up to 5 free-text slots + `PARTNER_PAYMENT_ID` + `PROMOTION` + `CZ_USER_ID`

`DebitAuditInfoDao` (`debitapi-ws` module) writes audit records to cbaseapp.

### 2.2 jobsvc
Accessed via `JobAccountMapDao`, `JobDao`, `SymbolDao` (`DebitApiImplConfig` lines 251–259). Stores job execution state for negative-balance job facility.

### 2.3 ordersvc (request schema)
`RequestProcessorConfigDao` (`DebitApiImplConfig` line 263) reads processor routing configuration; dictates which Core agent/strategy to use for a given program.

---

## 3. Sensitive Data Inventory

| Data Element | Location in Code | Classification |
|---|---|---|
| Database passwords | Azure Key Vault; Key Vault reference names in `app-config/*/appsettings.json` | Secret / PCI Sensitive |
| `memberId` GUID | `app-config/prod/appsettings.json` line 9 — committed to repo | Internal system credential |
| `account_id` (card account number) | `Request.account_id` field; present in SOAP request body and log statements | PCI Sensitive (potential PAN-adjacency) |
| `transfer_id` | Logged at INFO level in `BeginDebitService` (line 116–118) | Internal |
| `partner_user_id` | Present in SOAP request; potentially PII | PII |
| Addenda fields `ADDENDA_1`–`ADDENDA_5` | Unstructured; callers could inject any data | Risk: PII/PAN if misconfigured |
| Director URL (prod) | `app-config/prod/appsettings.json` line 3 — `https://prod.nam.wirecard.sys:8080/service/dispatch.asp` | Infrastructure hostname |

**Note**: No literal PAN, CVV, or SSN values were observed in committed source code or config files. Sensitive field names are logged in some cases (see risks).

---

## 4. Encryption

| Mechanism | Status |
|---|---|
| Azure Key Vault for DB credentials | Active — all four datasource passwords use Key Vault references |
| TLS on DB connections | Technically enabled but `trustServerCertificate=true` disables cert validation (all envs) |
| TLS on Director calls | HTTPS; custom CA cert `nam.wirecard.sys.crt` imported into JVM trust store via Dockerfile (lines 24–27) |
| Application-level field encryption | Not observed in debit-api code |
| SOAP message signing/encryption | Not observed |

---

## 5. Data Flow

```
External SOAP Caller
  │  [HTTPS / port 4005 observed in test]
  ▼
debitapiws (Spring Boot / Tomcat embedded)
  │
  ├─ RequestDataSource (SQL Server / ordersvc) → RequestProcessorConfigDao
  │    [read-only: program routing config]
  │
  ├─ cbaseapp (SQL Server) → DebitAuditInfoDao
  │    [write: audit records before/after each operation]
  │
  ├─ ECoreTransfer / ECoreDevice / ECoreMember (XML-RPC via Core2)
  │    [read/write: account lookup, transfer begin/commit/cancel]
  │
  ├─ jobsvc (SQL Server) → JobManager DAOs
  │    [read: job/symbol lookups for negative-balance facility]
  │
  └─ OrderDataSource (SQL Server) → OrderService
       [order state; URL config present, usage indirect]
```

---

## 6. Data Quality

- **Idempotency**: `transaction_id` is stored as `PARTNER_PAYMENT_ID` addenda but there is no observed duplicate-check guard at the API layer. Callers re-presenting the same `transaction_id` could create duplicate begin operations.
- **Amount type**: `long amount` represents cents (integer). No fractional-cent protection needed, but no explicit upper-bound validation visible beyond `TransactionStrategy` velocity.
- **Null comment handling**: `BeginDebitRequest.populateInput` (line 127) has a bug: `if(getComment() != null || getComment().length() > 0)` — the OR should be AND; a null comment will throw NPE on `getComment().length()`.

---

## 7. Compliance Gaps

| Gap | Standard | Detail |
|---|---|---|
| `trustServerCertificate=true` on all DB connections | PCI DSS Req 4.2.1 | Disables TLS certificate validation to SQL Server; violates requirement for strong encryption in transit |
| Potential PII in logs | GLBA / CCPA | `account_device_id` and `operator_device_id` logged at INFO in `BeginDebitService` (lines 116–118) |
| `memberId` GUID committed to app-config repo | PCI DSS Req 12.3 | System-level credential should not appear in version-controlled config files |
| No observed log masking | PCI DSS Req 3.5 | No log filter to mask account IDs in SOAP request/response logging |
| Duplicate begin not idempotent | Reg E Req 1005.11 | Callers must implement their own dedup; service does not enforce |
