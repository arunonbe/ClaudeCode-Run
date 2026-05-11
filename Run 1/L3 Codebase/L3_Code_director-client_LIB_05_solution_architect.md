# Solution Architect Report — director-client_LIB

## 1. Architecture Overview

director-client_LIB is a **single-module Java 21 library** providing a thread-safe XML-RPC client for the Director service. It is published to GitHub Packages and consumed by all Gen-2 Onbe services.

```
director-client_LIB
└── src/main/java/com/ecount/Core2/director/client/
    ├── IDirectorClient.java              — Interface: get(), getAgentSetting(), getSerivceLocationURI()
    ├── DirectorClientFactory.java        — Static factory; produces DirectorXMLRPCClient
    ├── DirectorXMLRPCClient.java         — Concrete XML-RPC implementation; thread-safe
    ├── DirectorServiceLocatingCache.java — TTL-cached service URI resolver (implements XMLRPCServiceLocator)
    ├── DirectorClientException.java      — Typed exception for service location failures
    ├── IDirectorLocationAware.java       — Unused marker interface
    ├── test.java                         — [MISPLACED] Swing GUI debug utility in main source
    ├── Input/GetInput.java               — XML-RPC request DTO
    └── Output/GetOutput.java             — XML-RPC response DTO
```

---

## 2. Public API Surface

### `IDirectorClient` Interface (package: `com.ecount.Core2.director.client`)

```java
// Get all settings under a key for a given agent
Map<String, Object> get(URI directorLocation, String key, String agent);

// Get agent-scoped setting with fallback (tries key\agent first, then key)
Map<String, Object> getAgentSetting(URI directorLocation, String key, String agent);

// Two-step service URI resolution: Services\{key}\{agent} → System\Servers\{agent}
URI getSerivceLocationURI(URI directorServiceLocation,
                          String serviceDirectorKeyName,
                          String serviceFriendlyName,
                          String agent) throws DirectorClientException;
```

### `DirectorServiceLocatingCache` (implements `XMLRPCServiceLocator`)

```java
// Thread-safe cached service address (1-hour TTL typical)
synchronized URI getServiceAddress() throws XMLRPCServiceLocatorException;
```

### Factory

```java
IDirectorClient client = DirectorClientFactory.getClient(DirectorClientTypes.XMLRPC);
```

---

## 3. Security Architecture

| Control | Status | Detail |
|---|---|---|
| Transport encryption | Partial | Production Director uses HTTPS (`https://prod.nam.wirecard.sys:8080/`); test/dev uses HTTP |
| Authentication | **None observed** | Only `agent` string sent as header; no token, certificate, or mutual TLS |
| Authorization | **Not enforced by client** | Director service presumably controls access; client has no auth capability |
| Credential in-flight protection | HTTPS only in prod | Non-prod Director calls are over HTTP; credentials unencrypted |
| Credential in-memory protection | **None** | Credentials stored as `String` in `Map<String, Object>`; heap-dumpable |
| Exception disclosure control | Poor | DEBUG-level logging on failure; callers get null with no explanation |

### Security Risk: Director as Unauthenticated Credential Dispenser

The most significant security concern with this library is that any service that can reach the Director HTTP endpoint and send a valid `agent` string can retrieve any credentials registered under that agent. There is no per-client authentication visible in this code. If Director is accessible from any host on the internal network, credential theft via network access alone is possible.

---

## 4. Technical Debt

| Item | Class / File | Severity |
|---|---|---|
| Commons HTTPClient 3.x (EOL) | `DirectorXMLRPCClient` imports + `pom.xml:33` | High |
| Hardcoded timeouts (5s socket, 60s connection) | `DirectorXMLRPCClient` lines 63, 87–89 | High — not configurable |
| Silent exception swallowing (DEBUG log, null return) | `DirectorXMLRPCClient.get()` lines 117–124 | Critical — operational risk |
| `test.java` in `src/main/java` | `src/main/java/.../test.java` | Medium — Swing GUI in production JAR |
| `IDirectorLocationAware` unused | `IDirectorLocationAware.java` | Low — dead interface |
| `assert false` for non-XMLRPC factory type | `DirectorClientFactory.java` line 38 | Low — assertions disabled at runtime |
| `DirectorServiceLocatingCache` old constructor without directorKey/friendlyName | Lines 58–77 | Medium — incomplete; `getServiceAddress()` will NPE if called on this constructor |
| Typo: `getSerivceLocationURI` | `IDirectorClient.java` line 49 | Low — API-breaking to fix |
| Typo: `cacheExpiracyMsec` | `DirectorServiceLocatingCache.java` line 22 | Low |
| Tests skipped in CI publish | `github-package-publish.yml` line 41 | Medium |

---

## 5. Gen-3 Migration — Solution Design

### Phase 1: Parallel Operation (No Service Changes Required)
Create a **Director-to-Azure bridge adapter** that:
1. Exposes the same `IDirectorClient` interface
2. Reads from Azure App Configuration using a key mapping (e.g., `System/DataCredentials/{agent}` → App Config label)
3. Reads secrets from Azure Key Vault using the same naming convention
4. Falls back to real Director on cache miss

### Phase 2: Service Migration
For each Gen-2 service:
1. Replace `director-client.yaml` URL with Azure App Config connection string
2. Remove `DirectorServiceLocatingCache` usages; replace with static Azure App Config lookups
3. Remove `ECountSystemConfiguration.java` bootAddress wiring (debit-api_API)
4. Update credentials to use Azure Key Vault references (debit-api_API already partially done)

### Phase 3: Director Retirement
1. Confirm zero active connections to `{env}.nam.wirecard.sys:8080/service/dispatch.asp`
2. Decommission Director server
3. Archive Director registry content

### Recommended Azure App Config Key Structure

| Director Key | Azure App Config Key | Notes |
|---|---|---|
| `System\DataCredentials\{agent}` | `Director:DataCredentials:{agent}` | Credentials in Key Vault, reference in App Config |
| `System\DataEnvironment\{agent}` | `Director:DataEnvironment:{agent}` | DB name mappings |
| `System\Servers` | `Director:Servers` | Server alias → URI map |
| `Services\{ServiceName}` | `Director:Services:{ServiceName}` | Service endpoint config |

---

## 6. Code Quality Risks — Critical Summary

| Risk | Impact | Urgency |
|---|---|---|
| `get()` returns null silently | Any caller that doesn't null-check will NPE; credential lookup failure becomes database authentication failure with unclear error | Fix immediately — add exception propagation or at minimum INFO/WARN logging |
| No authentication on Director calls | Any internal network actor can retrieve credentials for any agent | Requires Director server-side fix + network segmentation |
| Hardcoded 5-second timeout | Under Director load or network jitter, all callers fail simultaneously | Make timeout configurable via system property |
| `DirectorServiceLocatingCache` partial constructor | Constructor at lines 58–77 sets `directorKey=null`, `friendlyName=null`; `getServiceAddress()` will NPE at line 106 when it calls `directorClient.getSerivceLocationURI(..., null, null, agent)` | Fix or remove partial constructor |
| Commons HTTPClient 3.x TLS limitations | Cannot enforce TLS 1.2/1.3 minimum; known downgrade vulnerabilities | Upgrade to Apache HttpClient 5.x |
