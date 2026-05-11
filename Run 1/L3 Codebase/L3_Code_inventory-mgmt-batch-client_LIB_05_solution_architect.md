# Solution Architect View — inventory-mgmt-batch-client_LIB

## Technical Architecture

**Stack**: Java 6 (compiler target), Spring 2.5.4, Commons DBCP 1.4, Commons Pool 1.4, log4j 1.2.14, TIBCO JMS 5.0 (tibcrypt, tibjms), jtds 1.2.4 (SQL Server JDBC), ehcache 1.2.3, spring-dbctx (Onbe internal), ecount-system 2.0.0, director-client 1.0.11, xSecurity-common/impl 1.1.19, inventory-mgmt 1.0.14.

**Design pattern**: 
- Standalone batch applications with Spring XML application context loaded via `ClassPathXmlApplicationContext`.
- Spring XML bean wiring from both classpath XML files and a custom `applicationContext-inventory-mgmt-batch.xml`.
- Entry point via `public static void main()` in client classes (`CardExpiryAlertNotificatonClient`, `AutoReorderCardExpirationNotification`).
- DAO pattern using JdbcDaoSupport with `JdbcTemplate`.

**Key classes**:
| Class | Role |
|-------|------|
| `CardExpiryAlertNotificatonClient` | Main class for card expiry alert batch |
| `AutoReorderCardExpirationNotification` | Main class for auto-reorder / core sync batch |
| `CoreSyncCardDaoJdbcImpl` | JDBC DAO for reading DDA card states from ecountCore |
| `CardExpiryClientJDBCDao` | JDBC DAO for card expiry queries from JobSvc |
| `CardExternalClientJDBCDao` | JDBC DAO for external card data from ecountCore |
| `EmailNotificationDaoImpl` | JDBC DAO for email notification queue |
| `PopulateShippingInfoBatchImpl` | Shipping info population batch |
| `InventoryEmailNotification` | Email notification orchestrator |

## API Surface
Library / batch application — no HTTP endpoints.

**Batch entry points**:
- `CardExpiryAlertNotificatonClient.main(String[] args)` — card expiry alert batch
- `AutoReorderCardExpirationNotification.main(...)` (not read but referenced in Spring XML as `autoreorder` bean)
- `PopulateShippingInfoBatch` — shipping info population

## Security Posture

### Authentication / Authorisation
- No HTTP authentication.
- Database access via Director-resolved DBCP connections (credentials in `director-client.properties` and `inventoryMgmtBatchClient.properties`).
- Spring context loaded from classpath; no runtime authentication of the Spring context.

### Cryptography
- No cryptography in this library.
- DDA numbers and card data handled as plaintext strings.

### Secrets
- Database credentials in `D:/c-base/config/director-client.properties` and `D:/c-base/config/inventoryMgmt/inventoryMgmtBatchClient.properties` — plaintext files on server filesystem.
- Log4j configuration file path `D:/c-base/config/inventoryMgmt/CardExpiryClientLog4j.properties` — plaintext.
- TIBCO JMS credentials in `pconfig.xml` (referenced by consuming j2com log4j.xml).

### CVEs / Dependency Risks
- **log4j 1.2.14**: CVE-2019-17571 (SocketServer RCE, CVSS 9.8) — critical if SocketServer class is loaded. Also CVE-2022-23302 (JMSSink JNDI injection), CVE-2022-23305 (SQL injection via JDBCAppender). These are 1.x-specific CVEs distinct from log4shell.
- **commons-collections 3.x** (via spring 2.5.4 transitive): CVE-2015-6420 (deserialization gadget chain, CVSS 9.8) — critical.
- **Spring 2.5.4**: CVE-2013-4152, CVE-2014-0054 and many others; EOL since 2013.
- **jtds 1.2.4**: CVE-2018-11680 (SSRF via NTLM auth). Superseded by Microsoft JDBC driver.
- **ehcache 1.2.3**: Very old; check for known issues.
- **inventory-mgmt 1.0.14**: Running an older version (current is 2.0.x) — may lack bug fixes and security patches present in later versions.

## Technical Debt
1. Java 6 compiler target — zero security patch support; must upgrade to Java 17+.
2. `System.exit(0)` / `System.exit(-1)` calls in main methods — non-embeddable, untestable.
3. Spring 2.5.4 XML context — must migrate to Spring Boot 3.
4. Raw types throughout (no generics usage).
5. `e.printStackTrace()` in catch blocks instead of structured logging.
6. No retry logic for batch operations — a single failure aborts the entire batch.
7. `inventory-mgmt` version 1.0.14 is stale relative to current 2.0.x.
8. Fixed Windows-style paths (`D:/c-base/config/`) make the code non-portable.
9. `IOUtils.closeQuietly()` used (commons-io 1.3.2) — swallows exceptions on resource closure.
10. Spring mock dependency (2.0.4) in test scope — ancient test framework.

## Gen-3 Migration Requirements
1. Rewrite as Spring Batch job in a Spring Boot 3 / Java 21 application.
2. Replace OS scheduler with Kubernetes CronJob or Azure Scheduler.
3. Replace Director DBCP with Spring Boot DataSource + Azure Key Vault.
4. Upgrade `inventory-mgmt` dependency to 2.0.x then to the Gen-3 inventory service REST API.
5. Replace TIBCO JMS with Azure Service Bus.
6. Replace log4j 1.x with Logback + SLF4J (already in inventory-mgmt_LIB).
7. Replace plaintext properties files with Azure App Configuration + Key Vault.
8. Replace jtds with `com.microsoft.sqlserver:mssql-jdbc`.
9. Remove all `System.exit()` calls; use proper Spring Batch exit codes.
10. Add idempotency and retry to each batch step.

## Code-Level Risks

| File | Line | Risk |
|------|------|------|
| `CardExpiryAlertNotificatonClient.java` | 44 | `LOG_PROPERTIES = "D:/c-base/config/..."` — hardcoded Windows path |
| `CardExpiryAlertNotificatonClient.java` | 46 | `ECONT_CONFIG_PROPERTIES = "D:/c-base/config/..."` — hardcoded Windows path |
| `CardExpiryAlertNotificatonClient.java` | 176 | `System.exit(0)` inside `process()` — kills JVM from non-main method |
| `applicationContext-inventory-mgmt-batch.xml` | 15-16 | Properties files at hardcoded `d:/c-base/config/` paths |
| `CoreSyncCard.java` | 9 | `query_time_out = 5*60*60*1000` — 18-hour query timeout; effectively no timeout |
| `PopulateShippingInfoBatchImpl.java` | (not read) | Writes card_number to DB — PAN at rest risk |
| `DDA_Number.java` (in autoreorder) | (not read) | DDA number domain object — bank account data; ensure not logged |
