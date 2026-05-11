# Director SVC — Enterprise Architect View

## 1. Platform Generation

Director SVC spans two platform generations simultaneously:

| Generation | Deployment | Data Store | Packaging | Active? |
|---|---|---|---|---|
| **Gen-1** | On-premises Windows (`d-na-app01`, `q-na-app12`) | Windows Registry (`HKLM\SOFTWARE\ECount`) | Tomcat WAR (`directory-webapp.war`) | Legacy — still referenced in `.gitlab-ci.yml` |
| **Gen-2** | AKS container | Azure App Configuration | Spring Boot fat-JAR (containerised) | Active — all current CI/CD targets `Directory-SpringBootApp` |

The codebase supports both simultaneously. `Directory-War` (WAR module) and `Directory-SpringBootApp` (Boot module) coexist in the same Maven multi-module build. The WAR uses `DirectoryImpl` (reads Windows registry); the Boot app uses `AzureDirectoryImpl` (reads Azure App Config). Both are compiled together.

---

## 2. Domain

Director SVC occupies the **Platform Infrastructure / Configuration Management** domain. It is not a business-domain service (it does not process transactions, manage cardholders, or compute balances). It is a **foundational infrastructure service** analogous to a service mesh's config plane or a secrets manager.

Domain boundaries in the `ECount` hierarchy:

| Domain | Director's Role |
|---|---|
| **Payments / Card Issuance** (`cbaseapp`, `ECountCore`) | Provides DB connection strings and credentials for the core card processing databases |
| **Job Processing** (`jobsvc`, `JOBSVC_BMC`) | Provides ETL script configurations, ETL handler class names, DB settings |
| **Notification / Event** | Provides server URLs and DB credentials for notification and event-handling services |
| **Reporting** | Provides server aliases and service routing for reporting services |
| **Security** (`StrongBox`, `xSearch`, `SecurityService`) | Provides server URLs for StrongBox (key management) and XSECURITY |
| **Repository / File Transfer** | Provides FTP host credentials, remote paths, and cryptography handler configurations |
| **Order Management** | Provides server URLs for the Order Service |

---

## 3. Role in the Platform — Load-Bearing Status

Director is the **single configuration nerve centre** for the Gen-1/Gen-2 platform. This is not an exaggeration:

- The test Spring context (`DataSources.xml`, lines 12–18) explicitly states: _"This file defines data sources to use in case that settings cannot be read from director. The `AbstractDataLibrary` will first attempt to dynamically create data source based on settings from director."_ This confirms Director is the primary path for every service's database connectivity.
- `DirectorServiceLocator` (referenced in `applicationContext.xml`, lines 19–77) is the client-side class used by every Gen-1 service to look up remote service endpoints. It takes a Director client reference as its first argument.
- The `Services/ECountService.Config/Default/InterfaceServer: LOCALHOST` entry in `appsettings.json` (line 656) means Director itself consults itself for its own `ECountService.Config` operation — i.e., even Director's self-description is bootstrapped from its own registry.

**Consequence**: Director is the first service that must be running before any other service can start correctly. It is the platform's configuration bootstrap dependency.

---

## 4. Dependencies

### Inbound (who calls Director)
Based on the pattern `DirectorServiceLocator` and `DirectorClientFactory.getClient(DirectorURL)`:
- All services that inject a `Director` bean via `DirectorClientFactory`
- Named callers visible in the test context: eMember service, eDevice service, eTransfer service, Profile service, and by extension every service listed in the `ECount/Services/` tree

### Outbound (what Director calls)
- **Gen-1**: Windows Win32 Registry API via JNA (`Advapi32`) — requires running on a Windows host with HKLM access
- **Gen-2**: Azure App Configuration service via `azure-data-appconfiguration` SDK

### Internal Module Dependencies
```
directory-springbootapp
  → directory-common (IDirectoryService, GetOutput, ConfigException)
  → directory-service (AzureDirectoryImpl, JNAWinUtil, DirectoryImpl)
  → com.citi.prepaid.service.core:xmlrpc (XmlRPCServlet, XmlRPCRequest, OutputBase, Result)
  → com.ecount.service.common:services-common (MapFromXML, ToStringUtility)
  → com.azure:azure-data-appconfiguration:1.3.0
  → com.azure:azure-identity:1.5.3
  → io.projectreactor:reactor-core:3.5.0
  → net.java.dev.jna:jna + jna-platform:5.13.0
```

**Key external dependency risk**: `com.citi.prepaid.service.core:xmlrpc` — this is an internal Citi/Wirecard-era artifact (group ID `com.citi.prepaid`). It defines the XML-RPC protocol, servlet, request/response base classes that the entire platform uses. Director cannot be re-packaged or replaced without also replacing this XmlRPC framework used by all callers.

---

## 5. Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| **Service Locator** | `DirectorServiceLocator` (client-side, not in this repo) | Director acts as the registry that the Service Locator pattern reads from |
| **Registry / Config Externalisation** | `IDirectoryService.get(key, agent)` | Classic Registry pattern; agent = environment/tenant selector |
| **Proxy / Façade** | `EDirectoryProxy` wraps `IDirectoryService` for XML-RPC exposition | One proxy, one service interface |
| **Reactive programming** | `AzureDirectoryImpl` uses Project Reactor (`Mono`, `Flux`) | But blocks with `.block()` at line 53 — reactive is used but benefits are negated by blocking call |
| **Strategy** | `IDirectoryService` interface with `DirectoryImpl` (Win registry) and `AzureDirectoryImpl` (Azure) implementations | Selected by Spring profile/module packaging |
| **XML-RPC remoting** | Custom `XmlRPCServlet` + `XmlRPCRequest` | Non-standard, internal-only protocol from the legacy Citi platform era |

---

## 6. Strategic Status

Director SVC is in **active migration** from Gen-1 to Gen-2:

- `JsonFlattener.java` and `RegistryToPropertiesConverter.java` are **one-time migration utilities** that convert Windows registry exports (`.reg` files) to a format importable into Azure App Config. Their presence in the source tree indicates the registry-to-Azure migration is ongoing or recently completed.
- The `addKeyValueFromFile()` method in `AzureDirectoryImpl.java` (lines 135–156) with its inline comment block (lines 201–207) describing manual preparation steps confirms a **manual migration workflow** was in use.
- The `AzureDirectoryImpl` main method (line 158) contains commented-out calls for testing individual key queries — a developer migration scratch pad, not production code.
- The Git tags present (`20250206.085001`, `20250206.085044`) both dated 2025-02-06 suggest the Gen-2 Azure App Config version was promoted around that date.
- Both the Tomcat WAR pipeline (GitLab CI, still present) and the Spring Boot AKS pipeline (GitHub Actions, active) co-exist, indicating the Gen-1 Tomcat deployment has **not yet been decommissioned**.

---

## 7. Migration Blockers to Decommission Gen-1 / Director Entirely

| Blocker | Detail |
|---|---|
| **Every service must be updated to not use Director** | All Gen-1 services use `DirectorServiceLocator` which calls Director for both service-endpoint resolution and DB-credential lookup. These callers must be refactored to a Gen-3 mechanism. |
| **Windows Registry data must be fully migrated** | The registry migration utilities exist, but the Gen-1 `HKLM\SOFTWARE\ECount` tree must be 100% replicated in Azure App Config and validated before the Windows Director instance can be turned off. |
| **`com.citi.prepaid.service.core:xmlrpc` dependency** | All callers and Director itself use the internal Citi/Wirecard XML-RPC library. Replacing the protocol is a prerequisite for eliminating Director's XML-RPC interface. |
| **Agent namespace model** | The `agent` parameter is embedded in every caller. A replacement config system must either honour the same agent namespace or require all callers to be changed simultaneously (a flag-day migration). |
| **Credential rotation process** | Once Director is eliminated, a replacement secrets-management process (e.g., Azure Key Vault, HashiCorp Vault) must be established with equivalent or better automation for each downstream service. |
| **DataSources/DataCredentials/DataEnvironment resolution chain** | The three-level indirection (credential → environment → datasource) built into the registry model must be replicated or simplified in any replacement. |
| **Fallback DataSources** | Some services have hardcoded fallback `DataSources.xml` beans. These would need to be audited and either migrated or removed as part of any transition. |
