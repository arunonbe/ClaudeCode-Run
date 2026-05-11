# Business Analyst — onbe-log4j-utils

## Business Purpose
onbe-log4j-utils is a Maven library that adds a log-sanitization filter to Log4j 2.x (Apache logging framework). It is the Log4j 2 counterpart to onbe-log4j1-utils, providing the same log-injection protection for services that have been upgraded or are being built on modern Spring Boot.

## Capabilities
- Provides `SanitizingFilter`, a Log4j 2 plugin filter that intercepts every log event before it reaches any appender.
- Strips control characters (excluding `\t`) and collapses `\r` / `\n` to `_`.
- Truncates messages to 1 000 characters with `[TRUNCATED]` suffix.
- Ships a reference Spring XML configuration (`onbe-common-log4j2-spring.xml`) that includes noise-reduction logger suppression for common frameworks (Tomcat, Jetty, Hibernate Validator, Spring Boot Actuator).
- Published for both Java 8 and Java 21 via Maven profiles; artifact suffix distinguishes version (`1.0.3-java8`, `1.0.3-java21`).

## Entities / Domain Objects
- `SanitizingFilter` — Log4j 2 plugin registered under category `Core`, element type `Filter`.

## Business Rules
1. Filter returns `Result.NEUTRAL` always (never drops a log event; only mutates content).
2. Same sanitization rules as onbe-log4j1-utils: control chars → `_`, `\r\n` → `_`, >1 000 chars → truncated.
3. Consumer must opt in by adding `<SanitizingFilter/>` in appender configuration.

## Key Flows
1. Consumer adds dependency and includes the `onbe-common-log4j2-spring.xml` or configures `<SanitizingFilter/>` in their own log4j2 XML.
2. For each log event, Log4j 2 calls `SanitizingFilter.filter(LogEvent)`.
3. The filter casts the event to `MutableLogEvent` and replaces the message with a `SimpleMessage` wrapping the sanitized string.
4. Log4j 2 continues propagating the (now-sanitized) event to downstream appenders.

## Compliance Relevance
- Same log-injection / PCI DSS Req 10 rationale as onbe-log4j1-utils.
- The README recommends migrating to Spring Boot 3.4.0 structured logging as a longer-term alternative, signaling that this library itself may be deprecated once that migration is complete.

## Risks
1. **`MutableLogEvent` cast assumption**: The filter casts every `LogEvent` to `MutableLogEvent` without type-checking. If Log4j 2 ever delivers a non-mutable event (e.g., in an async ring-buffer path), a `ClassCastException` could crash the logging pipeline.
2. **Tab pass-through**: `\t` is not sanitized, consistent with onbe-log4j1-utils but remains a minor vector.
3. **No test for async/non-mutable events**: Test suite only exercises `MutableLogEvent` directly; real async appender behavior is untested.
4. **README recommends its own obsolescence**: Spring Boot 3.4.0 structured logging makes this library redundant for new services, but no migration schedule exists in the repo.
