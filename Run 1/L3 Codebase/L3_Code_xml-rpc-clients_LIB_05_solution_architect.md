# 05 Solution Architect — xml-rpc-clients_LIB

## Technical Architecture
Multi-module Maven library (`com.citi.prepaid.service.core:client:2016.1.1`, packaging `pom`). Seven sub-modules, each providing an XML-RPC client for a specific eCount/cbase platform service. No HTTP server; no Spring Boot; pure client-side library.

Sub-modules and their XML-RPC targets:
| Module | Client Class | Target Service |
|---|---|---|
| `directorClient` | `DirectorXMLRPCClient` / `DirectorClientFactory` | Director (eCount config/connection registry) |
| `ecountCoreClient` | Multiple clients (device, member, transfer, event, corelite) | eCount Core platform services |
| `profileClient` | `ProfileXMLRPCClient` | eCount Profile service |
| `eventServiceClient` | (event service client) | eCount Event service |
| `orderXMLRPCClient` | `OrderXMLRPCClient` | eCount Order service |
| `securityServiceClient` | `SecurityServiceXMLRPCClient`, `SecurityHierarchyServiceXMLRPCClient` | xSecurity service (user management, hierarchy) |
| `strongBoxClient` | `StrongBoxXMLRPCClient` | StrongBox / repository service |

Transport layer: Apache Commons HttpClient 3.x (`MultiThreadedHttpConnectionManager`), serialisation via internal `XmlRPCFromObjectMapper` / `XmlRPCToObjectMapper`.

## API Surface
No HTTP API. Programmatic Java library API. Each client exposes typed input/output DTOs:

Representative patterns:
```java
// DirectorXMLRPCClient
Map<String,Object> get(String key, String agent)
Map<String,Object> getAgentSetting(String key, String agent)
URI getSerivceLocationURI(String serviceDirectorKeyName, String serviceFriendlyName, String agent)

// SecurityServiceXMLRPCClient (inferred from input/output DTOs)
UserManagementRequestOutput processUserManagement(UserManagementRequestInput input)
BulkHierarchyNodeFileRequestOutput processBulkHierarchy(BulkHierarchyNodeFileRequestInput input)

// ProfileXMLRPCClient (inferred)
ProfileOutput classGet/classCreate/classPut/classDelete/classDrop/classRetrieve/classSelect/classUpdate
ProfileScopeOutput scopeCreate/scopeDelete/scopeRetrieve/scopeUpdate

// OrderXMLRPCClient / StrongBoxXMLRPCClient (inferred)
Typed request/response pairs per operation
```

## Security Posture
- **XML-RPC protocol**: plain HTTP XML-RPC (no TLS enforced at client level); if the target URLs are `http://` (not `https://`), all communication including potential credential data is unencrypted — **PCI DSS Req. 4** risk
- `DirectorXMLRPCClient` uses a static `HttpClient` with `MultiThreadedHttpConnectionManager`; connection pool is shared across all threads and all instances — **thread-safe by design** (noted in code comments) but certificate validation and TLS configuration depend on the JVM default trust store
- Socket timeout and connection timeout set to 5000ms (5 seconds) in `DirectorXMLRPCClient.get()` — appropriate for synchronous calls, but there is no retry logic; a transient failure returns `null`
- `SecurityServiceXMLRPCClient` handles user management and hierarchy requests; the input DTOs include `BulkUserRecord`, `UserRegistrationInfo`, `Location`, `Promotion` — user PII may flow through XML-RPC; plaintext XML-RPC transport is a PII exposure risk
- `StrongBoxXMLRPCClient` (StrongBox = credential / repository service): any credential or sensitive data stored in StrongBox must not flow over unencrypted XML-RPC connections
- No authentication on the XML-RPC calls at the HTTP level observed in `DirectorXMLRPCClient`; authentication is embedded in the `XMLRPCClientUtils.setRequestHeaders()` call (internal mechanism, not visible in this repo) — verify the agent/session token mechanism is robust

## Technical Debt
| Item | Severity |
|---|---|
| XML-RPC protocol (Gen-1, no standard security layer) | Critical |
| Apache Commons HttpClient 3.x (EOL; replaced by HttpClient 4/5) | Critical |
| No TLS enforcement in `DirectorXMLRPCClient` | Critical |
| Java target likely 1.5/1.6 (parent `service-parent:7`) | High |
| `ClientTest1.java` and `Testing.java` production source files in `orderXMLRPCClient/src/main` | High |
| Static `HttpClient` instance — certificate pinning and TLS config cannot be customised per call | High |
| `getSerivceLocationURI` — typo in method name (`Serivce`) | Low |
| `getStackTrace()` in `DirectorXMLRPCClient` uses `PrintWriter`/`StringWriter` — verbose; `ExceptionUtils.getStackTrace()` would be cleaner | Low |
| Version `2016.1.1` from Subversion SCM — no active development since 2016 | High |
| `change.log` present — review for any accidental credential commits | Low |

## Gen-3 Migration
**Migration is the only viable path.** XML-RPC is obsolete; the services this library connects to (Director, eCount Core, Profile, Order, Security, StrongBox) should all expose REST or gRPC APIs in Gen-3. Recommended approach:
1. Each target service should expose a REST API (or reuse an existing one, e.g., AccountManagementAPI for eCount Core operations)
2. Replace XML-RPC DTOs with REST request/response models (Jackson-annotated POJOs)
3. Use Spring's `RestClient` (Spring 6.1+) or `WebClient` for async
4. Replace Director config registry pattern with Azure App Configuration or Spring Cloud Config
5. Replace StrongBox with Azure Key Vault
6. All migration work is gated on the server-side XML-RPC services being re-implemented first

Until migration: ensure all XML-RPC endpoint URLs are `https://` and the Java trust store includes the server certificates. Do not use these clients to transmit PAN or cardholder data.

## Code-Level Risks
- `DirectorXMLRPCClient.get()` returns `null` on any exception or non-200 HTTP response without throwing — callers that don't null-check the return value will NPE silently
- `connectionManager.getParams().setDefaultMaxConnectionsPerHost(1000)` and `setMaxTotalConnections(1000)` — very high connection limits; in a containerised environment with many replicas, this could exhaust the target server's connection capacity
- `PostMethod` in `get()` is created per-call but uses the static `httpClient`; `myMethod.releaseConnection()` in `finally` is correct — no connection leak for the normal path
- XML-RPC response parsing via `XmlRPCToObjectMapper.toObject()` (internal library); untrusted XML-RPC responses could trigger XML entity expansion attacks (XXE) if the parser is not configured to disable external entity resolution — verify the internal parser configuration
- `TestClient1.java` and `Testing.java` in `src/main` (not `src/test`) will be compiled into the production JAR — these likely contain hard-coded test URLs or credentials that should not be in production artifacts
