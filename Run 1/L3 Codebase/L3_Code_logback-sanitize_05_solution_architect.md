# Solution Architect View — logback-sanitize

## Solution Design

`logback-sanitize` extends Logback's `MessageConverter` class to intercept log message formatting and apply HTML entity encoding. The solution uses Logback's standard `<conversionRule>` mechanism to replace the built-in `%m` conversion word globally for all appenders defined in the configuration.

## Component Design Analysis

### SanitizedMessageConverter (`SanitizedMessageConverter.java`)

```java
public class SanitizedMessageConverter extends MessageConverter {
    @Override
    public String convert(ILoggingEvent event) {
        return StringEscapeUtils.escapeHtml4(super.convert(event));
    }
}
```

This is the minimal, clean implementation. Design assessment:

**Strengths:**
- Extremely simple — 3 lines of logic, easily audited
- `super.convert(event)` delegates to `MessageConverter.convert()` which handles all Logback message formatting including parameter substitution
- No type casting issues (unlike the Log4j2 implementation's `MutableLogEvent` cast)
- Null-safe: `super.convert(event)` handles null messages by returning empty string

**Weaknesses:**
- Only processes the `%m` message token; exception, MDC, and other context data bypass sanitisation
- No PAN/SSN/CRLF handling
- Modifies the final rendered string, not the original event — no ability to filter based on structured message parameters

### Configuration (`logback-spring.xml`)

```xml
<conversionRule conversionWord="m" class="com.onbe.logging.SanitizedMessageConverter"/>
<appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <encoder>
        <pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %m%n</pattern>
    </encoder>
</appender>
```

**Debug mode risk** (`debug="true"` on line 2): Logback will print internal status messages to stdout. This leaks configuration details (appender class names, configuration file paths) and generates noise in production container logs. Remove in any production-bound configuration.

**Pattern token `%m` vs `%msg`**: Both `%m` and `%msg` resolve to the same `MessageConverter` chain. The override via `conversionRule` for word `"m"` covers `%m` but does **not** automatically cover `%msg` — the long-form alias may bypass the override. Verification:
```xml
<conversionRule conversionWord="m" class="com.onbe.logging.SanitizedMessageConverter"/>
<conversionRule conversionWord="msg" class="com.onbe.logging.SanitizedMessageConverter"/>
```
Both aliases should be overridden to ensure complete coverage.

### LogbackConfig Test Harness (`LogbackConfig.java`)

Line 14:
```java
logger.info("LogbackConfig initialized\n<script>alert('XSS')</script>");
```

The message contains `\n` (newline). The expected sanitised output should strip the newline and encode the script tag. Current behaviour: only the HTML encoding occurs; the `\n` passes through, causing the log output to split across two lines:
```
HH:mm:ss.SSS [main] INFO  c.o.l.LogbackConfig - LogbackConfig initialized
<script>alert('XSS')</script>
```
The second line (the HTML-encoded script tag on a new line) **could be mistaken for a real log entry** if a log monitoring tool parses line-by-line. This is a log injection vector that must be addressed.

## Security Architecture Assessment

### Threat Model

| Threat | Vector | Current Status |
|---|---|---|
| Stored XSS in log viewer | Attacker input → HTML in Kibana/Splunk | Mitigated |
| Log forging via CRLF | `\r\n` in input creates fake log line | NOT mitigated |
| PAN in log output | Application logs card number | NOT mitigated |
| SSN in log output | Application logs SSN | NOT mitigated |
| Log4Shell-style JNDI injection | Not applicable to Logback | N/A |
| Exception message PII exposure | `toString()` in exception messages | NOT mitigated |

### Architecture Quality Gates

Before this pattern is mandated in production services, the following quality gates should be passed:

1. **Unit test coverage**: Minimum 10 parameterised test cases covering XSS, CRLF, PAN-shaped strings, null inputs, Unicode edge cases.
2. **CRLF stripping**: Implemented in `SanitizedMessageConverter` before HTML encoding.
3. **PAN masking**: Regex-based 16-digit masking to first-6/last-4 format.
4. **SSN masking**: Regex-based `\d{3}-?\d{2}-?\d{4}` masking.
5. **`%msg` alias coverage**: Additional `conversionRule` for `msg`.
6. **`debug="true"` removed**: Production-safe configuration.
7. **Exception converter**: `SanitizedThrowableConverter` registered for `%ex`/`%xEx` tokens.
8. **MDC sanitisation**: Custom `MDCConverter` or MDC write interceptor.

## Reusability Pattern

The optimal solution architecture for Onbe's logging security is a **shared core + adapter pattern**:

```
com.onbe.logging:logging-security-core
  └── LogSanitizer.java           (static methods: maskPan, maskSsn, stripCrlf, encodeHtml)

com.onbe.logging:logback-sanitize  (depends on core)
  └── SanitizedMessageConverter.java  → calls LogSanitizer
  └── SanitizedThrowableConverter.java

com.onbe.logging:log4j2-sanitize   (depends on core)
  └── SanitizingFilter.java           → calls LogSanitizer
```

This ensures that a fix to PAN masking logic in `LogSanitizer` automatically propagates to both Logback and Log4j2 implementations upon library version bump.

## Solution Readiness Assessment

| Criterion | Status | Action Required |
|---|---|---|
| XSS prevention | Implemented | Test coverage needed |
| CRLF injection prevention | Not implemented | Implement in SanitizedMessageConverter |
| PAN masking | Not implemented | Implement with Luhn-aware regex |
| SSN masking | Not implemented | Implement |
| Exception sanitisation | Not implemented | New ThrowableConverter |
| Unit tests | None | Create comprehensive test suite |
| Published as shared library | Not done | Promote to Nexus |
| Mandated via parent POM | Not done | Enterprise governance action |
| `debug="true"` removed | Not done | Config fix |
| `%msg` alias covered | Not done | Config fix |
