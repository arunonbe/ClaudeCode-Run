# security-audit-common_LIB — Solution Architect View

## Technical Architecture
Spring Framework library (non-Boot). Three-layer architecture: helper → logger → DAO → SQL Server stored procedure. Spring XML wiring via `securityAudit-context.xml`. Jakarta Servlet API (Tomcat 10 compatible via `jakarta.servlet-api`). Lombok `@Slf4j` for logging. jTDS JDBC for SQL Server.

## API Surface (Library API)

### Primary Public API
```java
SecurityAuditClientHelper.sendMessage(
    HttpServletRequest request,
    Integer appId, Integer userId, String destUserName,
    EventType eventType, EventAccessType eventAccessType,
    EventResult eventResult, EventValidationIndicator eventValInd,
    String failureReason [, String additionalEventInfo [, String exceptionMsg
    [, String accountNumber, String cardNumber,
     Map<String,String> beforeData, Map<String,String> afterData]]])
```
Four overloads with progressively more parameters.

### Direct Lower-Level API
```java
SecurityDataLogger.sendMessage(AuditData auditData)
```

## Security Posture

### Authentication / Authorisation
Library-level — consumers must authenticate themselves. No internal authentication.

### Cryptography
No cryptographic operations in this library.

### Sensitive Data Handling — CRITICAL
- **`UserData.cardNumber`** (line 9, `UserData.java`) accepted and stored as plain String with no masking or validation. If consumers pass full PANs, they are stored unmasked in SQL Server.
- **`UserData.accountNumber`** — same concern for ACH account numbers.
- **AuditConstants.java** references `SOCIAL_SECURITY_CHANGE_FAILURE` and `DOB_CHANGE_FAILURE` event types — implies SSN and date-of-birth are part of business processes audited by this library, though the data elements themselves are in `EventData.beforeData`/`afterData` Maps which are stored as `Map.toString()`.

### IP Address Handling
`SecurityAuditClientHelper.populateRequestData()` (lines 249-257) concatenates `RemoteAddr` and `X-Forwarded-For` — truncated to 100 chars. Storing raw X-Forwarded-For is a security consideration as this header can be spoofed.

### CVE Exposure
- **jTDS 1.x** — EOL driver (last release 2012). Known vulnerabilities exist; not compatible with SQL Server encrypted connections (TLS). Microsoft recommends using `mssql-jdbc` instead.
- **Lombok** — generally safe at compile time.

## Technical Debt

### High Priority
- `ArcSightCEFFormat.java:7` — `convertIntoCEFFormat` returns `null`. Dead code. CEF/SIEM integration completely absent despite class placeholder. This is a **PCI DSS Req 10 gap** (centralised SIEM logging).
- `SecurityDataLoggerImpl.java:36-41` — `catch (Exception ex)` on database write suppresses all errors and returns `flag=false`. Calling applications receive no notification that the audit event was not recorded.
- `UserData.java:9` — `cardNumber` stored as plain unmasked String.

### Medium Priority
- `EventData.eventDateTime` not set in `SecurityAuditClientHelper.populateEventData()` (lines 171-173 are commented out — the `eventDateTime` will be null in all writes, relying on the stored procedure to supply it).
- `SecurityDataDAOImpl.java:54` — `eventDateTime1` parameter is a duplicate of `eventDateTime` — schema artefact.
- `RequestData.httpResponse` stores `request.getMethod() + " "` (a space-padded HTTP method) — this was presumably intended to capture response code but only captures request method.

### Low Priority
- PMD `.pmd` file has numerous duplicate rule entries.
- VBScript (`citiCPSSecurityAuditDataExtract.vbs`) stored in `src/main/java/` — incorrect location for a non-Java resource.

## Gen-3 Migration Requirements
1. Replace `cardNumber`/`accountNumber` with masked representations (first 6 / last 4 for PAN) at library entry point.
2. Complete ArcSight CEF or replace with structured log forwarding to a SIEM (Splunk, ELK, Microsoft Sentinel).
3. Replace jTDS with `com.microsoft.sqlserver:mssql-jdbc`.
4. Replace JNDI DataSource with Spring Boot DataSource auto-configuration.
5. Make `eventDateTime` explicit in Java layer (do not rely on stored procedure defaults).
6. Migrate VBScript export to a scheduled Java job or ETL pipeline.
7. Add PAN masking validation at library boundary.

## Code-Level Risks
| File | Line | Risk | Severity |
|---|---|---|---|
| `UserData.java` | 9,29–34 | `cardNumber` stored as plain unmasked String — PCI DSS Req 3.4 risk | CRITICAL |
| `ArcSightCEFFormat.java` | 7 | Returns null — SIEM integration stub not implemented | HIGH |
| `SecurityDataLoggerImpl.java` | 36–41 | Silently swallows all DB write failures — audit gaps undetectable | HIGH |
| `SecurityAuditClientHelper.java` | 171–173 | `eventDateTime` not set — null timestamp in all audit records | HIGH |
| `citiCPSSecurityAuditDataExtract.vbs` | 121 | SQL credentials passed in BCP command line argument | HIGH |
| `SecurityAuditClientHelper.java` | 252 | Raw X-Forwarded-For stored without validation | MEDIUM |
| `SecurityDataDAOImpl.java` | 54 | Duplicate `eventDateTime1` parameter | LOW |
