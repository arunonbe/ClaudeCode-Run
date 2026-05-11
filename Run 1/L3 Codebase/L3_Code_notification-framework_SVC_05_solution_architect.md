# Solution Architect Analysis — notification-framework_SVC

## Security Findings — PCI DSS Critical Review

### Finding 1: PII Logged at INFO Level in Batch Component (HIGH — PCI DSS Req 3, GDPR)

**File:** `notification-requests-generator_LIB/src/main/java/com/ecount/core/batch/dao/notification/request/jdbc/NotificationRequestDetailsRowMapper.java`, lines 41–113

Every row fetched from the notification queue database is logged at INFO level, including:
- `toEmailAddress` — cardholder email address (PII)
- `mergeData` — cardholder PII payload (name, phone numbers, postal address — see `NotificationRequest.java` line 33 comment)
- `fromEmailAddress`
- `friendlyToAddress`
- `bounceBackEmail`

The `log4j.properties` writes these at INFO to rolling file appender (`d:/c-base/logs/batch/notificationRequests.log`, max 100 backup files × 10 MB = 1 GB of logs) and to a Syslog appender at `10.1.1.130`.

**Impact:** Up to 1 GB of PII data may be stored in unencrypted log files on the batch server. The Syslog destination (`10.1.1.130`) receives PII over an unencrypted syslog connection (default UDP/TCP port 514). This violates:
- PCI DSS Requirement 3.3 (sensitive data must not be stored unencrypted)
- GDPR Article 32 (appropriate security measures for personal data)
- CCPA data minimisation principles

**Required remediation:**
1. Remove all `log.info("FieldName :" + fieldValue)` logging of PII fields from `NotificationRequestDetailsRowMapper.java`.
2. Mask email addresses before logging (e.g., `j***@example.com`).
3. Upgrade Syslog transport to TLS (RFC 5424/5425).

### Finding 2: NotificationRequest.toString() Exposes Full PII in Debug Logs (MEDIUM — PCI DSS Req 3)

**File:** `notification-requests-generator_LIB/src/main/java/com/ecount/core/batch/dto/notification/request/NotificationRequest.java`, lines 282–319

The `toString()` override includes `getMergeData()` and `getToEmailAddress()`. If this object is ever logged at DEBUG or ERROR level (e.g., in exception handlers), full PII is written to logs.

**Recommendation:** Override `toString()` to mask PII fields:
```java
notificationRequestObject.append(" ToEmailAddress: [MASKED]");
notificationRequestObject.append(" MergeData: [REDACTED]");
```

### Finding 3: Email Subject May Contain PII in Stage/Test Environment Subjects (MEDIUM — PCI DSS Req 3)

**File:** `Mailer/notification-mailer-impl/src/main/java/.../core/NotificationMailerImpl.java`, lines 362–376

In stage/test environments, the subject line is modified to include the original recipient addresses:
```java
sbSubject.append(" [").append(notificationQueue.getToAddress()).append("]");
```
The resulting subject (e.g., `"Card Loaded [cardholder@email.com]"`) is then logged via `log.debug` (line 383) and stored in the Mailgun tracking table (`emailSubject` field). Cardholder email addresses in subjects are PII that should not appear in tracking records.

**Recommendation:** Do not append recipient email addresses to email subjects. Use internal IDs or masked values.

### Finding 4: NotificationMailerImpl Debug Logging of Rendered Email Body (MEDIUM — PCI DSS Req 3)

**File:** `NotificationMailerImpl.java`, line 115:
```java
log.debug("NotificationMailerImpl::processMessage notificationDelivery: " + notificationDelivery);
```

`notificationDelivery.toString()` would include `notificationBody` — the fully rendered email body. If an email body contains card last-4 digits (e.g., "Your card ending in 0000 has been loaded"), enabling debug logging in production would expose this data in logs.

**PCI DSS assessment:** This is a conditional risk. If debug logging is never enabled in production, the risk is theoretical. However, there is no code-level guard preventing this. The `NotificationDelivery.toString()` method should be audited and overridden to mask sensitive fields.

### Finding 5: Hardcoded Sender Identity in Legacy Delivery Module (LOW)

**File:** `Delivery/src/main/java/com/ecount/service/notificationdelivery/EmailDeliveryImpl.java`, line 25:
```java
message.setFrom("admin@localhost", "Avinish Agarwal");
```

A developer's personal name is hardcoded as the email sender. While this appears to be a legacy `Delivery` module that is not the active code path (the active path uses the `Mailer` module), it represents an unresolved development artifact that could cause SPF failures and brand confusion if this code path were ever activated.

### Finding 6: SMS Delivery Returns True Without Sending (HIGH — Business Logic Defect)

**File:** `Delivery/src/main/java/com/ecount/service/notificationdelivery/ChannelDeliveryImpl.java`, line 46–48:
```java
private boolean deliverSMS(NotificationDelivery notificationDelivery){
    //TO DO : Implement SMS Delivery Functionality
    return true;
}
```

The SMS channel silently returns success without delivering. If any notification rule routes to SMS channel (channelId=1), the cardholder will not receive the message, but the system will record a successful delivery. This is a **silent failure** pattern — dangerous for fraud alerts, OTP delivery, or any time-sensitive notifications.

### Finding 7: Quartz 1.6.3 Java Deserialization Risk (HIGH — PCI DSS Req 6)

`pom.xml` line 223: `opensymphony:quartz:1.6.3`. Quartz 1.x stores job state using Java serialization. Known CVEs exist for old Quartz versions enabling deserialization attacks if the Quartz database tables are accessible by untrusted sources.

**Recommendation:** Upgrade to Quartz 2.3.2+ which uses a safer serialization approach and is actively maintained.

### Finding 8: CI Workflow Pinned to Unstable Feature Branch (MEDIUM)

**File:** `.github/workflows/deployment-mailer.yml`, line 22:
```yaml
uses: Onbe/om-ci-setup/.github/workflows/java-workflow.yml@feature/CRUS-0000-skip
```

Feature branches are mutable references. If the branch is deleted or force-pushed, the pipeline breaks. This affects all four deployment workflows.

**Recommendation:** Pin to a stable tag: `@v1.2.3` or a specific commit SHA.

### Finding 9: Tests Skipped in All Deployment Workflows (HIGH — Quality Control)

All four workflows include `-Dmaven.test.skip` in `MAVEN_ARGS`. No automated tests run before deployment. For a PCI DSS Level 1 service handling cardholder communications, automated testing is required by PCI DSS Requirement 6.2.4.

## Summary Risk Matrix

| Finding | Severity | PCI DSS Req |
|---|---|---|
| PII (email, name, address) logged at INFO to files and Syslog | HIGH | 3.3, 10.3 |
| SMS delivery silently returns true without sending | HIGH | N/A (business) |
| Quartz 1.6.3 deserialization risk | HIGH | 6.3.3 |
| Tests skipped in all CI/CD pipelines | HIGH | 6.2.4 |
| Debug logging of rendered email body (conditional) | MEDIUM | 3.3 |
| Stage/test environment subject line contains email | MEDIUM | 3.3 |
| `toString()` exposes PII | MEDIUM | 3.3 |
| CI workflow pinned to feature branch | MEDIUM | 6.3 |
| Hardcoded developer name in SMTP sender | LOW | — |
