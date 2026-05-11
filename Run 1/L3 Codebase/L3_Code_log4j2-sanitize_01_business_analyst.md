# Business Analyst View — log4j2-sanitize

## Executive Summary

`log4j2-sanitize` is a Spring Boot reference implementation demonstrating centralised log sanitisation for applications using the Apache Log4j2 logging framework. Its stated business purpose (from `README.md`) is to prevent **log injection** attacks by sanitising log messages before they are written to any appender. The library is a compliance utility aimed at protecting Onbe's logging infrastructure from log forging, cross-site scripting (XSS) via log viewers, and potential leakage of sensitive data through improperly sanitised log output.

## Business Context and Need

Onbe operates as a PCI DSS Level 1 payments service provider and must comply with PCI DSS v4.0.1 Requirement 10 (protect audit logs). Additionally, OWASP identifies log injection (also called log forging) as a documented application vulnerability. In a payments environment where application logs may contain cardholder data, transaction identifiers, or user inputs, uncontrolled log content creates two categories of risk:

1. **Log Injection / Forging**: An attacker who controls input data (e.g., a cardholder name, a merchant description, a webhook payload) could embed newlines, tab characters, or HTML tags in that data. When the application logs the input, these characters could create fake log entries, mask genuine audit events, or exploit log aggregation tools.

2. **XSS in Log Viewers**: Web-based log viewing tools (Kibana, Splunk Web, custom dashboards) may render log content as HTML. If unsanitised `<script>` tags reach the log store, they could execute in the browser of an operations engineer viewing those logs — a form of stored XSS.

The `LogConfig.java` test harness in this repo (`src/main/java/com/onbe/logging/LogConfig.java`, line 15) deliberately logs `<script>alert('XSS')</script>` as a proof-of-concept to demonstrate the filter intercepts and neutralises the payload.

## Sanitisation Approach — What Is and Is NOT Sanitised

### What IS Sanitised

The `SanitizingFilter` (`SanitizingFilter.java`, line 23) applies `StringEscapeUtils.escapeHtml4()` from Apache Commons Text 1.12.0 to every log message. This converts:

| Input Character | Escaped Output |
|---|---|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `&` | `&amp;` |
| `"` | `&quot;` |
| `'` | `&#x27;` (in some encoders; commons-text uses numeric form) |

This neutralises HTML/JavaScript injection in log viewers.

### What is NOT Sanitised — Critical Compliance Gaps

**The following sensitive data patterns are NOT masked or redacted by this implementation:**

| Data Type | Regulation | Status |
|---|---|---|
| Primary Account Number (PAN / card number) | PCI DSS Req 3.3, Req 10.3 | **NOT masked** |
| Card Verification Value (CVV/CVC) | PCI DSS Req 3.3 | **NOT masked** |
| Social Security Number (SSN) | GLBA, CCPA | **NOT masked** |
| Bank account / routing number | NACHA, GLBA | **NOT masked** |
| Email addresses | GDPR, CCPA | **NOT masked** |
| Phone numbers | GDPR, CCPA | **NOT masked** |
| Full name + address combinations | GDPR, CCPA | **NOT masked** |
| Log newline injection (`\n`, `\r`) | OWASP | **NOT sanitised** |
| CRLF log injection | OWASP | **NOT sanitised** |
| Null bytes | OWASP | **NOT sanitised** |

The library is scoped exclusively to HTML entity encoding. It is **not** a PII masking library and does not meet PCI DSS Requirement 3.3 (mask PAN when displayed) as applied to log output.

## Intended Usage

This repository is a **proof-of-concept / reference implementation**, not a deployable production library. The `README.md` states: "Currently uses `StringEscapeUtils.escapeHtml4` to sanitise the log messages... but can be replaced with any other sanitising implementation." The business intent is to provide a pattern that development teams can adopt and extend with regex-based PAN masking, SSN masking, and CRLF stripping.

## Stakeholders

- **Application Security Team**: Primary consumers of this pattern
- **Development Teams**: Teams building Spring Boot services on Log4j2 who need a sanitisation reference
- **Compliance / Risk**: Need to be aware that this library alone does not satisfy PCI DSS logging requirements for PAN suppression
- **Log Management Platform Team (ELK/Splunk)**: Should implement complementary field-level masking at the aggregation layer

## Compliance Alignment

| Standard | Requirement | This Library | Gap |
|---|---|---|---|
| PCI DSS v4.0.1 Req 10.3.1 | Protect logs from destruction/modification | Partial (prevents log injection) | Does not protect log files at OS level |
| PCI DSS v4.0.1 Req 3.3 | Mask PAN in logs | Not met | No PAN regex masking |
| OWASP ASVS V7.1 | Log injection prevention | Met (HTML encoding) | CRLF not stripped |
| NIST CSF 2.0 DE.CM | Monitor for anomalies | Out of scope | — |
