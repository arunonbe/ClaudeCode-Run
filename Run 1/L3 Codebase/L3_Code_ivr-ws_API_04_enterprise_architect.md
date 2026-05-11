# Enterprise Architect Analysis — ivr-ws_API

## 1. Platform Generation and Classification

`ivr-ws_API` is an **in-flight modernization project spanning Gen-1 through Gen-3** characteristics:

- **Gen-1 core** (`ivrapi-ws` module): Apache Axis / JAX-RPC SOAP services, `com.cbase.business.*` platform APIs, Log4j 1.x, Spring XML configuration, auto-generated WSDL stubs from Apache Axis 1.2.1 (as documented in `CardDetail.java` header: "This file was auto-generated from WSDL by the Apache Axis 1.2.1 Jun 14, 2005").
- **Gen-2 packaging** (`ivrapi-war`): Standard WAR deployment with Tomcat context.xml JNDI datasources, Spring MVC servlet, still XML-configured.
- **Gen-3 packaging** (`ivrapi-boot`): Spring Boot 3.5.7, Java 21, Docker container, Azure App Configuration, Kubernetes deployment with Dynatrace, published to Azure APIM.

This three-layered module structure reflects a team that is **wrapping old SOAP logic in a new Spring Boot container** rather than rewriting the business logic. The `ivrapi-ws` service logic (`AccountBalanceInquiryServiceImpl`, etc.) remains essentially unchanged from the Gen-1 codebase — the Spring Boot module is an adapter/runner around it.

Package name inconsistency confirms the history:
- `ivrapi-ws`: package `com.ecount.one.ivr.*` (Ecount era)
- `ivrapi-boot`: package `com.citi.prepaid.ivrapi.*` (Citi prepaid era — the business was previously a Citi unit)

## 2. Role in Enterprise Architecture

```
External PSTN / IVR Telephony Vendor
    ↓ (SOAP via Azure APIM external endpoint)
Azure API Management (EXTERNAL_APIM: true)
    ↓ (WSDL: wsdl.xml)
ivr-ws_API (Spring Boot container, K8s)
    ↓ (JAX-RPC service impl)
Apache Axis SOAP endpoint layer
    ↓ (eCount XML-RPC via xplatform lib)
eCount Core XML-RPC Services
    ↓
cbaseapp DB | ecountcore DB (SQL Server)
```

The service is the **IVR telephony integration hub** for all cardholder self-service operations. All IVR interactions for balance, transactions, ACH, and mobile phone go through this service.

## 3. Multi-Rail Architecture Context

The `BrandedCurrencyConfig` in `ivrapi-boot` (imports `branded-currency-common`, `branded-currency-impl` per `pom.xml`) indicates this service also supports **branded currency / loyalty point balances** in the IVR, not just monetary prepaid balances. This is consistent with Onbe's multi-product platform (prepaid + incentives + loyalty).

## 4. Azure API Management Integration

`PUBLISH_TO_APIM: true` and `EXTERNAL_APIM: true` in `deployment.yml` means the WSDL (`wsdl.xml`) is published to Azure APIM as an external API. This makes the IVR service accessible via the public Azure APIM gateway, which handles:
- TLS termination (addressing the HTTP transport concern from the legacy config)
- API key management
- Rate limiting
- Monitoring

This is a significant architectural improvement over the legacy on-premises HTTP deployment. However, it introduces a dependency on Azure APIM availability.

## 5. Dependency on Legacy eCount Core

The service remains tightly coupled to the eCount Core platform via the `xplatform` library:
- `xplatform.version=6.5.2-SNAPHOT` (typo: should be SNAPSHOT) — note the snapshot version in the root POM
- `com.cbase.business.*` classes — cbase (core banking-as-a-service platform) APIs used directly in service implementations
- Director service for XML-RPC endpoint resolution

This coupling means:
1. The service cannot function without the eCount Core XML-RPC services running.
2. Migration to a new core platform (nexpay stack) requires replacing all `com.cbase.business.*` calls.
3. The `xplatform` library version mismatch (SNAPHOT vs SNAPSHOT) indicates build coordination issues.

## 6. WSDL and API Contract

`wsdl.xml` at repo root defines the public API contract. This is published to Azure APIM (external) for the telephony vendor to consume. Breaking changes to this WSDL would require coordination with the IVR telephony vendor. The WSDL is versioned as part of the project (`ivrws` v3.0.2).

## 7. Architectural Risks

### 7.1 SOAP-over-HTTPS via APIM
The service is SOAP-based. Modern IVR platforms increasingly use REST/JSON APIs. The IVR telephony vendor is locked to the SOAP contract defined in `wsdl.xml`. Migration to REST would require vendor coordination and IVR reconfiguration.

### 7.2 cbase Libraries in Container
`com.cbase.business.*` are proprietary eCount/cbase libraries compiled into the service. These are binary dependencies — not open source, not managed via public Maven repos. If these libraries have security vulnerabilities, patching requires internal library updates and rebuilds.

### 7.3 Wirecard CA Certificate in Container
`nam.wirecard.sys.crt` is bundled in the Docker image (`bindings/ca-certificates/`). This is a legacy Wirecard/Northlane PKI certificate. As Onbe migrates infrastructure away from legacy Wirecard hostnames, this certificate becomes irrelevant and its presence is a maintenance burden. When/if the cert expires, the container fails to connect to on-premises XML-RPC services.

### 7.4 `xplatform` SNAPHOT Dependency
`pom.xml` line 32: `<xplatform.version>6.5.2-SNAPHOT</xplatform.version>` — this is a typo (should be SNAPSHOT). Maven enforcer plugin (`requireReleaseDeps`) in the build is configured to fail on SNAPSHOT dependencies, but this one slips through because it's scoped as `${project.groupId}*` exclusion. Building against a SNAPSHOT dependency means the build is not reproducible.

## 8. Migration Complexity

**Estimated migration complexity: HIGH**

The wrapping of Gen-1 SOAP logic in a Gen-3 Spring Boot container is a tactical solution, not a strategic one. True modernization requires:
1. Replacing `com.cbase.business.*` XML-RPC calls with REST API calls to the nexpay platform.
2. Replacing SOAP/WSDL API contract with REST/OpenAPI.
3. Coordinating IVR vendor WSDL migration.
4. Re-implementing all business logic (balance inquiry, ACH setup, etc.) against new platform APIs.
5. Removing Log4j 1.x (present in legacy `ivrapi-ws` module).

The current `ivrapi-boot` approach buys time but does not reduce the long-term migration debt.
