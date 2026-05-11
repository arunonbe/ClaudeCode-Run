# accept-prechecks_API — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 / Gen-2 hybrid in active migration.**

Evidence supporting this classification:

| Indicator | Evidence |
|---|---|
| SOAP/RPC-encoded web service (Gen-1 pattern) | Apache Axis 1.x, JAX-RPC, SOAP encoded style (`use="encoded"`) in `AcceptPrecheckService.wsdl` |
| Request/Response classes auto-generated from WSDL | `AcceptPrecheckRequest.java` header comment: "This file was auto-generated from WSDL by the Apache Axis 1.4 Apr 22, 2006" |
| XML-based Spring configuration (Gen-1) | `applicationContext.xml`, `server-config.wsdd`, `web.xml` still present and in use for WAR module |
| Dual packaging (WAR + Boot JAR) | `accept-prechecks-war` (Tomcat) and `accept-prechecks-boot` (Spring Boot / K8s) coexist |
| Spring Boot 3.5.7 + Azure integration (Gen-3 pattern) | `accept-prechecks-boot` uses Spring Boot autoconfiguration, Azure App Config, Key Vault, Managed Identity |
| Kubernetes deployment | `deployment.yml` deploys to AKS via `om-ci-setup/java-workflow.yml`; `redeploy.yaml` targets AKS |
| Jakarta EE namespace migration done | `web.xml` uses `jakarta.ee/xml/ns/jakartaee` v6.0; `jakarta.servlet` imports in Java code |
| Legacy GitLab CI pipeline still present | `.gitlab-ci.yml` targets on-premises Tomcat hosts (`d-na-app02`, `q-na-app01/02`) |

The boot module is the **active delivery path** (GitHub Actions deploys the boot JAR to AKS). The WAR module and GitLab CI pipeline are legacy artefacts that have not been removed.

## Business Domain

**Domain**: Payments — Check Processing / Precheck Acceptance

Sub-domain: Consumer check guarantee / precheck lifecycle management. This service sits in the **payment instrument validation** domain: it verifies that a paper check (precheck) is valid and authorised before it is physically accepted by a merchant or vendor, then marks it as accepted in the ecount Core ledger.

The facility code `certegy` (hardcoded in `application.yml`) identifies this as part of the Certegy check-guarantee programme, which is a third-party check guarantee network. Certegy is now owned by Fiserv.

## Role in Platform

This service is a **synchronous validation gateway** between external integrators/merchants and the ecount Core check-management backend.

```
External Caller / Merchant System
    ↕ SOAP (HTTP/HTTPS)
accept-prechecks_API  (this service)
    ↕ xplatform HTTP (ECoreEManage)
ecount Core dispatch service (nam.wirecard.sys)
    ↕ JDBC (SQL Server)
ecountcore / cbaseapp databases
```

The service has **no peers or siblings** consuming it from within the Onbe platform in a discoverable way from this codebase. It is a leaf service consumed by external parties (check-guarantee integrators) via the external APIM gateway (`EXTERNAL_APIM: true` in `deployment.yml`).

## Dependencies

### Upstream (this service consumes)
| Dependency | Artifact | Version | Nature |
|---|---|---|---|
| xplatform | `com.ecount:xplatform` | 6.5.0 | Internal Onbe library — ecount business object layer |
| xsearch | `com.ecount.service.xsearch:xsearch` | 2.0.1 | Internal Onbe search service client |
| ECoreEManage / ECoreManage | `com.cbase.business.core.spi.ecore.ECoreEManage` | (via xplatform) | ecount Core remote service client |
| ECoreMember | `com.cbase.business.core.spi.ecore.ECoreMember` | (via xplatform) | ecount member lookup |
| Apache Axis (jakarta fork) | `axis:jakarta-axis` | (from prepaid-parent) | SOAP engine |
| SQL Server databases | `mssql-jdbc:12.8.2.jre11` | 12.8.2 | ecountcore, cbaseapp, jobsvc |
| Azure App Configuration | `spring-cloud-azure-appconfiguration-config-web:5.23.0` | 5.23.0 | Runtime config |
| Azure Key Vault | `spring-cloud-azure-starter-keyvault-secrets:5.23.0` | 5.23.0 | Secrets |
| prepaid-parent POM | `com.parents:prepaid-parent:6.0.13` | 6.0.13 | Internal parent BOM |

### Downstream (consumes this service)
No downstream consumers are identifiable from within this repository. The service is published to external APIM; consumers are external parties or internal systems not visible here.

## Integration Patterns

| Pattern | Evidence |
|---|---|
| **SOAP RPC/Encoded (SOAP 1.1)** | `server-config.wsdd` — `provider="java:RPC" style="rpc"`, encoding `http://schemas.xmlsoap.org/soap/encoding/`, Apache Axis 1.x |
| **Request-Response (synchronous)** | Single `acceptPrecheck` operation; response returned in same HTTP call |
| **Spring JAX-RPC Remoting** | `JaxRpcAcceptPrecheckService extends ServletEndpointSupport` — uses deprecated Spring JAX-RPC remoting bridge (`org.springframework.remoting.jaxrpc.ServletEndpointSupport`) |
| **Spring XML Application Context** (WAR) | `applicationContext.xml` loaded via `ContextLoaderListener` |
| **Spring Boot Java Config** (Boot) | `AcceptPrechecksConfiguration.java`, `DatabaseConfiguration.java`, `ECountSystemConfiguration.java`, `WebConfiguration.java` |
| **Azure App Config pull** | Periodic refresh (default 15 min) — not event-driven push |
| **No message queue / async** | No JMS, Kafka, or messaging dependency found |
| **No REST endpoint** | All business functionality is exclusively SOAP. Only `/hc` is REST. |

## Strategic Status

**Status: Active legacy — modernisation in progress, not complete.**

The service serves an active external integration point (published to external APIM). However:

1. It was originally generated from WSDL in **2006** (Axis 1.4 generation comment in `AcceptPrecheckRequest.java`).
2. The WAR module and GitLab CI pipeline have not been decommissioned, indicating the migration to Kubernetes/Spring Boot is not fully ratified.
3. The `xplatform` and `xsearch` dependencies bind this service to the ecount Core on-premises infrastructure (`nam.wirecard.sys`), which must be migrated or retired for a full Gen-3 migration.
4. The root `wsdl.xml` (used for APIM publishing) is a generic placeholder, not the real service contract — this is a live defect in the API gateway configuration.
5. The facility hardcode (`certegy`) suggests this service supports a single use case; its scope may be narrow enough to evaluate replacement with a modern REST/JSON API in any re-platforming exercise.

## Migration Blockers

| Blocker | Description | Severity |
|---|---|---|
| **xplatform binding** | `com.ecount:xplatform:6.5.0` provides `ECoreEManage`, `ECoreManage`, `PreCheckDefinition`, and `IEManageManager`. These are the core business objects and cannot be replaced without migrating ecount Core or rebuilding the platform layer. | Critical |
| **Apache Axis 1.x / JAX-RPC** | `javax.xml.rpc.ServiceException` import in `JaxRpcAcceptPrecheckService.java` line 3 (note: `javax` not `jakarta`). Spring removed JAX-RPC support and the team has forked Axis with a `jakarta-` prefix. This is fragile and non-standard. | High |
| **SOAP encoded style** | `use="encoded"` in the WSDL is a SOAP 1.1 antipattern not supported by WS-I Basic Profile. WS-I-compliant stacks reject it. Re-platforming to REST requires a contract redesign. | High |
| **Hardcoded Citibank routing number** | The literal `38791282` appears in three places in `AcceptPrecheckServiceImpl.java` (lines 82, 114, 150). Any migration must preserve or externalize this special-case logic. | Medium |
| **Hardcoded facility `certegy`** | The facility code is hardcoded in `application.yml`. If the service serves multiple networks, this is incorrect and must be parameterised. | Medium |
| **Legacy WAR / Tomcat module** | `accept-prechecks-war` still exists and references preview JDBC drivers and Tomcat-specific JNDI resources. It is a migration risk if it is still deployed anywhere. | Medium |
| **nam.wirecard.sys DNS dependency** | All backend services and databases use `nam.wirecard.sys` hostnames (Wirecard legacy). DNS and routing changes are required for cloud-native deployment. | Medium |
| **`LastNameValidatorECountCore` not wired** | The `LastNameValidatorECountCore` bean is defined in `applicationContext.xml` and `AcceptPrechecksConfiguration.java` as `eMember`, but `AcceptPrecheckServiceImpl` does not use it — the service only checks the check addenda (`cz-lastname`), not the live cardholder record. This is a silent functional gap. | Low-Medium |
