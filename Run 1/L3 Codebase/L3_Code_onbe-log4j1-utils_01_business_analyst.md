# Business Analyst — onbe-log4j1-utils

## Business Purpose
onbe-log4j1-utils is a Java security-patching library published as a reusable Maven artifact. Its sole purpose is to prevent log-injection attacks in legacy Java 8 services that cannot be immediately upgraded from Log4j 1.x. It is explicitly described in the README as "a temporary solution."

## Capabilities
- Sanitizes log messages before they are written by any Log4j 1.x appender.
- Strips or replaces control characters (non-printable characters, carriage return, line feed) with underscores, preventing CRLF/log-injection payloads from splitting log lines.
- Truncates messages exceeding 1 000 characters, appending `[TRUNCATED]`.
- Provides drop-in replacements for three standard Log4j 1.x appender types: ConsoleAppender, RollingFileAppender, DailyRollingFileAppender.

## Entities / Domain Objects
- `LogUtils` — internal sanitization engine (not public API).
- `SanitizingConsoleAppender` — replaces `org.apache.log4j.ConsoleAppender`.
- `SanitizingRollingFileAppender` — replaces `org.apache.log4j.RollingFileAppender`.
- `SanitizingDailyRollingFileAppender` — replaces `org.apache.log4j.DailyRollingFileAppender`.

## Business Rules
1. Any control character except `\t` is replaced with `_`.
2. Both `\r` and `\n` are replaced with `_`.
3. Messages longer than 1 000 characters are truncated.
4. The appenders delegate actual I/O to the upstream Log4j 1.x base classes after sanitizing.

## Key Flows
1. A consuming application configures `SanitizingXXX` appenders in its `log4j.xml`.
2. At logging time, Log4j 1.x calls `subAppend()` on the custom appender.
3. The appender invokes `LogUtils.sanitizeLoggingEvent()` via reflection (`MESSAGE_FIELD.setAccessible(true)`) to mutate the message in-place.
4. The parent appender then writes the sanitized event.

## Compliance Relevance
- Directly addresses log-injection, a OWASP Top-10-class risk present in PCI DSS environments.
- PCI DSS v4.0.1 Req 10 (Audit Logs): log integrity is mandatory; injection attacks that forge or split entries violate this requirement.
- The README explicitly states Log4j 1.x has known security vulnerabilities and recommends upgrading to Log4j 2.x.

## Risks
1. **End-of-life dependency**: Log4j 1.x reached end-of-life in 2015 and carries multiple unpatched CVEs (including deserialization via SocketAppender). This library mitigates log injection only; it does not address the other CVEs.
2. **Reflection-based mutation**: `LogUtils` uses `Field.setAccessible(true)` to overwrite the private `message` field on `LoggingEvent`. This pattern is brittle across JVM versions and could fail silently on Java 17+ with strong encapsulation.
3. **Tab preservation**: `\t` is intentionally not sanitized; this can still be used in some log injection scenarios.
4. **No retention of original message**: If sanitization changes a message, there is no audit trail of the original.
5. **Temporary status not enforced**: There is no deprecation gate or lifecycle management to force consumers to upgrade.
