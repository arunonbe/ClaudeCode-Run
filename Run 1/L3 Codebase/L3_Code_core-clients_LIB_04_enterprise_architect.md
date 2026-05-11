# core-clients_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 / Gen-2 bridge library**

Evidence:
- The communication protocol is **XML-RPC over HTTP**, a protocol dating from the late 1990s. All seven client modules use `XMLRPCClient` as their base class and invoke `invokeXMLRPCCall()` to dispatch calls.
- The groupId references `com.citi.prepaid.service.core.client` — the legacy Citi Prepaid ancestry, indicating this library was originally written during the Citi/eCount era and has been carried forward.
- Director — a hierarchical XML-RPC configuration registry — is the service-discovery mechanism. This is a Gen-1 pattern with no equivalents in Gen-3 cloud-native architectures (e.g. Kubernetes service mesh, cloud config services).
- The `2.0.x` version stream indicates a partial modernisation (Java 21 compilation target, Lombok, Maven 3.9, GitHub Packages distribution), but the architectural pattern remains Gen-1.
- The `ecount-core-client` module depends on `FastPaymentDefinition` from `com.cbase.business.core.value` — a reference to legacy CBase domain objects.
- There is no Spring, no REST, no OpenAPI, no async messaging, no cloud SDK in any module.

## Business Domain

**Payments / Prepaid Card Disbursements** — specifically the back-end services for:
- Cardholder lifecycle management (member registration, profile management)
- Prepaid card issuance and management (device/card create, inquiry, update, control)
- Value transfer and card loading (Begin/Commit/Cancel transfer, QuickLoad)
- Fast payment execution (CoreLite)
- Programme configuration (Profile service)
- User/role provisioning for internal operations portals (Security service)
- Card fulfilment order management (Order service)
- Event-driven notification rules (Event service)
- Secret/credential retrieval (StrongBox)

This places the library at the core of the **cardholder data environment (CDE)** — all seven client modules mediate access to systems that create, store, or process cardholder data.

## Role in Platform

`core-clients_LIB` is a **shared infrastructure library** — the canonical way for any JVM-based service in the Onbe Gen-1/Gen-2 estate to call the ECountCore platform. Its role in the wider platform:

1. **Dependency consumed by upstream services** — any service that needs to register a cardholder, issue a card, execute a transfer, or query programme configuration imports one or more JARs from this library.
2. **Service-location abstraction** — through `DirectorServiceLocator` and `DirectorClientFactory`, it abstracts the physical addresses of back-end services from consuming applications.
3. **Protocol adapter** — it converts Java object graphs into XML-RPC wire format and back, isolating consuming services from the XML-RPC serialisation concerns.
4. **Single artefact vector** — a vulnerability or breaking change in this library propagates to all consuming services simultaneously.

## Dependencies

### Upstream (this library depends on)

| Artefact | Version | Owner Domain |
|---|---|---|
| `com.parents:prepaid-parent` | `6.0.13` | Onbe internal build infrastructure |
| `com.citi.prepaid.service.core:xmlrpc` | `3.1.3-SNAPSHOT` | Core XML-RPC transport layer (separate repo) |
| `com.ecount.service.core.ecountcore:common` | `3.1.5` | ECountCore domain model |
| `com.ecount.service.common:services-common` | `3.0.1` | Common service base types |
| `com.ecount.service.xSecurity:xsecurity-common` | `4.0.3` | Security domain types |
| `com.citi.prepaid.service.order:order-common` | `4.1.4` | Order domain types |
| Apache Commons HttpClient 3.x | (transitive) | Open source (EOL) |
| Lombok | (transitive) | Open source |

### Downstream (consuming this library)
Not directly observable from this repository, but logically: any J2EE/Spring service in the Onbe estate that creates members, issues cards, or performs transfers — including but not limited to card issuance services, customer portals, batch processing engines, and internal admin tools.

### Internal Module Dependencies
```
director-client          (base; no internal deps)
    ^
    |__ ecount-core-client
    |__ profile-client
    |__ securityServiceClient
    |__ eventServiceClient
    |__ strongBoxClient
    |__ orderXMLRPCClient
```
All non-director modules declare `director-client` as a compile dependency. `ecount-core-client` is a direct runtime dependency of any module needing member/device/transfer capability.

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| **XML-RPC over HTTP** | `DirectorXMLRPCClient`, all `XMLRPCClient` subclasses | Point-to-point synchronous RPC; Gen-1 pattern |
| **Service Locator via Director** | `DirectorServiceLocator` + `DirectorClientFactory` | Registry-based service discovery; agent-keyed URL resolution |
| **In-process URI cache** | `DirectorServiceLocator.uriCache` (HashMap) | TTL-based cache with stale-on-error fallback; JVM-local, not distributed |
| **Static HTTP connection pool** | `DirectorXMLRPCClient` static initialiser | Shared `MultiThreadedHttpConnectionManager` across all instances; not configurable at runtime |
| **Request/Response DTO pairs** | `*Input` / `*Output` class pairs in each module | Explicit typed contract per operation; no shared schema |
| **Agent-based multi-tenancy** | `agent` parameter on every call | Enables routing to environment-specific or client-specific back-end instances |
| **Affiliate-scoped operations** | `affiliate` parameter on member/device/transfer calls | Programme/brand isolation at the service layer |
| **Event dispatch (stub)** | `EventXMLRPCClient.eventDispatch()` | Actual dispatch is commented out; only UUID generated. Not an active integration |

## Strategic Status

**Status: Active but architecturally stale — candidate for replacement in Gen-3 migration**

Supporting evidence:
1. The library is in active development (version `2.0.3-SNAPSHOT`, Java 21, GitHub Packages CI) — it is being maintained and still delivers value.
2. The README explicitly calls out four modules as "excluded from 2.0.0-beta" with a TODO to include them in the final release — indicating ongoing investment.
3. However, the fundamental protocol (XML-RPC), the service discovery mechanism (Director), and the connection management (Apache Commons HttpClient 3.x) are all Gen-1 patterns with no path to cloud-native deployment.
4. The `EventXMLRPCClient` event dispatch stub is a sign of incomplete modernisation: the intent to publish events (a Gen-2/Gen-3 pattern) exists but the implementation is not active.
5. The SNAPSHOT dependency on `xmlrpc:3.1.3-SNAPSHOT` (the transport layer) creates an unstable foundation for any long-term reliance on this library.

## Migration Blockers

| Blocker | Impact | Notes |
|---|---|---|
| XML-RPC protocol dependency | High | All service interactions are XML-RPC. Migrating to REST/gRPC/message-driven requires re-implementing all seven client modules and coordinating with server-side service migration |
| Director service-discovery dependency | High | All URL resolution flows through Director. Gen-3 equivalent would be Kubernetes Services, API Gateway, or a service mesh. Director must be decommissioned or replaced concurrently |
| Apache Commons HttpClient 3.x (EOL) | Medium | No TLS 1.3 support; security patching impossible. Upgrade requires changes in the `xmlrpc` transport library (a separate repo) |
| `com.citi.prepaid.service.core:xmlrpc:3.1.3-SNAPSHOT` instability | Medium | SNAPSHOT artefact; any change breaks consuming builds. Must be stabilised before migration |
| `FastPaymentDefinition` from `com.cbase.business.core` | Medium | Legacy CBase domain type leaked into `CoreLiteXMLRPCClient`. Requires CBase domain model migration |
| Hardcoded internal hostnames in test/example code | Low | `ecappdev`, `ppamwdcddcor1` hostnames in `UsageExample.java`, `TestDirectorXMLRPCClient.java`, `DeviceXMLRPCClient.main()`. Must be externalised before any environment migration |
| Tests make live calls | Low | Integration tests in `director-client` call live internal Director instances. CI/CD pipeline would break if internal network access is removed during cloud migration |
| Event dispatch is disabled | Low | Consuming services may believe events are published; they are not. Any Gen-3 event-driven design will need to determine the correct event publishing strategy from scratch |
| SNAPSHOT version (`2.0.3-SNAPSHOT`) | Low | Mutable artefact; downstream services cannot pin to a fixed version. Must be released before migration freeze |
