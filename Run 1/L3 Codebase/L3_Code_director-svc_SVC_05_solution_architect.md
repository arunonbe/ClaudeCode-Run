# Director SVC — Solution Architect View

## 1. Full Architecture

Director SVC is a dual-mode Spring-based service — one mode reads from the Windows Registry, the other from Azure App Configuration — both exposing the same XML-RPC interface over HTTP.

```
┌────────────────────────────────────────────────────────────┐
│                      Gen-1 Deployment                      │
│  Tomcat 10 WAR — directory-webapp.war                      │
│                                                            │
│  HTTP :80/dispatch.asp                                     │
│    └── XmlRPCServlet (com.ecount.core.xmlrpc.servlet)      │
│          └── EDirectoryProxy (Directory-War)               │
│                └── DirectoryImpl                           │
│                      └── JNAWinUtil (JNA Advapi32)         │
│                            └── HKLM\SOFTWARE\ECount\       │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                      Gen-2 Deployment                      │
│  Spring Boot fat-JAR — directory-springbootapp-exec.jar    │
│  Docker / AKS — port 80                                    │
│                                                            │
│  HTTP :80/service/dispatch.asp                             │
│    └── XmlRPCServlet (registered via XmlrpcConfig)         │
│          └── EDirectoryProxy (Directory-SpringBootApp)     │
│                └── AzureDirectoryImpl                      │
│                      └── ConfigurationAsyncClient          │
│                            └── Azure App Configuration     │
│                                  (prefix: DirectorySVCAPI) │
│                                                            │
│  HTTP :80/hc  → HealthCheck (Spring @RestController)       │
└────────────────────────────────────────────────────────────┘
```

---

## 2. API Surface

### Protocol: XML-RPC over HTTP

Director does **not** use REST, SOAP, gRPC, or JNDI. It uses a proprietary XML-RPC protocol defined by the internal `com.citi.prepaid.service.core:xmlrpc` library.

| Endpoint | Module | Class | Notes |
|---|---|---|---|
| `POST /dispatch.asp` | Directory-War (Tomcat WAR) | `com.ecount.core.xmlrpc.servlet.XmlRPCServlet` | Legacy WAR path |
| `POST /service/dispatch.asp` | Directory-SpringBootApp | `com.ecount.core.xmlrpc.servlet.XmlRPCServlet` (registered via `XmlrpcConfig.java:17`) | Spring Boot path |
| `GET /hc` | Directory-SpringBootApp and Directory-War | `com.ecount.directorysvc.health.HealthCheck` | Returns plain `"OK"` |

### XML-RPC Call Convention

The XML-RPC request is handled by `EDirectoryProxy.Get(GetXMLRPCInput input)`:

```
Input:  GetXMLRPCInput extends XmlRPCRequest
          - input (String XML): either
              a) XML-encoded Hashtable with key "key" → String path
              b) XML-encoded String (plain key path)
          - agentName (String): agent/environment identifier

Output: 
  a) GetOutput extends OutputBase
          - result: Result(code, message)  [0="OK" on success]
          - value: Dictionary<String, Object>  [the config key-value map]
  b) Dictionary<String, Object>  [raw, for legacy J++ callers]
```

The XML-RPC method name registered in the `AppConfig` beans is **`"ECountService.Config.Get"`**:
- `@Bean("ECountService.Config.Get.Impl")` → `EDirectoryProxy` instance (`AppConfig.java:21-22`)
- `@Bean("ECountService.Config.Get.Input")` → prototype `GetXMLRPCInput` (`AppConfig.java:24-28`)

This naming convention is consumed by the `XmlRPCServlet` which maps incoming XML-RPC method calls to Spring beans by name.

### Health Check
- `GET /hc` — returns HTTP 200 with body `"OK"` (`HealthCheck.java:8-10`).
- Spring Actuator health endpoint also mapped to `/hc` via `management.endpoints.web.path-mapping.health=hc` (`application.properties:8`).

---

## 3. Security Posture — Director IS the Credential Vault

Director is architecturally equivalent to a secrets vault. This creates the following security surface:

### Authentication (Incoming)
**There is no authentication on the XML-RPC endpoint.**

`EDirectoryProxy.Get()` (`EDirectoryProxy.java:62`) receives `GetXMLRPCInput` and immediately processes it. There is no:
- API key or bearer token check
- mTLS client certificate validation
- IP allowlist enforcement (not configured in `server.xml` or Spring Security)
- Basic Auth

Any host that can reach Director on port 80 can query `System\DataCredentials\<ANY_AGENT>` and receive database passwords in the XML-RPC response. This is a **critical, unauthenticated access to credentials** path.

### Authentication (Outbound — Azure App Config, Gen-2)
- Dev: HMAC-based connection string via env var `AZURE_APP_CONFIG_CONNECTION_STRING`
- QA/Prod: Azure Managed Identity via `AZURE_MANAGED_IDENTITY_CLIENT_ID`
- `AzureConfig.java` correctly throws if required env vars are absent (lines 28-29, 43-45)

### Transport Security
- Gen-1 Tomcat: HTTP only on port 80 per `server.xml`. No TLS connector defined. XML-RPC payload (including credential dictionaries) travels in plaintext on the wire unless TLS is terminated upstream.
- Gen-2 Spring Boot: HTTP on port 80 inside the container; TLS presumably terminated at the AKS ingress. The container itself does not terminate TLS.

### Credential Exposure in Logs

`DirectoryImpl.java:74`:
```java
log.get().info("DirectoryService: result=" + result);
```
This line logs the full resolved `Dictionary<String, Object>` at INFO level. If the query was for `System\DataCredentials\B2CSTAGE`, this line writes `{UserID=b2cstage, Password=<plaintext>}` to the application log. Same pattern exists in `AzureDirectoryImpl.java:92`.

`EDirectoryProxy.java:53-55`: Constructor logs at INFO and ERROR on instantiation — benign but indicates the log channel is open.

### Input Validation
`DirectoryImpl.get()` at lines 58-60:
```java
if(key == null || agent == null){
    return new Hashtable();
}
```
Only null checks. No:
- Length limits
- Character whitelist (no control against path traversal within the registry tree)
- Agent name validation against a known-good set

An attacker supplying arbitrary `key` values could traverse to registry keys outside the intended `SOFTWARE\ECount\` subtree if the prefixing in `DirectoryImpl.java:67` (`key = "SOFTWARE\\ECount\\" + key`) is not considered sufficient isolation. The prepend is hard-coded, but there is no guard against relative-path components like `..` in the key string (though Windows registry does not support `..` traversal, the lack of validation is a defence-in-depth gap).

---

## 4. Technical Debt

| Item | File / Location | Severity | Detail |
|---|---|---|---|
| **Hard-coded developer paths** | `JsonFlattener.java:15,21`; `RegistryToPropertiesConverter.java:14,15` | High | Hard-coded local developer paths (`C:\Users\ATadigiri\Desktop\...`) in committed source files. These are migration utilities, not production code, but they reveal developer machine names and should not be in the main source tree. |
| **`DirectoryImpl` instantiates `JNAWinUtil` directly** | `DirectoryImpl.java:43` | Medium | `private IWinRegsitryUtil winUtil = new com.ecount.directorysvc.util.JNAWinUtil();` — bypasses Spring DI. The commented-out line above it (`//private IWinRegsitryUtil winUtil;`) shows the intent was DI. The direct instantiation prevents mocking in unit tests and makes the Gen-2 build carry unnecessary Win32 code. |
| **`@Component("directoryService")` name collision** | `DirectoryImpl.java:32`; `AzureDirectoryImpl.java:29` | High | Both classes declare `@Component("directoryService")`. This will cause a Spring bean-definition conflict if both modules are on the classpath. Only one can win. The Spring Boot app silently uses whichever Spring registers last. This is an uncontrolled coupling risk. |
| **Blocking call in reactive chain** | `AzureDirectoryImpl.java:53` | Medium | `.block()` called on a Reactor `Mono` inside a servlet thread. Project Reactor is used for the Azure SDK calls but its benefit is negated by the blocking wait. Under high concurrency this can exhaust the thread pool. |
| **`Vector` (raw type) usage** | `EDirectoryProxy.java:66` | Low | `Vector vResult = (Vector)MapFromXML.map(...)` — raw (unchecked) type, deprecated collection class. A legacy artifact of the 2010 codebase. |
| **Triple duplicate Javadoc block** | `ConfigException.java:5-47` | Low | The `ConfigException` class has the same Javadoc block duplicated three times, indicating copy-paste from the original generation. No functional impact but signals the code was never properly reviewed. |
| **Recursive `traverseSubKey` with no depth limit** | `DirectoryImpl.java:90` | Medium | No maximum recursion depth. A deeply nested or circular registry key structure could cause a `StackOverflowError`. |
| **`jakarta.servlet.http.HttpUtils` re-implemented** | `Directory-War/src/main/java/jakarta/servlet/http/HttpUtils.java` | Medium | A full `HttpUtils` class is committed in the `jakarta.servlet.http` package — this is a class that was removed from the Jakarta Servlet API. Rather than updating dependencies, the team copied the class verbatim into the project in the standard library package namespace. This is a namespace pollution anti-pattern that can cause classloader conflicts. |
| **`appsettings.json` with credentials in Git** | `app-config/qa/appsettings.json` lines 697-706, 190+ | Critical | QA plaintext passwords are committed to the repository. PCI DSS finding. |
| **Suppressed CVEs in container scan** | `.github/containerscan/allowedlist.yaml` | Medium | 13 CVEs are permanently suppressed, including Spring Web (`CVE-2024-22259`, `CVE-2024-22262`, `CVE-2024-38816`) and Jackson (`CVE-2020-36518`, `CVE-2021-46877`, `CVE-2022-42003`, `CVE-2022-42004`). Some of these have high/critical CVSS scores. |
| **`azure-data-appconfiguration:1.3.0` (2022)** | `Directory-Service/pom.xml:63-67` | Medium | SDK is over 3 years behind current. May contain resolved CVEs and lack newer features. |
| **`startup.sh` does nothing** | `Directory-SpringBootApp/startup.sh` | Low | Contains only `echo "SPRING_PROFILES_ACTIVE=$SPRING_PROFILES_ACTIVE"`. Placeholder that was never populated. |
| **Test DataSources.xml contains credentials** | `Directory-Service/src/test/resources/DataSources.xml:26-28` | Medium | Test resource contains a DataSource with explicit username and password values for a development SQL Server. Credentials committed to repository (test-only but still a risk). |
| **Pact/contract testing skipped** | `deployment.yml:27` | Low | `VERIFY_PROVIDER_PACT: false` — contract tests against downstream consumers are disabled. Breaking API changes cannot be detected automatically. |

---

## 5. Gen-3 Migration Requirements

To replace Director in a Gen-3 architecture, the following must be addressed:

### 5.1 Replace the Credential Vault Function
- **Recommendation**: Azure Key Vault or HashiCorp Vault as the secrets back end.
- **Migration step**: Audit all `ECount/System/DataCredentials/` entries in `appsettings.json`, rotate all passwords during migration, and store them in the vault. Remove `app-config/qa/appsettings.json` credentials from Git.
- **Blocker**: Vault must support the same per-agent credential model or all callers must be updated.

### 5.2 Replace the Service Registry Function
- **Recommendation**: Kubernetes Service DNS + environment-specific `ConfigMap`s for service URLs, replacing the `ECount/System/Servers/` and `ECount/Services/` trees.
- **Migration step**: Remove `DirectorServiceLocator` from all client services. Replace with Spring `@Value` or Spring Cloud Config injection.

### 5.3 Replace the DataSources/DataEnvironment Function
- **Recommendation**: Spring Boot `DataSource` auto-configuration with per-environment `application-{profile}.yaml` + Azure Key Vault references. Or a connection pool manager like HikariCP with vault-backed credentials.
- **Migration step**: Each service must own its datasource configuration rather than delegating to Director.

### 5.4 Replace the XML-RPC Protocol
- **Blocker**: `com.citi.prepaid.service.core:xmlrpc` is used by every caller and by Director. Eliminating Director requires eliminating this library from all callers simultaneously or providing a bridge.
- **Recommendation**: A lightweight REST or gRPC config API can act as a bridge during transition. Callers are migrated service-by-service.

### 5.5 Replace ETL Script Configuration
- **Recommendation**: Move `ECount/CoreServices/JobService/ETL/` entries to service-owned configuration (e.g., YAML files bundled with each ETL service or mounted as ConfigMaps).

### 5.6 Eliminate the Agent Model
- The `agent` parameter (e.g., `B2CSTAGE`, `WORKBENCHSTAGE`) is a multi-tenant environment selector embedded across hundreds of registry keys. In Gen-3, this should be replaced by Kubernetes namespace + environment-specific Helm values or Azure App Config labels (the labels feature of Azure App Config is a direct replacement for the agent model).

### 5.7 Remove Windows Registry Dependency
- `JNAWinUtil.java` requires a Windows host with HKLM access. This is incompatible with Linux containers. The Gen-2 AKS deployment already avoids this by using `AzureDirectoryImpl`. Gen-1 decommission unblocks full Linux containerisation.

### 5.8 Address the `@Component("directoryService")` Name Conflict
- Before any further Gen-2 work, the bean naming collision between `DirectoryImpl` and `AzureDirectoryImpl` must be resolved (e.g., rename Gen-1 bean, use `@ConditionalOnProperty`, or separate them into distinct modules with explicit `@Primary`).

---

## 6. Code-Level Risks Summary

| Class | File | Line | Risk |
|---|---|---|---|
| `DirectoryImpl` | `Directory-War/.../service/DirectoryImpl.java` | 67 | Prefix `SOFTWARE\\ECount\\` added to caller-supplied key — no validation of key content |
| `DirectoryImpl` | `Directory-War/.../service/DirectoryImpl.java` | 74 | `log.get().info("DirectoryService: result=" + result)` — may log credentials at INFO |
| `DirectoryImpl` | `Directory-War/.../service/DirectoryImpl.java` | 90 | `traverseSubKey()` — unbounded recursion, no depth guard |
| `AzureDirectoryImpl` | `Directory-SpringBootApp/.../service/AzureDirectoryImpl.java` | 53 | `.block()` on Reactor Mono in servlet thread — thread-pool exhaustion risk |
| `AzureDirectoryImpl` | `Directory-SpringBootApp/.../service/AzureDirectoryImpl.java` | 92 | `log.info("DirectoryService: result={}", result)` — may log credentials at INFO |
| `EDirectoryProxy` | Both modules | 62 | `Get()` method — no caller authentication, no rate limiting |
| `JNAWinUtil` | `Directory-Service/.../util/JNAWinUtil.java` | 38 | `byte[] lpData = null` — class-level mutable field used across `readData`, `readRegistryValues`, `readSubKeys` without synchronisation; in a multi-threaded Tomcat environment this is a thread-safety hazard |
| `AppConfig` (War) | `Directory-War/.../config/AppConfig.java` | 19 | `@Autowired EDirectoryProxy eDirectoryProxy` as field — potential circular dependency or eager init issue |
| `PropertyConfig` | `Directory-War/.../config/PropertyConfig.java` | 19-22 | Reads `CBASE_HOME_URL` env var; silently returns `null` configurer if env var is absent (line 26 catches exception but returns `null`), which may cause property placeholders to remain unresolved at startup |
| `HttpUtils` | `Directory-War/src/main/java/jakarta/servlet/http/HttpUtils.java` | all | Class declared in `jakarta.servlet.http` package in the project source — pollutes the standard namespace; classloader may prefer this over the container's version |
| `JsonFlattener` | `Directory-Service/.../service/JsonFlattener.java` | 15, 21 | Hard-coded developer desktop paths (`C:\Users\ATadigiri\Desktop\...`) in main source |
| `RegistryToPropertiesConverter` | `Directory-Service/.../service/RegistryToPropertiesConverter.java` | 14-15 | Same hard-coded developer paths |
| `DataSources.xml` (test) | `Directory-Service/src/test/resources/DataSources.xml` | 26-28 | Test datasource bean with username/password values committed |
| `appsettings.json` | `app-config/qa/appsettings.json` | 697-706, 190+ | Plaintext credentials committed to Git — PCI DSS violation |
