# Solution Architect View — strict-null-checks_DEMO

## Technical Architecture
- Single-module Maven project, `groupId=com.onbe.core`, `artifactId=strict-null-checks_DEMO`, `version=0.0.1-SNAPSHOT`.
- Java 17, Spring Framework 6.1.6 (annotations only), Lombok 1.18.32.
- Four source files in package `com.onbe.strictnullchecks`.

## API Surface
None. No REST endpoints, no RPC interfaces, no public API.

## Security Posture

### Authentication & Authorization
Not applicable.

### Cryptography
Not applicable.

### Secrets Management
Not applicable.

### Known CVEs / Vulnerable Dependencies
- `spring-core:6.1.6` — verify against current Spring Security advisories (Spring 6.x is actively maintained as of 2025).
- `lombok:1.18.32` — no known critical CVEs at time of analysis.
- `notnull-instrumenter-maven-plugin:1.1.1` — last release 2022; no active maintenance signals. Low risk as it only affects build output.

## Technical Debt

| Item | File:Line | Severity | Notes |
|------|-----------|----------|-------|
| `ServiceImpl` returns `null` from `Optional.x()` | `ServiceImpl.java:26` | High | Directly violates the pattern this demo is supposed to teach. |
| `ServiceImpl` sets list to `null` at runtime despite `@Nullable` guard logic | `ServiceImpl.java:15-16` | High | `if (1 == 1) result = null;` — always executes, always returns null list. |
| `ServiceImpl.test()` calls `serviceMethod(null, null)` ignoring `Objects.requireNonNull` | `ServiceImpl.java:21` | Medium | Demonstrates anti-pattern without a corrected counterpart in the same file. |
| No unit tests | — | Medium | The instrumented bytecode is never exercised. The demo is incomplete without a test proving runtime assertion fires. |
| `notnull-instrumenter-maven-plugin` Java 17 ceiling | `pom.xml:56` | Medium | Plugin is unmaintained; will silently degrade on JDK 21+. |
| SNAPSHOT version | `pom.xml:9` | Low | `0.0.1-SNAPSHOT` signals no formal release cadence. |

## Gen-3 Migration Requirements
Not applicable — this is a standards reference, not a production service.

## Code-Level Risks

| Risk | Location | Description |
|------|----------|-------------|
| Anti-pattern in demo code | `ServiceImpl.java:13-17` | `Objects.requireNonNull(text)` is called on a `@Nullable` parameter, which will throw NPE at runtime if null is passed, despite the annotation promising null is acceptable. |
| Null return from Optional | `ServiceImpl.java:25-27` | `return null` from an `Optional<String>` method; calling `.isPresent()` on the result will throw NPE. |
| Plugin maintenance gap | `pom.xml:55-74` | `se.eris:notnull-instrumenter-maven-plugin` has no commits since 2022; should be replaced before JDK 21 adoption. |
