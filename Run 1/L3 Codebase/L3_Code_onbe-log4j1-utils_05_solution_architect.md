# Solution Architect — onbe-log4j1-utils

## Technical Architecture
- Language: Java 8.
- Build: Maven, artifact type `jar`.
- Zero runtime dependencies beyond Log4j 1.2.17 (consumer-provided).
- Package: `com.onbe.logging`.
- Four classes: `LogUtils` (package-private), `SanitizingConsoleAppender`, `SanitizingRollingFileAppender`, `SanitizingDailyRollingFileAppender` (all public).

## API Surface
No public API beyond the three appender class names themselves (used in `log4j.xml`). `LogUtils` is package-private. No REST, gRPC, or JMS endpoints.

## Security Posture

### Authentication / Authorization
Not applicable (library).

### Cryptography
None.

### Secrets Management
None.

### CVEs and Vulnerable Dependencies

| Dependency | Version | Notes |
|---|---|---|
| `log4j:log4j` | 1.2.17 | **EOL since 2015**. Multiple unpatched CVEs including CVE-2019-17571 (CVSS 9.8, remote code execution via SocketServer), CVE-2022-23302, CVE-2022-23303, CVE-2022-23305 (SQL injection, deserialization). This library does NOT mitigate any of these CVEs — it only addresses log injection. |

### Code-Level Security Risks
- `LogUtils.java:15-16`: `MESSAGE_FIELD = LoggingEvent.class.getDeclaredField("message"); MESSAGE_FIELD.setAccessible(true);` — reflection-based field access. On Java 17+ with `--add-opens` not configured, this static initializer will throw `InaccessibleObjectException` at classload time, silently breaking all logging.
- `LogUtils.java:28`: `MESSAGE_FIELD.set(event, sanitizedMessage)` — mutation of a private field in a third-party class. If Log4j 1.x changes the field name in a patch, the initializer throws `NoSuchFieldException` at classload.

## Technical Debt
1. **Log4j 1.x is EOL**: entire library exists because of technical debt in consumers.
2. **Reflection hack**: brittle, JVM-version-sensitive approach to mutating log events.
3. **No release tags**: version is hardcoded in POM; no Git tag strategy visible.
4. **Shared CI workflow on feature branch**: `@feature/spring-boot-build-image` is not a stable ref.

## Gen-3 Migration Requirements
Not itself a Gen-3 artifact. For consumers to retire this library:
1. Upgrade consuming service to Log4j 2.x → adopt `onbe-log4j-utils`.
2. Or upgrade consuming service to Spring Boot 3.4.0 → adopt structured logging, retire both log4j-utils libraries.

## Code-Level Risks (file:line references)
- `LogUtils.java:14-18` — static initializer: reflection `getDeclaredField` + `setAccessible(true)`. Will fail on Java 17+ without explicit JVM flags.
- `LogUtils.java:26-28` — `MESSAGE_FIELD.set(event, sanitizedMessage)`: ClassCastException / IllegalAccessException risk.
- `LogUtils.java:41` — regex `[\\p{Cntrl}&&[^\r\n\t]]`: tabs are explicitly excluded from sanitization; any consumer logging tab-separated data may inadvertently preserve structured tab content in injection payloads.
- `pom.xml:16` — `log4j.version=1.2.17`: EOL, multiple unpatched CVEs.
