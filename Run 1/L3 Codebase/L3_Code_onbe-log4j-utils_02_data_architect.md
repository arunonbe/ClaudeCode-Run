# Data Architect — onbe-log4j-utils

## Data Stores
None. Stateless library; no database, cache, or file dependencies.

## Schema / Tables
Not applicable.

## Sensitive Data Handling
Same considerations as onbe-log4j1-utils:
- The filter processes log message strings in memory. It does not persist or transmit them.
- Consuming services may log PAN fragments, usernames, or error details; this library sanitizes injection vectors only, not sensitive data content.

## Encryption
Not applicable.

## Data Flow
```
Consuming service → Log4j 2 appender pipeline
  → SanitizingFilter.filter(LogEvent) [in-process, in-memory mutation via MutableLogEvent]
  → downstream appenders (Console, File, etc.)
```

## Data Quality / Retention
- Truncation at 1 000 characters may lose diagnostic information from long stack traces or large request bodies that are (inadvisably) logged.
- The shipped reference configuration `onbe-common-log4j2-spring.xml` suppresses several verbose framework loggers (Tomcat, Jetty, Spring Boot Actuator JMX) at `error` or `warn` level, which reduces noise but could hide legitimate errors during an incident.

## Compliance Gaps
1. **No PAN / PII masking**: The same gap as onbe-log4j1-utils. Characters are sanitized for injection only.
2. **Log integrity**: No tamper-evidence mechanism.
3. **Structured logging path not covered**: The README recommends Spring Boot 3.4.0 structured logging; that path does not use this filter. If services adopt structured logging without removing this dependency, dual-path sanitization coverage inconsistencies could arise.
