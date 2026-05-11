# Solution Architect — onbe-log4j-utils

## Technical Architecture
- Language: Java 8 and Java 21 (dual-profile build).
- Build: Maven, artifact type `jar`.
- Dependencies: `log4j-core:2.24.3`, `log4j-api:2.24.3`.
- Package: `com.onbe.logging`.
- One production class: `SanitizingFilter`.
- One resource: `onbe-common-log4j2-spring.xml` (reference Log4j 2 Spring configuration).

## API Surface
- Log4j 2 plugin element: `<SanitizingFilter/>` in XML configuration. No constructor arguments required; factory method accepts `onMatch` and `onMismatch` attributes but ignores them (the implementation never uses them).
- No REST, gRPC, JMS, or other external endpoints.

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
| `log4j-core` | 2.24.3 | Current at time of analysis (December 2024). CVE-2021-44228 (Log4Shell) is patched in 2.15.0+; 2.24.3 is well past that. No known critical CVEs at this version. |
| `log4j-api` | 2.24.3 | Same. |

### Code-Level Security Risks
- `SanitizingFilter.java:26`: `MutableLogEvent mutableLogEvent = (MutableLogEvent) event;` — unchecked cast. Log4j 2's async appenders may deliver `Log4jLogEvent` (immutable) instead of `MutableLogEvent`, causing `ClassCastException` at runtime which propagates up and may silently disable the filter or crash the logging thread.
- `SanitizingFilter.java:47-50`: `createFilter` factory ignores `onMatch` / `onMismatch` parameters, so consumers cannot configure filter result behavior from XML.

## Technical Debt
1. **Unchecked MutableLogEvent cast**: high-severity brittleness in async logging scenarios.
2. **`onMatch` / `onMismatch` parameters silently ignored**: inconsistent with Log4j 2 plugin contract.
3. **Shared CI on feature branch**: same instability as onbe-log4j1-utils.
4. **No test for async path**: all tests use synchronous `MutableLogEvent` directly.

## Gen-3 Migration Requirements
- Gen-3 services on Spring Boot 3.4.0 can adopt structured logging and drop this dependency.
- Migration steps: remove `onbe-log4j-utils` dependency, add Spring Boot 3.4.0 structured logging config, validate no sensitive data is logged in structured fields.

## Code-Level Risks (file:line references)
- `SanitizingFilter.java:26` — `(MutableLogEvent) event`: ClassCastException risk with async Log4j 2 appenders.
- `SanitizingFilter.java:47-50` — `createFilter()`: `onMatch` / `onMismatch` parameters not wired to filter behavior.
- `SanitizingFilter.java:38` — regex `[\\p{Cntrl}&&[^\r\n\t]]`: tab pass-through, consistent with onbe-log4j1-utils but inherits the same minor risk.
- `onbe-common-log4j2-spring.xml:33` — `Root level="info"`: this suppresses DEBUG logs globally; if a consumer relies on DEBUG for compliance audit traces, the reference config will silently discard them.
