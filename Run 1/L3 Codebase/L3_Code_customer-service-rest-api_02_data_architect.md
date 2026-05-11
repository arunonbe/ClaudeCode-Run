# customer-service-rest-api — Data Architect View

## Data Stores
| Store | Bean Name | JDBC URL Source | Driver | Purpose |
|---|---|---|---|---|
| cbaseapp SQL Server DB | `CbaseappDataSource` | `${CUSTOMERSERVICE_CBASEAPPDB_URL}` | `com.microsoft.sqlserver.jdbc.SQLServerDriver` | Core cardholder / account data (comments, CSA inquiry types, affiliate data) |
| jobsvc SQL Server DB | `JobSvcDataSource` | `${CUSTOMERSERVICE_JOBSVCDB_URL}` | `com.microsoft.sqlserver.jdbc.SQLServerDriver` | Job service data (order processing) |
| Legacy xPlatform service | RMI / XML-RPC (via `SearchAccount`, `ReissueCard`) | `${ECOUNT_CONFIG_SERVICE_URL}` | n/a | Account inquiry, card reissue via eCount xPlatform |
| ECountCore REST | HTTP client | `${ECOUNT_CORE_BASE_URL}` | Feign / WebClient | Modern eCount-Core REST API for member/device operations |
| AccountManagementAPI (CMS) | SOAP-style lib | `${CMS_OP_LOGIN_URL}` | n/a | Account status updates and PIN setting via Citi CMS integration |

## Schema / Key Tables Accessed
- **cbaseapp:** CSA inquiry types, inquiry categories, escalation data, comment history, affiliate data — accessed via stored procedures through DAO classes (`CommentHistoryDAOImpl`, `InsertCommentDAOImpl`, etc. configured in `CSConfig.java`).
- **jobsvc:** Job service records (bean configured but operations routed through legacy xPlatform job libraries).

## Sensitive Data
| Data Element | Location in Flow | Handling |
|---|---|---|
| Card number (PAN) | Received in `cardNumber` header (`GET /v1/account-inquiry`) | Logged with last-4 masking in `CustomerService.java` line 94; returned masked by backend |
| PIN | Received in `SetPinRequest.newPin` | NOT logged (log statement at line 143–145 explicitly omits `newPin`); passed to `SetPinService` |
| Account number | Received in request body/header | Not logged in full; partial masking applied |
| Application ID | Received in header | Logged with last-10 masking (`CustomerService.java` line 245) |
| Registration PII (name, address, phones, email) | Returned in `AccountInquiryResponse.registration` | No masking applied in the API layer — returned as-is from backend |

## Encryption
- TLS for all external communication enforced at the APIM/gateway layer (not visible in this repo).
- DB credentials injected via environment variables (`${CUSTOMERSERVICEAPI_CBASAPPDB_PASSWORD}`, `${CUSTOMERSERVICEAPI_JOBSVCDB_PASSWORD}`) — never hard-coded.
- CA certificate for internal AD (`nam-ad-dc1-ca.crt`) imported into JRE truststore in `Dockerfile` (line 27).

## Data Flow
```
Client → APIM (External-Auth-Response JWT) → AuthenticationFilter
    → CustomerServiceController
        → CustomerService (reactive Mono pipeline)
            → [AccountMgmtAPI / SearchAccount / ReissueCard / SetPinService]
                → cbaseapp DB (stored procs via Spring JDBC)
                → ECountCore REST
                → Legacy xPlatform (RMI)
            ← Mapper layer (AccountInquiryMapper, etc.)
        ← Mono<ResponseModel>
    ← JSON response
```

## Connection Pool Configuration (`application.yml` lines 84–136)
- Both datasources use HikariCP.
- `max-pool-size`: env-configurable (`${MAX_POOL_SIZE:10}`), default 10.
- `min-idle`: hard-coded 10 (equal to max — no dynamic scaling).
- `max-lifetime`: default 180000 ms (3 minutes) — short; may cause excessive reconnections under load.
- JNDI names registered: `jdbc/CbaseappDataSource`, `jdbc/JobSvcDataSource`.

## Data Quality
- Idempotency key: `transactionId` on requests; `existingTransaction: true` returned for duplicates.
- Input validation via Bean Validation (`@Valid`) and OpenAPI-generated constraints (pattern, minLength, maxLength).
- Date parameters converted from `yyyy-MM-dd` string to integer `yyyyMMdd` via `CustomerService.convertDate()` line 219.

## Compliance Gaps
- Registration profile (PII: full name, address, phone, email) returned in `AccountInquiry` response without field-level masking in the API layer; data classification and access-control on who may call with `registrationDetail=true` must be enforced at APIM/auth level.
- No explicit data-retention or data-minimisation policy visible in this service.
- `allow-circular-references: true` (`application.yml` line 75) is a Spring anti-pattern that can hide misconfigured bean lifecycles; not a data issue but an architectural risk.
