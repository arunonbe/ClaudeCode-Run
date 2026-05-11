# Director SVC — Business Analyst View

## 1. Business Purpose

Director SVC (`directoryservice`, artifact `com.ecount.service:directoryservice:3.0.1`) is the **platform-wide configuration and credential registry** for the entire Gen-1/Gen-2 prepaid-card platform. It is explicitly described in `README.md` as "an internal service, consumed by all the applications." Its job is to broker every service endpoint URL, database connection string, database credential, ETL-script configuration, MQ-series queue name, FTP host/credential, and encryption key reference that the platform's dozens of downstream services need at runtime. No downstream service manages its own connection strings; they all call Director.

The service was first authored in December 2010 (`@author OFSS`; OFSS = Oracle Financial Services Software, the original outsourced development vendor), making it a legacy core that has been running continuously for 15+ years.

---

## 2. Capabilities — What Director Serves

Director answers one fundamental query:

> **"Given a registry key path and an agent name, return all configuration key-value pairs that apply to that agent."**

The key namespaces found in `app-config/qa/appsettings.json` reveal the full scope of what Director serves:

| Namespace | What it Contains |
|---|---|
| `ECount/System/DataSources/` | OLEDB / JDBC connection strings for every SQL Server database in the platform (cbaseapp, ECountCore, jobsvc, strongbox, ordersvc, repositorysvc, notificationsvc, EcountBatchJobRepository, cf_report, vendor, etc.) |
| `ECount/System/DataCredentials/` | Per-agent database username + password pairs (existence confirmed at lines 697–706 of `appsettings.json`; values noted but not reproduced here) |
| `ECount/System/DataEnvironment/` | Mapping from agent name + logical database alias to the concrete DataSources entry (e.g., `B2CSTAGE/cbaseapp` → `cbaseapp.STAGE1A1`) |
| `ECount/System/DataSettings/` | JDBC/ADO timeout values, cursor locations, connection pool sizes per agent and database |
| `ECount/System/ServiceDirectory/` | Per-service, per-agent: which `ServiceProvider` (server alias) hosts that service; which COM/WSC script file implements it |
| `ECount/System/Servers/` | Canonical URL for every server alias (DIRECTOR, PPACORE, STRONGBOX, XSECURITY, JOBSVC, PROFILE, BATCH, PAYMENTSERVICE, NOTIFICATION_EVENT_HANDLER, REPOSITORY, J2JOBSVC, etc.) |
| `ECount/Services/` | Per-service interface routing: which `InterfaceServer` alias a named service uses |
| `ECount/CoreServices/` | ETL-script configurations for JobService (script paths, extra params, handler class names per ETL step and client) |
| `ECount/CBaseServer/` | IBM MQ Series queue names and connection parameters for BankOne |
| `ECount/BulkServices/` | Bulk-processing thread pool and queue parameters |
| `ECount/ClientApplications/` | UI application URLs |

**Downstream consumers confirmed by the test Spring context** (`Directory-Service/src/test/resources/applicationContext.xml`):
- `CoreMemberServiceLocator` (`Services\ECountCore.eMember`)
- `CoreDeviceServiceLocator` (`Services\ECountCore.eDevice`)
- `CoreTransferServiceLocator` (`Services\ECountCore.eTransfer`)
- `CoreProfileServiceLocator` (`Services\ECountCore.Profile`)
- Every other service that uses `com.ecount.core.client.locator.DirectorServiceLocator`

---

## 3. Entities / Data Model

Director has no database of its own. The entities it manages are purely configuration records stored externally:

| Entity | Description |
|---|---|
| **Key** | A backslash-delimited path within the `SOFTWARE\ECount\` registry tree (Gen-1 Windows) or under the `DirectorySVCAPI/ECount/` prefix in Azure App Config (Gen-2) |
| **Agent** | A named deployment context (e.g., `B2CSTAGE`, `WORKBENCHSTAGE`, `NOTIFICATIONSVCSTAGE`) that selects a sub-tree of configuration; roughly equivalent to a "tenant/environment" identifier |
| **Value Dictionary** | The resolved `Dictionary<String, Object>` returned for a (key, agent) pair; may be nested (sub-dicts) when the registry tree has sub-keys |
| **Server Alias** | A symbolic name (e.g., `PPACORE`, `DIRECTOR`) that resolves to a concrete URL |
| **DataSource Alias** | A symbolic name (e.g., `cbaseapp.STAGE1A1`) that resolves to a connection string |

---

## 4. Credential Provisioning Rules

### Gen-1 (Windows Registry — `DirectoryImpl`)
1. Callers supply a `key` (e.g., `System\DataCredentials\B2CSTAGE`) and an `agent` (e.g., `B2CSTAGE`).
2. `DirectoryImpl.get()` prepends `SOFTWARE\ECount\` to the key and calls `traverseSubKey()` against `HKEY_LOCAL_MACHINE` via JNA (`JNAWinUtil`).
3. The algorithm checks if the registry key for the given agent has a named value; if that value is itself a registry key (indirection), it follows it. If the agent maps to a sub-key by name, it reads all values under that sub-key. This allows multi-level indirection.
4. Credentials are stored as plain REG_SZ values in the Windows registry under `HKLM\SOFTWARE\ECount\System\DataCredentials\<AGENT>\UserID` and `...\Password`.
5. **There is no encryption of credentials at rest in the registry.** Any Windows account with HKLM read rights can read them.

### Gen-2 (Azure App Configuration — `AzureDirectoryImpl`)
1. Same `get(prefix, agent)` interface.
2. Prefix is rewritten: backslashes replaced with forward-slashes, then prefixed with `DirectorySVCAPI/ECount/`.
3. A `SettingSelector` with key filter `prefix + "*"` is sent to Azure App Config via a reactive `ConfigurationAsyncClient`.
4. Results are de-nested by splitting keys on `/`.
5. Credentials (if migrated to Azure App Config) are stored as plain-text key-value pairs. The `appsettings.json` file (`app-config/qa/appsettings.json`) contains credentials in clear text and is committed to the Git repository.
6. For dev profile, authentication uses `AZURE_APP_CONFIG_CONNECTION_STRING` env var. For QA/prod, authentication uses Azure Managed Identity (`AZURE_MANAGED_IDENTITY_CLIENT_ID` + `AZURE_APP_CONFIG_ENDPOINT`).

---

## 5. Request Flow

```
Downstream Service
  → DirectorClientFactory.getClient(DirectorURL)
  → XmlRPCServlet at /dispatch.asp or /service/dispatch.asp
  → EDirectoryProxy.Get(GetXMLRPCInput)
      → MapFromXML.map(xml) — parses XML-RPC input
      → IDirectoryService.get(key, agentName)
          [Gen-1] DirectoryImpl → JNAWinUtil → Advapi32 (Win32 registry API) → HKLM
          [Gen-2] AzureDirectoryImpl → ConfigurationAsyncClient → Azure App Config
      ← Dictionary<String, Object>
  ← GetOutput (result + value dict) serialised as XML-RPC response
```

---

## 6. Compliance Concerns

### PCI DSS (v4.0.1)
- **Requirement 3**: Database passwords and connection strings stored in Director are equivalent to system credentials that protect access to the Cardholder Data Environment (CDE). Under PCI DSS they must be protected with strong encryption at rest. The Windows registry stores them in plaintext (Gen-1), and `appsettings.json` stores them in plaintext in Git (Gen-2 QA).
- **Requirement 6.3 / 6.5**: Director is a bespoke internal service with no input sanitisation on the `key` or `agent` parameters (no validation in `DirectoryImpl.get()`, lines 58-60 only check for null). A malformed key navigates the HKLM registry tree arbitrarily.
- **Requirement 7 / 8**: There is no authentication on the XML-RPC endpoint. Any host that can reach Director's port can query any key, including credentials. There is no caller-identity check anywhere in `EDirectoryProxy` or `DirectoryImpl`.
- **Requirement 10**: Logging in `DirectoryImpl` logs `result=` at INFO level (line 74), which may log returned credential dictionaries to application logs.

### GLBA / Reg E
- Connection strings and credentials for systems that hold cardholder PII (cbaseapp, ECountCore, notificationsvc) flow through Director. Unauthorized disclosure of these credentials enables direct database access.

### NIST CSF 2.0
- Director constitutes a critical asset under the **Identify** function. Its compromise is equivalent to compromise of every downstream service's data store.

---

## 7. Business Risks

| Risk | Severity | Detail |
|---|---|---|
| **Complete platform outage on Director failure** | Critical | Every Gen-1/2 service that calls `DirectorServiceLocator` cannot start or resolve dependencies if Director is unavailable. There is no caching of resolved values in the client code shown. |
| **Credential exposure via log files** | High | `log.get().info("DirectoryService: result=" + result)` at `DirectoryImpl.java:74` may write credential dictionaries to application logs. |
| **No endpoint authentication** | Critical | XML-RPC endpoint `/dispatch.asp` has no authentication. Any network-reachable client can query `System\DataCredentials\*` for all agent passwords. |
| **Plaintext credentials in Git** | Critical | `app-config/qa/appsettings.json` contains plaintext database passwords for QA environment and is committed to the repository. This is a PCI DSS finding. |
| **Windows registry as credential store (Gen-1)** | High | HKLM-resident plaintext passwords are readable by any process running under a sufficiently privileged Windows account; no HSM or secrets management system is involved. |
| **Single-service blast radius** | Critical | Director is not replicated or load-balanced per the available deployment config; a single host failure removes the configuration plane for the entire platform. |
