# Enterprise Architect Report — xml-rpc_LIB

## Platform Generation

**Gen-1 (eCount/Citi) — the load-bearing internal bus.** Despite recent updates to Java 21 compiler target and GitHub Actions CI/CD, this library's architecture, wire format, and design patterns are definitively Gen-1:
- Package namespace: `com.ecount.core.xmlrpc` — eCount original namespace.
- Parent: `com.citi.prepaid:prepaid-parent` — Citi prepaid Gen-1 parent chain.
- Group ID: `com.citi.prepaid.service.core:xmlrpc` — Citi namespace.
- Uses Apache Commons HttpClient 3.x (2007 vintage).
- Uses Spring `WebApplicationContextUtils` and `ThreadLocalStorage` patterns from pre-Spring-Boot era.
- Custom XML wire format (`application/x-mapxml`) that is proprietary, not standard XML-RPC or REST.

The Java 21 compiler target and GitHub Actions CI are **modernization of the build pipeline only** — the library's design and dependencies remain Gen-1. This creates a false impression of modernity.

## Integration Patterns

- **Custom XML-RPC over HTTP**: The proprietary `application/x-mapxml` wire format is not compatible with any standard XML-RPC client or server. All interoperability is confined to Onbe's own codebase.
- **Spring context bean dispatch**: The servlet's dispatch algorithm (`{Interface}.{Method}.Impl` bean lookup) tightly couples the RPC layer to the Spring application context. Services must register their implementations as specifically-named Spring beans.
- **Agent-scoped override**: The `{Interface}.{Method}.Impl.{AgentName}` override pattern enables per-agent business logic without code branching — a powerful but opaque customization mechanism.
- **Reflection-based invocation**: All method calls are made via `Method.invoke()` — no interface contract, no type safety at the RPC boundary.
- **Thread-local request context**: `IRequestContextHolder` bound to thread-local for request context propagation — a pre-reactive, pre-coroutine pattern that breaks with virtual threads (Java 21 Loom).
- **Asynchronous flag**: The `asyncExecution` flag and `txId` support asynchronous RPC — but the async mechanism is implemented by the server-side bean, not the transport.

## External Dependencies

- `springutils-generic:3.1.0` — internal eCount Spring utilities library.
- `ecountcore-common:3.1.5` — internal eCount Core common library (provides `PrintObject`, request context classes).
- `commons-httpclient:3.x` — Apache Commons HttpClient (EOL).
- `commons-io`, `commons-codec` — Apache Commons utilities.
- `jakarta.servlet-api` — provided by hosting container.
- `com.parents:prepaid-parent:6.0.13` — parent BOM.

## Position in the Broader Platform

`xml-rpc_LIB` is the **single most critical infrastructure dependency in the Gen-1/Gen-2 estate**:

1. **Universal transport**: Every service-to-service call in Gen-1 uses this library as either the server (via `XmlRPCServlet`) or the client (via `XMLRPCClient`). The following services are known consumers: ecount-core, cs-api, clientapi, ivr-ws, ivrintegration, jobservice, strongbox-xmlrpc, xsearch-xmlrpc, xsso, xsecurity, csapiws-payout, all VBScript operational scripts (via J2COM bridge).

2. **VBScript bridge root**: The J2COM bridge (`ECountService.Connection`) that VBScript uses is a COM wrapper around the `XMLRPCClient` — making this library the root of the entire VBScript operational script layer as well.

3. **No viable internal replacement**: Replacing this library requires rewriting both the server-side dispatch mechanism and the client-side invocation in every consuming service simultaneously, or implementing a protocol bridge.

## Migration Blockers

1. **Proprietary wire format**: The `application/x-mapxml` format is implemented only by this library. Migration to REST/JSON or gRPC requires replacing both sides of every service communication simultaneously — a big-bang migration.
2. **Spring context coupling**: The `{Interface}.{Method}.Impl` bean naming convention is enforced by the servlet dispatch algorithm. Changing this requires updating Spring configuration in every consuming service.
3. **Agent-specific overrides**: The `{Interface}.{Method}.Impl.{AgentName}` pattern provides agent-specific business logic. Migrating this requires a configuration-driven routing layer in the Gen-3 architecture.
4. **Thread-local context**: Java 21 virtual threads and reactive programming do not work cleanly with thread-local request contexts. A context propagation strategy (e.g., `ThreadLocal.inheritableThreadLocal()` or a context object passed explicitly) is needed.
5. **VBScript J2COM dependency**: Replacing the J2COM bridge requires also replacing all VBScript operational scripts — a separate migration track.
6. **SNAPSHOT version**: Cannot safely freeze consuming services to a specific version while the library is a SNAPSHOT.

## Strategic Status

**Critical estate-wide infrastructure — must be stabilized before any major migration.** Immediate actions:
1. Release `3.1.3` as a GA artifact (remove SNAPSHOT).
2. Upgrade `commons-httpclient` to Apache HttpClient 5.x (breaking API change — requires code updates).
3. Implement TLS 1.2+ enforcement in the outbound client.
4. Document all consuming services and their RPC interface/method registrations.
5. Define a migration path to REST APIs for Gen-3 services, with a protocol bridge layer for backward compatibility.
