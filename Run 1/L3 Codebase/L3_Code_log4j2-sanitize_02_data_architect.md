# Data Architect View — log4j2-sanitize

## Overview

From a data architecture perspective, `log4j2-sanitize` is a **log message transformation library** that intercepts log events in the Log4j2 pipeline and applies string transformation before the events reach any appender. Understanding the data flow, transformation logic, and its limitations is essential to assessing whether this library adequately protects sensitive data in Onbe's log streams.

## Log4j2 Data Flow with SanitizingFilter

Log4j2's filter pipeline works as follows:

```
Application code: logger.info("message {}", variable)
        │
        ▼
Log4j2 Logger
        │ creates LogEvent
        ▼
Filter Chain  ◄── SanitizingFilter intercepts here
        │ transforms message
        ▼
Appender (Console, File, Syslog, etc.)
        │ writes transformed message
        ▼
Log Storage (filesystem, ELK, Splunk, CloudWatch)
```

The `SanitizingFilter` (`SanitizingFilter.java`) is registered as a `Plugin` with `category = Node.CATEGORY` and `elementType = Filter.ELEMENT_TYPE`. In `log4j2-spring.xml` (lines 22–24), it is applied at the Console appender level:

```xml
<Console name="Console" target="SYSTEM_OUT" follow="true">
    <filters>
        <SanitizingFilter/>
        <ThresholdFilter level="${sys:CONSOLE_LOG_THRESHOLD:-TRACE}"/>
    </filters>
</Console>
```

This placement means sanitisation occurs **per appender**. If additional appenders (File, Syslog, SMTP) are added to the configuration without the `SanitizingFilter`, they will receive unsanitised messages.

## Transformation Logic Detail

`SanitizingFilter.filter(LogEvent event)` (lines 19–28):

1. Retrieves the `Message` object from the `LogEvent`.
2. Calls `message.getFormattedMessage()` — this resolves any parameter substitutions (e.g., `{}` placeholders) to produce the final string.
3. Applies `StringEscapeUtils.escapeHtml4()` from `commons-text:1.12.0`.
4. Casts the `LogEvent` to `MutableLogEvent` and replaces the message with a new `SimpleMessage` wrapping the sanitised string.
5. Returns `Result.NEUTRAL` — the filter does not accept or deny; it passes control to the next filter in the chain.

### Data Mutation Risk

The cast to `MutableLogEvent` (line 24) modifies the event in-place. If any other filter or appender holds a reference to the same `LogEvent` object, it will see the modified message. This is by design in Log4j2's async appender pipeline, but in synchronous configurations it means the original message is permanently replaced and cannot be recovered for diagnostic purposes.

## What Data Patterns Are Transformed

### Transformed (HTML entity encoding)
- Any HTML tags: `<script>`, `<img>`, `<a href=...>`, `<iframe>`, etc.
- HTML entities in message content
- Quoted strings containing `"` or `'` adjacent to HTML context

### NOT Transformed — Data Protection Gaps

The library performs no regex-based pattern matching or redaction. The following sensitive data patterns would pass through to the log store in plaintext:

**PAN (Primary Account Number)**
- 16-digit sequences: `4111111111110000`
- Hyphenated: `4111-1111-1111-0000`
- No Luhn-check-based masking implemented

**CVV/CVC**
- 3–4 digit values: `123`, `4321`
- No context-aware masking

**SSN**
- `123-45-6789` or `123456789`
- No masking

**Bank Account / Routing**
- 9-digit routing numbers, 4–17 digit account numbers
- No masking

**Email Addresses**
- `user@example.com` — logged in full
- No obfuscation

**Phone Numbers**
- `+1-555-123-4567` — logged in full

**CRLF / Log Injection Sequences**
- `\r\n` — not stripped; multi-line log injection still possible
- Null bytes `\0` — not stripped

## Recommended Data Transformation Extensions

To meet PCI DSS Req 3.3 and Req 10.3 for log data, the `SanitizingFilter` should be extended with the following transformation pipeline:

```java
// Step 1: Strip CRLF
sanitized = sanitized.replaceAll("[\r\n\t]", "_");

// Step 2: Mask PAN (keep first 6 / last 4, mask middle)
sanitized = sanitized.replaceAll(
    "\\b(\\d{6})\\d{6,9}(\\d{4})\\b", "$1******$2"
);

// Step 3: Mask SSN
sanitized = sanitized.replaceAll(
    "\\b(\\d{3})-?(\\d{2})-?(\\d{4})\\b", "***-**-$3"
);

// Step 4: Mask CVV (3-4 digits following "cvv", "cvc", "security code")
sanitized = sanitized.replaceAll(
    "(?i)(cvv|cvc|security.?code)[:\\s=]+\\d{3,4}", "$1: ***"
);

// Step 5: HTML encode (existing step)
sanitized = StringEscapeUtils.escapeHtml4(sanitized);
```

## Data Schema of the Log Event

The `MutableLogEvent` carries:
- `level` — log level (INFO, WARN, ERROR)
- `loggerName` — fully qualified class name
- `message` — the `Message` object (mutated by this filter)
- `timeMillis` — timestamp
- `threadName` — thread name
- `thrown` — exception (not sanitised by this filter — exception stack traces may contain PII)
- `contextData` — MDC/NDC values (not sanitised by this filter)

**Important Gap**: Exception stack traces (`event.getThrown()`) and MDC context data (`event.getContextData()`) are NOT processed by this filter. Stack traces in Java applications frequently contain object `toString()` representations that may include PII field values.
