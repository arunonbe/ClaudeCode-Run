# Enterprise Architect View — cs-api-singlewar_API

## Platform Generation
**Gen-1 / Gen-2 Bridge** — This repository packages both the original V1 SOAP service logic and the V3-enhanced logic into a single deployment unit. It is an architectural interim artefact, created to ease client migration from V1 to V3 without requiring simultaneous client-side API version cutover.

The underlying platform is the C-Base / ecount xPlatform (proprietary ECount card platform), which is Gen-1 infrastructure. The V3 business logic layer represents Gen-2 capabilities (affiliate-driven metadata, comment history, PPD promotions) running on the same Gen-1 platform substrate.

## Domain
- **Domain**: Customer Service (CS) — Cardholder Inquiry and Management
- **Bounded context**: CS API — the internal B2B SOAP interface consumed by client-facing applications and internal CS tools
- **Position in value chain**: Middleware bridge between client applications and the C-Base card processing platform

## Role in Ecosystem
```
Client Application / CS Tool
        │
        ▼ SOAP (application_id-authenticated)
cs-api-singlewar_API (WAR)
  ├── V1 endpoint: /CardManagement/services/AccountManagement
  └── V3 endpoint: /CardManagementV3/services/AccountManagement
        │
        ├── AffiliateService (SQL Server: CbaseApp)
        ├── CommentService (comment platform)
        └── xPlatform DeviceManager/EMember (C-Base core)
```

## Dependencies
| Upstream | Downstream | Type |
|---|---|---|
| CbaseApp SQL Server | → this service | JDBC (affiliate lookup) |
| JobSvc SQL Server | → this service | JDBC (PUID) |
| C-Base xPlatform | → this service | Proprietary RPC |
| Comment Service | → this service | Spring classpath JAR |
| cs-api-singlewar_API | → client applications | SOAP/HTTPS |

## Patterns
- **SOAP-RPC**: Apache Axis 1.x with `ServletEndpointSupport`
- **Service Locator via Spring XML**: All beans resolved via `ClassPathXmlApplicationContext` or `ApplicationContext.getBean()`
- **Strategy Pattern**: `requestContextLookup.lookup()` dispatches application_id to program_id — though implemented as a simple HashMap
- **Template Method**: `AccountManagementImpl` base class provides shared logic (`initRequestContext`, `add1DayToEndDate`, `getPPIDFromTransactionAddenda`) inherited by both V1 and V3 paths
- **No API gateway**: Direct client-to-service SOAP calls; no rate limiting, no routing layer

## Architectural Status
- **Status**: Legacy / Maintenance mode
- This artifact is likely superseded by the Spring Boot versions (`cs-api-v1_API` with Boot module, `cs-api-v3_API` with Boot module)
- The lack of a CI deployment pipeline suggests active deployments are not being maintained through this repository
- The Maven parent `com.citi.prepaid:prepaid-parent:4.0.0` references the Citi era — predates Onbe branding

## Migration Blockers to Gen-3
1. **Apache Axis dependency**: Cannot be brought forward to Spring Boot 3.x without replacing the SOAP stack entirely (JAX-WS or Spring-WS)
2. **Spring 2.x Bean XML configs**: Over 400 lines of XML bean definitions need to be converted to `@Configuration` classes
3. **JNDI DataSources**: Must be replaced with Spring Boot datasource auto-configuration or Azure-injected credentials
4. **Proprietary C-Base xPlatform RPC**: Migration to the REST-based `ecount-core-rest-api` (used in cs-api-v3_API) is required
5. **No test coverage**: No unit tests in this repository — migration carries high regression risk
6. **Static application_id mapping**: Must be replaced with dynamic affiliate service lookup (already done in cs-api-v1_API and cs-api-v3_API)
7. **Windows filesystem configuration paths**: Must be replaced with cloud-native config (Azure App Configuration)
