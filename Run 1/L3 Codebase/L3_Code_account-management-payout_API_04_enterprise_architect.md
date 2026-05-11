# account-management-payout_API — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

This service is **Gen-2**. The evidence is:

- **Package namespace is `com.citi.prepaid`** — the historical Citi prepaid / eCount origin. Onbe-namespaced code (`com.onbe`) appears only in the thin `HealthCheck.java` class added post-migration.
- **Spring XML configuration** everywhere — no Spring Boot, no `@SpringBootApplication`, no `application.yml`. All wiring is through verbose XML files (`accountmanagementapi-implContext.xml`, `accountmanagementapi-wsContext.xml`, `appCtx-core.xml`, `validation.xml`, `validator.xml`).
- **Apache Axis 1.4 SOAP** (`jakarta-axis`, `jakarta-axis-wsdl4j`, `jakarta-axis-saaj`, `jakarta-axis-jaxrpc`) — Axis 1.4 reached end-of-life. This is a Gen-1-era SOAP stack that has been ported to Jakarta namespaces.
- **Spring Remoting / `ServletEndpointSupport`** — `AccountManagementApiWebServiceImpl extends ServletEndpointSupport` — deprecated Spring class removed in Spring 6; usage of `getWebApplicationContext().getBean(...)` (manual bean lookup from servlet context) is an anti-pattern.
- **Parent POM `prepaid-parent:6.0.12`** — shared Gen-2 parent POM.
- **eCount/CBase platform dependencies** — `xplatform:6.3.0`, `xsecurity-common/impl:4.0.3`, `xsearch-common/impl:4.0.1`, `xaffiliate-service:4.0.1`, `branded-currency-common/impl:3.0.3`, `job-common/impl:4.0.1`, `order-common:4.0.3` — these are all internal eCount platform libraries with no cloud-native equivalents.
- **Containerised deployment** (Dockerfile, docker-compose, AKS) — lift-and-shift from VM-based deployment to AKS, which is characteristic of a Gen-2 containerisation effort.
- **Version 3.x** — the `3.0.1-SNAPSHOT` version numbering suggests this is a third major release within the Gen-2 lineage.

The `.gitlab-ci.yml` still referencing Northlane-era pipelines and the hardcoded `wirecard.sys` endpoint in the WSDL are residual Gen-1 artifacts.

---

## Business Domain

**Prepaid Card Lifecycle — Cardholder Mobile Operations**

This service sits within the **Card Account Management** subdomain, specifically:
- Cardholder **self-service activation** of newly issued prepaid cards.
- **Identity verification** at point of activation (postal code check, KYC check).
- **PIN management** for prepaid cardholders.
- **Registration update** (name, address, PII) for cardholder self-service.

It is the backend for the mobile payout application's account management capabilities, bridging mobile clients and the CBase/eCount core platform.

---

## Role in Platform

| Role | Description |
|---|---|
| **API Gateway / Facade** for mobile | Acts as a SOAP service layer over the eCount/CBase platform. Handles input validation, encryption/decryption of DDA numbers, and orchestration of downstream calls. |
| **KYC Gate** | Intercepts activation status inquiries for KYC-required programs and enforces KYC completion before disclosing account status. |
| **Payout Mobile Enablement** | Enables the "payout" app to activate cards received by disbursement recipients (e.g. insurance claimants, healthcare refunds). |
| **Upstream of Order Service** | For registration updates, it feeds `ProcessSweepRequest` events to the Order Service JMS bus — the platform's transactional processing backbone. |

The service is a **consumer-facing edge service** with external APIM publication (`PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` in `deployment.yml`).

---

## Dependencies

### Upstream (consumers of this service)
- Mobile payout application (direct SOAP calls)
- Azure API Management (APIM) — publishes the WSDL externally

### Downstream (services this service calls)
| Service | Protocol | Notes |
|---|---|---|
| **eCore/eDevice** (CBase platform) | Legacy ECount RPC (`ECount.System.RPC`) | Card activation, account status inquiry, PIN set, DDA/member lookup |
| **Order Service** | JMS (`SynchronousOrderProcessor`) | Registration update and all disabled JIRA-476 operations |
| **JobSvc DB** | JDBC (SQL Server via HikariCP) | UserMapping lookup (partner_user_id ↔ emember_id) |
| **EcountCore DB** | JDBC (SQL Server via HikariCP) | FDR card detail, BIN/program lookup, KYC status table |
| **CbaseApp DB** | JDBC + Hibernate (SQL Server) | Affiliate metadata, security domains, user data |
| **KYC Portal** | HTTPS + MSAL | External third-party identity verification service |
| **api-security-lib** | In-process (`com.citi.prepaid.security`) | `AuthenticationCheckFilter`, `SecurityValidator`, `CandidateStore` |
| **xaffiliate-service** | In-process | Affiliate metadata queries (kyc_required flag, BIN/bank name) |

---

## Integration Patterns

1. **SOAP/Document-literal over HTTP**: The public API is SOAP 1.1 using document-literal binding (WSDL `wsdlsoap:binding style="document"`), served by Apache Axis 1.4 via the `AxisServlet` at `/services/*`.

2. **Spring AOP proxy chain**: The `accountManagementHandler` bean is proxied with `GlobalRequestIDInterceptor` (injects a UUID request ID into MDC) and `AuditMethodInterceptor` (call statistics). This is a classic Gen-2 Spring AOP cross-cutting concern pattern.

3. **Synchronous JMS request-reply**: `SynchronousOrderProcessor.processSweepRequest()` sends a `ProcessSweepRequest` JMS message and blocks waiting for a `ProcessSweepResponse`. Timeout results in a `PROCESSING` (code 2) status returned to the client.

4. **Stored procedure calls**: Database interactions use stored procedures directly via Spring `JdbcTemplate`-style stored proc wrappers (`FDRCardAccountDetailInquirySP`, `KYCStatusInsertUpdateSP`, `GetBankByProgramStoredProc`, `ProcGetAffiliateByValue`, `ProcGetAffiliatePresentation`).

5. **Hibernate ORM**: The `CbaseappDataSource` is also used with a Hibernate `LocalSessionFactoryBean` for affiliate and security domain entity reads (20 annotated classes wired in `accountmanagementapi-implContext.xml`).

6. **External HTTPS + MSAL**: KYC portal integration uses Microsoft Authentication Library (`kyc.ms.client.id`, `kyc.ms.client.secret`, `kyc.ms.authority`, `kyc.ms.scope`) for OAuth2 token acquisition before calling the KYC endpoint.

7. **JWE Encryption**: DDA numbers encrypted with JWE (Nimbus JOSE JWT, direct-encryption AES-256-GCM) for transit between mobile client and this service. Token includes timestamp for replay prevention.

8. **Config repo pattern**: External configuration files are managed in a separate Git repository (`OnbeEast/api-config-repo`) mounted at container startup. This is the Onbe config-as-infrastructure pattern.

---

## Strategic Status

**Operate / Maintain — Migration Target**

- The service is live and actively deployed to AKS QA, with GitHub Actions CI/CD and external APIM publication. It is in active operation.
- However, the dominant characteristic of the codebase is **scope reduction**: the JIRA-476 block comment disables the vast majority of the originally designed operations (12+ service methods). Only 3 operations are active: `activationStatusInquiry`, `activateCard`, `setPin`.
- The technology stack (Axis 1.4, Spring XML config, `ServletEndpointSupport`, eCount RPC) is legacy and not aligned with any Gen-3 REST/event-driven target architecture.
- The remaining three active operations are direct mobile-app dependencies, making near-term decommission unlikely without a Gen-3 replacement.
- **Assessment**: This service is a **stable legacy asset** providing critical mobile payout onboarding capabilities. It should be a **migration candidate** for a Gen-3 REST API replacement that retains the KYC gate and JWE-encrypted DDA pattern.

---

## Migration Blockers

1. **Apache Axis 1.4 SOAP interface**: All mobile clients use the SOAP WSDL contract. Migration to REST requires a client-breaking change or a parallel REST facade with SOAP adapter. The WSDL has been published to external APIM, suggesting external consumer dependencies.

2. **`ServletEndpointSupport` + manual bean lookup**: `AccountManagementApiWebServiceImpl` extends `ServletEndpointSupport` (removed in Spring 6) and does `getWebApplicationContext().getBean("accountManagementHandler")` — not injection-compatible. Must be redesigned for Spring Boot.

3. **eCount RPC dependency**: The PIN set and card activation operations call `ECount.System.RPC.rpcException`-throwing legacy RPC code. There is no REST/gRPC equivalent. Until eCore exposes a modern API, this is a hard blocker for any Gen-3 migration of those operations.

4. **Order Service JMS coupling**: `UpdateRegistrationService` constructs `ProcessSweepRequest` and `SweepRequest` objects tied to the eCount Order Service message format. This coupling must be broken or an adapter created.

5. **External configuration file dependencies**: All runtime properties are externally mounted from `api-config-repo` via file path. Migration to Kubernetes ConfigMaps/Secrets or a secrets manager (Azure Key Vault) requires infrastructure changes in addition to code changes.

6. **Disabled service methods (JIRA 476)**: The commented-out code for createAccount, addFunds, withdraw, assignPackage, createPackage, linkCard, etc. represents substantial technical debt. It is unclear whether these need to be reimplemented or formally decommissioned before any migration.

7. **KYC portal tight coupling**: KYC integration is embedded directly in `ActivationStatusInquiryService.java`. Extracting this into a dedicated KYC microservice would be necessary for a clean Gen-3 decomposition.

8. **Shared platform library versions**: Dependencies on `xplatform:6.3.0`, `xsecurity-common:4.0.3`, `branded-currency-impl:3.0.3`, etc. require the Gen-3 platform to provide compatible equivalents or migration adapters before this service can be re-platformed.
