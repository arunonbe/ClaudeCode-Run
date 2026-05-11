# Solution Architect Analysis — notification-requests-generator_LIB

## Security Findings — PCI DSS Critical Review

### Finding 1: PII Logged at INFO Level — Email, Name, Address, Phone (CRITICAL — PCI DSS Req 3.3, GDPR Art.32)

**File:** `src/main/java/com/ecount/core/batch/dao/notification/request/jdbc/NotificationRequestDetailsRowMapper.java`, lines 41–113

The `mapRow()` method individually logs every mapped field at `INFO` level using `log.info(...)`:
- Line 42: `log.info("in resultSet.getString(1)="+resultSet.getString(1))` — logs the raw first column value
- Line 47: `log.info("Email Queue Uid :" + uid)`
- Line 53: `log.info("TemplateName :" + templateName)`
- Line 59: `log.info("MergeData :" + mergeData)` — **logs full PII payload** (name, address, phone numbers)
- Line 67: `log.info("Application :" + application)`
- Line 71: `log.info("Partner :" + partner)`
- Line 78: `log.info("ToEmailAddress :" + toEmailAddress)` — **cardholder email**
- Line 84: `log.info("FromEmailAddress :" + fromEmailAddress)`
- Line 91: `log.info("FriendlyFromAddress :" + friendlyFromAddress)`
- Line 99: `log.info("FriendlyToAddress :" + friendlyToAddress)` — **cardholder display name**
- Line 108: `log.info("NotificationBatchId :" + notificationBatchId)`
- Line 113: `log.info("BounceBackEmail :" + bounceBackEmail)`

The `mergeData` field (line 59) contains the complete cardholder profile as a URL-encoded string (first name, last name, middle name, address line 1, address line 2, city, state, ZIP, mobile phone, home phone, business phone). This is logged **every time a notification request row is read** — once per notification per batch run.

**Three log destinations receive this PII:**
1. Console stdout (INFO threshold)
2. Rolling file `d:/c-base/logs/batch/notificationRequests.log` (INFO threshold, up to 1 GB)
3. Remote Syslog at `10.1.1.130` (INFO threshold, **unencrypted transport**)

**Required remediation (immediate):**
```java
// Replace all log.info lines with PII content with either no logging or masked logging:
log.debug("Mapped row uid: " + uid);  // non-PII OK at debug
// Do NOT log mergeData, toEmailAddress, friendlyToAddress, bounceBackEmail, mobilePhone
```

### Finding 2: `NotificationRequest.toString()` Serialises Full PII (HIGH — PCI DSS Req 3.3)

**File:** `src/main/java/com/ecount/core/batch/dto/notification/request/NotificationRequest.java`, lines 282–319

The `toString()` method includes all PII fields including `getMergeData()`, `getToEmailAddress()`, `getFriendlyToAddress()`. Any component that logs `notificationRequest.toString()` (e.g., exception handlers, debug logging) will produce a full PII dump in the log.

**Code comment at line 33 contains what appears to be real PII data from development:**
```java
//MOBILEPHONE=&HOMEPHONE=6109414600&BUSINESSPHONE=&PHONE=6109414600&CITY=Wynnewood
//&LASTNAME=Eastern&STATE=PA&POSTAL=19096&FIRSTNAME=North...
```
Even if this is synthetic test data, it normalises the pattern of including PII in source code comments, which risks real data appearing in the same way. This comment should be removed.

**Required remediation:**
Override `toString()` to exclude or mask all PII fields:
```java
@Override
public String toString() {
    return "NotificationRequest{uid=" + uid + ", msgTemplateName=" + msgTemplateName +
           ", application=" + application + ", partner=" + partner +
           ", notificationBatchId=" + notificationBatchId + "}";
    // Never include mergeData, toEmailAddress, friendlyToAddress
}
```

### Finding 3: Unencrypted Syslog Transmission of PII (HIGH — PCI DSS Req 4.2.1)

**File:** `src/main/resources/log4j.properties`, lines 34–41

```properties
log4j.appender.SYSLOG=org.apache.log4j.net.SyslogAppender
log4j.appender.SYSLOG.SyslogHost=10.1.1.130
log4j.appender.SYSLOG.Threshold=info
```

Log4j's `SyslogAppender` transmits over UDP (default) or TCP without TLS. PII-containing log messages are sent in plaintext over the network to `10.1.1.130`.

**PCI DSS Req 4.2.1** prohibits transmission of PAN or cardholder data over open, public networks without strong cryptography. While the syslog destination (`10.1.1.130`) is an internal IP, PCI DSS also requires network monitoring — unencrypted internal transmission of PII is a risk.

**Required remediation:**
1. Remove PII from log statements (Finding 1 above — this is the primary fix).
2. Configure TLS syslog if the destination supports RFC 5425 (TLS Syslog).

### Finding 4: Pre-built JARs Committed to Repository (MEDIUM — PCI DSS Req 6.3)

**Files:** `releases/notification-requests-1.0-SNAPSHOT.jar`, `releases/notification-requests-1.0.jar`

Binary JARs committed to the repository cannot be verified as built from the current source code. A compromised build or malicious modification could inject code into the committed JAR without any code review. PCI DSS Requirement 6.3 requires that all software components be obtained from trusted sources and verified for integrity.

**Required remediation:** Remove JARs from repository. Use a CI/CD pipeline to build from source and an artifact repository (Nexus, GitHub Packages) for distribution.

### Finding 5: Log4j 1.x End-of-Life Security Risk (HIGH — PCI DSS Req 6.3.3)

**File:** `src/main/resources/log4j.properties` (Log4j 1.x syntax)

Log4j 1.x reached end-of-life in August 2015 and has multiple unpatched CVEs including:
- CVE-2019-17571 (Log4j SocketServer deserialization, CVSS 9.8)
- CVE-2022-23302, CVE-2022-23303, CVE-2022-23305 (JMSSink/JDBCAppender SQL injection)

**Required remediation:** Migrate to Log4j 2.x or SLF4J/Logback.

### Finding 6: CodeQL Scan Present but No SAST on Deployment (MEDIUM)

Only a CodeQL scan workflow exists (`.github/workflows/codeql.yml`). There is no deployment pipeline, so even security findings from CodeQL do not gate deployment. CodeQL results are advisory only.

## Risk Summary

| Finding | Severity | PCI DSS Req | GDPR |
|---|---|---|---|
| PII (email, name, address, phone) logged at INFO | CRITICAL | 3.3 | Art.32 |
| `toString()` serialises full PII | HIGH | 3.3 | Art.32 |
| PII transmitted via unencrypted Syslog | HIGH | 4.2.1 | Art.32 |
| Binary JARs in repository | MEDIUM | 6.3 | — |
| Log4j 1.x EOL security vulnerabilities | HIGH | 6.3.3 | — |
| No deployment pipeline or quality gate | HIGH | 6.2.4 | — |
| PII comment in source code | LOW | 3.3 | Art.25 |
