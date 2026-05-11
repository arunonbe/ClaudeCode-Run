# Data Architect Report — director-client_LIB

## 1. Data Stores

director-client_LIB is a **Java client library**. It has no data stores of its own. Data is retrieved at runtime from the **Director service** via XML-RPC over HTTP/HTTPS.

| Data Location | Type | Access Pattern |
|---|---|---|
| Director service registry | Remote key-value store (Windows Registry-like hierarchy) | Read-only; XML-RPC POST |
| `DirectorServiceLocatingCache` | In-memory (JVM heap) | Cached URI; 1-hour TTL; synchronized access |
| `MultiThreadedHttpConnectionManager` | JVM-level HTTP connection pool | Static; shared across all threads via `DirectorXMLRPCClient` static fields |

---

## 2. Director Registry Data Schema (Inferred)

Director organises data in a hierarchical namespace with backslash delimiters. Values are key-value maps (can be nested). The XML-RPC wire format uses the standard `methodCall` / `methodResponse` encoding.

### 2.1 `System\DataCredentials[\\{agent}]`
```
{
  "Password": "<db_password>",
  "UserID":   "<db_username>"
}
```
Agent-specific credentials override this structure at `System\DataCredentials\{agent}`.

### 2.2 `System\DataEnvironment[\\{agent}]`
```
{
  "ECountCore":  "<dbname>.<sqlserver_host>",   // e.g. "ECountCore_Test.ECSQLDEV1"
  "JOBSVC":      "<dbname>.<sqlserver_host>",   // e.g. "JOBSVC_TEST.ECSQLDEV1"
  ...
}
```

### 2.3 `System\DataSettings[\\{agent}]`
```
{
  "CursorLocation":  <int>,      // e.g. 3
  "JOBSVC": {
    "CursorLocation":    <int>,  // 3
    "CommandTimeout":    <int>,  // 0x78 = 120
    "ConnectionTimeout": <int>   // 0xf = 15
  }
}
```

### 2.4 `System\DataSources[\\{agent}]`
```
{
  "<key>": "<OLE DB / ADO connection string>"
  // e.g. "ECountCore.VSQLSTAGE1B":
  //   "Provider=SQLOLEDB;Network Library=dbmssocn;Data Source=Vsqlstage1b\\vsqlstage1b1;Initial Catalog=ECountCore"
}
```

### 2.5 `System\Servers[\\{agent}]`
```
{
  "<server_alias>": "<URI>",
  // e.g. "ECAPPDEV1": "http://ecappdev1/..."
}
```

### 2.6 `Services\{ServiceName}[\\{agent}]`
```
{
  "InterfaceServer": "<server_alias>",
  // Additional service-specific settings
}
```

### 2.7 XML-RPC Wire Format

**Request** (method: `ECountService.Config.Get`):
```xml
<?xml version="1.0"?>
<methodCall>
  <methodName>ECountService.Config.Get</methodName>
  <params>
    <param><value><struct>
      <member><name>key</name><value><string>System\DataCredentials</string></value></member>
    </struct></value></param>
  </params>
</methodCall>
```
Header set by `XMLRPCClientUtils.setRequestHeaders(agent, "ECountService.Config", "Get", ...)`.

**Response**: Standard XML-RPC `methodResponse` with nested `struct` values mapped to `Map<String, Object>`.

---

## 3. Sensitive Data Inventory

| Data Element | Location | Classification | Risk |
|---|---|---|---|
| Database passwords | Returned by `System\DataCredentials` lookup | Secret / PCI Sensitive | Transmitted over network from Director; stored in JVM heap after retrieval |
| Database usernames | Returned by `System\DataCredentials` | Sensitive | As above |
| Connection strings (OLE DB) | Returned by `System\DataSources` | Sensitive | May contain embedded credentials |
| Service endpoint URIs | Returned by `System\Servers` | Internal infrastructure | Exposes internal network topology |
| Expected test credential values | `TestDirectorXMLRPCClient.java` lines 52–101 | **HIGH RISK** | Credential assertion values committed to version control — must be confirmed as non-production |
| Director server hostnames (QA) | `TestDirectorXMLRPCClient.java` line 40: `Http://ecappdev/service/dispatch.asp`; `test.java` line 35 same | Internal hostname | Committed to source; reveals QA Director server hostname |
| Server alias `ECAPPDEV1` | `TestDirectorXMLRPCClient.java` line 78 | Internal hostname | Committed in test assertions |
| ECountCore DB mapping | `TestDirectorXMLRPCClient.java` lines 110, 117: `ECountCore_Test.ECSQLDEV1`, `ECountCore.VSQLSTAGE1B`, `VSQLSTAGE1A` | Internal DB server names | Committed in test assertions |
| OLE DB connection string | `TestDirectorXMLRPCClient.java` line 148–149: Full connection string to `Vsqlstage1b\\vsqlstage1b1\ECountCore` | **Critical** | Full OLE DB connection string committed to test code |

**FLAG — Connection String in Tests**: `TestDirectorXMLRPCClient.dataSourcesValues()` (line 148) asserts that the Director response contains the full OLE DB connection string: `"Provider=SQLOLEDB;Network Library=dbmssocn;Data Source=Vsqlstage1b\\vsqlstage1b1;Initial Catalog=ECountCore"`. This is a database connection string pointing to an internal SQL Server instance committed to version control. This must be reviewed under PCI DSS Req 12.3 and confirmed as a decommissioned or non-CDE server.

---

## 4. Encryption

| Mechanism | Status | Detail |
|---|---|---|
| TLS on Director calls | Partially | Production: `https://prod.nam.wirecard.sys:8080/service/dispatch.asp` (HTTPS); QA/test in test code uses `Http://ecappdev/...` (HTTP — no TLS for non-prod) |
| Credential values in transit | Partially protected | HTTPS in prod only; HTTP in non-prod and test scenarios |
| In-memory credential storage | No encryption | Credentials stored as plain `String` in `Map<String, Object>` in JVM heap |
| Connection pool security | `MultiThreadedHttpConnectionManager` | No explicit TLS config in static initializer (`DirectorXMLRPCClient` lines 60–66); relies on URL scheme |

---

## 5. Data Flow

```
Calling Service
  │
  ▼
DirectorClientFactory.getClient(XMLRPC)
  → DirectorXMLRPCClient (singleton pattern via static HttpClient)
       │ HTTP POST (XML-RPC)
       │ URL: http[s]://{director_host}/service/dispatch.asp
       │ Headers: agent, service="ECountService.Config", method="Get"
       │ Body: XML-RPC methodCall with key
       ▼
    Director Service (Windows/.NET registry frontend)
       │ Returns XML-RPC methodResponse
       │ Structure: nested Map<String, Object>
       ▼
    DirectorXMLRPCClient.get() → Map<String, Object>
       │
  [Optional cache layer]
  DirectorServiceLocatingCache.getServiceAddress()
    → Caches URI for up to {cacheExpiracyMsec} ms
    → Thread-safe (synchronized method, line 85)
       │
       ▼
  Calling Service uses credentials/URIs
```

---

## 6. Data Quality

- **Null return on failure**: `DirectorXMLRPCClient.get()` catches all exceptions at line 117 and returns `null`. Callers must handle null. Many callers may not — `getAgentSetting()` (line 149) checks for null/empty but only at one layer.
- **Map type safety**: All values returned as `Object`; callers must cast. Type errors are not caught at compile time.
- **Cache staleness**: `DirectorServiceLocatingCache` caches for `cacheExpiracyMsec` (configurable). If Director is updated mid-cache-period, service will use stale endpoints until expiry.
- **No TTL on credentials**: Credential lookups are not cached; each operation fetches fresh from Director. Under high load this is N calls to Director per second.

---

## 7. Compliance Gaps

| Gap | Standard | Detail |
|---|---|---|
| OLE DB connection string committed to test code | PCI DSS Req 12.3 | `TestDirectorXMLRPCClient.java` line 148 contains full internal DB connection string |
| Expected credential values in test assertions | PCI DSS Req 3.5 | Lines 52–101 contain expected password/username return values; must be confirmed non-production |
| HTTP (non-TLS) Director URL in test | PCI DSS Req 4.2.1 | `Http://ecappdev/service/dispatch.asp` — credentials transmitted in plaintext in non-prod |
| Credentials in JVM heap unencrypted | PCI DSS Req 3.7 | No SecureString or encryption of in-memory credential values |
| No audit log of credential retrievals | PCI DSS Req 10.2 | No logging of which service retrieved which credentials from Director |
