# Enterprise Architect View — request-context_LIB

## Platform Generation

**Gen-1 (eCount/Citi)** — confirmed by:
- `groupId: com.citi.prepaid.module` — the Citi/eCount groupId namespace
- `parent: com.parents:prepaid-parent:6.0.13` — the Gen-1 eCount parent BOM
- The `IRequestContextHolder` interface's authorship attribution to Simon Galperin (eCount/Citi era author)
- The `sasiContext` field referencing SASI, which is a Gen-1 eCount platform concept
- Usage patterns confirmed in `qa-test-automation` where context configuration XML (`ecount-config.xml`, `strongbox-config.xml`) is the standard Gen-1 wiring mechanism

Despite targeting Java 21 at the compiler level, the library's API and patterns are Gen-1. Java 21 targeting was likely a later upgrade to the build configuration without a corresponding architectural modernization.

## Integration Patterns

The library implements the **Thread-Scoped Context** pattern (a variant of the Ambient Context pattern). This is a classical Enterprise Java pattern for propagating cross-cutting concerns (caller identity, request correlation) through deep call stacks without explicit parameter threading. It was widely used in the EJB and Spring 2.x era before reactive/coroutine programming made ThreadLocal-based patterns problematic.

The `GlobalRequestIDGenerator` interface is designed for use with AOP (Aspect-Oriented Programming) — the method signature `getGlobalRequestID(Method method, Object[] arguments, Object target)` is characteristic of a Spring AOP `MethodInterceptor` or `MethodBeforeAdvice`, indicating the library was designed to be wired into Spring's AOP proxy chain to automatically initialize the request context at service method entry points.

## External Dependencies

- **`com.parents:prepaid-parent:6.0.13`** — the Gen-1 eCount platform parent BOM, which provides dependency management for Lombok, SLF4J, and other shared dependencies.
- **No external runtime dependencies beyond the JDK and Lombok/SLF4J** — this is intentional for a utility library that must be portable across all Gen-1 services.

## Position in the Broader Platform

`request-context_LIB` is a **foundational shared library** in the Gen-1 platform. It is consumed by a large number of Gen-1 services — any service that participates in the eCount XML-RPC service mesh and needs to propagate request context (agent, programId, globalRequestID) would depend on this library. Its architectural position:

```
[Gen-1 Services] (Director, Repository, StrongBox, OrderService, etc.)
    └── depends on → [request-context_LIB]
                            └── provides → ThreadLocal request context
                            └── provides → GlobalRequestID for audit correlation
```

This library has no Gen-3 equivalent visible in the codebase. Gen-3 services use Spring Boot's `MDC` (Mapped Diagnostic Context), OpenTelemetry trace propagation, or custom correlation headers rather than ThreadLocal-based ambient context.

## Migration Blockers

The primary migration blocker is **pervasive implicit dependency**. Because the library uses ThreadLocal (invisible in method signatures), its use is difficult to detect through static analysis — it may be used in any Gen-1 service that imports the library, even services where no explicit call to `ThreadLocalRequestContextHolder` is visible in the top-level code.

Migration considerations for Gen-3:
1. Replace `globalRequestID` propagation with OpenTelemetry trace IDs (spans propagated via W3C TraceContext headers).
2. Replace `agent` and `programId` propagation with OAuth 2.0 JWT claims or Spring Security `Authentication` objects.
3. Replace `sasiContext` with the Gen-3 equivalent authorization mechanism (if SASI has a Gen-3 successor).
4. The ThreadLocal pattern cannot be carried forward into reactive/async Gen-3 services without modification — `Reactor Context` or coroutine scope must be used instead.

## Strategic Status

**Maintenance-only, no new investment.** This library should:
1. Remain on its current `2.1.0` version and receive only security patch updates via Dependabot.
2. Not be extended with new fields or capabilities — Gen-3 services should not adopt this library.
3. Be sunset when the last Gen-1 service consuming it is decommissioned.
4. Have a documented migration guide created for teams moving Gen-1 services to Gen-3, explaining how to replace `ThreadLocalRequestContextHolder` with OpenTelemetry and Spring Security.
