# Business Analyst Report — director-client_LIB

## 1. Business Purpose

director-client_LIB is the **Java client library for the Director service** — the **platform-wide, centralised service-discovery and credential-management system** of the Onbe/ECount platform (formerly Citi Prepaid / Wirecard legacy). Every internal Onbe service that requires database credentials, internal service endpoint locations, or system configuration properties retrieves them at runtime through the Director service via this library.

Director is analogous to a **service registry + secrets vault** for the Gen-2 platform. It serves the role that Azure App Configuration + Azure Key Vault serve for Gen-3 services.

**Library identity**:  
Group: `com.ecount.service.Core2.director`  
Artifact: `director-client`  
Version: `2.0.1`  
Package: `com.ecount.Core2.director.client`

---

## 2. Capabilities

| Capability | Method | Class | Description |
|---|---|---|---|
| Generic key lookup | `get(URI, String key, String agent)` | `IDirectorClient` (line 25) | Returns all settings under a given registry key for a given agent |
| Agent-scoped lookup | `getAgentSetting(URI, String key, String agent)` | `IDirectorClient` (line 38) | First tries `key\agent`, falls back to `key`, returns agent-appropriate defaults |
| Service location resolution | `getSerivceLocationURI(URI, String keyName, String friendlyName, String agent)` | `IDirectorClient` (line 49) | Two-step lookup: resolves `InterfaceServer` alias from service key, then resolves alias to full URI from `System\Servers` |
| Cached service location | `getServiceAddress()` | `DirectorServiceLocatingCache` (line 85) | Thread-safe 1-hour cache of a previously resolved service URI |

Factory entry point: `DirectorClientFactory.getClient(DirectorClientTypes.XMLRPC)` — returns a `DirectorXMLRPCClient` instance.

---

## 3. Director Registry Key Hierarchy

The Director service organises configuration as a hierarchical key-value registry (analogous to Windows Registry). Known keys:

| Constant | Value | Purpose |
|---|---|---|
| `SYSTEM_KEY` | `System` | Root system config |
| `SYSTEM_DATACREDENTIALS_KEY` | `System\DataCredentials` | **Database usernames and passwords** |
| `SYSTEM_DATAENVIRONMENT_KEY` | `System\DataEnvironment` | Database names and server mappings (e.g., `ECountCore_Test.ECSQLDEV1`) |
| `SYSTEM_DATASETTINGS_KEY` | `System\DataSettings` | ODBC/ADO connection settings (cursor location, timeouts) |
| `SYSTEM_DATASOURCES_KEY` | `System\DataSources` | Full ADO/OLE DB connection strings |
| `SYSTEM_SERVERS_KEY` | `System\Servers` | Server hostname → URI mappings |
| `SERVICES_KEY` | `Services` | Root service registry |
| `SERVICES_ECOUNTCORE_PROFILE_KEY` | `Services\ECountCore.Profile` | Profile service location |
| `SERVICES_SRONGBOX_REPOSVC_KEY` | `Services\StrongBox.RepositoryService` | StrongBox repository service location |
| `SERVICES_ECOUNTCORE_EMEMBER_KEY` | `Services\ECountCore.eMember` | eMember service location |

The `CoreServices\JobService\ETL` key (shown in `test.java` line 31) suggests additional keys for ETL/job services.

---

## 4. Credential Retrieval Protocol

The most critical use of Director is **database credential retrieval** via `System\DataCredentials`. The flow:

```
1. Service calls: directorClient.getAgentSetting(
     directorURI,
     "System\DataCredentials",    ← key
     "B2CTEST"                    ← agent
   )

2. DirectorXMLRPCClient first tries:
     GET "System\DataCredentials\B2CTEST"   ← agent-specific credentials

3. If empty, falls back to:
     GET "System\DataCredentials"           ← agent-fallback (Director returns default for agent)

4. Returns Map: { "Password": "...", "UserID": "..." }
```

Test data in `TestDirectorXMLRPCClient.java` confirms:
- Agent `B2CTEST` → returns `Password` and `UserID` values (credential names confirmed at lines 52–55)
- Agent `B2CLOAD` → returns `b2cstage`-prefixed credentials (lines 92–94) — **CAUTION**: test assertions include expected credential values; these appear to be legacy QA values committed to test code
- Agent `NON_EXISTING` → returns default ("brigantinetest") credentials (lines 97–101) — **CAUTION**: default credential name committed to test

**Note**: Lines 52–101 of `TestDirectorXMLRPCClient.java` contain expected values for credential assertions. These values appear to be historical QA/test credentials, not production values. They must be reviewed and the test environment confirmed as sanitised.

---

## 5. Service Location Resolution Protocol

```
1. Call getSerivceLocationURI(directorURI, "Services\ECountCore.Profile", "Profile", "B2CTEST")

2. Resolve service settings:
   GET "Services\ECountCore.Profile\B2CTEST" (or fallback to "Services\ECountCore.Profile")
   → Returns Map containing "InterfaceServer" = "ECAPPDEV1"  (server alias)

3. Resolve server alias to URI:
   GET "System\Servers\B2CTEST" (or fallback)
   → Returns Map containing "ECAPPDEV1" = "http://ecappdev1/service/..."

4. Return URI("http://ecappdev1/service/...")
```

Confirmed by `TestDirectorXMLRPCClient.valuesComplex()` (lines 60–78): `ECountCore.eDevice.Test.InterfaceServer = "ECAPPDEV1"`.

---

## 6. Known Service Consumers (Within This Codebase)

| Service | Director Key Used | Evidence |
|---|---|---|
| debit-api_API | `System\DataCredentials`, `System\DataEnvironment`, ECount Core service locations | `debitapi-boot/src/main/resources/config/director-client.yaml`; `ECountSystemConfiguration.java` `bootAddress` = Director URL |
| ECountCore.Profile | `Services\ECountCore.Profile` | `IDirectorClient.SERVICES_ECOUNTCORE_PROFILE_KEY` |
| StrongBox.RepositoryService | `Services\StrongBox.RepositoryService` | `IDirectorClient.SERVICES_SRONGBOX_REPOSVC_KEY` |
| ECountCore.eMember | `Services\ECountCore.eMember` | `IDirectorClient.SERVICES_ECOUNTCORE_EMEMBER_KEY` |
| ECountCore.eDevice | `Services\ECountCore.eDevice` | Confirmed in `valuesComplex()` test |
| Job/ETL services | `CoreServices\JobService\ETL` | `test.java` line 31 |

Director is effectively a **dependency of the entire Gen-2 platform**. Any service outage on Director propagates to all services that call it at startup or runtime.

---

## 7. Compliance Relevance

- **PCI DSS Req 3.5 / 8.6**: Director stores and distributes database credentials. The Director service itself must be treated as a credential store and protected accordingly. Access to Director must be restricted, audited, and TLS-protected.
- **PCI DSS Req 6.3 / 12.3**: The Director client uses Commons HTTPClient 3.x (deprecated); credentials in transit must be protected by current TLS standards.
- **NIST CSF 2.0 ID.AM**: Director is a critical asset for platform identity and access management.

---

## 8. Risks

| Risk | Severity | Detail |
|---|---|---|
| Single point of failure | Critical | All Gen-2 services depend on Director for credentials and service discovery; Director outage = platform outage |
| Credential values in test code | High | `TestDirectorXMLRPCClient.java` lines 52–101 contain expected credential return values — reviewed above; may represent real QA credential state |
| No authentication on Director calls | High | `DirectorXMLRPCClient` sends only `agent` string in header (line 94: `XMLRPCClientUtils.setRequestHeaders(agent, ...)`); no token/cert auth visible |
| Commons HTTPClient 3.x (deprecated) | High | `pom.xml` line 33; Apache Commons HTTPClient 3.x is EOL; known TLS issues |
| 5-second socket timeout | Medium | `DirectorXMLRPCClient` lines 87–89: `http.socket.timeout=5000`, `http.connection.timeout=5000`; Director slowness causes credential fetch failures |
| Exception swallowed on Director call | High | `DirectorXMLRPCClient.get()` line 117 catches ALL exceptions and logs at DEBUG level only; returns `null` silently — callers receive `null` credentials with no error indication |
| `IDirectorLocationAware` interface unused | Low | `IDirectorLocationAware.java` — setter/getter interface with no implementation in this repo; dead interface |
| `test.java` in main source | Low | `test.java` is in `src/main/java` (not `src/test/java`); GUI Swing test utility will be packaged in the JAR |
