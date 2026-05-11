# Data Architect View — spring-refer-a-friend_WAPP

## Data Models

**`RAFRequest`** — primary request/response object for referral lookups:
- `phone` (String) — cardholder phone number (PII)
- `year` (Integer) — referral program year
- `status` (String) — lookup status: "OK", "FAIL", "SYSTEM_ERROR"
- `errorMsg` (String) — error description

**`ReferralInfo`** — interface for referral data retrieval; implementation queries SQL Server via JDBC/stored procedures; returns referral records associated with a phone number and year

**`Referral2DAO`** / **`Referral2Value`** — DAO for referral record retrieval; `Referral2Value` holds individual referral details (referral date, status, bonus amount, etc.)

**`PlasticInfo`** / **`PlasticInfoMock`** — interface for card plastic/status information related to referral eligibility; mock implementation suggests the real implementation integrates with the eCount card service

**`SearchCriteria`** — web form backing object:
- `phone` (String) — cleaned cardholder phone number
- `year` (Integer) — year selection

**`ILastLoadDateDAO`** / **`LastLoadDateDAO`** — DAO for batch last-load-date tracking; used in referral batch processing

**`RequestContextLookup`** — retrieves `RequestContext` for Spring service calls

## Sensitive Data Handled

| Data Category | Presence | Risk |
|---|---|---|
| Cardholder phone number | Primary search key; logged in SearchController | PII under CCPA/GLBA; logged in plaintext — HIGH RISK |
| Referral status/bonus | Core data returned | Financial data; subject to GLBA |
| Referral dates | Returned in `Referral2Value` | PII-adjacent |
| Card plastic status | Via `PlasticInfo` | Card-related data; PCI-adjacent |
| No PAN / CVV | Not present | Correct; referral data does not include payment card numbers |

**Critical finding**: The cardholder phone number is logged at INFO level in `SearchController.java:210` — `log.info("query phone: " + raf.getPhone() + ", year:" + raf.getYear())`. This means all referral lookup phone numbers are written to the application log files, which may be retained and potentially accessible to parties without need-to-know. This is a GLBA safeguard violation and a CCPA data minimization concern.

## Encryption and Protection Status

- No application-level encryption observed
- Referral data is transmitted over HTTP/HTTPS (depends on the load balancer/reverse proxy configuration; the application itself does not enforce HTTPS)
- Ehcache in-memory cache stores `RAFRequest` objects (including phone numbers) in JVM memory — no encryption at rest
- JDBC connection to SQL Server: TLS depends on driver configuration (jTDS 1.2 driver used; TLS 1.2 support is limited in older jTDS versions)
- XStream serialization used for logging/debugging: `xstr.toXML(raf)` at line 267 — XStream with default config is a known deserialization vulnerability vector

## Database Schemas

SQL scripts found in `src/main/sql/`:

| Script | Description |
|---|---|
| `add_sprint_batch.sql` | Inserts a new referral batch record |
| `complete_sprint_batch.sql` | Marks a referral batch as complete |
| `spring_get_refs_orig.sql` | Original referral query |
| `sprint_get_refs.sql` | Current referral retrieval query |
| `sprint_import_info.sql` | Import status query |
| `sprint_referral_details.sql` | Detailed referral data retrieval |
| `test.sql` | Ad-hoc test query (should not be in production) |

Tables (inferred from SQL script names):
- `sprint_batch` — batch processing records with status and date tracking
- `sprint_referral` or `referral` — individual referral records (referrer phone, referred phone, referral date, status, bonus)
- `last_load_date` — batch processing tracking

Database: SQL Server (Microsoft SQL Server JDBC driver in test scope; jTDS in production scope)

## Data Flows

```
CSA / Program Admin (browser)
  → Spring MVC (SearchController) at /search/referral.htm
    → SearchCriteria (phone + year)
      → Ehcache (rafCache — check)
        → ReferralInfo.lookupReferralInfo(RAFRequest)
          → Referral2DAO → SQL Server (sprint_referral tables)
          → LastLoadDateDAO → SQL Server (batch tracking)
        → RAFRequest (result)
          → Ehcache (rafCache — store if OK)
      → JSP view (referral.jsp or referrals-printer.jsp)
        → HTML response
```

Side-effects:
- Phone number logged to application log on every lookup
- XStream serialization of RAFRequest on FAIL status (conditionally logged)

## Retention Concerns

- Referral records in SQL Server: Sprint program records should have a defined retention schedule; if the Sprint program is terminated, these records may still need to be retained for dispute resolution or audit purposes under NACHA/GLBA
- Application log files: Phone numbers in logs must be governed by the log retention policy; if logs are retained for operational purposes, PII masking must be applied retroactively or prospectively
- Ehcache: In-memory only; cleared on application restart. No retention concern beyond the JVM session.

## PCI DSS Data Storage Compliance

- No PAN, CVV, or SAD stored — the referral system is not a CDE component
- Phone numbers as PII require GLBA and CCPA-compliant handling
- `test.sql` committed to production source should be removed; ad-hoc SQL scripts in production codebases represent a data governance risk
- jTDS JDBC driver (version 1.2) has limited TLS support; if SQL Server requires TLS 1.2, this driver version may fail to connect or fall back to an insecure connection
