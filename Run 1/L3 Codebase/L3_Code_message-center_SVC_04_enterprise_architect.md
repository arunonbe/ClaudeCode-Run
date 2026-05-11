# Enterprise Architect Report — message-center_SVC

## 1. Generation Classification

`message-center_SVC` is unambiguously a **Gen-2 (legacy)** service. It exhibits all hallmarks of the Onbe Gen-2 architecture:
- Spring XML bean configuration (no `@Configuration` classes)
- XML-RPC transport (not REST/gRPC)
- WAR packaging deployed to an embedded Tomcat
- Director-managed data source (proprietary internal service discovery)
- `com.ecount.*` and `com.citi.prepaid.*` package namespaces
- Raw `ArrayList` return types without generics

It has been **partially modernized**: Java 21 runtime (pom.xml lines 20-21), BellSoft Liberica JRE base image, and GitHub Actions CI — but the application architecture itself remains unchanged from its Wirecard-era origins (the SCM URL in the `module-parent` POM points to `d-na-stk01.nam.wirecard.sys/svn/`).

## 2. Position in the Onbe Architecture Landscape

```
Gen-2 Platform                    Gen-3 NexPay Platform
──────────────────────            ───────────────────────────────
EcountCore (SQL Server)           nexpay-cardprocessor-svc
    │                             nexpay-claim-code-svc
    ▼                             nexpay-auth-svc
message-center_SVC  ◄─────────── mpv (cardholder portal)
    │  XML-RPC
    ▼
ClientZone / CSA (admin portals)
```

`message-center_SVC` is a leaf service in the Gen-2 topology. It is consumed by MPV (the Gen-3 cardholder portal) via XML-RPC, creating a **cross-generation dependency** that constrains the Gen-3 migration path.

## 3. Integration Architecture

The service uses **XML-RPC over HTTP** as its primary integration protocol. The `MessageServiceClient.java` in `message-common` is the client stub used by upstream callers. This integration style:
- Is **synchronous and blocking** — no async, queue, or event-driven pattern.
- Is **tightly coupled**: callers must have the `message-common` JAR on their classpath and must use the XML-RPC wire protocol.
- Is **not discoverable** in an API gateway sense — no OpenAPI spec, no Swagger UI.

The `PUBLISH_TO_APIM: true` CI flag publishes the WSDL to an API Management gateway, suggesting there is a facade layer, but the underlying transport remains XML-RPC.

## 4. Gen-3 Migration Assessment

| Assessment Dimension | Current State | Gen-3 Target State | Gap |
|---|---|---|---|
| Transport protocol | XML-RPC over HTTP | REST/JSON or gRPC | High |
| Packaging | WAR on Tomcat | Spring Boot JAR on ACA | Medium |
| Configuration | Volume-mounted `.properties` file | Azure App Config + Key Vault | High |
| Data access | Stored procedures via Spring XML beans | Spring Data JPA + Flyway | High |
| Observability | Commons Logging | OpenTelemetry + structured JSON | High |
| Security | Directory-service credentials | Managed identity + OIDC | High |
| Java version | 21 (runtime OK) | 25 (NexPay target) | Low |

The service is a **candidate for replacement** rather than incremental modernization. A Gen-3 equivalent would be a Spring Boot microservice with a REST API, backed by Azure SQL or PostgreSQL, with Azure App Configuration for runtime config.

## 5. Dependency Graph

```
message-center_SVC
├── prepaid-parent:6.0.12 (com.parents) — Gen-2 parent POM
├── xsecurity-web:4.0.3 (com.ecount.service.xsecurity) — internal security library
├── xmlrpc:3.0.2 (com.citi.prepaid.service.core) — XML-RPC library
├── ecount-system:4.0.2 (com.ecount.service.Core2) — Core2 framework
├── director-client:2.0.1 (com.ecount.service.Core2.director) — Director service client
└── dao-util:2.0.1 (com.ecount.daoutil) — DB utility library
```

All dependencies are internal Onbe libraries with `com.ecount.*` or `com.citi.prepaid.*` group IDs. There are no public Maven Central dependencies beyond Spring Framework itself (pulled transitively through the parent POM). This tight internal dependency web means upgrades are coordinated across multiple internal repos.

## 6. Non-Functional Characteristic Assessment

- **Availability**: Depends on Director service availability at startup. If Director is unreachable, the service fails to initialize. No circuit breaker.
- **Scalability**: Stateless at the application layer; scales via additional Tomcat container instances. Connection pool scaling is limited by DBCP configuration (not visible in repo).
- **Resilience**: No retry logic, no circuit breaker, no bulkhead at the service layer.
- **Security posture**: Gen-2 security based on `xsecurity-web` library. No JWT/OAuth2 token validation visible; authentication likely handled by a reverse proxy or the Tomcat `server.xml` filter chain.

## 7. Strategic Recommendation

The service should be included in the Gen-3 migration roadmap. Priority should be given to eliminating the cross-generation dependency from MPV (which is a Gen-3 service) back to this Gen-2 XML-RPC endpoint. A notification microservice based on the Gen-3 `nexpay-parent` stack would align with Azure Container Apps deployment and Entra-based authentication. The SQL Server stored procedures should be migrated to PostgreSQL with Flyway-managed schema evolution.
