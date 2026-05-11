# Data Architect Report — onbe-spring-boot-parent_PARENT

## Data Models

This repository contains only a POM XML file — there are no data models, Java classes, Kotlin files, or schema definitions. Its role is entirely build-time governance. All data architecture concerns are delegated to consuming services.

## Dependency-Level Data Architecture Decisions

Although the parent POM contains no code, its dependency management choices directly shape the data architecture of every consuming service:

### Database Connectivity
- **MS SQL Server (MSSQL):** `mssql-jdbc` version 12.8.1.jre11 is managed — the JDBC driver for SQL Server, used by both synchronous (JDBC/JOOQ) and as a fallback for non-reactive access.
- **R2DBC (Reactive SQL Server):** `r2dbc-proxy` is included in `dependencyManagement`. Combined with the `onbe-spring-boot` framework's `ConnectionFactoryFactory`, this provides reactive non-blocking SQL Server connectivity.
- **Redis:** Lettuce client (6.5.4.RELEASE) managed for Redis cache/state store access. In Dapr-mediated services, Redis is typically accessed via the Dapr state store API rather than directly.
- **HikariCP:** Version 6.2.1 managed for traditional JDBC connection pooling in non-reactive services.

### Event / Message Architecture
- **Apache Avro:** Version 1.12.0 with the Avro Maven plugin for schema-driven event serialization — Onbe's Gen-3 event bus payload format for payment domain events.
- **Debezium (CDC):** Version 3.0.7.Final for SQL Server change data capture — supports event-sourcing patterns where payment state changes (card load, disbursement, refund) are streamed as database events.
- **Spring Cloud Stream + Dapr Binder:** `spring-cloud-stream-binder-dapr` 1.0.0 — enables message-driven payment events via Dapr pub/sub (backed by Azure Service Bus in production).

### Identity / Auth Data
- **MSAL4J:** 1.19.0 — Microsoft Authentication Library for Java, handling OAuth 2.0/OIDC tokens for Azure resource access (Key Vault, Service Bus, App Configuration). Token data is managed by the library and not persisted by Onbe services directly.
- **Azure Identity:** 1.15.2 — managed identity and service principal credential management for Azure resources.

## Sensitive Data Handling at POM Level

The POM itself contains one potentially concerning artifact:

**File: `pom.xml`, line 721:**
```xml
<jdbcUrl>jdbc:sqlserver://localhost:1433;databaseName=AdventureWorks;user=MyUserName;password=*****;encrypt=false;</jdbcUrl>
```

This is in the QueryDSL plugin configuration as a template. Key observations:
1. `encrypt=false` — this would disable TLS for the QueryDSL code generation connection. This must never be used against a real database containing CHD or PII.
2. `password=*****` — this appears to be a documentation placeholder, not a real credential. However, the presence of `MyUserName` as the user field suggests this may be a developer template that teams copy and modify. If any team substitutes a real password here and commits, it becomes a credential exposure in source control.
3. `databaseName=AdventureWorks` — this is a Microsoft sample database name, confirming this is a template for local development only.

**Recommendation:** Replace the inline JDBC URL template with a property reference (e.g., `${querydsl.jdbcUrl}`) sourced from a CI secret, and add a comment explicitly prohibiting use against CDE databases.

## Data Flows Established by POM Governance

The POM's dependency choices establish the following canonical data flow patterns for Gen-3 services:

```
[Azure Key Vault]  <-- Dapr SDK 1.13.3 (secret retrieval)
[Azure Service Bus] <-- Dapr + spring-cloud-stream-binder-dapr (payment events)
[SQL Server (CDE)] <-- MSSQL JDBC 12.8.1 / R2DBC (transactional payment data)
[Redis]            <-- Lettuce 6.5.4 (session state, rate limiting)
[Azure App Config] <-- Spring Cloud Azure 5.20.0 (feature flags, runtime config)
[OpenTelemetry]    <-- 2.13.1-alpha (distributed traces)
```

## Encryption and TLS Governance

The parent POM does not enforce TLS at the code level — it is a dependency governance artifact. However:
- `mssql-jdbc` 12.8.1 supports and defaults to `encrypt=true` for Azure SQL Server (changed in JDBC 10.x+). The QueryDSL template with `encrypt=false` is a discordant signal that could mislead developers.
- The Azure Identity and Spring Cloud Azure dependencies support managed identity, eliminating the need for static credentials in most cases.
- MSAL4J and Azure Identity handle TLS internally for all Azure service communications.

## PCI DSS Compliance Assessment

- Req 6.3.2 (SBOM): CycloneDX plugin generates aggregate SBOM at package phase — compliant.
- Req 6.2 (Secure Development): Java 21 enforcement, pre-release version exclusion — aligned.
- Gap: QueryDSL configuration template with `encrypt=false` should be corrected or removed.
- Gap: `opentelemetry-instrumentation.version=2.13.1-alpha` — alpha software in a PCI-scope BOM is a risk; validate that tracing agents do not capture or log CHD.
- Recommendation: Confirm with the Security team whether Debezium CDC connector for SQL Server is in scope for PCI CDE change management (CDC on CDE tables requires Requirement 10 audit trail review).
