# card-notification-restful_API — Data Architect View

## Data Stores

The service interacts with three Microsoft SQL Server databases, all on the `nam.wirecard.sys` domain:

| Logical Name | Bean ID | Prod Host | Database | Primary Use |
|---|---|---|---|---|
| CBase Application DB | `CbaseappDataSource` | `P-LIS-DB03.nam.wirecard.sys:2231` | `cbaseapp` | Card account data (balances, journals, definitions, affiliate config, SMS profiles); cardholder enrollment and audit log tables |
| ECount Core DB | `EcountSvcDataSource` (ecountcore) | `P-LIS-DB02.nam.wirecard.sys:2231` | `EcountCore` | ECount core service layer data |
| Job Service DB | `JobSvcDataSource` | `P-LIS-DB01.nam.wirecard.sys:2231` | `jobsvc` | Job/workflow data (declared in config, but no direct DAO usage is visible in this service's code) |

All connections use `trustServerCertificate=true` (visible in all `appsettings.json` configs), which bypasses TLS certificate validation.

A fourth runtime data source, **xSearch-XMLRPC**, is accessed via HTTP through the Director service (`director.address` / ECount boot address). This is not a JDBC data source but an internal RPC call to retrieve member data by mobile phone number.

---

## Schema & Tables

The following database objects are referenced directly in source code:

### Table: `sms_cardnotification_log` (cbaseapp database)
Stored procedure: `dbo.sms_cardnotification_log_insert`  
Source: `CardNotificationLogInsertDAO.java`

| Column | SQL Type | Description |
|---|---|---|
| `program_id` | VARCHAR | Prepaid program identifier |
| `mobile_phone` | VARCHAR | Cardholder mobile phone number (PII) |
| `msg_category` | VARCHAR | Always "PULL" (hardcoded in `CardNotificationLoggingInterceptor`) |
| `msg_type` | VARCHAR | Action type: BALANCE, PAYMENT, TRANSACTION, HELP, START, STOP |
| `create_date` | TIMESTAMP | Interaction timestamp |
| `RETURN_CODE` | INTEGER (OUT) | SP return code |

### Table: `sms_cardnotification_profile` (cbaseapp database)
Stored procedure: `dbo.sms_cardnotification_profile_insert`  
Source: `CardNotificationProfileInsertDAO.java`

| Column | SQL Type | Description |
|---|---|---|
| `mobile_phone` | VARCHAR | Mobile phone number (PII) |
| `msg_type` | VARCHAR | Action type ("START" or "STOP") |
| `create_date` | TIMESTAMP | Enrollment/opt-out timestamp |
| `RETURN_CODE` | INTEGER (FUNCTION return) | 1=existing START, 2=new START, 3=STOP success, 4=already stopped |

### Table: `app_sms_msg_profile` (cbaseapp database — inferred)
Accessed via `AppSmsMsgProfileClass.retrieve()` from the ECount xplatform library. Stores per-program SMS message templates with variables (CARD_NUMBER, BAL_AMOUNT, CUR_AMOUNT, DATE, TIME, CS_PHONE, DATE_RANGE_MONTH) and positional ordering. Not a direct JDBC call in this service's code.

### Hibernate-managed Tables (cbaseapp database)
The `LegacyXmlConfig.appContextFactory()` registers these Hibernate entity classes (from `xaffiliate-service` library):
- `com.ecount.one.service.affiliate.Affiliate`
- `com.ecount.one.service.affiliate.AffiliateDetail`
- `com.ecount.one.service.affiliate.AffiliateLocale`
- `com.ecount.one.service.affiliate.AffiliateLocaleAffiliate`
- `com.ecount.one.service.affiliate.AffiliateLocaleCopy`
- `com.ecount.one.service.affiliate.AffiliateLocaleCopyTag`
- `com.ecount.one.service.affiliate.AffiliateLocaleSkin`
- `com.ecount.one.service.affiliate.AffiliateLocaleCopyType`

These are used to determine SMS-pull-enabled programs via `AffiliateService.getAffiliateForValue("SMSPULLENABLEDPROGRAMS", "Y")`.

---

## Sensitive Data Handling

| Data Element | Classification | Where Processed | Where Stored |
|---|---|---|---|
| **Mobile Phone Number (MSISDN)** | PII | Extracted in `CardNotificationUtils.getCardnotificationRequestFromMoRequest()` (chars 2–12 of MSISDN); logged in `cardNotificationInquiry` log statement | Written to `sms_cardnotification_log.mobile_phone` and `sms_cardnotification_profile.mobile_phone` |
| **Cardholder Card Number** | PCI DSS PAD — masked | Only the last 4 digits are used: `EcountUtils.getLastFourDigitsCC(member.getCardNumber())` in `CardNotificationServiceImpl` line 425 | Never persisted by this service; appears only in outbound SMS text |
| **Account Balance** | Financial — sensitive | Formatted in `CardNotificationUtils.getFormattedCurrencyAmount()` | Sent in outbound SMS only; not persisted |
| **SAP/Sinch Credentials** | Secrets | `JaxRsCardNotificationService.sapMtusername` / `sapMtpassword` static fields | Stored in Azure Key Vault via `key_vault_references` in `appsettings.json`; injected via Spring property |
| **Database Credentials** | Secrets | Spring Boot DataSource properties | Azure Key Vault references in `appsettings.json` |
| **Mobile Phone in Logs** | PII in application logs | `log.info("mobile number." + moRequest.getMSISDN())` in `JaxRsCardNotificationService` lines 115, 253 | Application log output — may flow to Dynatrace or log aggregator |

**Critical gap**: The mobile phone number is logged at INFO level **without masking** in `JaxRsCardNotificationService.processMO()` (lines 115) and `processMO_InternalTesting()` (line 253), and also in `CardNotificationUtils.getCardnotificationRequestFromMoRequest()` (line 153). This means full MSISDN (e.g., `+17412354621`) appears in plain text in application logs.

---

## Encryption & Protection

| Mechanism | Applied To | Details |
|---|---|---|
| **Azure Key Vault** | DB credentials (username/password for all 3 datasources), SAP MT credentials | Referenced in all environment `appsettings.json` files via `key_vault_references`; resolved by Spring Cloud Azure Key Vault starter |
| **Azure App Configuration** | All environment-specific settings | Bootstrap via `spring.cloud.azure.appconfiguration`; Managed Identity authentication in non-local environments (`bootstrap.yaml`) |
| **Managed Identity** | Azure App Config + Key Vault access | `credential.managed-identity-enabled: true` in non-local Spring profile; client ID injected via `AZURE_MANAGED_IDENTITY_CLIENT_ID` |
| **TLS (Transport)** | External DB connections | All JDBC URLs use port 2231; `trustServerCertificate=true` bypasses certificate validation — no mutual TLS |
| **TLS (SAP/Sinch)** | Outbound SMS MT | HTTPS URLs used for Sinch endpoint in prod `appsettings.json`: `https://eu.sms.sdi.sinch.com/...` |
| **Java TrustStore** | Internal CA | `nam.wirecard.sys.crt` imported into JRE cacerts in Dockerfile using `keytool` with default password `changeit` |
| **Ehcache (in-memory)** | Member data and SMS profiles | 30-second TTL, heap-only (200 entries), no encryption. Contains `MemberInquiryValue[]` which includes member ID, device ID, EBN (account identifier) |
| **Card Number** | Last 4 digits only in SMS | Full PAN never exposed in this service's output |

**No encryption at rest** for the Ehcache. Member data including device IDs and account identifiers are cached in heap memory unencrypted.

---

## Data Flow

```
[Cardholder Mobile] → SMS Carrier → SAP/Sinch (SMS aggregator)
    ↓ POST (URL-encoded XML / SMS_MO)
[card-notification-restful_API]
    ├── READ: xSearch-XMLRPC via Director (HTTP)
    │     → Returns MemberInquiryValue[] (memberId, deviceId, cardNumber, EBN, userStatus)
    │     → Cached in Ehcache "MOBILE_<mobileNumber>" key (30s TTL)
    ├── READ: AffiliateService via Hibernate (CbaseappDataSource)
    │     → Returns SMSPULLENABLEDPROGRAMS list
    ├── READ: AppSmsMsgProfileClass via xplatform (CbaseappDataSource / ECount)
    │     → Returns SMS message templates per program
    │     → Cached in Ehcache "MSG_<programId>" key (30s TTL)
    ├── READ: EDevice.processInquiry() via ECount Director (HTTP)
    │     → Returns AccountBalance, AccountJournal, AccountDefinition, Member
    ├── WRITE: dbo.sms_cardnotification_profile_insert (CbaseappDataSource)
    │     → On START or STOP commands, or auto-enroll before BALANCE
    ├── WRITE (AOP/async-like): dbo.sms_cardnotification_log_insert (CbaseappDataSource)
    │     → After every cardNotificationInquiry call via CardNotificationLoggingInterceptor
    ↓ POST (URL-form-encoded SMS_MT)
[SAP/Sinch] → SMS Carrier → [Cardholder Mobile]
```

---

## Data Quality & Retention

- **No data retention policy** is implemented in this codebase. The `sms_cardnotification_log` and `sms_cardnotification_profile` tables grow without bounds; archival/purge logic is not present.
- **Cache TTL is 30 seconds** (`ehcache.xml` lines 8–10). Member data and message profile data are considered stale after 30 seconds, which is functionally correct for a real-time balance service but could return momentarily stale member status.
- **No input validation** of the MSISDN or message body beyond null checks (`null == moRequest.getMESSAGE() || null == moRequest.getMSISDN()`). Invalid/malformed phone numbers will be forwarded to xSearch where the error is caught and returned as a system error SMS.
- **Mobile number extraction** is positional: `mobileNum.substring(2, 12)` — assumes MSISDN is always `+1XXXXXXXXXX` format. Non-US numbers or numbers with different prefix lengths will be silently truncated/corrupted.

---

## Compliance Gaps

| Gap | Regulation | Severity | Evidence |
|---|---|---|---|
| Full MSISDN logged unmasked | GDPR Art. 25 (data minimisation), CCPA | High | `JaxRsCardNotificationService` lines 115, 253; `CardNotificationUtils` line 153 |
| `trustServerCertificate=true` on all JDBC connections | PCI DSS Req. 4 (data in transit) | High | `app-config/prod/appsettings.json`, `qa/appsettings.json`, `staging/appsettings.json` |
| No data retention / deletion for PII tables | GDPR Art. 5(1)(e), CCPA right to delete | High | Absence of purge SPs or TTL logic in codebase |
| Ehcache in-memory holds member data unencrypted | PCI DSS Req. 3 (protect stored data) | Medium | `ehcache.xml`; `CardNotificationServiceImpl` cache keys |
| No inbound request authentication | PCI DSS Req. 8 / general API security | High | No auth headers, tokens, or IP allowlists in `JaxRsCardNotificationService` |
| Static SAP credentials in static fields | PCI DSS Req. 8 | Low (mitigated by Key Vault) | `JaxRsCardNotificationService.sapMtusername/sapMtpassword` are static fields injected at startup |
