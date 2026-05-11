# account-management-api_API — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-2 (migrating toward Gen-3)**

Evidence:
- The service retains a full Gen-2 WAR module (`accountmanagementapi-war`) with Apache Axis servlet, Spring XML context files (`accountmanagementapi-implContext.xml`, `accountmanagementapi-wsContext.xml`, `accountmanagementapi-sasiContext.xml`), JNDI datasources, and `web.xml` targeting Jakarta EE 6.0.
- A Spring Boot module (`accountmanagementapi-boot`) has been added alongside the WAR, producing an executable JAR with Docker/Kubernetes support — this is the Gen-3 target deployment form.
- Both packaging modes coexist in the Maven multi-module build and both are deployable (CI/CD pipelines support both WAR-to-Tomcat-VM and JAR-to-container paths).
- Gen-2 indicators: Apache Axis SOAP engine, `org.apache.axis.transport.http.AxisServlet`, manual Spring XML configuration, `allow-circular-references: true`, JNDI datasource references, Wirecard/NAM domain hostnames, `c-base` file path conventions on Windows VMs.
- Gen-3 indicators: Spring Boot 3.5.7, Java 21, Azure App Config, Azure Key Vault Managed Identity, containerized via Docker with Liberica OpenJRE Alpine, Dynatrace via Kubernetes injection.
- The `accountmanagementapi-sasi` module is commented out in the root POM, indicating further decomposition is in progress.

## Business Domain

**Prepaid Account Lifecycle & Disbursement Management**

This service is the primary programmatic interface for partner clients to perform account creation, funding, card management, and withdrawal operations for prepaid card products. It sits at the intersection of:
- **Card issuance** (createAccount with CardInput, linkCard, assignPackage, instantIssue)
- **Value loading** (addFunds, createBulkOrder)
- **Cardholder management** (updateRegistration, updateAccountStatus, setPin)
- **Disbursement** (withdraw via ACH, Check, and their void operations)
- **Inquiry** (cardInquiry, cvvInquiry, activationStatusInquiry, getBalance, getRequestStatus)

The service name includes `citi.prepaid` package namespace, indicating its Citi Prepaid origin. It is now operated under the Onbe brand (maintainer email `janaka.ranathunga@onbe.com` in Dockerfile).

## Role in Platform

**Central API Gateway for Partner-Facing Account Operations**

Position in the platform:
- Sits between **external partner integrations** (B2B SOAP clients) and **core processing engines** (ECount/xplatform Order Service, cbase/CreditCard system, Job Manager)
- Acts as a **security enforcement layer** — all operations are independently authorized via the `api-security-lib` `SecurityValidator` against named security domains and feature flags
- Acts as an **orchestrator** — `CreateAccountService` can trigger up to four downstream actions in one call: RegisterUser, AddFunds, IssueCard, LinkCard
- Acts as a **data aggregation layer** — assembles response from Order Service output, cbase card data, and UserMapping from Job Service
- The WSDL is published to **external API Management** (APIM) at `api-qa.onbe.io`, confirming this is a customer-facing API
- The `ProvisionServiceApiWebService` (separate interface in the same `accountmanagementapi-ws` module) handles provision-specific operations

Dependencies this service **provides to**:
- Partner client systems (direct SOAP consumers)
- Potentially internal portal systems (ClientZone — `executeWebRequest()` method in `CreateAccountService` referenced as "caters to Create Account requests from ClientZone")

## Dependencies

### Upstream (consumed by this service)

| Service / System | Type | Version / Config | Protocol |
|---|---|---|---|
| Order Service (`SynchronousOrderProcessor`) | Core transaction engine | `order-common:4.1.5`, `spring.cloud.azure` | HTTP Invoker (Spring Remoting) |
| Job Manager (`AgentCachingJobManagerClient`) | Account/UserMapping lookup | `job-common:4.0.1`, `job-impl:4.0.1` | HTTP Invoker |
| cbase (`DeviceManagerImpl`, `MemberManagerImpl`, `ECoreDevice`) | Card & member management | `xplatform:6.5.8`, `xplatformlibrary:4.2.0` | Internal library / TCP |
| Banker Service (`BankerServiceAPI`) | Balance retrieval | `banker-common:4.0.3` | HTTP Invoker |
| Director Service | xplatform director | `director-client:2.0.1` | HTTP |
| EcountCore DB | SQL Server | `mssql-jdbc:12.8.2.jre11` | JDBC |
| CbaseApp DB | SQL Server | `mssql-jdbc:12.8.2.jre11` | JDBC |
| JobSvc DB | SQL Server | `mssql-jdbc:12.8.2.jre11` | JDBC |
| Azure App Configuration | Config store | `spring-cloud-azure:5.23.0` | HTTPS |
| Azure Key Vault | Secret management | `spring-cloud-azure:5.23.0` | HTTPS |
| End Client Service | KYC relationship validation | `ENDCLIENT_SERVICE_URL` (runtime) | HTTPS REST (OAuth 2.0 client_credentials) |
| Azure AD (MSAL4J) | OAuth token provider | `msal4j:1.22.0` | HTTPS |
| Recipient Screening | OFAC/screening | `cms.op.url` (runtime) | HTTP |
| Redis Admin Cache Service | Caching | `redis.cacheservice.url` (runtime) | HTTP |
| BrandedCurrency | Branded currency support | `branded-currency-common:3.0.4`, `branded-currency-impl:3.0.4` | Library |
| xSearch | Search functionality | `xsearch-common:4.0.1`, `xsearch-impl:4.0.1` | Library |
| Spring Utils (JMS) | JMS utilities | `springutils-jms:3.1.0` | Library |

### Downstream (systems that call this service)
- Partner client systems via SOAP
- ClientZone portal (`executeWebRequest()` entry point)
- API Management (APIM) gateway proxies inbound traffic

## Integration Patterns

1. **SOAP/Document-Literal Web Service**: Primary integration pattern. Apache Axis serves the WSDL at `/services/AccountManagementApiWebServices`. Message serialization via Axis XML binding. Requests/responses are Java POJOs annotated or mapped via Axis.

2. **Spring HTTP Invoker (Remote EJB-style)**: All Order Service, Job Manager, and Banker Service calls use Spring's `SynchronousOrderProcessor` proxy over HTTP Invoker — a Spring-proprietary Java serialization-based RPC mechanism. This is a significant migration blocker (see below).

3. **OAuth 2.0 Client Credentials**: End Client relationship validation uses `EndClientOAuthTokenProvider` with thread-safe cached token management (`ReentrantLock`, token expiry with 60-second skew). Token endpoint: Azure AD `login.microsoftonline.com`.

4. **JDBC Stored Procedure**: `PromotionBelongToProgramSP` and `APIProcGetAffiliatePresentation` use Spring `StoredProcedure` pattern for database calls.

5. **AOP Proxy Chain**: `AccountManagementHandler` and `SecurityValidator` are wrapped in `ProxyFactoryBean` with `GlobalRequestIDInterceptor` and `AuditMethodInterceptor` interceptors — classic Spring AOP with named interceptors.

6. **Azure App Configuration with Push/Pull refresh**: Configuration is dynamically refreshed every 15 minutes via Azure App Config polling.

7. **Synchronous request-response with async polling support**: `SynchronousOrderProcessor.processSweepRequest()` may return `PROCESSING` status on timeout; clients are expected to poll `getRequestStatus`. This is a hybrid sync-async pattern.

## Strategic Status

**Active, business-critical, in-flight migration**

- This is a **high-value, high-risk service** — it is the primary partner-facing API for all prepaid account operations.
- It is **actively maintained**: version `3.1.8`, Java 21 migration complete, Spring Boot 3.5.7 adopted, Azure cloud-native config in place.
- The **Spring Boot module is production-ready in principle** but coexists with the WAR module, and CI/CD still supports dual-track deployment.
- The service is published to **external APIM**, confirming active partner usage and the impossibility of unilateral breaking changes.
- The `accountmanagementapi-sasi` module being commented out and the end-client feature flag (`isEndclientFeature.available: false`) suggest ongoing capability expansion work.

## Migration Blockers

1. **Apache Axis SOAP dependency**: `AxisServlet` is registered in Spring Boot via `WebConfiguration`, and `server-config.wsdd` is loaded from classpath. SOAP/Axis is deeply integrated — migration to REST or modern SOAP (CXF/JAXWS) requires rewriting all 18+ operations and coordinating with all partner clients.

2. **Spring HTTP Invoker for downstream services**: All calls to Order Service, Job Manager, and Banker use Spring HTTP Invoker (Java object serialization over HTTP). This is a deprecated Spring mechanism (removed in Spring 6) — however, it is still functioning via `SynchronousOrderProcessor` interfaces from `order-common:4.1.5`. Migration requires coordinating API changes across Order Service, Job Service, and Banker.

3. **JNDI DataSource references**: `AccountManagementApiConfiguration` still defines JNDI beans (`java:comp/env/jdbc/EcountCoreDataSource`, `java:comp/env/jdbc/CbaseappDataSource`) as fallback — though the Boot datasource auto-configurations are the active path. Removing JNDI safely requires verifying no live Tomcat WAR deployments use the old JNDI names.

4. **`allow-circular-references: true`**: This flag was introduced because of unresolved bean dependency cycles introduced during the Spring Boot migration. Until these are resolved, upgrading Spring Boot to future versions that may not support this flag could break startup.

5. **Wirecard/NAM CA Certificate**: The service imports `nam.wirecard.sys.crt` into the JVM truststore. If the Wirecard NAM infrastructure is decommissioned or the cert expires without a replacement, Order Service and core system connectivity breaks.

6. **cbase library dependencies**: `xplatform:6.5.8` and `xplatformlibrary:4.2.0` are internal ecount/cbase platform libraries with numerous exclusions. These are likely not available as public artifacts and bind the service to the ecount platform generation.

7. **BouncyCastle 1.60 (2018 release)**: Used in `JWEHelper`. This version has known CVEs and is very old. Upgrading requires verifying API compatibility with the Visa JWE implementation.

8. **Test mode infrastructure in production code**: `TestAPI` bean is wired into every service. This should be isolated to non-production profiles or removed before the service is considered "clean" for Gen-3.
