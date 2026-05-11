# Business Analyst View — request-context_LIB

## Business Purpose

`request-context_LIB` is a shared Java library that provides a thread-scoped request context propagation mechanism for Onbe's Gen-1 eCount/Citi platform services. It enables all services within a single request processing chain to access common request metadata — specifically the agent identifier, program ID, global request ID, and SASI (Security and Audit System Integration) context — without requiring each service layer to explicitly pass this context as method parameters.

This is foundational infrastructure rather than a business-capability library. Its business value is indirect: it enables consistent audit logging, request correlation, and agent/program-scoped authorization decisions across the eCount service mesh.

## Capabilities

The library provides the following capabilities:

- **Request context model**: A `RequestContext` value object holding `agent`, `programId`, `globalRequestID`, and `sasiContext` fields.
- **Thread-local propagation**: `ThreadLocalRequestContextHolder` binds a `RequestContext` to the current executing thread, enabling transparent access throughout the call stack without parameter threading.
- **History-aware context stacking**: `HistoryRequestContextHolder` maintains a stack of contexts using `java.util.Stack`, allowing nested context binds and unbinds (useful when a service makes downstream calls that require a different context scope, then restores the original context on return).
- **Context access interfaces**: `IRequestContext` and `IRequestContextHolder` define the contract for accessing context values, enabling substitution of different holder implementations.
- **Global request ID generation**: The `GlobalRequestIDGenerator` interface and `UUIDGlobalRequestIDGenerator` implementation generate unique request correlation IDs (UUID-based), used for distributed request tracing across the XML-RPC service mesh.
- **Static holder**: `StaticRequestContextHolder` provides a non-thread-local, process-wide static context holder, likely used for single-threaded or test environments.

## Client and Cardholder Impact

This library has no direct client or cardholder-facing function. However, its reliability indirectly affects:
- **Audit trails**: If the `globalRequestID` propagation is broken (e.g., due to thread-pool handoff without context transfer), audit log entries across services cannot be correlated, impairing fraud investigation and regulatory audit capabilities.
- **Program-scoped authorization**: If `programId` propagation is lost during request processing, a service may operate without program context, potentially applying incorrect authorization rules or business logic for multi-tenant programs.

## Business Rules in Code

- The `agent` field carries the identity of the calling system or user agent (e.g., `B2CSTAGE`, observed in `qa-test-automation`), used for authorization and audit.
- The `programId` maps requests to specific client programs, enabling multi-tenant behavior across shared platform services.
- The `sasiContext` field carries a security context token for the SASI system, which governs cross-service authorization in the eCount platform.
- The `globalRequestID` is a UUID generated at the entry point of each request and propagated across all downstream service calls for end-to-end traceability.

## Regulatory Obligations

- **PCI DSS Req 10.2**: Audit log integrity requires that all events be attributable to a specific requestor. The `agent` and `globalRequestID` fields support this audit trail requirement.
- **PCI DSS Req 10.3**: Log entries must include sufficient detail to reconstruct events. The `programId` contextualizes which cardholder environment an event occurred in.
- **GLBA Safeguards Rule**: Access to financial system services must be controlled and audited. The agent/SASI context mechanism supports access control decisions and audit trail completeness.

## Key Business Risks

1. **Thread-pool context loss**: The `ThreadLocalRequestContextHolder` warning in the class Javadoc — "Be careful when using this in a thread-pooling environment" — is a significant risk. If any Gen-1 service uses thread pools (e.g., async processing, scheduled tasks) without explicitly transferring the `ThreadLocal` context to the worker thread, the downstream processing will have a null or stale context. This breaks audit trails and may cause authorization failures.
2. **Stack overflow risk**: `HistoryRequestContextHolder` uses `java.util.Stack`, which has no depth limit. In a recursive or deeply nested service-call pattern, unbounded stack growth is possible, though unlikely in normal operation.
3. **Shared library versioning**: The library is versioned at `2.1.0`. Downstream services compiled against older versions will use outdated context propagation behavior. There is no visible deprecation or migration guide.
