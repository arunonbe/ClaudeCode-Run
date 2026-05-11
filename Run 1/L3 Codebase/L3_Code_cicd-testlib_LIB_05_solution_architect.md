# cicd-testlib_LIB — Solution Architect View

## Technical Architecture

The library is a **pure Java 8 utility JAR** with zero runtime dependencies beyond `slf4j-api`. It implements a set of concurrency wrappers that propagate SLF4J MDC state across thread boundaries using the **Decorator** and **Template Method** design patterns.

### Class Hierarchy

```
java.util.concurrent.Callable<T>
    └── CorrelationCallable<T>          (abstract)
            ↑ anonymous subclasses created inside CorrelationExecutorServiceDecorator

java.lang.Runnable
    └── CorrelationRunnable             (abstract)
            ↑ anonymous subclasses created inside CorrelationExecutorServiceDecorator
                                         and CorrelationThreadFactoryDecorator

java.util.concurrent.ExecutorService
    └── CorrelationExecutorServiceDecorator   (concrete, wraps any ExecutorService)

java.util.concurrent.ThreadFactory
    └── CorrelationThreadFactoryDecorator     (concrete, wraps any ThreadFactory)

java.io.Serializable
    └── CorrelationID                   (value object, package-private constructor)

CorrelationIDContext                    (static utility, non-instantiable)
LogContextConstants                     (static constants, non-instantiable)
```

### Package Structure
All production classes in `com.ecount.opensource` (`src/main/java/com/ecount/opensource/`):
- `CorrelationID.java` — value object
- `CorrelationIDContext.java` — context manager (MDC facade)
- `CorrelationCallable.java` — abstract Callable with ID capture
- `CorrelationRunnable.java` — abstract Runnable with ID capture
- `CorrelationExecutorServiceDecorator.java` — ExecutorService wrapper
- `CorrelationThreadFactoryDecorator.java` — ThreadFactory wrapper
- `LogContextConstants.java` — key name constants

Test class: `com.ecount.opensource.CorrelationLogTest` (TestNG, `src/test/java/`)

### Core Mechanics

**ID Capture at construction time (not at execution time)**:
- `CorrelationCallable` constructor (line 17): `this.correlationId = CorrelationIDContext.requires()`
- `CorrelationRunnable` constructor (line 13): `this.correlationId = CorrelationIDContext.requires()`
- This is correct: the parent thread's ID is snapshotted when the task is queued, not when it runs.

**ID Restoration in child thread**:
- `CorrelationCallable.call()` (line 30): `CorrelationIDContext.requiresNew(correlationId)` then `doCall()` then `CorrelationIDContext.clear()`
- `CorrelationRunnable.run()` (line 18): same pattern

**MDC operations**:
- `MDC.put(LogContextConstants.CORRELATION_ID, id)` — stores ID in current thread
- `MDC.get(LogContextConstants.CORRELATION_ID)` — retrieves current ID
- `MDC.remove(LogContextConstants.CORRELATION_ID)` — clears ID from current thread

## API Surface

This library exposes no HTTP, gRPC, or messaging API. Its public API is entirely Java class/method surface:

### Public API (intended for consumers)

| Class | Method | Purpose |
|---|---|---|
| `CorrelationIDContext` | `static CorrelationID requires()` | Get-or-create correlation ID for current thread |
| `CorrelationIDContext` | `static CorrelationID requiresNew()` | Always create and store a new UUID correlation ID |
| `CorrelationIDContext` | `static CorrelationID requiresNew(String id)` | Store a caller-supplied string as correlation ID |
| `CorrelationIDContext` | `static CorrelationID requiresNew(CorrelationID id)` | Store an existing `CorrelationID` object |
| `CorrelationIDContext` | `static void clear()` | Remove correlation ID from current thread's MDC |
| `CorrelationCallable<T>` | `protected abstract T doCall() throws Exception` | Extension point for async tasks |
| `CorrelationRunnable` | `protected abstract void doRun()` | Extension point for async tasks |
| `CorrelationExecutorServiceDecorator` | `static ExecutorService newSingleThreadExecutor()` | Factory for a correlation-aware single-thread executor |
| `CorrelationExecutorServiceDecorator` | Constructor `(ExecutorService decorated)` | Wrap any existing ExecutorService |
| `CorrelationThreadFactoryDecorator` | Constructor `(ThreadFactory decorated)` | Wrap any existing ThreadFactory |
| `LogContextConstants` | `CORRELATION_ID = "correlationId"` | MDC key |
| `LogContextConstants` | `CORRELATION_ID_HEADER = "CORRELATION-ID"` | HTTP header key |
| `LogContextConstants` | `JMS_CORRELATION_ID_HEADER = "APP_CorrelationID"` | JMS header key |

### Package-Private
- `CorrelationID` constructor `CorrelationID(String v)` — package-private; only `CorrelationIDContext` can create instances. This is correct encapsulation.

## Security Posture

### Strengths
- Library has no network connections, no file I/O, no database access — minimal attack surface.
- `CorrelationID` has a package-private constructor, preventing external instantiation with arbitrary values.
- CodeQL SAST scanning is configured via `.github/workflows/codeql.yml`.
- Dependabot is configured for weekly Maven dependency updates.

### Vulnerabilities and Findings

**CRITICAL — Plaintext credentials in SCM (`.mvn/wrapper/settings.xml`)**
- `nexus-qa`: username `deployment`, password `dwil15?` (line 38)
- `ecount.release`: username `deployment`, password `d3v0nly` (line 43)
- `ecount.snapshot`: username `deployment`, password `d3v0nly` (line 49)
- `wirecard-mavenproxy-repository`: username `acmng`, password `acmng` (line 33)
- All four must be considered compromised. Passwords must be rotated immediately. The file must be rewritten to use environment variable substitution (`${env.VAR_NAME}`) for all credentials, and the repository history must be scrubbed (git-filter-repo or equivalent).

**HIGH — Log4j2 2.1 (test scope)**
- `org.apache.logging.log4j:log4j-core:2.1`, `log4j-api:2.1`, `log4j-slf4j-impl:2.1` declared as `<scope>test</scope>` in `pom.xml` lines 43–65.
- CVE-2021-44228 (CVSS 10.0), CVE-2021-45046, CVE-2021-45105, CVE-2021-44832 all apply to this version.
- While test-scoped JARs are not shipped in the distribution JAR, CI/CD build environments and developer workstations running `mvn test` are exposed if any log input during tests contains JNDI lookup strings.
- Upgrade to `log4j2` 2.17.2 (Java 8 compatible) or 2.20.0 minimum.

**MEDIUM — SLF4J 1.7.7 (compile scope)**
- Released 2014. Current stable is 2.0.x. While no critical CVEs affect MDC functionality specifically in 1.7.7, running decade-old logging infrastructure in a PCI DSS environment carries unnecessary risk.

**LOW — No `finally` block in lifecycle methods**
```java
// CorrelationCallable.call() lines 29-33:
public final T call() throws Exception {
    CorrelationIDContext.requiresNew(correlationId);
    T result = doCall();          // If doCall() throws, clear() is never called
    CorrelationIDContext.clear();
    return result;
}
```
If `doCall()` or `doRun()` throws an unchecked exception, `clear()` is not invoked, leaving the correlation ID in the thread pool thread's MDC. The next task on that thread will inherit the wrong correlation ID. Fix: wrap in `try { … } finally { CorrelationIDContext.clear(); }`.

**LOW — `invokeAll` / `invokeAny` not wrapped**
`CorrelationExecutorServiceDecorator` lines 92–108 delegate `invokeAll` and `invokeAny` directly to the underlying executor without wrapping the supplied callables. These are the only `ExecutorService` methods that escape the decorator's ID injection. Any consumer using bulk submission will lose correlation.

**LOW — No null guard on `requiresNew(CorrelationID id)`**
`CorrelationIDContext.requiresNew(CorrelationID id)` at line 37 calls `id.toString()` without a null check; passing null produces an NPE.

## Technical Debt

| Item | Location | Severity | Remediation |
|---|---|---|---|
| Log4j2 2.1 (Log4Shell) | `pom.xml` lines 43–64 | High | Upgrade to 2.20.0 |
| SLF4J 1.7.7 | `pom.xml` line 36 | Medium | Upgrade to 2.0.x |
| No `finally` in `call()` / `run()` | `CorrelationCallable.java:29`, `CorrelationRunnable.java:18` | Medium | Add `try/finally` |
| `invokeAll` / `invokeAny` bypass | `CorrelationExecutorServiceDecorator.java:92–108` | Medium | Wrap callables in `CorrelationCallable` |
| Version stuck at SNAPSHOT | `pom.xml` line 15 | Medium | Cut release `1.0.0` |
| Plaintext credentials in SCM | `.mvn/wrapper/settings.xml:33–54` | Critical | Rotate, externalize, scrub history |
| Java 8 target | `pom.xml` lines 74–75 | Low | Migrate to Java 17 |
| `animal-sniffer` checking java17 with Java 8 source | `pom.xml` lines 94–112 | Low | Align sniffer signature with actual JDK target |
| TestNG 6.8.21 | `pom.xml` line 57 | Low | Upgrade to 7.x |
| Duplicate `maven-source-plugin` declaration | `pom.xml` lines 80–82 (mgmt) and 114–126 (direct) | Low | Remove duplicate; keep single declaration |
| No `serialVersionUID` on `CorrelationID` | `CorrelationID.java` | Low | Add explicit `serialVersionUID` |
| Tests skipped in all CI phases | `.gitlab-ci.yml` lines 7–9 | Medium | Remove `-Dmaven.test.skip=true` from at least `MAVEN_TEST_OPTS` |

## Gen-3 Migration Requirements

To migrate the capability provided by this library to a Gen-3 / cloud-native pattern:

1. **Replace with OpenTelemetry Java SDK context propagation**
   - OTEL `io.opentelemetry:opentelemetry-api` provides `Context` and `Span` with built-in thread propagation via `Context.wrap(Runnable)` and `Context.wrap(Callable)` — directly replacing `CorrelationRunnable` and `CorrelationCallable`.
   - OTEL auto-instruments Spring Boot `@Async`, `CompletableFuture`, and JMS listeners via the Java agent, eliminating the need for manual decorator wrappers.

2. **Replace with Spring Boot 3.x Micrometer Tracing**
   - `io.micrometer:micrometer-tracing` with `io.micrometer:micrometer-tracing-bridge-otel` provides Spring-managed trace context that propagates automatically across `@Async` methods, `TaskExecutor`, and Spring JMS.
   - MDC key `traceId` (or configurable) is populated automatically, replacing `correlationId`.

3. **HTTP header migration**
   - Current: `CORRELATION-ID` header (non-standard)
   - Target: W3C `traceparent` / `tracestate` headers (OTEL standard) — requires update of all HTTP clients, servers, and API gateway configurations.
   - Transition: dual-write both headers for one release cycle.

4. **JMS header migration**
   - Current: `APP_CorrelationID` JMS property
   - Target: Inject OTEL context into JMS `TextMessage` properties using the OTEL JMS instrumentation.

5. **Prerequisites**
   - Upgrade all consuming services to Java 17 minimum
   - Upgrade to Spring Boot 3.x
   - Deploy OTEL Collector sidecar or agent in the target environment
   - Update log aggregation (Splunk/ELK) parsers from `correlationId` to OTEL trace ID field names

## Code-Level Risks

| Risk | File | Lines | Detail |
|---|---|---|---|
| MDC leak on exception | `CorrelationCallable.java` | 29–33 | No `finally` — MDC not cleared if `doCall()` throws |
| MDC leak on exception | `CorrelationRunnable.java` | 18–23 | No `finally` — MDC not cleared if `doRun()` throws |
| Bulk submit correlation loss | `CorrelationExecutorServiceDecorator.java` | 92–108 | `invokeAll`/`invokeAny` bypass wrapping |
| NPE on null CorrelationID | `CorrelationIDContext.java` | 37–41 | `id.toString()` without null check |
| Plaintext secrets in SCM | `.mvn/wrapper/settings.xml` | 33–54 | Four credential sets in plaintext; treat as compromised |
| Log4Shell exposure (build/test) | `pom.xml` | 43–64 | Log4j2 2.1 test-scope; CVE-2021-44228 |
| Mutable SNAPSHOT dependency | `pom.xml` | 15 | `1.0.0-SNAPSHOT` artefact is non-deterministic |
| CI tests always skipped | `.gitlab-ci.yml` | 7–9 | All Maven phases have `maven.test.skip=true`; no automated regression |
