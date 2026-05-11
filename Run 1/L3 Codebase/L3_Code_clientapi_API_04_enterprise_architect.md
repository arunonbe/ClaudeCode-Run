# clientapi_API — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

This service exhibits a **mixed Gen-1/Gen-2 profile** with early Gen-3 infrastructure scaffolding:

**Gen-1 indicators (legacy):**
- Apache Axis 1.4 SOAP stack (generated WSDL2Java stubs, `javax.rmi.Remote` interfaces in `ClientApiWebService.java`; Axis was end-of-life in 2006)
- `SpringRemoting` / `ServletEndpointSupport` (`ClientApiWebServiceImpl extends ServletEndpointSupport`)
- XML-based Spring bean configuration for validators (`validationNA.xml`, `validationEMEA.xml`, `validation.xml`) using classic Spring DTD `spring-beans.dtd`
- `server-config.wsdd` (Axis Web Service Deployment Descriptor) at `clientapi-boot/src/main/resources/`
- `java.rmi.Remote` / `java.rmi.RemoteException` in service interface
- Auto-generated Axis boilerplate: `__equalsCalc`, `__hashCodeCalc` patterns in all domain classes (e.g., `UpdateRegistrationInput.java`, `AddFundsInput.java`)
- ECount proprietary service bus (`ECount.Common.ServiceConfig`, `ServiceObjectEx`, `SynchronousOrderProcessor`) still in use
- XStream serialization for HTTP Invoker (`XStreamMarshaller` in `OrderServiceConnectionConfiguration.java`)
- Jakarta servlet shim: `clientapi-ws/src/main/java/jakarta/servlet/http/HttpUtils.java` is a compatibility class to bridge Axis's use of the old `HttpUtils` API

**Gen-2 indicators (modernisation in progress):**
- Spring Boot 3.5.7 (`spring-boot.version` in root `pom.xml`) as the deployment container
- Java 21 compile target
- Docker + Kubernetes (AKS) deployment
- Azure App Configuration + Azure Key Vault for secrets management (MSAL4J `1.22.0`, `spring-cloud-azure-dependencies:5.23.0`)
- Spring Cloud `2025.0.0` BOM
- Log4j2 structured logging
- GitHub Actions CI/CD pipeline
- External APIM publishing
- Multi-module Maven project with enforced dependency management

**Gen-3 indicators (partial):**
- Azure Managed Identity authentication to Key Vault and App Config (`bootstrap.yaml`)
- Container-based deployment with Dynatrace APM injection
- No REST/OpenAPI layer yet — still SOAP-only

**Assessment**: The service is best described as a **Gen-2 service** — it has been lifted and containerised but the core technology (Axis 1.4, SOAP, RMI-based service interfaces, XStream serialization, ECount proprietary bus) remains Gen-1. Gen-3 migration would require a full rewrite of the API surface.

## Business Domain

**Domain**: Prepaid Card Account Management / Instant Issue Operations

**Sub-domain capabilities**:
- B2B client API gateway — accepts external corporate client requests
- Cardholder PII management (registration, address, SSN, DOB)
- Card funding (instant load)
- Card lifecycle management (account closure)
- ACH/DFI disbursement instrument provisioning
- International program routing

**Client-facing brand**: The production `wsdl.xml` references `northlane.com` and `mypaymentvault.com` payment vault URLs, and the App Config references the `B2C` payment director agent, indicating this service supports the Northlane/MyPaymentVault disbursement channel.

## Role in Platform

`clientapi_API` is the **external B2B API gateway** for card account management. Its role in the platform architecture:

```
Corporate Clients (Program Sponsors, Issuers)
        |
        | SOAP over HTTPS (external APIM)
        v
[clientapi_API]  <-- This service
        |
        | Spring HTTP Invoker / XStream
        v
OrderService (nam.wirecard.sys:9003)  -- core card processing engine
        |
        +-- cbaseapp DB (SQL Server) -- security + entity model
        +-- jobsvc DB (SQL Server)
        +-- ECount ServiceBus
        +-- Redis (international flags)
```

This service does NOT own any card accounts, transactions, or cardholder records — it is a **gateway and translator** that converts SOAP requests into internal `ProcessInstantIssueRequest` messages and relays them to the OrderService. It owns only the access-control data (cbaseapp) and does not persist any PII or transaction history directly.

## Dependencies

### Inbound (consumers of this service)
- External corporate clients via APIM (`client-api` suffix, external APIM only)
- No internal consumers identified in source

### Outbound (dependencies this service calls)
| Dependency | Artifact / Version | Purpose |
|---|---|---|
| `com.citi.prepaid.service.order:order-common:4.1.5` | Internal library | OrderService domain types, `SynchronousOrderProcessor`, `ProcessInstantIssueRequest/Response`, `OrderManagerException` |
| `com.citi.prepaid.security:api-security-lib:3.0.1` | Internal library | API security validation, entity management, IP/cert access control |
| `com.citi.prepaid.spring-dbctx:spring-dbctx-container:2.0.1` | Internal library | Spring DB context (likely multi-tenant DB context support) |
| `com.ecount:xplatform:6.5.8` | Internal library | ECount platform (ServiceConfig, ServiceObject, SAX parser pool, spring-utils) |
| `OrderService` (HTTP) | Runtime | Core card processing (add funds, update registration, account status, request status) |
| `cbaseapp` SQL Server | Runtime | Security entity store |
| `jobsvc` SQL Server | Runtime | Job service data |
| `Redis Admin Service` (HTTP) | Runtime | International program flag + country list |
| Azure App Config | Runtime | Configuration |
| Azure Key Vault | Runtime | Credentials |
| `nam.wirecard.sys` infrastructure | Runtime | All core backend services |

### Key internal library versions (from root `pom.xml`):
- Spring Boot: `3.5.7`
- Spring Cloud: `2025.0.0`
- Spring Cloud Azure: `5.23.0`
- MSAL4J: `1.22.0`
- MSSQL JDBC: `12.8.2.jre11`

## Integration Patterns

1. **SOAP over HTTPS (inbound)**: Apache Axis 1.4 SOAP engine exposing services at `/services/ClientApiWebServices` (V1), `/services/ClientApiWebServices/v2`, `/v3`, `/v4`. WSDL published to external APIM.

2. **Spring HTTP Invoker (outbound to OrderService)**: Java object serialization (XStream) over HTTPS. This is a Spring proprietary protocol, tightly coupling this service to the OrderService implementation. Not interoperable with non-Java clients.

3. **HTTP REST GET (outbound to Redis Admin)**: `InternationalFlagService` uses Java 11 `HttpClient` with no authentication for two endpoints. No circuit breaker or retry logic.

4. **JDBC (inbound to cbaseapp/jobsvc)**: Standard JDBC via Spring `DataSourceTransactionManager`.

5. **AOP-based interceptors**: `GlobalRequestIDInterceptor` and `AuditMethodInterceptor` wrap all service handlers as Spring AOP proxies for cross-cutting request tracking and auditing.

6. **Cache-based security**: `CacheEntityManager` loads all access control data into memory at startup (`initMethod = "load"`), with lazy dependencies to avoid circular initialisation issues.

## Strategic Status

**Status: Active / Maintenance with modernisation debt**

Evidence:
- Active CI/CD (5 deployment workflows, CodeQL scanning)
- Version `3.0.6-SNAPSHOT` indicates ongoing development
- Spring Boot 3.5.7 (released 2025) shows the infrastructure wrapper is being kept current
- `order-common:4.1.5` dependency is actively versioned
- V4 API (`deployment-v4.yml`) adds `region_id` and international routing — feature development is still occurring
- The V2/V3/V4 deployment workflows point to a `feature/VIST-1558_apim` branch (not `@main`), indicating in-flight APIM work

**Strategic concerns**:
- Axis 1.4 was end-of-life in 2006; it carries unresolvable CVEs (`CVE-2018-1000632`, `CVE-2020-10683` in allowedlist)
- The XStream HTTP Invoker pattern to OrderService creates tight Java-to-Java coupling that prevents independent evolution of either service
- No REST/JSON API exists; all clients are locked into SOAP/XML

## Migration Blockers

For a Gen-3 migration (REST/JSON, event-driven, cloud-native), the following blockers exist:

1. **Axis 1.4 SOAP framework**: Must be entirely replaced with a modern HTTP/REST layer (Spring MVC REST, Spring Web Services, etc.). All auto-generated WSDL2Java code (`ClientApiWebService.java`, all request/response classes in `clientapi-ws`) would need rewriting.

2. **Spring HTTP Invoker to OrderService**: The `SynchronousOrderProcessor` interface is called via Spring HTTP Invoker + XStream — a proprietary Java-only binary protocol. OrderService must expose a REST/gRPC/message-queue interface before this client can be modernised.

3. **ECount ServiceConfig / ServiceObjectEx**: `ECountSystemConfiguration.java` bootstraps the proprietary ECount service bus configuration. Replacing this requires equivalent configuration injection in the OrderService adapter.

4. **`xplatform` library dependency**: `com.ecount:xplatform:6.5.8` bundles multiple proprietary eCount components (SAX pool, spring-utils, service bus). This library has no public documentation and likely has no Maven Central equivalent.

5. **api-security-lib**: `com.citi.prepaid.security:api-security-lib:3.0.1` implements the IP/certificate access control and cbaseapp schema. Migration would require either consuming this library from a Gen-3 service or replicating the access control logic with a modern identity solution (OAuth2/mTLS).

6. **XML-based validator configuration**: `validationNA.xml`, `validationEMEA.xml`, `validation.xml` use Spring 2.x DTD XML format. These must be converted to code-based validators or replaced with Bean Validation (JSR-380) annotations.

7. **`jakarta.servlet.http.HttpUtils` shim**: The inclusion of `clientapi-ws/src/main/java/jakarta/servlet/http/HttpUtils.java` (a compatibility shim for Axis) would need removal in any migration.

8. **Circular reference and bean definition override flags**: `allow-circular-references: true` and `allow-bean-definition-overriding: true` in `application.yml` indicate architectural coupling that must be resolved before a clean modular Gen-3 design can be implemented.

9. **Dual deployment model (WAR + Boot)**: The coexistence of `clientapi-war` (legacy WAR for VM) and `clientapi-boot` (Spring Boot for K8s) means two parallel deployment tracks. Migration must consolidate to a single track.
