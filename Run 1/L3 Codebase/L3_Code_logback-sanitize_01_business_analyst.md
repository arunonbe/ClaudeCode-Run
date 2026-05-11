# Business Analyst View — logback-sanitize

## Executive Summary

`logback-sanitize` is a Spring Boot reference implementation demonstrating centralised log sanitisation for applications using the Logback logging framework. Its stated purpose (per `README.md`) is **"Log Injection prevention using logback"**. It is the functional twin of `log4j2-sanitize`, designed for the significant portion of Onbe's Spring Boot service portfolio that uses Logback (the default Spring Boot logging framework) rather than Log4j2.

## Business Purpose

Logback is the default logging framework included in `spring-boot-starter-logging`. The majority of Spring Boot services that have not explicitly switched to Log4j2 use Logback by default. This means `logback-sanitize` addresses a broader population of Onbe services than `log4j2-sanitize`.

The business rationale is identical to `log4j2-sanitize`:
1. **Log Injection Prevention**: Prevent attackers from injecting forged log lines via malicious input data.
2. **XSS Prevention in Log Viewers**: Prevent HTML/JavaScript payloads in log content from executing in web-based log viewers (Kibana, Splunk dashboards).
3. **PCI DSS Compliance Support**: Support adherence to PCI DSS Requirement 10 by ensuring log content integrity.

The `LogbackConfig.java` test harness (`src/main/java/com/onbe/logging/LogbackConfig.java`, line 14) demonstrates the same XSS proof-of-concept:
```java
logger.info("LogbackConfig initialized\n<script>alert('XSS')</script>");
```

## Sanitisation Coverage — What IS and IS NOT Sanitised

### What IS Sanitised

`SanitizedMessageConverter` (`SanitizedMessageConverter.java`, line 15) calls `StringEscapeUtils.escapeHtml4()` on the message text, identical to the `log4j2-sanitize` approach. The following are transformed:

| Character | Output |
|---|---|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `&` | `&amp;` |
| `"` | `&quot;` |

### What is NOT Sanitised — Critical Compliance Gaps

The same gaps documented for `log4j2-sanitize` apply here:

| Data Type | Regulatory Obligation | Status |
|---|---|---|
| PAN (card number) | PCI DSS Req 3.3 | **NOT masked** |
| CVV / CVC | PCI DSS Req 3.3 | **NOT masked** |
| SSN | GLBA, CCPA | **NOT masked** |
| Bank account / routing | NACHA | **NOT masked** |
| Email address | GDPR, CCPA | **NOT masked** |
| Phone number | GDPR, CCPA | **NOT masked** |
| Newline / CRLF injection | OWASP | **NOT stripped** |
| Null bytes | OWASP | **NOT stripped** |

## Technical Approach Comparison with log4j2-sanitize

| Aspect | log4j2-sanitize | logback-sanitize |
|---|---|---|
| Framework | Log4j2 | Logback |
| Extension point | `AbstractFilter` (event-level) | `MessageConverter` (pattern-level) |
| Configuration | `<SanitizingFilter/>` in appender | `conversionRule` replacing `%m` |
| Scope | All messages through the appender | All messages using `%m` pattern token |
| Exception handling | Not sanitised | Not sanitised |
| MDC context | Not sanitised | Not sanitised |

## Intended Usage Population

Logback is used by default in:
- All Spring Boot services that have not explicitly excluded `spring-boot-starter-logging`
- Services using Logback without the Log4j2 replacement

Review of the Onbe repo estate suggests many services fall into this category. The `logback-sanitize` pattern therefore has broader immediate applicability than `log4j2-sanitize`.

## Stakeholders

- **Application Security Team**: Owns the pattern; responsible for promoting adoption
- **Development Teams (Logback users)**: Primary consumers
- **Compliance / Audit**: Should verify adoption across CDE-touching services
- **Log Platform Team**: Should implement complementary log-level masking at the aggregation tier

## Compliance Alignment

| Standard | Clause | Status |
|---|---|---|
| PCI DSS v4.0.1 Req 10.3 | Audit log integrity | Partially addressed (injection prevention) |
| PCI DSS v4.0.1 Req 3.3.1 | PAN masking | Not met |
| OWASP ASVS V7.1.1 | No sensitive data in logs | Not met — PAN, SSN not masked |
| OWASP ASVS V7.1.2 | No PII in logs unless required | Not met |
| GDPR Art 5(1)(f) | Integrity and confidentiality | Partially addressed |

## Business Recommendation

Both `log4j2-sanitize` and `logback-sanitize` should be extended with the same PAN/SSN/CRLF masking logic and published as a unified shared library. The masking rules should be defined once (e.g., in a `com.onbe.logging:logging-sanitize-core` module) and consumed by both the Log4j2 and Logback wrappers.
