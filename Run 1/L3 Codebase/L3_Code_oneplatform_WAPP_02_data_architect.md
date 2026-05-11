# Data Architect — oneplatform_WAPP

## Data Stores

| Store | Technology | Purpose |
|---|---|---|
| Primary application DB | Microsoft SQL Server (jTDS 1.2 JDBC driver) | User accounts, affiliate config, transactions, sessions |
| cbaseapp DB | SQL Server (via `cbaseappContext.xml`) | Core card platform data |
| xsecurity DB | SQL Server (via `applicationContext-xsecurity-*`) | Security, login, MFA data |
| JobService DB | SQL Server (via `appCtx-jobsvc-ds.xml`) | Background job scheduling |
| Subaru Rewards DB | SQL Server (via `applicationContext-subaru-ds-alias.xml`) | Subaru rewards program data |
| Message Center | Message queue / service (via `MessageCenter-client.xml`) | Notification dispatch |
| Log files | Rolling file appender (D:/c-base/logs, D:/c-base/config) | Application and security audit logs |

## Schema / Tables (inferred from code)
- `one_login_user` — login credentials, password hash, status, velocity counters.
- Tables accessed via `IEcountProfile` context objects (affiliate, user, security, device) — exact schema in upstream library modules (xplatform, xSecurity, cbase).
- `users_groups` — user / velocity group mapping (referenced in `MobileUtils.setUserGroupSettings`).

## Sensitive Data

| Category | Where Processed |
|---|---|
| Card number (PAN) | Card activation form (user input); passed to backend auth service |
| PIN | Card activation PIN setup; never stored in this application (delegated to card platform) |
| Username / password (plaintext at point of auth) | `MobileLoginAction.java:98-99` — extracted from JSON request body in memory |
| Legacy MD5 password hash | `MobileLoginAction.java:201` — compared against DB value before upgrade |
| Salted password hash | `MobileLoginAction.java:215` — `Password.getSaltedHashPasswordFromPlainTextPwd()` |
| IP address | Captured and passed to auth service and audit events |
| Device fingerprint / CSID | Biocatch CSID stored in session; device print in RSA MFA |
| Geographical location | Captured from request JSON, stored in session |
| Bank account details | Entered in ACH/IEFT forms; passed to backend services |
| SSN / identity data | KYC portal (external); redirect only — not stored in this app |

## Encryption
- Passwords: new format is salted hash (`Password.genSaltedHashPassword`); legacy is MD5 (`Password.encryptPasswordMD5`). MD5 is cryptographically broken.
- Transport: `SSLLoginFilter` redirects non-HTTPS to HTTPS (enforced for all non-localhost).
- No explicit encryption of data at rest visible in this application layer; relies on underlying database and OS-level encryption.

## Data Flow
```
Browser/Mobile client (HTTPS)
  → SSLLoginFilter (enforce TLS)
  → ParamFilter (input sanitization, file upload temp)
  → AffiliateSkinFilter → AppContextFilter → EcountProfileFilter
  → Struts ActionServlet → Action classes
  → IEcountProfile (session-scoped) → xPlatform / xSecurity services
  → SQL Server databases
  → Audit message → Message Center service
  → Log files (Log4j 1.x)
```

## Data Quality / Retention
- Session-scoped `IEcountProfile` is the primary in-flight data container; destroyed on session invalidation or logout.
- Log retention period: 90 days per Jetty NCSA request log config (`<retainDays>90</retainDays>` in pom.xml dev config).
- No explicit data retention / archival policy visible in this repository.

## Compliance Gaps
1. **MD5 passwords in production**: MD5 is explicitly broken for password storage. PCI DSS Req 8.3 requires strong cryptography. Lazy migration on login leaves accounts on MD5 until they next log in.
2. **Log4j 1.x logging without PAN masking**: `web.xml:49` references `log4j.xml` on the filesystem. Log4j 1.x does not have built-in PAN masking; if card numbers flow through log statements, they could appear in log files — a PCI DSS Req 3.4 violation.
3. **Hardcoded Windows path**: `log4jConfigLocation = file:D:/c-base/config/oneplatform/log4j.xml` in `web.xml:49` — brittle, environment-specific, and non-containerizable.
4. **Biocatch CSID in session**: session-stored behavioral analytics ID may persist beyond reasonable session lifetime; no explicit expiry shown.
5. **fileUploadTempRepository = d:/C-Base/logs** in `web.xml:82` — file uploads are temporarily written to the logs directory; separation of concerns violation, potential data leakage in log files.
