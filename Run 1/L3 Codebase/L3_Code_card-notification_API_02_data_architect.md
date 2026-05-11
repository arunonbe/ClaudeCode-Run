# card-notification_API — Data Architect View

## Data Stores

### 1. SQL Server — CbaseApp Database
- **Connection**: Configured at runtime via `DirectorConfiguredDBCPdatasourceCreator` (bean `dataSourceCreator` in `dataSourcesContext.xml` line 19). The director service resolves the connection using `${cardnotification.agent}` and `${cardnotification.cbaseapp.database}` properties.
- **Test override** (`applicationContextTest.xml` line 6): `jdbc:jtds:sqlserver://ecsqldev1:1433/cbaseapp` — reveals that the dev/test database host is `ecsqldev1`, the DB is `cbaseapp`, with credentials `test/test`.
- **Purpose**: Stores notification audit logs and is queried for affiliate/program configuration via Hibernate-mapped entities.

### 2. SQL Server — EcountCore Database
- **Test override** (`applicationContextTest.xml` line 21): `jdbc:jtds:sqlserver://ecsqldev1:1433/ecountcore_test`
- **Purpose**: eCount core account data accessed indirectly through the `EDevice`, `EMember`, and related platform objects.

### 3. EHCache (In-Process, Disk-Overflow)
- **Configuration file**: `src/main/resources/ehcache.xml`
- **Cache name**: `cardnotification_cache`
- **Memory limit**: 1,000 elements in memory; 100,000 elements on disk
- **Disk path**: `java.io.tmpdir` (system temp directory)
- **TTL (idle)**: 604,800 seconds (7 days)
- **TTL (live)**: 1,209,600 seconds (14 days)
- **diskPersistent**: false (cache clears on server restart)
- **Keys stored**:
  - `MOBILE_{mobileNumber}` → `MemberInquiryValue[]` (member records including card number)
  - `MSG_{programId}` → `AppSmsMsgProfileCollection` (SMS message templates)

### 4. xSearch-xmlrpc / Director Service (Remote Read-Only)
- Accessed via `IXSearchClient` through `XSearchClientFactory.getClient(XSearchClientTypes.XMLRPC_Client, URI(directorUrl), agent)` in `CardNotificationServiceImpl.java` line 386.
- Used exclusively to look up `MemberInquiryValue[]` by mobile phone number.

## Schema & Tables

### sms_cardnotification_log (SQL Server, CbaseApp)
Populated by stored procedure `dbo.sms_cardnotification_log_insert` via `CardNotificationLogInsertDAO.java`.

| Column | SQL Type | Source |
|---|---|---|
| program_id | VARCHAR | `MobileResponse.programId` |
| mobile_phone | VARCHAR | `MobileResponse.mobileNumber` |
| msg_category | VARCHAR | Always `"PULL"` (hardcoded in `CardNotificationLoggingInterceptor.java` line 53) |
| msg_type | VARCHAR | `MobileResponse.actionType` (BALANCE / PAYMENT / TRANSACTION / HELP) |
| create_date | TIMESTAMP | `MobileResponse.timestamp` |
| RETURN_CODE | INTEGER | OUT parameter from stored proc |

### app_sms_msg_profile (SQL Server, CbaseApp — read via Hibernate/xAffiliateService)
Referenced in `CardNotificationServiceImpl.java` line 200 error message: `"No SMS message is configured for program id {0} in app_sms_msg_profile table"`. Accessed via `AppSmsMsgProfileClass.retrieve()`.

| Column (inferred from code) | Type | Notes |
|---|---|---|
| program_id | VARCHAR | Program identifier |
| msg_type | VARCHAR | BALANCE, PAYMENT, TRANSACTION, TRANSACTION_NULL, PAYMENT_NULL, HELP |
| msg_text | VARCHAR | Template text with positional `{0}`, `{1}` placeholders |
| order1–order4 | VARCHAR | Variable substitution order (CARD_NUMBER, BAL_AMOUNT, CUR_AMOUNT, DATE, TIME, CS_PHONE, DATE_RANGE_MONTH) |
| date_range_month | VARCHAR | Look-back window in months for journal queries |

### Affiliate / Program Tables (Hibernate-mapped, CbaseApp)
Mapped entities in `applicationContext.xml` lines 72–94:
- `com.ecount.one.service.affiliate.Affiliate`
- `com.ecount.one.service.affiliate.AffiliateDetail`
- `com.ecount.one.service.affiliate.AffiliateLocale`
- `com.ecount.one.service.affiliate.AffiliateLocaleAffiliate`
- `com.ecount.one.service.affiliate.AffiliateLocaleCopy`
- `com.ecount.one.service.affiliate.AffiliateLocaleCopyTag`
- `com.ecount.one.service.affiliate.AffiliateLocaleSkin`
- `com.ecount.one.service.affiliate.AffiliateLocaleCopyType`

Queried via `ProcGetAffiliateByValue` (stored proc) to retrieve `SMSPULLENABLEDPROGRAMS` flag, and via `ProcGetAffiliatePresentation` (stored proc) to retrieve metadata such as `contact_info_phone` for HELP messages.

## Sensitive Data Handling

| Data Element | Classification | Where Seen | Handling |
|---|---|---|---|
| Full card number | PAN (PCI DSS SAD) | `MemberInquiryValue.cardNumber` cached in EHCache under `MOBILE_{mobileNumber}` | Masked to last-4 via `EcountUtils.getLastFourDigitsCC()` before SMS construction (line 216, `CardNotificationServiceImpl`). Full PAN is in cache. |
| Mobile phone number | PII (GLBA/CCPA) | `CardNotificationRequest.mobileNumber`; cache key; DB log column `mobile_phone`; application log output (line 42, `JaxRpcCardNotificationService`) | Logged in plaintext to application log and to `sms_cardnotification_log` table |
| Member ID | PII | `MemberInquiryValue.memberId`; EHCache value | Not logged to DB audit table; present in in-memory/disk cache |
| EBN / DDA | Account identifier | `MemberInquiryValue.ebn`; cached | Used to derive programId; not logged to DB |
| Available balance (integer cents) | Financial | Returned in SMS text | Formatted to currency string; not persisted in log table |
| Transaction amount | Financial | Returned in SMS text | Formatted to currency string; not persisted in log table |

## Encryption & Protection

- **In-transit**: No TLS configuration is present in the repository. The WSDL endpoint (`CardNotificationService.wsdl` line 109) uses `http://localhost:9070/...` (plain HTTP). There is no evidence of HTTPS enforcement in `web.xml` or `server-config.wsdd`.
- **At-rest (EHCache disk)**: The `ehcache.xml` disk store writes to `java.io.tmpdir` with no encryption configuration. Full PAN values stored in `MemberInquiryValue` objects flow to disk in serialized form with no encryption.
- **Database**: No connection encryption properties are specified in the datasource configuration. The test context uses `DriverManagerDataSource` with no SSL JDBC parameters.
- **Passwords/secrets**: Properties files (externalized via `${CBASE_HOME_URL}/config/CardNotification/CardNotification.properties`) are not in the repository. The `settings.xml` Maven wrapper file may contain Nexus credentials (not examined — binary artifact).

## Data Flow

```
SMS Gateway
    |
    | SOAP/HTTP: CardNotificationRequest{mobileNumber, actionType, carrier}
    v
JaxRpcCardNotificationService (logs mobileNumber + actionType to app log)
    |
    v
CardNotificationServiceImpl.cardNotificationInquiry()
    |
    +--[EHCache MISS]--> xSearch-xmlrpc: FindMemberByMobilPhone(mobileNumber)
    |                         --> returns MemberInquiryValue[] (incl. full cardNumber)
    |                    [EHCache PUT] MOBILE_{mobileNumber} -> MemberInquiryValue[]
    |
    +--[EHCache MISS]--> AppSmsMsgProfileClass.retrieve(programId)
    |                    [EHCache PUT] MSG_{programId} -> AppSmsMsgProfileCollection
    |
    +--> EDevice.processInquiry() --> AccountDetail{balance, journal, definition}
    |         (not cached; real-time)
    |
    +--> Format SMS text (masked card number, formatted balance/amount)
    |
    +--> [AOP AfterReturning] CardNotificationLogInsertDAO
    |         --> dbo.sms_cardnotification_log_insert(programId, mobilePhone,
    |                                                  "PULL", actionType, timestamp)
    v
CardNotificationResponse{MobileResponse[]{programId, mobileNumber, carrier, smsData, timestamp}}
    |
    v
SMS Gateway
```

## Data Quality & Retention

- **Cache staleness risk**: Member status changes (e.g., suspend, mobile number re-assignment) are not reflected in cached responses for up to 14 days. This is explicitly documented in `ehcache.xml` lines 28–35.
- **Log table retention**: No retention policy or purge mechanism is visible in the repository. The `sms_cardnotification_log` table grows unbounded based on the code.
- **No input validation on mobileNumber**: `CardNotificationRequest` accepts any string for `mobileNumber` — no format, length, or character validation is applied before it is used as a cache key and passed to xSearch. This creates a potential for cache pollution or injection attacks.
- **Balance formatting edge case**: `CardNotificationUtils.getFormattedCurrencyAmount()` (line 88) applies different decimal precision rules depending on whether the amount exceeds 9,999.99 — amounts above this threshold lose decimal precision in the formatted string.

## Compliance Gaps

1. **PCI DSS 3.3 / 3.4 — PAN stored unencrypted in EHCache disk overflow**: Full card numbers from `MemberInquiryValue` are cached to `java.io.tmpdir` without encryption. This is a PCI DSS scope violation if the disk is not protected by OS-level FDE meeting PCI requirements.
2. **PCI DSS 4.2 — Unencrypted transmission**: No HTTPS is configured in the repository. If the SMS gateway calls this service over plain HTTP, PANs and PII are exposed in transit.
3. **GLBA / CCPA — PII logging**: Mobile phone numbers are logged to application logs in plaintext (`JaxRpcCardNotificationService.java` line 42). Log storage and access controls are not defined in this repository.
4. **No data masking in audit log**: The `sms_cardnotification_log` table stores `mobile_phone` in plaintext with no masking or tokenization.
5. **Test credentials in source control**: `applicationContextTest.xml` contains database host name (`ecsqldev1`), database names, and credentials (`test/test`). While these are test values, the host name leakage could assist reconnaissance.
