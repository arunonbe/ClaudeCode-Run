# cicd-testlib_LIB — Business Analyst View

## Business Purpose

`cicd-testlib` (artifact ID `com.ecount.opensource:cicd-testlib`, version `1.0.0-SNAPSHOT`) is a shared Java utility library whose sole business purpose is to ensure that **correlation IDs flow correctly through multi-threaded application code** so that distributed log events for a single business transaction can be correlated across threads, services, and messaging systems. It is packaged as a JAR and consumed by other application services in the Onbe/ecount/Northlane platform as a compile-time or runtime dependency.

The SCM metadata (`gitlab.com/northlane/development/application-development/libraries/cicd-testlib.git`) places this library inside the Northlane/ecount application development estate, which is the legacy prepaid-card and disbursements platform that was subsequently absorbed into Onbe.

## Business Capabilities

| Capability | Description | Key Class |
|---|---|---|
| Correlation ID generation | Creates a UUID-based correlation ID when none exists in the current thread | `CorrelationIDContext.requires()` / `requiresNew()` |
| Correlation ID propagation – HTTP | Defines the HTTP header name `CORRELATION-ID` for inbound and outbound HTTP calls | `LogContextConstants.CORRELATION_ID_HEADER` |
| Correlation ID propagation – JMS | Defines the JMS header name `APP_CorrelationID` for message-driven flows | `LogContextConstants.JMS_CORRELATION_ID_HEADER` |
| Correlation ID propagation – threads | Wraps `Callable`, `Runnable`, `ExecutorService`, and `ThreadFactory` so that the parent thread's ID is copied into child threads at spawn time | `CorrelationCallable`, `CorrelationRunnable`, `CorrelationExecutorServiceDecorator`, `CorrelationThreadFactoryDecorator` |
| MDC integration | Binds the correlation ID to SLF4J's Mapped Diagnostic Context under the key `correlationId` so log appenders can include it in every log line | `CorrelationIDContext` (uses `org.slf4j.MDC`) |
| Structured log output | Test log4j2 configuration demonstrates structured console output including `correlationId` in every log message | `src/test/resources/log4j2.xml` |

## Business Entities

- **Correlation ID**: A UUID string (`java.util.UUID.randomUUID().toString()`) uniquely identifying a single logical business transaction or request. Represented as `CorrelationID` (package-private constructor, public `toString()`).
- **Thread Context**: The SLF4J MDC map bound to each thread, holding the correlation ID under the key `"correlationId"`.
- **Log Event**: Any SLF4J/Log4j2 log statement emitted by services that consume this library; enriched with the correlation ID at render time via the MDC pattern `%X{correlationId}`.

## Business Rules & Validations

1. **Single ID per transaction thread**: `CorrelationIDContext.requires()` — if a correlation ID is already stored in the current thread's MDC, it is reused; no new one is generated. This preserves causal continuity across method calls within the same thread (enforced at line 50–56 of `CorrelationIDContext.java`).
2. **Mandatory ID in child threads**: `CorrelationCallable` and `CorrelationRunnable` capture the parent's correlation ID at construction time (not at execution time), ensuring the ID is available even if the parent thread has already completed or cleared its own MDC.
3. **Cleanup after execution**: Both `CorrelationCallable.call()` (line 31–33) and `CorrelationRunnable.run()` (line 20–22) call `CorrelationIDContext.clear()` after task completion. This prevents MDC leakage in thread-pool scenarios where threads are reused.
4. **Standard key names**: HTTP header `CORRELATION-ID` and JMS header `APP_CorrelationID` are declared as constants in `LogContextConstants`, establishing a platform-wide naming convention.
5. **Serialisability**: `CorrelationID implements Serializable`, allowing IDs to be transported across process boundaries (e.g., session replication, message payloads).

## Business Flows

### Synchronous / Single-Thread Flow
```
Inbound request → HTTP filter reads "CORRELATION-ID" header
  → CorrelationIDContext.requiresNew(headerId)
  → Business logic executes; every log statement includes correlationId in MDC
  → Response returned → (optional) CorrelationIDContext.clear()
```

### Asynchronous / Multi-Thread Flow
```
Parent thread holds correlationId in MDC
  → new CorrelationCallable<T>() { doCall() { … } }  ← ID captured at construction
  → CorrelationExecutorServiceDecorator.submit(callable)
      → child thread executes: requiresNew(capturedId) → doCall() → clear()
  → Future<T> returned to parent
```

### Messaging Flow (JMS)
```
Message consumer reads "APP_CorrelationID" JMS header
  → CorrelationIDContext.requiresNew(jmsCorrelationId)
  → Message handling logic executes with ID in MDC
  → CorrelationIDContext.clear()
```

## Compliance & Regulatory Concerns

- **PCI DSS Req 10 (Audit Logging)**: Correlation IDs are foundational infrastructure for linking log events across services. PCI DSS 10.2 requires logging sufficient detail to reconstruct events; correlation IDs directly support this. The library enables but does not enforce the requirement — consuming services must actually call `CorrelationIDContext.requires()` at ingress points.
- **No PII / SAD handling**: The library does not process payment card data, account numbers, or any sensitive authentication data. The correlation ID is a synthetic UUID with no relationship to cardholder data.
- **Log integrity**: Because every log line can carry the correlation ID, logs become more suitable for SIEM correlation and forensic investigation — relevant to SOC 2 CC7.2 (anomaly detection) and PCI DSS Req 10.6 (log review).

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| Version pinned at `1.0.0-SNAPSHOT` | Medium | SNAPSHOT versions are mutable; a consuming service may silently pick up a different binary without a version change |
| MDC leakage if `clear()` not called | Medium | If a `CorrelationCallable` or `CorrelationRunnable` throws an unhandled exception before `clear()`, the ID may persist in the thread pool thread for the next unrelated task (no `finally` block in `call()` or `run()`) |
| `invokeAll` / `invokeAny` not wrapped | Low-Medium | Lines 92–108 of `CorrelationExecutorServiceDecorator` pass collections through to the underlying executor without wrapping callables in `CorrelationCallable`, meaning bulk submissions lose correlation context |
| Hardcoded credentials in `settings.xml` | High | Plaintext passwords for `nexus-qa`, `ecount.release`, and `ecount.snapshot` Maven repositories are present in `.mvn/wrapper/settings.xml` (see Security section) |
| Parent POM from legacy estate | Low | `com.citi.prepaid:module-parent:7` suggests the parent POM originates in a Citi/prepaid estate; governance of that artifact may be unclear post-acquisition |
