# core-clients_LIB — Solution Architect View

## Technical Architecture

### Module Structure
```
core-clients_LIB/
├── pom.xml                          (root multi-module POM, groupId: com.citi.prepaid.service.core.client, v2.0.3-SNAPSHOT)
├── director-client/                 (service location + Director config retrieval)
│   └── DirectorXMLRPCClient        (HTTP POST to Director, static MultiThreadedHttpConnectionManager)
│   └── DirectorClientFactory       (static factory, DirectorClientTypes enum: XMLRPC only)
│   └── DirectorServiceLocator      (XMLRPCServiceLocator impl, in-memory URI cache with TTL + stale fallback)
│   └── IDirectorLocationAware      (interface: get/setDirectorAddress)
│   └── GetInput / GetOutput        (Director key-value DTOs)
├── ecount-core-client/              (depends on director-client)
│   └── CoreLiteXMLRPCClient        → ECountCore.coreLite / FastPayment
│   └── MemberXMLRPCClient          → ECountCore.eMember / 10 operations
│   └── DeviceXMLRPCClient          → ECountCore.eDevice / 8 operations
│   └── TransferXMLRPCClient        → ECountCore.eTransfer / 5 operations (Begin/Commit/Cancel/Inquiry/QuickLoad)
│   └── EcountcoreEventXMLRPCClient → ECountCore.Event / RuleCreate
├── profile-client/                  (depends on director-client)
│   └── ProfileXMLRPCClient         → ECountCore.Profile / 12 operations (ClassCreate/Delete/Drop/Get/Put/Retrieve/Select/Update + ScopeCreate/Delete/Retrieve/Update)
├── securityServiceClient/           (depends on director-client)
│   └── SecurityServiceXMLRPCClient → SecurityService.SecurityManager / SetUserManagementRequest
│   └── SecurityHierarchyServiceXMLRPCClient → SecurityService.HierarchyManager / SetHierarchyNodesRequest
├── eventServiceClient/              (depends on director-client)
│   └── EventXMLRPCClient           → EventService.Publish / EventDispatch (STUB — actual call commented out)
├── strongBoxClient/                 (depends on director-client)
│   └── StrongBoxXMLRPCClient       → StrongBox.RepositoryService / Read
└── orderXMLRPCClient/               (depends on director-client)
    └── OrderXMLRPCClient           → OrderService.OrderManager / CreateFileOrder, ForceOrderStatus, PostFileOrder, PostCompletedFileOrder, CancelOrderWithReason
```

### Inheritance Chain
All service clients extend `com.ecount.core.xmlrpc.client.XMLRPCClient` (from the `xmlrpc` transport library). The base class provides:
- `invokeXMLRPCCall(input, output, agent, methodName)` — standard dispatch
- `invokeXMLRPCCall(input, output, agent, affiliate, methodName)` — affiliate-scoped dispatch
- `invokeXMLRPCCall(input, output, agent, boolean, txId, methodName)` — txId-bearing dispatch (used by Security, Event, StrongBox)
- SLF4J `log` field (via Lombok in implementing classes)

The library does not own `XMLRPCClient`; it is provided by `com.citi.prepaid.service.core:xmlrpc:3.1.3-SNAPSHOT`.

## API Surface

### director-client
| Method | Signature | RPC Target |
|---|---|---|
| `get` | `Map<String,Object> get(String key, String agent)` | `ECountService.Config.Get` |
| `getAgentSetting` | `Map<String,Object> getAgentSetting(String key, String agent)` | Director registry (agent-fallback logic) |
| `getSerivceLocationURI` | `URI getSerivceLocationURI(String serviceDirectorKeyName, String serviceFriendlyName, String agent)` | Multi-step Director lookup |

### ecount-core-client — MemberXMLRPCClient
| Method | RPC Method |
|---|---|
| `inquiryBasic(agent, member)` | `ECountCore.eMember.InquiryBasic` |
| `inquiryDefaultDevice(agent, member, device)` | `ECountCore.eMember.InquiryDefaultDevice` |
| `addBasic(agent, affiliate, registration, addenda)` | `ECountCore.eMember.AddBasic` |
| `addExtended(agent, affiliate, registration, secure_profile, addenda)` | `ECountCore.eMember.AddExtended` |
| `updateExtended(agent, affiliate, member, registration)` | `ECountCore.eMember.UpdateExtended` |
| `inquiryExtended(agent, affiliate, member)` | `ECountCore.eMember.InquiryExtended` |
| `addUniversalRegistration(affiliate, registration, addenda, secureProfile, agent)` | `ECountCore.eMember.AddUniversalRegistration` |
| `updateUniversalRegistration(agent, affiliate, member, registration)` | `ECountCore.eMember.UpdateUniversalRegistration` |
| `updateSecureProfile(agent, affiliate, member, secureUserProfile)` | `ECountCore.eMember.UpdateSecureProfile` |
| `puidMemberSearch(agent, affiliate, partnerID, affiliateID, programID, lookupPartnerUserID, lookupEmemberID)` | `ECountCore.eMember.PUIDMemberSearch` |
| `inquirySecureProfile(agent, affiliate, member)` | `ECountCore.eMember.InquirySecureProfile` |
| `updateAddenda(agent, affiliate, member, addenda)` | `ECountCore.eMember.UpdateAddenda` |

### ecount-core-client — DeviceXMLRPCClient
| Method | RPC Method |
|---|---|
| `create(agent, affiliate, member, definition)` | `ECountCore.eDevice.Create` |
| `createDevice(agent, affiliate, member, createDeviceInput)` | `ECountCore.eDevice.Create` (extended options) |
| `inquiry(agent, affiliate, account, detail)` | `ECountCore.eDevice.Inquiry` |
| `ecardInquiry(agent, affiliate, account, detail)` | `ECountCore.eDevice.Inquiry` → `EcardDeviceInquiryOutput` |
| `eCheckInquiry(agent, affiliate, account, detail)` | `ECountCore.eDevice.Inquiry` → `ECheckDeviceInquiryOutput` |
| `inquiryTransaction(agent, affiliate, account, detail, options)` | `ECountCore.eDevice.Inquiry` (with AccountInquiryOptions) |
| `update(agent, accountDefinition)` | `ECountCore.eDevice.Update` |
| `control(agent, affiliate, account, method, options)` | `ECountCore.eDevice.Control` |
| `groupCatalogInquiry(agent, affiliate, member, group, deviceType, detailLevel)` | `ECountCore.eDevice.GroupCatalogInquiry` |
| `createandInquiry(agent, affiliate, member, definition, options, batch, plastic, detailLevel, inquiryOptions)` | `ECountCore.eDevice.CreateandInquiry` |

### ecount-core-client — TransferXMLRPCClient
| Method | RPC Method |
|---|---|
| `Begin(agent, affiliate, member, transaction, transfer)` | `ECountCore.eTransfer.Begin` |
| `Commit(agent, transfer)` | `ECountCore.eTransfer.Commit` |
| `Inquiry(agent, transfer, detailLevel)` | `ECountCore.eTransfer.Inquiry` |
| `Cancel(agent, transfer)` | `ECountCore.eTransfer.Cancel` |
| `QuickLoad(agent, tx)` | `ECountCore.eTransfer.QuickLoad` |
| `QuickLoad(agent, tx, strategy[])` | `ECountCore.eTransfer.QuickLoad` (with TransactionStrategy) |

### profile-client — ProfileXMLRPCClient (12 methods)
ClassCreate, ClassDelete, ClassDrop, ClassGet, ClassPut, ClassRetrieve, ClassSelect, ClassUpdate, ScopeCreate, ScopeDelete, ScopeRetrieve, ScopeUpdate — all targeting `ECountCore.Profile`.

### Other clients
- `CoreLiteXMLRPCClient.fastPayment(FastPaymentDefinition, agent)` → `ECountCore.coreLite.FastPayment`
- `EcountcoreEventXMLRPCClient.RuleCreate(agent, name, member, trigger, action, programId)` → `ECountCore.Event.RuleCreate`
- `EventXMLRPCClient.eventDispatch(EventDispatchInput)` → `EventService.Publish.EventDispatch` (STUB — call is commented out at line 50)
- `SecurityServiceXMLRPCClient.setUserManagementRequest(input)` → `SecurityService.SecurityManager.SetUserManagementRequest`
- `SecurityHierarchyServiceXMLRPCClient.setHierarchyNodesRequest(agent, requestFile, programId)` → `SecurityService.HierarchyManager.SetHierarchyNodesRequest`
- `StrongBoxXMLRPCClient.repositoryServiceRead(input, target)` → `StrongBox.RepositoryService.Read`
- `OrderXMLRPCClient`: CreateFileOrder, ForceOrderStatus, PostFileOrder, PostCompletedFileOrder, CancelOrderWithReason → `OrderService.OrderManager`

## Security Posture

### Authentication
- **Agent parameter** is the closest concept to an API key — it discriminates which Director subtree is used for settings. There is no OAuth2, JWT, API key header, or mutual TLS visible in this library.
- `XMLRPCClientUtils.setRequestHeaders(agent, interfaceName, methodName, postMethod, clientName)` is called on every Director request (line 95 of `DirectorXMLRPCClient`), but the implementation is in the external `xmlrpc` transport library and not visible here. The exact header names and values cannot be determined from this repository alone.

### Transport Security
- **All observed URLs use HTTP, not HTTPS**: `http://ecappdev/service/dispatch.asp` (`UsageExample.java` line 39), `http://ppamwdcddcor1/service/dispatch.asp` (`TestDirectorXMLRPCClient` line 22), `http://localhost:9001/service/dispatch.asp` (`DeviceXMLRPCClient.main()` line 256). No TLS configuration is present anywhere in the library.
- Apache Commons HttpClient 3.x does not support TLS 1.2 or 1.3 natively. This is the HTTP library used for all Director calls.

### Authorisation
- No authorisation checks in the library. The consuming server-side services are responsible for authorisation based on agent and affiliate parameters.

### Secrets
- Credentials (`System\DataCredentials\{agent}`) are retrieved from Director as plain-text key-value Map entries.
- `BulkUserRecord.password` is a plain String field, serialised as XML-RPC and transmitted without encryption.
- StrongBox (`StrongBoxXMLRPCClient.repositoryServiceRead()`) provides a lookup-by-reference pattern for retrieving secrets, but the secret value is returned as a generic `Object` with no encryption at the library layer.

### Skipped CVEs
The Azure container scan suppresses `CVE-2018-1000632` and `CVE-2020-10683` — both are dom4j XML external entity (XXE) and XML injection vulnerabilities. Since this library processes XML-RPC responses, these are directly applicable risk surface items.

## Technical Debt

| Debt Item | Location | Severity |
|---|---|---|
| EventDispatch is a no-op stub | `EventXMLRPCClient.eventDispatch()` lines 49-51 | High — silent data loss |
| Apache Commons HttpClient 3.x (EOL, no TLS 1.2/1.3) | `DirectorXMLRPCClient` imports | High |
| Exception swallowed with null return | `DirectorXMLRPCClient.get()` lines 120-123 | High — silent failure |
| PAN logged via `log.info()` | `DeviceXMLRPCClient.main()` line 304 | High — PCI DSS violation |
| Password as plaintext String | `BulkUserRecord.password` | High — PCI DSS / security |
| Raw types (`Vector`, `Dictionary`) | `BeginInput.transaction`, `EventDispatchInput.topic` | Medium — Java 1.4 era patterns |
| Hardcoded internal hostnames | `UsageExample.java`, `TestDirectorXMLRPCClient`, `DeviceXMLRPCClient.main()` | Medium |
| Integration tests as unit tests | `TestDirectorXMLRPCClient` — requires live Director | Medium |
| Tests skipped in CI | `github-package-publish.yml` `-Dmaven.test.skip` | Medium |
| SNAPSHOT dependency on XML-RPC transport | `xmlrpc:3.1.3-SNAPSHOT` | Medium — reproducibility |
| Main version in SNAPSHOT | `2.0.3-SNAPSHOT` | Medium — downstream stability |
| Typo in constructor string | `EcountcoreEventXMLRPCClient` constructor passes `"com.ecount.core.client.member.xmlrpc.TransferXMLRPCClient"` as the class name (line 56) — should be the Event client class name | Low |
| Same typo in TransferXMLRPCClient | Constructor passes `"com.ecount.core.client.member.xmlrpc.TransferXMLRPCClient"` (correct class but wrong package prefix pattern) | Low |
| `DeviceXMLRPCClient.main()` uses non-existent test member UUIDs | Lines 298-299 contain hardcoded GUIDs | Low |
| `Testing.java` in orderXMLRPCClient | Trivial `a+b` main method committed to source (`orderXMLRPCClient/.../Testing.java`) | Low |
| `UsageExample.java` uses Swing (AWT/Swing in a server library) | Lines 3-15, full Swing tree viewer | Low — dead code but increases JAR footprint |
| `DEFUALT_RESULT` (typo) | Every client class — `"DEFUALT_RESULT"` should be `"DEFAULT_RESULT"` | Low |

## Gen-3 Migration Requirements

The following changes are required to migrate consumers of this library to a Gen-3 architecture:

### Protocol Replacement
1. Replace all seven `XMLRPCClient` subclasses with REST (OpenAPI 3.x) or gRPC clients.
2. Eliminate `com.citi.prepaid.service.core:xmlrpc` dependency entirely.
3. Replace Apache Commons HttpClient 3.x with `java.net.http.HttpClient` (Java 11+) or Spring WebClient.

### Service Discovery Replacement
1. Replace `DirectorServiceLocator` + `DirectorClientFactory` + `DirectorXMLRPCClient` with a cloud-native service registry (e.g. Kubernetes DNS, AWS App Mesh, Spring Cloud Gateway routes).
2. Externalise all agent/affiliate routing as application configuration (Spring Config Server, AWS Parameter Store, or similar).

### Security Hardening (mandatory before Gen-3)
1. Enforce HTTPS for all service calls; reject HTTP endpoints.
2. Implement OAuth2 client credentials or mutual TLS for service-to-service authentication.
3. Remove `BulkUserRecord.password` as a String field; use a secure credential type or delegate password hashing to the security service.
4. Remove PAN logging from `DeviceXMLRPCClient.main()` or remove the main() method entirely.
5. Replace suppressed dom4j CVEs with an upgrade to a non-vulnerable XML library.

### API Contract Modernisation
1. Replace paired `*Input` / `*Output` POJOs with formally specified OpenAPI request/response schemas.
2. Add validation constraints (Bean Validation / Jakarta Validation) to all request DTOs.
3. Replace `Map<String,Object>` return types (Profile, Director) with typed domain objects.
4. Replace `Vector` (raw) and `Dictionary` (raw) with typed generic collections.

### Event-Driven Integration
1. Implement `EventXMLRPCClient.eventDispatch()` or its successor using a real message broker (Kafka, SQS, Azure Service Bus).
2. Define event schema using Avro/Protobuf/CloudEvents format.

### Observability
1. Add OpenTelemetry instrumentation to all client calls.
2. Emit structured logs (JSON) with correlation IDs, masking PII and card data.
3. Expose Micrometer metrics for call latency and error rates.

## Code-Level Risks

| Risk | File | Line(s) | Detail |
|---|---|---|---|
| Silent null return on Director failure | `DirectorXMLRPCClient.java` | 120-123 | `catch (Exception ex)` logs to debug and returns null; callers receive null Map with no exception |
| Event dispatch disabled | `EventXMLRPCClient.java` | 49-51 | `invokeXMLRPCCall` is commented out; `eventDispatch()` always succeeds with a fake txId |
| PAN in log statement | `DeviceXMLRPCClient.java` | 304 | `log.info("Result code:" + output.getDefinition().getCard().getNumber())` |
| HTTP-only Director connection | `DirectorXMLRPCClient.java` | 39-63 | Static initialiser creates plain `HttpClient` with no SSL context |
| 60s connection timeout | `DirectorXMLRPCClient.java` | 55 | `connectionManager.getParams().setConnectionTimeout(1000*60)` — one minute will stall calling threads |
| 1000 max connections per host | `DirectorXMLRPCClient.java` | 59-60 | Potentially exhausts OS sockets in high-concurrency environments |
| `assert false` in factory | `DirectorClientFactory.java` | 52 | If `DirectorClientTypes` gains new values, the factory silently returns null (asserts are disabled by default) |
| Constructor class name typo | `EcountcoreEventXMLRPCClient.java` | 56 | Passes `"com.ecount.core.client.member.xmlrpc.TransferXMLRPCClient"` as own class name |
| `BulkUserRecord.setPassword(String)` | `BulkUserRecord.java` | 16, 57-59 | Plaintext password setter with public getter |
| Allowed XXE CVEs | `.github/containerscan/allowedlist.yaml` | 4-5 | CVE-2018-1000632 and CVE-2020-10683 suppressed; XXE risk in XML-RPC response parsing |
| Live network tests committed | `TestDirectorXMLRPCClient.java` | 22 | `new URI("http://ppamwdcddcor1/service/dispatch.asp")` — will fail in any environment without internal network access |
| Stale README module list | `README.md` | 17-27 | TODO to include excluded modules never resolved; documents `2.0.0-beta` state, not current `2.0.3-SNAPSHOT` reality |
