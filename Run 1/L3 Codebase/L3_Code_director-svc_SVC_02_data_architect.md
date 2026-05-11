# Director SVC — Data Architect View

## 1. Data Stores

Director does not own a relational database. It is a **read-through façade** over two external configuration stores, depending on deployment generation:

### Gen-1: Windows Registry (HKEY_LOCAL_MACHINE)

- **Root**: `HKEY_LOCAL_MACHINE\SOFTWARE\ECount\`
- **Access mechanism**: Java Native Access (JNA) via `com.sun.jna.platform.win32.Advapi32` — Windows Win32 API calls `RegOpenKeyEx`, `RegQueryInfoKey`, `RegEnumValue`, `RegQueryValueEx`, `RegCloseKey`.
- **Implementation**: `JNAWinUtil.java` (`Directory-Service/src/main/java/com/ecount/directorysvc/util/JNAWinUtil.java`)
- **Data types**: `REG_SZ` (string) and `REG_DWORD` (integer). Strings are read into `char[]` buffers and converted with `com.sun.jna.Native.toString()`.
- **Access rights**: `WinNT.KEY_READ` is requested on every key open (line 61, 103, 174, 277, 375 in `JNAWinUtil.java`). No write operations are performed by the service at runtime.
- **Population method**: Historical manual registry exports (`.reg` files) translated via the `RegistryToPropertiesConverter` and `JsonFlattener` migration utilities (`Directory-Service/src/main/java/com/ecount/directorysvc/service/`).

### Gen-2: Azure App Configuration

- **Service**: Azure App Config (SDK `com.azure:azure-data-appconfiguration:1.3.0`)
- **Key namespace prefix**: `DirectorySVCAPI/ECount/` (set by `AzureDirectoryImpl.java:49` and the `app-config.yml` workflow which publishes with `AZURE_APP_CONFIG_PREFIX: "DirectorySVCAPI"`)
- **Access mechanism**: Reactive `ConfigurationAsyncClient` (Reactor/Netty). Key-value pairs are fetched with a wildcard prefix filter.
- **Authentication**:
  - Dev: `AZURE_APP_CONFIG_CONNECTION_STRING` environment variable (connection string = endpoint + HMAC key).
  - QA/Staging/Prod: Azure Managed Identity (`AZURE_MANAGED_IDENTITY_CLIENT_ID` + `AZURE_APP_CONFIG_ENDPOINT`).
- **Source of truth for QA config**: `app-config/qa/appsettings.json` — published to Azure App Config on every push to `main` via the `app-config.yml` GitHub Actions workflow.

---

## 2. Schema

There is no formal schema or DDL. The data model is a **hierarchical key-value tree** with the following observed namespaces (from `app-config/qa/appsettings.json`):

```
ECount/
  BulkServices/
    Main/Default/                   — thread pool, queue, retry params
    Queues/Default/                 — queue-name-to-batch-class mappings
  CBaseServer/
    BankOne/MQSeries/{env}/         — IBM MQ client IDs, queue managers, queue names
    CertAccountSvc/MSCS/{env}/      — payment pipeline file paths
  ClientApplications/
    Workbench/{env}/                — UI URLs (file upload/download endpoints)
    WorkbenchFileManager/Default/   — repository path
  CoreServices/
    JobService/Configuration/       — FilePath, MaxWorkers, sleep intervals
    JobService/ETL/{env}/{client}/{step}/ — per-client ETL script names and params
    RepositoryService/Configuration/{env}/ — FileRoot, FileTemp, SystemRoot paths
    RepositoryService/Cryptography/Default/{handler}/ — PGP/BTRADE handler classes + scripts
    RepositoryService/Hosts/Default/{alias}/ — FTP hostname, port, credentials, root paths
  Services/
    {ServiceName}.{Operation}/{env}/ — InterfaceServer alias, ServiceClass FQCN
  System/
    Configuration/{env}/            — LocalServer alias
    DataCredentials/{AGENT}/        — UserID, Password  *** SENSITIVE ***
    DataEnvironment/{AGENT}/        — logical-db-alias → DataSource-alias mappings
    DataSettings/{AGENT}/{db}/      — connection pool, timeout parameters
    DataSources/Default/            — connection string per DataSource alias *** SENSITIVE ***
    ServiceDirectory/{service}/{env}/ — ServiceProvider alias, ScriptCodeProvider, ScriptFileName
    Servers/Default/                — alias → HTTPS URL mappings
```

**Value types observed**: String (URLs, class names, script paths, usernames, passwords, connection strings), Integer (timeouts, thread counts, port numbers), Boolean-as-Integer (debug flags).

---

## 3. Sensitive Data Handling — Credentials as Data

Director's primary cargo IS sensitive data. The following credential categories are stored:

### Database Passwords (`ECount/System/DataCredentials/`)
- Found at lines 697–706 of `app-config/qa/appsettings.json`.
- Includes UserID + Password for agents: B2CSTAGE, BANKER, GREATPLAINS, NOTIFICATIONSVCSTAGE, WORKBENCHSTAGE.
- **Storage format**: Plaintext string values.
- **At-rest protection (Gen-1)**: Windows ACL on the registry key — no encryption.
- **At-rest protection (Gen-2)**: Azure App Config stores values as plaintext by default. Azure App Config does not encrypt individual values separately from its own platform-level encryption (AES-256 for data at rest in Microsoft's control). No customer-managed key (CMK) configuration is evident.
- **In-flight protection**: XML-RPC responses travel over HTTP in the Tomcat config (`server.xml` defines only port 80 HTTP with redirect to 8443, but no HTTPS connector is configured in the file). The QA `appsettings.json` `Servers` block does use `https://` for most service URLs.
- **In Git**: `app-config/qa/appsettings.json` containing QA passwords is committed to the repository. This is a PCI DSS Requirement 3 / Requirement 12.3 violation.

### Database Connection Strings (`ECount/System/DataSources/`)
- Found at lines 870–887 of `app-config/qa/appsettings.json`.
- Contains hostnames and SQL Server instance addresses (Q-LIS-DB01 through Q-LIS-DB04) with port 2231.
- Connection strings include `Initial Catalog` (database names) and provider details but **do not embed passwords** in the DataSources entries; passwords are separate in DataCredentials. Consuming services must combine DataEnvironment + DataCredentials + DataSources at runtime.
- **One exception**: Line 877 contains a Sybase connection string with a partial PWD field that appears blank: `PWD=` — this is the FDR ODS entry.

### FTP Passwords (`ECount/CoreServices/RepositoryService/Hosts/`)
- Found at lines 190, 199, 208, 218, 226 (and more) of `appsettings.json`.
- FTP credentials are stored as plaintext key-value pairs under the `RepositoryService/Hosts/Default/` sub-tree.
- These are noted as existing; specific values are not reproduced in this document.

---

## 4. Encryption

| Layer | Gen-1 (Registry) | Gen-2 (Azure App Config) |
|---|---|---|
| **At rest — application level** | None. Values are plaintext REG_SZ. | None. Values are plaintext strings in Azure App Config. |
| **At rest — platform level** | Windows NTFS/registry ACL only. | Azure App Config platform AES-256 (Microsoft-managed key, not CMK). |
| **In transit — service to Director** | HTTP (port 80) per `server.xml`. TLS redirect to 8443 configured but no HTTPS connector defined in `server.xml`. | HTTPS (Azure App Config SDK uses TLS by default). |
| **In transit — GitHub Actions to Azure App Config** | N/A | `app-config.yml` uses `secrets: inherit`; connection string or managed identity credentials are GitHub secrets — acceptable. |
| **Credential masking in logs** | None. `DirectoryImpl.java:74`: `log.get().info("DirectoryService: result=" + result)` logs the full resolved dictionary including passwords. | `AzureDirectoryImpl.java:92`: `log.info("DirectoryService: result={}", result)` — same risk. |

---

## 5. Data Flow (Read Path)

```
Caller (any Gen-1/2 service)
  → XML-RPC POST to /dispatch.asp
  → EDirectoryProxy.Get()
      → MapFromXML.map(xmlString)  — deserialise XML-RPC envelope
      → Extract {key, agentName} from Hashtable or plain String
      → IDirectoryService.get(key, agentName)

[Gen-1 path — DirectoryImpl.java]
  → prepend "SOFTWARE\\ECount\\" to key
  → traverseSubKey(HKLM, key, agent, emptyDict)
      → JNAWinUtil.readSubKeys(HKLM, key)       — RegEnumKeyEx
      → JNAWinUtil.readData(HKLM, key, agent)   — RegQueryValueEx for agent value
      → JNAWinUtil.readRegistryValues(HKLM, key) — read all name=data pairs
      → recursive descent into sub-keys
  ← Dictionary<String, Object> (may contain passwords if key includes DataCredentials)

[Gen-2 path — AzureDirectoryImpl.java]
  → rewrite key: backslash→slash, prefix "DirectorySVCAPI/ECount/"
  → ConfigurationAsyncClient.listConfigurationSettings(keyFilter=prefix+"*")
  → collectMap(key→value)
  → re-nest keys by splitting on "/"
  ← Dictionary<String, Object>

  → GetOutput.setValue(dict)
  → serialise as XML-RPC response
  → HTTP response to caller
```

---

## 6. Data Quality

- **No schema validation**: Keys and values are opaque strings. There is no type enforcement beyond the REG_DWORD / REG_SZ distinction in the Win32 API. Misspelled agent names silently return empty dictionaries.
- **No referential integrity**: A `DataEnvironment` entry that points to a non-existent `DataSources` key will cause the consuming service to fail with a null connection string at runtime, not at Directory query time.
- **Stale data risk**: The QA configuration is published from `app-config/qa/appsettings.json` via Git push. There is no change-management workflow or approval gate for credential rotation in this file.
- **Duplicate agent logic**: `traverseSubKey()` in `DirectoryImpl.java` implements a multi-step indirection (default value, named sub-key, or direct sub-key). If indirection chains are long or circular, the recursive descent has no depth limit and no cycle detection.

---

## 7. Compliance Gaps

| Requirement | Standard | Gap |
|---|---|---|
| Credentials must not be stored in source-code repositories | PCI DSS v4.0.1 Req 3.4 / 8.6 | `app-config/qa/appsettings.json` with plaintext passwords committed to Git. |
| Credentials must be encrypted at rest | PCI DSS Req 3.5 | Gen-1 Windows registry stores passwords as plaintext REG_SZ. No application-layer encryption. |
| Access to credential data must be logged | PCI DSS Req 10.2 | `EDirectoryProxy.Get()` has no audit logging of what key was requested or by whom. |
| Authentication to access secrets vault | PCI DSS Req 8 / NIST CSF PR.AC | XML-RPC endpoint `/dispatch.asp` requires no authentication. Any network peer can query `System\DataCredentials\*`. |
| Secrets rotation | PCI DSS Req 8.6.3 | No automated rotation. Manual updates to registry or `appsettings.json`. |
| Log masking of sensitive data | PCI DSS Req 3.4 | `DirectoryImpl:74` and `AzureDirectoryImpl:92` log resolved dictionaries at INFO level. |
