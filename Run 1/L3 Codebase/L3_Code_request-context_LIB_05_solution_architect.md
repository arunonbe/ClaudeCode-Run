# Solution Architect View — request-context_LIB

## API Surface

The library exposes the following public API (all in package `com.citi.prepaid.context`):

**Interfaces**:
- `IRequestContext` — read access: `getAgent()`, `getProgramId()`, `getGlobalRequestID()`, `getSASIContext()`
- `IRequestContextHolder` — full lifecycle: read access + `bind(RequestContext)`, `unbind()`, `clear()`
- `GlobalRequestIDGenerator` — `getGlobalRequestID()`, `getGlobalRequestID(Method, Object[], Object)`

**Concrete Classes**:
- `RequestContext` — implements `IRequestContext`, `Cloneable`; mutable VO with 4 fields
- `ThreadLocalRequestContextHolder` — implements `IRequestContextHolder`; delegates to `HistoryRequestContextHolder` stored in a `ThreadLocal`
- `HistoryRequestContextHolder` — implements `IRequestContextHolder`; manages a `Stack<RequestContext>`
- `StaticRequestContextHolder` — implements `IRequestContextHolder`; presumably a static/global holder (implementation not fully read)
- `UUIDGlobalRequestIDGenerator` — implements `GlobalRequestIDGenerator`; returns `UUID.randomUUID().toString()`

## Security Posture

The library's security posture concerns are subtle but significant:

### Finding 1: SASI Context Written to DEBUG Logs

**Files**: `ThreadLocalRequestContextHolder.java` (implicit, all get* methods log at DEBUG) and `HistoryRequestContextHolder.java` (bind/unbind log the full context including `sasiContext`)

The `HistoryRequestContextHolder.bind()` method logs all four context fields at DEBUG level:
```java
log.debug("Pushing current request context: agent={}, programId={}, globalRequestID={}, SASIContext={}", ...)
```

If `sasiContext` is a security credential or session token (which it likely is — "SASI" = Security and Audit System Integration), writing it to DEBUG logs violates the principle that credentials must not appear in logs. In a Gen-1 environment where DEBUG logging may be enabled on troublesome services, this token could be captured by log aggregation and exposed to operators without need-to-know access.

**Remediation**: Redact the `sasiContext` value in all log statements, or replace it with a hash/fingerprint that can identify the token without revealing its content.

### Finding 2: Mutable RequestContext — No Defensive Copy on get

**File**: `RequestContext.java` — all fields are public with getters and setters

`RequestContext` implements `Cloneable` and the `HistoryRequestContextHolder` clones the context on push. However, the clone is a shallow copy — for String fields this is safe (Strings are immutable in Java). The mutation risk is that any code holding a reference to a `RequestContext` obtained from `currentContext()` (if exposed) could modify it after bind. The current design mitigates this by returning the internal holder's values through delegation (`currentContext().getAgent()`) rather than exposing the `RequestContext` object directly through `IRequestContextHolder`. This is good design but should be explicitly documented.

### Finding 3: `java.util.Stack` — Synchronized, Legacy Collection

**File**: `HistoryRequestContextHolder.java`, line 19

```java
private final Stack<RequestContext> history = new Stack<RequestContext>();
```

`java.util.Stack` extends `java.util.Vector`, which is fully synchronized on every operation. In a high-throughput Gen-1 service, the synchronized stack operations on the ThreadLocal (itself per-thread, thus not shared) add unnecessary overhead. More critically, `Stack.peek()` and `Stack.pop()` throw `EmptyStackException` rather than returning null — the current code guards against this with `!history.isEmpty()` checks, which is correct but verbose.

**Remediation**: Replace `Stack<RequestContext>` with `ArrayDeque<RequestContext>`, using `peekFirst()`/`pollFirst()` for equivalent behavior without synchronization overhead or the `EmptyStackException` issue.

### Finding 4: Thread-Pool Context Loss — No Mitigation Provided

**File**: `ThreadLocalRequestContextHolder.java`, Javadoc

The class Javadoc explicitly warns:
> "Be careful when using this in a thread-pooling environment."

However, the library provides no solution for this known problem — no `TaskDecorator` adapter for Spring's `ThreadPoolTaskExecutor`, no `InheritableThreadLocal` option, and no documentation of how consuming services should handle context transfer across thread boundaries.

In Gen-1 services that use `@Async` methods, scheduled tasks, or any thread-pool-based execution, this is a latent defect that causes:
- Silent loss of `globalRequestID` in async processing, breaking distributed audit trails
- Silent loss of `agent` and `programId`, potentially causing multi-tenant authorization defects
- Silent loss of `sasiContext`, potentially causing authorization failures in async downstream calls

**Remediation**: Provide a `ContextAwareTaskDecorator` class (implements Spring's `TaskDecorator`) that captures the current context before async dispatch and restores it in the worker thread. Document this as required for all async usage.

## Technical Debt

1. `java.util.Stack` usage — replace with `ArrayDeque`
2. Mutable `RequestContext` — consider making fields `final` and providing a builder
3. SASI context in logs — redact or hash
4. No async/thread-pool context transfer utility provided
5. No null-safety annotations (`@NonNull`, `@Nullable`) on the public API — consuming code must infer nullability from the `isEmpty()` logic
6. Package root `com.citi.prepaid` — still in Citi namespace; should be migrated to `com.onbe.*` or `com.ecount.*` during any library refactoring

## Code-Level Findings Summary

| Finding | File | Line | Severity |
|---|---|---|---|
| SASI context logged at DEBUG | `HistoryRequestContextHolder.java` | 67–75 | High |
| ThreadLocal context loss in thread pools | `ThreadLocalRequestContextHolder.java` | all | High |
| `java.util.Stack` (synchronized, legacy) | `HistoryRequestContextHolder.java` | 19 | Low |
| Mutable `RequestContext` exposed publicly | `RequestContext.java` | all setters | Low |
| `com.citi.prepaid` namespace not migrated | package root | — | Low |
