# correlation-core_LIB — Solution Architect View

## Technical Architecture

The library is a **pure Java 21 utility JAR** with zero transitive runtime dependencies beyond SLF4J (which every consumer already has). Its architecture is intentionally minimal:

```
com.ecount.opensource
├── CorrelationID.java                  — Value object (Serializable, equals/hashCode)
├── CorrelationIDContext.java           — Static factory + MDC lifecycle manager (@Slf4j)
├── LogContextConstants.java            — Compile-time constants (MDC key, HTTP header, JMS header)
├── CorrelationCallable.java            — Abstract Callable with ID capture/restore/clear
├── CorrelationRunnable.java            — Abstract Runnable with ID capture/restore/clear
├── CorrelationExecutorServiceDecorator.java — ExecutorService decorator (submit/execute wrapped)
└── CorrelationThreadFactoryDecorator.java   — ThreadFactory decorator
```

**Key design decisions:**
- `CorrelationID` constructor is package-private (line 12, `CorrelationID.java`) — instantiation is controlled exclusively by `CorrelationIDContext`, preventing external construction of arbitrary IDs.
- `CorrelationIDContext` is a static utility class with a private constructor (line 14) — no instantiation, no Spring bean required.
- SLF4J MDC is the only storage mechanism — fully compatible with all MDC-aware logging frameworks (Log4j2, Logback).
- Decorator pattern used for `ExecutorService` and `ThreadFactory` — zero changes required to existing thread pool configuration, just wrap the existing instance.
- Template method pattern in `CorrelationCallable`/`CorrelationRunnable` — `call()` and `run()` are `final`, preventing consumers from accidentally bypassing the correlation lifecycle.

## API Surface

### Public API (all in package `com.ecount.opensource`)

**`CorrelationIDContext`** — primary entry point
| Method | Signature | Behaviour |
|---|---|---|
| `requiresNew()` | `static CorrelationID requiresNew()` | Generates UUID v4, stores in MDC, returns `CorrelationID` |
| `requiresNew(String)` | `static CorrelationID requiresNew(String id)` | Stores caller-supplied string in MDC, returns `CorrelationID` |
| `requiresNew(CorrelationID)` | `static CorrelationID requiresNew(CorrelationID id)` | Stores existing ID in MDC (used for thread propagation) |
| `requires()` | `static CorrelationID requires()` | Reuses existing MDC value or generates new one if absent |
| `clear()` | `static void clear()` | Removes `correlationId` from MDC |

**`LogContextConstants`** — constants
| Constant | Value | Usage |
|---|---|---|
| `CORRELATION_ID` | `"correlationId"` | SLF4J MDC key |
| `CORRELATION_ID_HEADER` | `"CORRELATION-ID"` | HTTP request/response header name |
| `JMS_CORRELATION_ID_HEADER` | `"APP_CorrelationID"` | JMS message property name |

**`CorrelationCallable<T>`** — abstract base class
- Consumers subclass and implement `doCall()`.
- Constructor captures `CorrelationIDContext.requires()` at construction time.
- `call()` is `final` — restores ID, invokes `doCall()`, clears MDC, returns result.

**`CorrelationRunnable`** — abstract base class
- Consumers subclass and implement `doRun()`.
- Same lifecycle as `CorrelationCallable`.

**`CorrelationExecutorServiceDecorator`** — drop-in `ExecutorService` wrapper
- `submit(Callable<T>)`, `submit(Runnable, T)`, `submit(Runnable)`, `execute(Runnable)` — all wrapped with correlation propagation.
- Static factory: `CorrelationExecutorServiceDecorator.newSingleThreadExecutor()`
- `invokeAll(...)` and `invokeAny(...)` — NOT wrapped; delegates directly to underlying `ExecutorService`.

**`CorrelationThreadFactoryDecorator`** — `ThreadFactory` wrapper
- `newThread(Runnable)` wraps the `Runnable` in a `CorrelationRunnable` before passing to the decorated factory.

**`CorrelationID`** — value object
- `toString()`, `equals()`, `hashCode()` — standard value semantics.
- Package-private constructor — not directly instantiable by consumers.
- Implements `Serializable`.

## Security Posture

### Strengths
- No sensitive data (PAN, CVV, credentials) handled anywhere in the library.
- Minimal attack surface — pure in-process logic, no I/O, no network calls.
- CodeQL SAST scanning configured (weekly, via `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`).
- Dependabot enabled for Maven (weekly), reducing exposure from known-vulnerable transitive dependencies.
- `GITHUB_TOKEN` handled via environment variable injection, never hardcoded in source.

### Weaknesses / Vulnerabilities

1. **Log injection via unsanitised input** (`CorrelationExecutorServiceDecorator.java` lines 59, 70, 112)
   ```java
   log.debug("Spicing with the correlation id " + CorrelationIDContext.requires());
   ```
   String concatenation with a value ultimately sourced from an inbound HTTP/JMS header. If a caller sets the correlation ID from a header without sanitisation, a crafted newline sequence in the header value could inject false log lines (OWASP Log Injection). These should use parameterised logging: `log.debug("Spicing with correlation id {}", ...)`.

2. **No input validation in `requiresNew(String id)`** (`CorrelationIDContext.java` line 23)
   - No length limit, no character-set restriction, no format check.
   - A very long string (e.g., 10 KB) stored in MDC will appear in every log line for that thread, potentially causing log storage exhaustion or MDC-size-related issues in some frameworks.

3. **Missing `finally` block in `CorrelationCallable.call()`** (`CorrelationCallable.java` lines 29–34)
   ```java
   public final T call() throws Exception {
       CorrelationIDContext.requiresNew(correlationId);
       T result = doCall();          // if this throws...
       CorrelationIDContext.clear(); // ...this line is never reached
       return result;
   }
   ```
   An unchecked exception from `doCall()` bypasses `clear()`. The thread retains the previous correlation ID in its MDC. In thread pool reuse scenarios, the next task on that thread inherits the wrong ID — an audit trail integrity issue. Same pattern in `CorrelationRunnable.run()` (lines 18–22 of `CorrelationRunnable.java`).

4. **`invokeAll` / `invokeAny` not decorated** (`CorrelationExecutorServiceDecorator.java` lines 91–108)
   - Silently breaks correlation for all bulk task submissions without any log warning. Callers have no indication that propagation will not occur.

5. **`CorrelationID` is `Serializable`** — if serialised into an `ObjectMessage` over JMS or persisted in a session store, the UUID string travels with it. This is low risk (UUID is not sensitive) but opens a deserialization surface if `CorrelationID` is ever part of a larger serialised object graph.

## Technical Debt

| Item | Location | Debt Type | Severity |
|---|---|---|---|
| No `finally` block on MDC cleanup | `CorrelationCallable.java:29-34`, `CorrelationRunnable.java:18-22` | Bug / reliability | High |
| `invokeAll`/`invokeAny` not correlated | `CorrelationExecutorServiceDecorator.java:91-108` | Incomplete feature | High |
| String concatenation in log statements | `CorrelationExecutorServiceDecorator.java:59,70,112` | Security / style | Medium |
| No input validation on `requiresNew(String)` | `CorrelationIDContext.java:23` | Security | Medium |
| Tests skipped in CI | `.github/workflows/github-package-publish.yml:39` | Testing | Medium |
| Single test with no assertion | `CorrelationLogTest.java` | Testing | Medium |
| Hardcoded key/header constants | `LogContextConstants.java:7,13,17` | Flexibility | Low |
| No Spring Boot autoconfiguration | — | Usability | Low |
| No reactive/OTel support | — | Forward compatibility | High (for Gen-3) |
| Tomcat 10.x prerequisite in README | `README.md:8` | Documentation | Low (irrelevant for a library) |

## Gen-3 Migration Requirements

To make `correlation-core` fit for purpose in a Gen-3 cloud-native platform:

1. **OpenTelemetry integration** — Bridge the correlation ID with OTel `Span` context. Either:
   - Add a `CorrelationOtelPropagator` that reads/writes both the `CORRELATION-ID` header and the W3C `traceparent` header, or
   - Deprecate `CORRELATION-ID` in favour of `traceparent`/`tracestate` and map the MDC `correlationId` to the OTel trace ID.

2. **Reactive (Project Reactor) support** — Implement a `CorrelationContextOperator` using Reactor's `Context` API so that correlation IDs propagate through reactive pipelines without MDC (which is thread-local and unreliable in non-blocking runtimes).

3. **Fix `finally` blocks** — Critical correctness fix required before any migration:
   ```java
   public final T call() throws Exception {
       CorrelationIDContext.requiresNew(correlationId);
       try {
           return doCall();
       } finally {
           CorrelationIDContext.clear();
       }
   }
   ```

4. **Implement `invokeAll`/`invokeAny` wrapping** — Wrap each `Callable` in the collection with `CorrelationCallable` before delegating.

5. **Spring Boot autoconfiguration** — Provide a `spring-boot-autoconfigure` module that auto-registers a `CorrelationExecutorServiceDecorator` bean and an MVC/WebFlux filter that reads `CORRELATION-ID` from inbound requests.

6. **Input validation** — Add a guard in `requiresNew(String id)`:
   - Maximum length (e.g., 128 characters).
   - Character allow-list (UUID hex chars + hyphens, or configurable).

7. **Re-enable tests in CI** — Remove `-Dmaven.test.skip` from the publish workflow and expand `CorrelationLogTest` to include proper assertions.

8. **Parameterise log statements** — Replace string concatenation with SLF4J parameterised logging throughout `CorrelationExecutorServiceDecorator`.

## Code-Level Risks

| Risk | File | Lines | Description |
|---|---|---|---|
| MDC leak on exception | `CorrelationCallable.java` | 29–34 | No `finally`; MDC not cleared if `doCall()` throws |
| MDC leak on exception | `CorrelationRunnable.java` | 18–22 | No `finally`; MDC not cleared if `doRun()` throws |
| Broken correlation for bulk tasks | `CorrelationExecutorServiceDecorator.java` | 91–108 | `invokeAll`/`invokeAny` bypass decoration entirely |
| Log injection | `CorrelationExecutorServiceDecorator.java` | 59, 70, 112 | String concatenation with MDC-derived value in log statement |
| No ID validation | `CorrelationIDContext.java` | 23 | Arbitrary string accepted from callers without sanitisation |
| False correlation on missing ID | `CorrelationIDContext.java` | 47–55 (`requires()`) | Silent auto-generation masks missing propagation — log lines appear correlated when they may represent different logical requests |
| Serializable value object | `CorrelationID.java` | 9 | Serializable interface opens deserialization surface if used in broader serialisation contexts |
