# Data Architect — onbe-log4j1-utils

## Data Stores
None. This is a stateless library. It has no database, file, or cache dependencies.

## Schema / Tables
Not applicable.

## Sensitive Data Handling
The library operates on log message strings. It does not parse, store, or transmit sensitive data. However:
- Log messages from consuming applications may contain cardholder data, PII, or credentials before they reach this filter.
- This library reduces (but does not eliminate) the risk that such data ends up in log files by sanitizing injection characters; it does NOT mask or redact PAN, PII, or secrets.

## Encryption
Not applicable. The library does not perform any encryption or decryption.

## Data Flow
```
Consuming app → Log4j 1.x logger → SanitizingXXXAppender.subAppend()
  → LogUtils.sanitizeLoggingEvent() [in-process, in-memory mutation]
  → parent appender I/O (console / rolling file)
```
All processing is synchronous, in-JVM, and ephemeral.

## Data Quality / Retention
- Message truncation at 1 000 characters represents a data-quality trade-off: log analysis tools may lose context on long exception stack traces.
- No retention policy defined here; retention is the responsibility of the consuming deployment.

## Compliance Gaps
1. **No PAN / PII masking**: This library sanitizes injection characters but does not mask card numbers, SSNs, or other sensitive data that consuming code might log. Services must implement their own data-masking upstream of the logger.
2. **No log integrity assurance**: PCI DSS Req 10 also requires log integrity (tamper evidence). This library only addresses log injection; no HMAC or signing mechanism is present.
3. **Log4j 1.x end-of-life**: The underlying Log4j 1.x library itself has unpatched CVEs. From a data-protection standpoint, any vulnerability in the appender I/O path is unmitigated by this wrapper.
