# Enterprise Architect Report — director-client_LIB

## 1. Platform Generation Classification

| Attribute | Value |
|---|---|
| Generation | Gen-2 critical infrastructure — central to entire legacy platform |
| Runtime | Java 21 (updated) on JVM; distributed as library JAR |
| Protocol | XML-RPC over HTTP/HTTPS |
| Framework | None (pure Java + Apache Commons HTTPClient 3.x) |
| Modernization urgency | **Critical** — must be replaced as part of Gen-3 migration |

---

## 2. Director Service Role — Platform-Wide Analysis

Director is the **central nervous system** of the Gen-2 Onbe platform. Its functions:

| Function | Analogy | Modern Equivalent |
|---|---|---|
| Database credential distribution | Secrets management | Azure Key Vault |
| Service endpoint registry | Service discovery | Azure Service Bus / App Config / Kubernetes DNS |
| Connection string distribution | Config management | Azure App Configuration |
| Per-agent configuration | Multi-tenant config | Azure App Configuration with labels |
| Hierarchical settings store | Registry | Azure App Configuration hierarchy |

### Director Is the Root Dependency

The Director server at `{env}.nam.wirecard.sys:8080` is the bootstrap dependency:
- **debit-api_API** uses Director URL as `bootAddress` for `ECountSystemConfiguration.java` and as `director.address` in YAML config
- Every ECount service lookup (Profile, eMember, eDevice, StrongBox, JobService) requires Director to be available
- All database credentials flow through Director; without it, no service can authenticate to any database

**Director downtime = platform-wide outage for all Gen-2 services.**

---

## 3. Director Protocol — Detailed Specification

### 3.1 Transport
- **Protocol**: XML-RPC (http://xmlrpc.com/spec)
- **Transport**: HTTP POST
- **Content-Type**: `text/xml`
- **Endpoint**: `http[s]://{director_host}/service/dispatch.asp`

### 3.2 Request Headers (set by `XMLRPCClientUtils.setRequestHeaders`)
```
Agent: {agent}               (e.g. "B2C", "B2CTEST", "B2CSTAGE")
X-Service-Name: ECountService.Config
X-Method-Name: Get
X-Client-Application: Director.client
```

### 3.3 Request Body (XML-RPC methodCall)
```xml
<methodCall>
  <methodName>ECountService.Config.Get</methodName>
  <params>
    <param><value><struct>
      <member>
        <name>key</name>
        <value><string>System\DataCredentials\B2CTEST</string></value>
      </member>
    </struct></value></param>
  </params>
</methodCall>
```

### 3.4 Response Body (XML-RPC methodResponse)
```xml
<methodResponse>
  <params>
    <param><value><struct>
      <member><name>Password</name><value><string>...</string></value></member>
      <member><name>UserID</name><value><string>...</string></value></member>
    </struct></value></param>
  </params>
</methodResponse>
```

Nested structs represent sub-keys in the hierarchy (e.g., `Services` contains named service maps).

### 3.5 Agent-Scoped Lookup Algorithm
```
1. Attempt GET "key\agent"
2. If result is null or empty → attempt GET "key"
3. Return result (may be null)
```
(`DirectorXMLRPCClient.getAgentSetting()` lines 141–153)

### 3.6 Two-Step Service Location Algorithm
```
1. GET "Services\{ServiceName}[\{agent}]" → Map containing "InterfaceServer" = "<alias>"
2. GET "System\Servers[\{agent}]" → Map containing "<alias>" = "<URI string>"
3. Return new URI(<URI string>)
```
(`DirectorXMLRPCClient.getSerivceLocationURI()` lines 174–226)

---

## 4. Services Known to Depend on Director

| Service | Director Keys Used | Evidence |
|---|---|---|
| **debit-api_API** | All `System\*` keys via `ECountSystemConfiguration`; Director URL = bootAddress | `application.yml`, `director-client.yaml`, `ECountSystemConfiguration.java` |
| **ECountCore.Profile** | `Services\ECountCore.Profile`, `System\Servers` | `IDirectorClient.SERVICES_ECOUNTCORE_PROFILE_KEY` |
| **ECountCore.eMember** | `Services\ECountCore.eMember` | `IDirectorClient.SERVICES_ECOUNTCORE_EMEMBER_KEY` |
| **ECountCore.eDevice** | `Services\ECountCore.eDevice` | Confirmed in test `valuesComplex()` line 66 |
| **StrongBox.RepositoryService** | `Services\StrongBox.RepositoryService` | `IDirectorClient.SERVICES_SRONGBOX_REPOSVC_KEY` |
| **Job/ETL services** | `CoreServices\JobService\ETL` | `test.java` line 31 |
| **Any service using DataCredentials** | `System\DataCredentials` | Implicit — all Gen-2 services with SQL Server DBs |

---

## 5. Architectural Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| Factory | `DirectorClientFactory.getClient(DirectorClientTypes.XMLRPC)` (line 29) | Static factory; only XMLRPC supported despite enum suggesting extensibility |
| Strategy | `DirectorClientTypes` enum; only `XMLRPC` implemented | `assert false` for any other type (line 38) — poor pattern |
| TTL Cache | `DirectorServiceLocatingCache` — 1-hour default expiry, synchronized `getServiceAddress()` | Thread-safe; suitable for service URI caching |
| ThreadLocal Logger | `DirectorXMLRPCClient` — per-thread Logger instance | Justified for shared classloader environments (library) |
| Static HTTP connection pool | `DirectorXMLRPCClient` — static `HttpClient` + `MultiThreadedHttpConnectionManager` | Efficient but hardcoded timeouts |

---

## 6. Current Status

| Aspect | Status |
|---|---|
| Version | `2.0.1` |
| Branch | `main` |
| Java target | 21 (recently updated — previously lower) |
| Published to GitHub Packages | Yes — via `github-package-publish.yml` |
| Tests run in CI | No — `Dmaven.test.skip` |
| Test class in main source | `test.java` in `src/main/java` (should be test source) |

---

## 7. Gen-3 Migration — Critical Path

Director is on the **critical path of Gen-3 migration**. Until Director is replaced:
1. All Gen-2 services remain dependent on `{env}.nam.wirecard.sys`
2. Azure Key Vault cannot fully replace Director (services use Director for both credentials AND service discovery)
3. Gen-3 services that partially migrate (like debit-api_API) still call Director for bootstrap config

**Migration approach**:
1. Freeze new Director registrations — all new services must use Azure App Config + Key Vault
2. Implement a Director → Azure App Config bridge to mirror Director keys into App Config (allows gradual migration)
3. Update each Gen-2 service to read from Azure App Config first, fall back to Director
4. Retire Director when zero services call it

**Blockers**:
- Director's two-step service location protocol has no direct equivalent in Azure App Config without custom resolver logic
- Credential rotation in Director is centrally managed; migration must maintain zero-downtime rotation
- Unknown total number of Director keys / consumers across the platform (beyond what is visible in this codebase)
