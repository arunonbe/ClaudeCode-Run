# Business Analyst View — xml-rpc-clients_LIB

## Business Purpose

xml-rpc-clients_LIB (`com.citi.prepaid.service.core:client:2016.1.1`) is the Gen-1 eCount/Citi inter-service communication library. It provides Java client stubs and DTO (data transfer object) classes that allow Gen-1 web applications and backend services to invoke eCountCore and supporting backend services over the XML-RPC protocol. XML-RPC is an HTTP-based remote procedure call protocol that encodes request and response bodies as XML — a technology standardized in the late 1990s and characteristic of the Gen-1 Citi-era Onbe platform architecture.

This library is the programmatic contract between consumer applications (cardholder portals, CSA tools, batch processes) and the core eCount backend services that manage prepaid card member records, fund transfers, device (card) creation, event rules, orders, security credentials, and profile data. Without this library, none of the Gen-1/Gen-2 OnePlatform applications can issue cards, load funds, look up members, or process orders against the eCountCore backend.

## Capabilities Provided

The library is a multi-module Maven project with seven sub-modules, each encapsulating a distinct eCountCore service domain:

- **directorClient**: Client for the Director configuration service — the Gen-1 service registry/service locator. `DirectorXMLRPCClient` resolves runtime locations of other services by querying Director for service endpoint URLs keyed by agent and service name. This is the bootstrap dependency: all other clients depend on Director to locate their target services.

- **ecountCoreClient**: The primary domain client module, providing XML-RPC clients and DTOs for:
  - **Member operations** (`MemberXMLRPCClient`): `AddBasic`, `AddExtended`, `AddUniversalRegistration`, `UpdateExtended`, `UpdateUniversalRegistration`, `UpdateSecureProfile`, `InquiryBasic`, `InquiryDefaultDevice`, `InquiryExtended`, `InquirySecureProfile`, `PUIDMemberSearch`, `UpdateAddenda` — full cardholder lifecycle management
  - **Device operations** (`DeviceXMLRPCClient`): `CreateDevice`, `DeviceInquiry`, `GroupCatalogInquiry`, `DeviceUpdate`, `Control` — prepaid card device management
  - **Transfer operations** (`TransferXMLRPCClient`): `Begin`, `Commit`, `Cancel`, `Inquiry`, `QuickLoad` — fund transfer lifecycle (three-phase: begin / commit / cancel)
  - **Event operations** (`EcountcoreEventXMLRPCClient`): `RuleCreate` — business event rule management
  - **CoreLite operations** (`CoreLiteXMLRPCClient`): `FastPayment` — expedited payment processing

- **profileClient** (`ProfileXMLRPCClient`): CRUD operations on cardholder profile data (class-based profile attributes, scope-based profile segmentation): `ClassCreate`, `ClassGet`, `ClassPut`, `ClassUpdate`, `ClassDelete`, `ClassDrop`, `ClassRetrieve`, `ClassSelect`, `ScopeCreate`, `ScopeRetrieve`, `ScopeUpdate`, `ScopeDelete`

- **eventServiceClient** (`EventXMLRPCClient`): Client for the eCount Event service: `EventDispatch` with `EventAction` enumeration — asynchronous business event dispatch

- **orderXMLRPCClient** (`OrderXMLRPCClient`): Order processing client: `CreateFileOrder`, `PostFileOrder`, `PostCompletedFileOrder`, `CancelOrder`, `ForceOrderStatus` — card order file lifecycle management

- **securityServiceClient**: Security service XML-RPC client (credential verification, PIN management)

- **strongBoxClient**: StrongBox service client (secure credential storage, key retrieval)

## Client/Cardholder Impact

This library is the API gateway for all cardholder-affecting operations in the Gen-1 platform. Defects in this library have direct cardholder impact:

- **Transfer Begin/Commit/Cancel**: Errors can result in fund loads that begin but never commit, leaving cardholders without accessible funds or with duplicate loads
- **Member AddBasic/AddExtended**: Errors block new cardholder enrollment
- **Device CreateDevice**: Card issuance failure — cardholders cannot receive physical or virtual cards
- **QuickLoad**: Rapid fund loading failure disrupts disbursement programs (insurance, healthcare, auto finance)
- **OrderXMLRPCClient**: Order file submission failure blocks bulk card order processing for client programs

## Business Rules Found in Code

- Director-based service discovery: all XML-RPC service endpoint URLs are resolved at runtime from Director; no service URLs are hardcoded in client code — this is an operational service mesh for the Gen-1 era
- Agent-scoped service lookup: all Director queries are scoped by `agent` parameter (e.g., "B2CTEST", "B2CTEMP"), enabling per-program service routing
- Three-phase transfer protocol: fund transfers follow Begin → Commit (or Cancel) lifecycle; partial execution without commit/cancel leaves transfers in an indeterminate state — the application layer is responsible for completion
- `QuickLoad` supports an overloaded form with `TransactionStrategy[]` array — suggests A/B processing strategies or multi-rail routing strategies for fund loading
- `PUIDMemberSearch` accepts a partner user ID (`lookupPartnerUserID`) as a cardholder lookup key — enabling partner-side member lookup without exposing internal member IDs

## Regulatory Obligations

- **PCI DSS Requirement 6**: All member, device, and transfer operations interact with cardholder account data; this library's transport layer (XML-RPC over HTTP) must use TLS (HTTPS) to protect cardholder data in transit per PCI DSS Req 4.2.1
- **Reg E**: Transfer operations (Begin/Commit/Cancel) are financial transactions subject to Regulation E; any transfer that begins but is not committed or cancelled may create a Reg E dispute obligation
- **GLBA**: Cardholder identity and financial data traversing XML-RPC calls must be protected; unencrypted HTTP XML-RPC channels are a GLBA violation

## Key Business Risks Found in Code

- **Version `2016.1.1` frozen in time**: Version identifier encodes a 2016 release year — this library has not had a version increment in approximately a decade. All XML-RPC protocol dependencies, Apache Commons HttpClient, and supporting classes are correspondingly aged
- **Apache Commons HttpClient (3.x)**: The `DirectorXMLRPCClient` uses `org.apache.commons.httpclient.HttpClient` (Commons HttpClient 3.x, EOL since 2011). Multiple CVEs affect this version. HTTP communication with no explicit HTTPS enforcement is a PCI DSS Req 4.2.1 risk
- **`log.info()` with combined PII fields in `puidMemberSearch()`**: Line 242 of `MemberXMLRPCClient` logs `agent + affiliate + programID + affiliateID + partnerID + lookupPartnerUserID` in a single concatenated log message. `lookupPartnerUserID` may constitute cardholder PII depending on program implementation
- **No retry or circuit-breaker logic**: XML-RPC calls have no retry mechanism; a transient Director or backend service failure results in immediate call failure with no resilience
- **Static shared `HttpClient` with `MultiThreadedHttpConnectionManager`**: The Director client uses a static shared connection pool with hardcoded limits (1000 max connections per host, 1000 total). If Director is unavailable, all threads block until timeout (1 minute connection timeout, 5 seconds socket timeout per method call). Thread starvation risk under Director outage
