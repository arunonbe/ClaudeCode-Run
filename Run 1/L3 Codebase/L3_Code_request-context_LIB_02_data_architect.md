# Data Architect View — request-context_LIB

## Data Models

The library defines a single primary value object:

**`RequestContext`** (`com.citi.prepaid.context.RequestContext`):
```java
String agent         // caller system identifier (e.g., "B2CSTAGE")
String programId     // Onbe client program identifier (e.g., "04017384")
String globalRequestID  // UUID correlation identifier
String sasiContext   // SASI security/authorization context token
```

This object is immutable in intent but not in implementation — all fields have public setters, making it mutable after construction. This is a design limitation.

**Supporting interfaces**:
- `IRequestContext` — read-only view: `getAgent()`, `getProgramId()`, `getGlobalRequestID()`, `getSASIContext()`
- `IRequestContextHolder` — lifecycle management: `getAgent()`, `getProgramId()`, `getGlobalRequestID()`, `getSASIContext()`, `bind(RequestContext)`, `unbind()`, `clear()`

**`GlobalRequestIDGenerator`** (interface):
- `getGlobalRequestID()` — generates a new UUID string
- `getGlobalRequestID(Method method, Object[] getArguments, Object getThis)` — generates a UUID in the context of an AOP method interception (used by aspect-oriented request context initialization)

## Sensitive Data

The library itself does not process or store cardholder data (PANs, CVVs, SSNs, DDA numbers). However, the fields it carries are important from a security context perspective:

- **`sasiContext`**: This field carries a security context token for the SASI system. Depending on the SASI implementation, this token may encode authorization grants, session identifiers, or signed credentials. If the SASI context is a signed JWT or similar token, it could be considered a sensitive security credential. The library writes the SASI context to DEBUG logs in `ThreadLocalRequestContextHolder` and `HistoryRequestContextHolder`, which could expose security tokens if DEBUG logging is enabled in production.

- **`programId`**: Maps to a specific client program. While not sensitive in isolation, combined with transaction data it provides the multi-tenant boundary context for financial data access. Logging the programId (as done in DEBUG logs) is acceptable but must be accompanied by appropriate log access controls.

- **`globalRequestID`**: UUID-based correlation identifier. Not sensitive in itself but essential for audit trail integrity.

- **`agent`**: Caller identifier (e.g., `B2CSTAGE`). Used for authorization decisions — a corrupted or spoofed agent value could allow a caller to impersonate a privileged agent.

## Encryption Status

No encryption is applied by this library. The context values are held in memory only (ThreadLocal variable) and are not persisted. The library does not write context data to any storage medium — it is purely in-memory, per-request state. Log output (DEBUG level only) includes context field values as plain text.

## Database Schemas

No database access. The library is purely in-memory.

## Data Flows

The intended data flow for a typical Gen-1 service request:

```
[Inbound Request (XML-RPC)] 
    → AOP interceptor calls GlobalRequestIDGenerator.getGlobalRequestID(method, args, target)
    → Creates RequestContext(agent, programId, UUID)
    → ThreadLocalRequestContextHolder.bind(context) — stores in ThreadLocal
    → Service layer calls proceed; any layer calls currentContext().getAgent() etc.
    → [Outbound XML-RPC call to downstream service]
        → Context is forwarded as part of the XML-RPC request header/parameter
    → Return path: ThreadLocalRequestContextHolder.unbind() or .clear()
```

The critical gap in this flow is the thread-pool boundary: if the service dispatches work to a thread pool (e.g., `CompletableFuture`, `@Async`, scheduled executor), the `ThreadLocal` is not automatically inherited by worker threads. The library provides no `TaskDecorator` or `InheritableThreadLocal` mechanism to bridge this gap.

## Retention Concerns

No data retention concerns — the library holds no persistent state. Context data exists only for the duration of a single request thread and is cleared on unbind/clear. However, if DEBUG logging is forwarded to a log aggregation system, the SASI context token written to logs may be retained per the log retention policy.

## PCI DSS Compliance

No direct PCI DSS data (PAN, CVV, SAD) is processed. The library supports PCI DSS Req 10 (audit logs) by providing the `globalRequestID` and `programId` context that makes log entries meaningful and attributable. The SASI context token in DEBUG logs should be reviewed: if it encodes authentication credentials, it must be redacted from log output to comply with PCI DSS Req 10.3 (protect log data) and Req 8 (identify and authenticate access).
