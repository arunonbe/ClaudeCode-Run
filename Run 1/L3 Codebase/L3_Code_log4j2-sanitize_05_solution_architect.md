# Solution Architect View — log4j2-sanitize

## Solution Design

`log4j2-sanitize` implements a Log4j2 custom filter (`AbstractFilter` subclass) that transforms log message content inline within the logging pipeline. The solution leverages Log4j2's plugin architecture for zero-configuration adoption — the filter is declared in `log4j2-spring.xml` and automatically registered by Log4j2's plugin scanning.

## Component Design Analysis

### SanitizingFilter (`SanitizingFilter.java`)

The filter is a Log4j2 `@Plugin` registered under the name `"SanitizingFilter"`. Key design decisions:

**Plugin registration** (lines 15–16):
```java
@Plugin(name = "SanitizingFilter", category = Node.CATEGORY, elementType = Filter.ELEMENT_TYPE)
public class SanitizingFilter extends AbstractFilter {
```
This is the correct Log4j2 plugin pattern. The filter is usable in any Log4j2 configuration file by the XML element name `<SanitizingFilter/>`.

**Factory method** (lines 30–34):
```java
@PluginFactory
public static SanitizingFilter createFilter(
        @PluginAttribute("onMatch") Result onMatch,
        @PluginAttribute("onMismatch") Result onMismatch) {
    return new SanitizingFilter();
}
```
The `onMatch` and `onMismatch` attributes are accepted but **ignored** in the constructor — the filter always returns `Result.NEUTRAL` regardless. This means the `onMatch`/`onMismatch` parameters have no effect, which may confuse administrators configuring the filter with these attributes.

**Message mutation** (lines 19–28):
```java
public Result filter(LogEvent event) {
    Message message = event.getMessage();
    String sanitizedMessage = StringEscapeUtils.escapeHtml4(message.getFormattedMessage());
    MutableLogEvent mutableLogEvent = (MutableLogEvent) event;
    mutableLogEvent.setMessage(new SimpleMessage(sanitizedMessage));
    return Result.NEUTRAL;
}
```

Design risks:
1. **Unchecked cast**: `(MutableLogEvent) event` will throw `ClassCastException` for non-mutable event implementations (e.g., `Log4jLogEvent` in some configurations). No `instanceof` guard is present.
2. **Parameter information lost**: `message.getFormattedMessage()` resolves all `{}` parameters before sanitisation. The original parameter array is discarded. This means MDC/NDC context is preserved at the event level, but parameterised message components are merged into a single string.
3. **Exception not sanitised**: The `event.getThrown()` throwable is not processed. Stack frames in exception messages may contain PII from object `toString()` calls.

### LogConfig Test Harness (`LogConfig.java`)

The `LogConfig` class serves as a live test of the filter:
```java
logger.info("LogConfig initialized\n<script>alert('XSS')</script>");
```
On startup, this logs a string containing a newline (`\n`) and an XSS payload. The expected sanitised output is:
```
LogConfig initialized\n&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;
```
Note: the `\n` is NOT removed by the current implementation — it is only HTML-encoded. The newline will still cause log-splitting in text-format log files, potentially creating a forged log line.

### Log4j2 Configuration (`log4j2-spring.xml`)

The configuration defines a single Console appender with the `SanitizingFilter` attached before the `ThresholdFilter`. Production adoption requires:
- Adding the same filter pattern to `RollingFile` and `Socket` appenders
- Ensuring the `monitorInterval` attribute is set for hot-reload support
- Considering `AsyncAppender` wrapping for performance

## Solution Patterns

| Pattern | Implementation | Assessment |
|---|---|---|
| Log4j2 custom filter plugin | `@Plugin`, `@PluginFactory` | Correct and idiomatic |
| Centralized sanitisation | Per-appender filter | Appropriate; but must be replicated for each appender |
| HTML encoding | `StringEscapeUtils.escapeHtml4` | Suitable for XSS prevention; insufficient for PAN masking |
| Spring Boot auto-configuration | `log4j2-spring.xml` naming | Correct — Spring Boot auto-detects `-spring` suffix |

## Security Architecture Assessment

### Threat Model

| Threat | Vector | Mitigation Status |
|---|---|---|
| Stored XSS via log viewer | Attacker controls log input → XSS in Kibana/Splunk | Mitigated (HTML encoding) |
| Log forging via newline injection | Attacker injects `\r\n` to create fake log lines | NOT mitigated |
| PAN exposure in logs | Application logs card numbers | NOT mitigated |
| SSN exposure in logs | Application logs SSN | NOT mitigated |
| Deserialization via Log4j JNDI | Historical Log4Shell vector | Mitigated (Log4j2 ≥2.17.1 via Spring Boot BOM) |

### Recommendations

1. **Fix ClassCastException risk** — add `instanceof MutableLogEvent` guard before casting.
2. **Strip CRLF** — prepend `input.replaceAll("[\r\n]", " ")` before HTML encoding.
3. **Add PAN masking regex** — 13–19 digit sequences passing Luhn check should be masked to first 6 / last 4.
4. **Add SSN masking** — `\d{3}-?\d{2}-?\d{4}` pattern.
5. **Process exception messages** — implement a separate `ThrowableProxyConverter` or override `event.getThrown()` handling to mask sensitive exception message text.
6. **Honour `onMatch` / `onMismatch`** — fix the factory method to pass these parameters to `AbstractFilter` super constructor for correct filter chain semantics.
7. **Add unit tests** — implement Spock or JUnit 5 parameterised tests covering: HTML injection, CRLF injection, PAN-shaped strings, null input, and very long strings (DoS via regex backtracking).
8. **Publish to shared Maven repository** — coordinate with `logback-sanitize` to ensure the masking logic is implemented consistently across both libraries.
