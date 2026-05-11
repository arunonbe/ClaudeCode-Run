# Data Architect — oneplatform-rest_API

## Data Stores
| Store | Type | Notes |
|-------|------|-------|
| `cbaseapp` SQL Server | Primary relational DB | `q-lis-db01.nam.wirecard.sys:2231` (dev/qa); `P-LIS-DB03` (prod) |
| `EcountCore` SQL Server | Secondary relational DB | `q-lis-db02.nam.wirecard.sys:2231` (dev/qa); `P-LIS-DB02` (prod) |
| `jobsvc` SQL Server | Tertiary relational DB | `q-lis-db01` (dev/qa); `P-LIS-DB01` (prod) |
| Azure Redis Cache | Cache (Jedis 5.2.0, TLS) | `radis-az1-cluster-qa-ss.redis.cache.windows.net:6379` (dev); `redis-az1-recipientweb-prod-ss.redis.cache.windows.net:6380` (prod) |
| Ehcache (in-process) | Local JVM cache | `ehcache.xml` config; used for affiliate content and copy cache |
| Azure App Configuration | Feature flags / config | Connection string in `application.yaml` (dev value hardcoded) |
| H2 (test) | In-memory DB | Test scope only |

## Schema and Access Patterns
- **cbaseapp**: Accessed via JDBC stored procedures (Spring `JdbcTemplate` / `StoredProcedure` subclasses).
  - Key SPs: `b2c_proc_get_user_popup`, `check_for_existing_user`, `create_ccc_user`, `create_user_ecount_member`, `get_user_by_member_id`, `get_spin_config`, `InsertOtpGracePeriodSP`, `IsOtpGracePeriodSessionValidSP`, `CloseOtpGracePeriodsWithLogoutSP`, `CheckUsersTermsAndConditions`, `CreateTermsAndConditions`, `Insert_recipient_api_audit`, `UpdateUserEcardIdSP`, `DeleteRecordSP`.
  - Claimable payment tables: `ClaimablePaymentAddendaDao`, `ClaimablePaymentTransactionDao`, `ProgramClaimableChoiceDao`.
  - Claim code redemption: `ClaimCodeRedemptionInfoDAO`.
- **EcountCore**: Accessed via XMLRPC (`director-service` at `bootAddress`) and JDBC for some paths.
- **jobsvc**: Used via JDBC; specific SPs not visible in the inspected source.

## Sensitive Data Classification
| Data Element | Classification | How Handled |
|-------------|---------------|-------------|
| Cardholder username / password | Authentication credentials | Delegated to ecount/xplatform layer; not stored by this service |
| JWT tokens | Session credential | HS256, 10-min TTL; secret from Key Vault |
| DDA (bank routing + account number) | PII / financial | AES-encrypted on mobile path (`mobileApp.ddaEncrypt=Y`); AES key/IV from Key Vault |
| Card details (balance, last 4) | Financial / PCI scope | Read from ecount backend; not persisted by this service |
| OTP codes | Authentication | Stored in DB with grace period; `InsertOtpGracePeriodSP` |
| IP address | PII (GDPR) | Sent to GeoIP service for lookup; not explicitly logged |
| Email address | PII | Used for notifications; passed to xplatform notification layer |
| Affiliate/program configuration | Business-confidential | Cached in Redis and Ehcache |
| Claim codes | Financial (disbursement token) | Redeemed via `ClaimCodeRedemptionInfoDAO` |

## Encryption
- SQL Server: TLS 1.2 on all three data source connections (`sslProtocol=TLSv1.2`).
- Redis: TLS in production (`port: 6380`); plaintext in dev (`port: 6379`).
- JWT: HS256 signed with secret from Key Vault (`mypaymentvaultapi-jwt-secret`).
- AES encryption for DDA data on mobile flows; key and IV from Key Vault (`mypaymentvaultapi-aes-secret`, `mypaymentvaultapi-aes-iv`).
- JWE helper (`JweHelper.java`) for encrypting selected response payloads — key management not visible in config files inspected.
- Western Union integration uses a static key (`westernunion.statickey`) stored in plaintext in `application.yaml`.

## Data Flow
```
Browser / Mobile App
        │ HTTPS (JWT)
        ▼
oneplatform-rest_API
  ├── Redis Cache ──────────────────── Affiliate/content config (read)
  ├── cbaseapp SQL ─────────────────── User auth, OTP, claimable, audit
  ├── EcountCore SQL / XMLRPC ─────── Card data, transactions, registration
  ├── jobsvc SQL ──────────────────── Job/scheduling data
  ├── Dapr sidecar ────────────────── PayPal, PayPal payout, push provisioning, GeoIP
  ├── CBTS HTTP ───────────────────── Cross-border (IEFT) transfer
  ├── BioCatch API (HTTPS) ────────── Behavioral risk scoring
  └── Google reCAPTCHA (HTTPS) ─────── CAPTCHA verification
```

## Data Quality and Retention
- OTP grace periods stored in `cbaseapp`; closed on logout (`CloseOtpGracePeriodsWithLogoutSP`).
- Audit records inserted via `Insert_recipient_api_audit` stored procedure on sensitive operations.
- Redis cache has no TTL — affiliate configuration persists until admin service refreshes it.
- Ehcache (`ehcache.xml`) in-process cache for copy/content; configuration not read in this analysis but XML present.
- No data retention policies are enforced by this service; upstream DB handles retention.

## Compliance Gaps
- **PCI DSS Req 3**: No evidence of tokenization or masking of card data within this service; card data flows through from ecount backend.
- **PCI DSS Req 6.3 / Req 3.5**: Multiple secrets in `application.yaml` (Azure App Config connection string with embedded secret, Redis cache key, CBTS credentials, Western Union static key).
- **GDPR / CCPA**: IP addresses processed by GeoIP; audit log insertion (`Insert_recipient_api_audit`) — confirm PII fields logged are within consent scope.
- **Reg E**: OTP grace period logic is critical for fund-transfer authorization; any bypass represents a Reg E risk.
- **NACHA**: ACH bank details (`SaveBankDetailsRequest`) — need to verify routing number validation and fraud controls are enforced at the XMLRPC/DAO layer.
