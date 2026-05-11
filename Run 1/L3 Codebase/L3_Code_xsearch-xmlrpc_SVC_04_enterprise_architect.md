# xSearch XML-RPC SVC — Enterprise Architect View

## 1. Role in the Platform Architecture

xSearch XML-RPC occupies a central position in the Onbe Gen-1 platform's operator tooling layer. It is the cardholder identity resolution service that sits between the CSA/Workbench front-end operator applications and the CDE (Cardholder Data Environment) database. Its architectural position makes it a shared service with platform-wide scope: any Gen-1 application that needs to look up a cardholder by any identifier routes through xSearch.

The service follows the classic Gen-1 architectural pattern: a Java WAR deployed on Tomcat, exposing XML-RPC over HTTP, with service location mediated through the Director service registry. This pattern is consistent across multiple Gen-1 services (xSecurity also uses XML-RPC; xSSO uses raw HTTP servlet).

## 2. Module Decomposition and Separation of Concerns

The Maven multi-module layout embodies a reasonable layered architecture:

```
xsearch-new (parent)
├── xsearch-common       Interface definitions + domain objects (shared)
├── xsearch-client       Consumer-side library (JAR for calling services)
├── xsearch-impl         Business logic + DAO layer (SQL Server queries)
└── xsearch-xmlrpc       WAR — servlet + XML-RPC proxy (server-side)
```

This separation means:
- **xsearch-client** can be versioned and distributed independently, allowing multiple consumers to use different versions of the client while the server evolves
- **xsearch-common** provides the canonical domain model shared between client and server, preventing divergent interpretations of `MemberInquiryValue`
- **xsearch-impl** encapsulates all database interaction, making it theoretically replaceable without changing the service interface

In practice, the architecture is partially undermined by the `EMember` interface's 24-parameter `find()` method, which couples client and server tightly to a specific search parameter schema. Adding a new search dimension requires changing the interface, the client, and the implementation simultaneously.

## 3. Integration Patterns

### Service Discovery Pattern
xSearch uses the platform Director service for dynamic endpoint discovery. The `SimpleXSearchServiceLocationResolvingCache` in the client resolves the service URL once per hour. This is a service registry pattern rather than DNS-based or Kubernetes-native discovery — appropriate for the Gen-1 on-premises environment but not idiomatic for cloud-native deployments.

### XML-RPC Protocol
The XML-RPC protocol choice reflects the Gen-1 era of the platform (early-to-mid 2000s technology). XML-RPC provides:
- Simple request/response semantics over HTTP POST
- Method dispatching via XML payload
- No built-in authentication, authorization, or encryption at the protocol level

The RPC interface is named `xSearch.xSearch` with method `FindMemberByMobilPhone` (note: "Mobil" without an 'e' is a legacy spelling consistent throughout the codebase). The server-side `XSearchXmlRPCServlet` extends `XmlRPCServlet` from `com.ecount.core.xmlrpc.servlet`, which is the platform-specific XML-RPC framework.

### Client Library Pattern
The `xsearch-client` module publishes a JAR to GitHub Packages. This is the preferred consumption pattern — consumers should import the client library rather than constructing raw XML-RPC requests. The `IXSearchClient` interface extends `EMember`, meaning the client presents the same search interface as the server-side implementation, and callers can swap between a direct implementation and the remote client without changing their code.

## 4. Service Dependencies

```
xSearch XML-RPC
├── xPlatform 6.1.8                    Platform runtime (Spring, DB context)
├── ecount-system 4.0.2                Core ecount domain objects
├── director-client 2.0.1              Service registry client
├── com.citi.prepaid.service.core:xmlrpc 3.0.2  XML-RPC framework
├── spring-dbctx-mock 2.0.1            Database context (mock — test use)
└── SQL Server (via mssql-jdbc 12.5.0) Data store
```

The README notes: _"Has dependencies on Core2 that need to be removed."_ Core2 (`ecount-system`) is an older platform generation. The continued dependency on Core2 is an architectural liability that couples xSearch to the Gen-1 data model and prevents independent evolution. This is flagged as a known migration task.

## 5. Enterprise Integration Concerns

### Single Point of Failure
xSearch is a synchronous, request-response service with no queuing, circuit breaker, or fallback pattern visible in the codebase. If the xSearch service or its database becomes unavailable, all dependent operator workflows fail synchronously. For a service used by customer service representatives handling live cardholder calls, this is a significant operational resilience gap.

### No API Gateway Integration at the Protocol Level
While `PUBLISH_TO_APIM: true` in the CI pipeline suggests the service descriptor is registered in the API Management platform, the XML-RPC protocol itself is not natively supported by modern API gateways (which generally work with REST/JSON or gRPC). The APIM registration likely describes the service for inventory purposes rather than providing actual gateway-mediated access control.

### Client Proliferation Risk
Because the `xsearch-client` JAR is published to GitHub Packages and any service can depend on it, there is a risk of multiple consuming services with different cached versions of the client making incompatible calls to the server. The 1-hour Director cache TTL means in a rolling deployment scenario, some clients may be talking to an old version of the server for up to one hour.

## 6. Fitness for Purpose vs. Strategic Direction

| Dimension | Current State | Strategic Direction |
|---|---|---|
| Protocol | XML-RPC (legacy) | REST/JSON or gRPC |
| Service discovery | Director registry (proprietary) | Kubernetes DNS / service mesh |
| Container support | None — WAR on Tomcat | Containerized, Kubernetes-deployed |
| Authentication | Agent identifier (implicit) | OAuth2 / mTLS |
| Observability | Log4j2 logs only | OpenTelemetry traces + metrics |

The service is architecturally aligned with the Gen-1 platform pattern but is not suited for the Gen-2 cloud-native target architecture without significant refactoring. The noted Core2 dependency removal is a prerequisite for any migration path.

## 7. Multi-Module Publishing and Versioning

The current version is `4.0.2-SNAPSHOT`. The `maven-enforcer-plugin` prohibits SNAPSHOT transitive dependencies from non-internal groups, but the project itself is in SNAPSHOT state. The CI pipeline's `UPDATE_DEPENDENCIES: true` and `UPDATE_PARENT_VERSION: true` flags mean automated dependency bumps can change the behavior of the service without developer intervention — a governance concern for a CDE-adjacent service.

## 8. Architectural Debt Register

| Item | Impact | Priority |
|---|---|---|
| Core2 dependency (noted in README) | Blocks modernization | High |
| XML-RPC protocol (no auth, no schema) | Security and interoperability | High |
| 24-parameter `find()` method | Interface design debt | Medium |
| EOL Apache Commons HttpClient 3.x | Security patching gap | Medium |
| No circuit breaker / resilience patterns | Availability risk | Medium |
| No Dockerfile | Cloud-native migration blocker | Medium |
