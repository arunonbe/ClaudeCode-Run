# Business Analyst View — spring-refer-a-friend_WAPP

## Business Purpose

spring-refer-a-friend_WAPP (`com.ecount.one.raf:sprint-raf:1.0-SNAPSHOT`) is a Gen-1 web application built for a Sprint-branded prepaid card refer-a-friend (RAF) program. It provides an internal lookup tool — likely used by customer service agents or program administrators — to search referral records by cardholder phone number and year. The application retrieves referral status, referral details, and bonus eligibility information from the Sprint RAF database.

The SCM URL points to an eCount SVN repository (`ecsvn.office.ecount.com/svn/ecount/webapps/sprint-raf/trunk`), confirming this is a direct Gen-1 eCount artifact from the Sprint prepaid card era. The Sprint brand is visible in image assets (`sprinthead.gif`, `sprintprogress.gif`) and the SQL scripts reference a `sprint_batch` and `sprint_referral_details` table.

## Capabilities Provided

- **Referral lookup**: search referrals by cardholder phone number and year; displays referral table with status
- **Printer-friendly view**: dedicated print layout for referral reports
- **In-memory caching**: Ehcache-based caching of referral lookup results keyed by `phone_year`; cache is configurable (on/off) and flushable via URL parameter
- **Maintenance mode**: `site_admin=maintenance` URL parameter puts the application into a maintenance/read mode; `site_admin=up` restores normal operation — this is an unauthenticated admin control
- **Referral batch management**: SQL scripts for adding sprint batches (`add_sprint_batch.sql`), completing batches (`complete_sprint_batch.sql`), and querying referral details (`sprint_referral_details.sql`, `sprint_get_refs.sql`)
- **Plastic card info lookup**: `PlasticInfo` interface for card status lookups related to referral eligibility

## Client/Cardholder Impact

This application served Sprint prepaid cardholders enrolled in a refer-a-friend promotional program. Referral bonuses (likely loaded as card value) depended on correct referral tracking. Incorrect referral status could deny cardholder bonuses (UDAAP concern) or credit bonuses incorrectly (financial loss for Onbe/Sprint).

**Current status**: Sprint no longer offers prepaid cards under the Boost Mobile/Sprint brand in the same format as the eCount era. This application is very likely dormant or decommissioned but the code and any associated database remain relevant for historical audit purposes.

## Business Rules Found in Code

- Referral search requires both phone number and year; missing either parameter returns an empty result without error
- Phone number input is cleaned of dashes, dots, and spaces (`clean()` method) before lookup — normalization rule
- Cache key is `phone + "_" + year` — cached at the search-result level, not individual referral level
- Cache is only populated for successful lookups (`status == "OK"`) — failed lookups are not cached
- Maintenance mode is toggled via URL parameter `site_admin=maintenance`/`up` — **this is an unauthenticated control exposed via GET/POST request**
- The application logs the phone number in plaintext (`log.info("query phone: " + raf.getPhone() + ...")`), creating a log data risk for cardholder phone numbers (PII under CCPA/GDPR)

## Regulatory Obligations

- **GLBA**: Cardholder phone numbers used as search keys constitute financial customer PII; logging them in plain text violates safeguard requirements for data minimization in logs.
- **CCPA**: Cardholder phone numbers are PII under CCPA; logging or retaining them in log files creates a data subject rights obligation.
- **PCI DSS**: While this application does not handle PANs directly, the referral system is adjacent to cardholder data; the maintenance-mode bypass and unauthenticated admin control represent security control failures per PCI DSS Requirement 8.
- **UDAAP**: Referral bonus eligibility decisions must be consistently applied; incorrect referral status could constitute an unfair practice.

## Key Business Risks Found in Code

- **Unauthenticated maintenance mode control**: `site_admin=maintenance` URL parameter can be passed by any user to put the application in maintenance mode. This is a critical security control failure — any cardholder or attacker who discovers this parameter can take the application offline for all users. (`SearchController.java`, line 138)
- **Phone number logged in plaintext**: `log.info("query phone: " + raf.getPhone() + ...)` at `SearchController.java:210` logs cardholder phone numbers. This is a PII data exposure risk in log files.
- **XStream deserialization**: `XStream xstr = new XStream()` is instantiated with default settings. In older XStream versions (present in this codebase), default XStream configuration allows remote code execution via Java deserialization. If serialized objects are ever accepted from untrusted input, this is a critical vulnerability.
- **SNAPSHOT dependency on `spring-dbctx-mock`**: The `spring-dbctx-mock:1.0.1-SNAPSHOT` is a test dependency in production scope — mock implementations should not be on the production classpath.
- **Sprint brand**: If this application is still in production, the Sprint brand (decommissioned prepaid program) may mean the application is serving no users but still consuming infrastructure resources.
