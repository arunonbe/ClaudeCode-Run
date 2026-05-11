# Enterprise Architect View — xsearch-new_SVC

## Platform Generation
**Gen-2** — Modernised search service. Wraps the Gen-1 xsearch_LIB data-access layer in an XML-RPC HTTP service, enabling network-accessible search from distributed clients. Despite the "new" designation, the underlying technology choices (XML-RPC, Spring 2.5.4, Servlet 2.5) are themselves legacy.

## Business Domain
Customer Service / Cardholder Account Lookup. Network-accessible version of the xsearch_LIB capabilities, extended with mobile phone search, device-by-member search, and PUID lookup.

## Role in the Platform
**Gen-2 search service.** Bridges the Gen-1 xsearch_LIB data-access layer with network-accessible consumers (CSA tools, other services). The XML-RPC client module (`xSearch-client`) allows any service to consume the search capability without a direct database connection.

## Dependency Hierarchy
```
xplatform-library_LIB
        |
xplatform_LIB (2014.1.1 in root POM / actual version TBC from impl POM)
        |
xSearch-impl (xsearch_LIB equivalent)
        |
xSearch-xmlrpc (WAR — XML-RPC service)
        ^
        |  (consumed via)
xSearch-client (XML-RPC client stub)
        ^
        |
Other platform services (CSA tools, etc.)
```

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| xplatform_LIB | Upstream | Version 2014.1.1 in root POM (very old); impl module may use a different version |
| director-client 1.0.11 | External | Director service for dynamic datasource configuration |
| ecount-system 1.0.10 | External | Core system library |
| xmlrpc 1.0.9 | External | Internal XML-RPC framework |
| SQL Server (4 databases) | External | Same as xsearch_LIB |
| Director Service | External | Runtime datasource configuration |

## Integration Patterns
- **XML-RPC over HTTP** — all service operations are XML-RPC method calls
- **Client stub pattern** — `XSearchXMLRPCClient` provides a typed Java client for consuming services
- **Dynamic datasource pattern** — Director service provides connection parameters at runtime
- **Module decomposition** — 4-module Maven project separating common objects, client, implementation, and transport layer

## Strategic Status
**Gen-2 bridge service — plan to replace with REST/gRPC.** Key observations:
- XML-RPC is a legacy protocol; no standard tooling for observability, security, or API management
- The service is actively used (CodeQL scanning suggests it is a maintained asset)
- The root POM's very old dependency versions (`xPlatform 2014.1.1`, `Spring 2.5.4`) are a serious concern and must be reconciled with module-level POM overrides
- The Servlet 2.5 / `javax.servlet` namespace conflict with Tomcat 10 (Jakarta EE) is a deployment blocker
- Dependabot is configured — dependency hygiene is being managed

## Migration Blockers
- **XML-RPC client coupling:** All consumers of this service use `XSearchXMLRPCClient` — migration to REST/gRPC requires updating all clients simultaneously or providing a compatibility layer
- **Director service dependency:** The Director-based datasource configuration is an internal infrastructure dependency; a Gen-3 replacement must replicate or replace this mechanism
- **Servlet 2.5 / javax.servlet namespace:** Migration to Jakarta EE (Tomcat 10) requires javax → jakarta namespace migration throughout
- **`xPlatform 2014.1.1` in root POM:** This 2014-vintage version must be aligned with the current `xplatform_LIB` version (6.x) before a clean migration
- **Hardcoded Log4j file path:** Must be externalised before any containerised deployment
