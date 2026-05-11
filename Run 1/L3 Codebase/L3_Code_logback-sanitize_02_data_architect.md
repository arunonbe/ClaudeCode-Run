# Data Architect View — logback-sanitize

## Overview

`logback-sanitize` implements log message sanitisation using Logback's `MessageConverter` extension point. Unlike the Log4j2 approach which intercepts at the `Filter` level (operating on the full `LogEvent`), Logback's converter operates at the **pattern layout** level — it is invoked during the formatting of the log message for each appender that uses a pattern containing `%m`.

## Logback Data Flow with SanitizedMessageConverter

```
Application code: logger.info("message {}", variable)
        │
        ▼
Logback Logger
        │ creates ILoggingEvent
        ▼
Appender (ConsoleAppender, FileAppender, etc.)
        │ applies PatternLayout
        ▼
PatternLayout resolves conversion tokens:
  %d    → timestamp
  %thread → thread name
  %-5level → log level
  %logger → logger name
  %m    → MESSAGE  ◄── SanitizedMessageConverter intercepts here
  %n    → newline
        │
        ▼
Formatted string → written to output stream
```

### Configuration (`logback-spring.xml`, lines 3):
```xml
<conversionRule conversionWord="m" class="com.onbe.logging.SanitizedMessageConverter"/>
```
This replaces the built-in `%m` token handler with `SanitizedMessageConverter` **globally for all appenders** using this `logback-spring.xml`. Any appender whose pattern uses `%m` will invoke the sanitiser.

This is architecturally superior to the Log4j2 per-appender filter approach for one reason: **you cannot forget to add it to a new appender** — it is applied at the conversion token level, not per-appender.

## Transformation Logic Detail

`SanitizedMessageConverter.convert(ILoggingEvent event)` (`SanitizedMessageConverter.java`, lines 14–16):

```java
public String convert(ILoggingEvent event) {
    return StringEscapeUtils.escapeHtml4(super.convert(event));
}
```

`super.convert(event)` calls `MessageConverter.convert()`, which calls `event.getFormattedMessage()` — this resolves all `{}` placeholders and returns the fully composed message string. The HTML encoding is then applied.

This is a clean, minimal extension. However, it shares the same scope and limitations as the Log4j2 implementation.

## Data Transformation Coverage

### Transformed
- HTML tags and entities (identical to `log4j2-sanitize`)
- All text within the `%m` message token of any pattern layout

### NOT Transformed

**Pattern tokens NOT covered by `%m` substitution:**
- `%ex` / `%throwable` — exception stack traces rendered by `ThrowableProxyConverter` or `ExtendedThrowableProxyConverter`
- `%X` / `%mdc` — MDC (Mapped Diagnostic Context) values
- `%nopex` — no-exception token
- Any custom conversion tokens added by other libraries

**Data patterns NOT sanitised within messages:**
- PAN: 16-digit card numbers (e.g., `4111111111110000`)
- CVV/CVC: 3–4 digit codes
- SSN: `123-45-6789`
- Bank account / routing numbers
- Email addresses
- Phone numbers
- CRLF sequences: `\r\n` — the `%m` output will contain the newline, potentially splitting log entries in file-based appenders

### Exception Stack Trace Gap

Stack traces are rendered by Logback's `ThrowableProxyConverter` using the `%ex` or `%xEx` token. These are **separate** from `%m` and are **not processed** by `SanitizedMessageConverter`. In Java applications, exception messages often contain:
- Object `toString()` representations with PII field values
- SQL exception messages containing query parameters
- Validation error messages containing input values (which may be PAN or SSN in payment workflows)

## MDC Context Data Gap

Logback's MDC (`org.slf4j.MDC`) allows application code to attach key-value pairs to the logging context. These are accessible via `%X{key}` tokens. Common MDC fields in payment services include:
- `correlationId` — transaction identifier
- `programId` — client program
- `userId` — cardholder or API user identifier

MDC values are **not processed** by `SanitizedMessageConverter`. A MDC entry like `partnerUserId=A123456789` or `accountNumber=0401114500019542` would appear in logs unsanitised.

## Scope Comparison: Logback vs Log4j2 Approach

| Aspect | logback-sanitize (MessageConverter) | log4j2-sanitize (Filter) |
|---|---|---|
| Message body `%m` | Sanitised | Sanitised |
| Exception `%ex` | NOT sanitised | NOT sanitised |
| MDC `%X{key}` | NOT sanitised | NOT sanitised |
| New appenders automatically covered | YES (if pattern uses `%m`) | NO (filter must be added to each appender) |
| Event metadata (level, timestamp) | N/A | NOT sanitised (not needed) |
| Performance impact | Per formatted message | Per LogEvent |

## Recommended Extension

To achieve comprehensive log data protection, the following should be added:

```java
public class SanitizedMessageConverter extends MessageConverter {
    private static final Pattern PAN_PATTERN = Pattern.compile("\\b(\\d{6})\\d{6,9}(\\d{4})\\b");
    private static final Pattern SSN_PATTERN = Pattern.compile("\\b(\\d{3})-?(\\d{2})-?(\\d{4})\\b");
    private static final Pattern CRLF_PATTERN = Pattern.compile("[\\r\\n]");

    @Override
    public String convert(ILoggingEvent event) {
        String message = super.convert(event);
        // Strip CRLF first to prevent log splitting
        message = CRLF_PATTERN.matcher(message).replaceAll(" ");
        // Mask PAN
        message = PAN_PATTERN.matcher(message).replaceAll("$1******$2");
        // Mask SSN
        message = SSN_PATTERN.matcher(message).replaceAll("***-**-$3");
        // HTML encode last (to avoid double-encoding)
        return StringEscapeUtils.escapeHtml4(message);
    }
}
```

Additionally, a custom `ThrowableConverter` should be registered to sanitise exception messages:
```xml
<conversionRule conversionWord="ex" class="com.onbe.logging.SanitizedThrowableConverter"/>
```
