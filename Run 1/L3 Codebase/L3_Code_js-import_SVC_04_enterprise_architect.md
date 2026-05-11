# Enterprise Architect View — js-import_SVC

## Architectural Classification

`js-import_SVC` is a **legacy batch-ingestion service** operating within Onbe's Generation-1 / Generation-2 platform layer. It uses a classic Java EE WAR deployment model with Spring 2.x XML configuration, JNDI-managed connection pools, and proprietary fixed-width file formats. It occupies a critical position in the Onbe payments value chain as the primary entry point for bulk client-initiated cardholder lifecycle operations.

## Position in Onbe Platform Landscape

```
External Client (SFTP / HTTP)
        │
        ▼
js-import_SVC (jsvalidator WAR)   ◄── This service
        │  parses, validates, persists
        ▼
jobsvc SQL Server Database
        │  consumed by
        ▼
jobservice_SVC (batch fulfilment engine)
        │  calls
        ▼
ecount-core_SVC / director-svc / payment rails
        │
        ▼
Prepaid Card / ACH / Check Output
```

This service is a **CDE-adjacent** component. It handles PII that feeds card issuance and fund loading — operations that directly affect cardholder data environments. It is not a card-data processor itself (no PAN flows through its import files), but the downstream execution pipeline it feeds is within PCI DSS scope.

## Architectural Concerns

### 1. Technology Obsolescence
The service uses Spring Framework 2.0.4 (released ~2007), Log4j 1.x, and Java 8 — all end-of-life or imminently unsupported. The jTDS JDBC driver (1.2.2) is no longer maintained. These create compounding CVE exposure and prevent the use of modern security controls (TLS 1.3, JVM security patches post-Java 8).

### 2. Proprietary File Format Lock-in
The JS fixed-width file format is a bespoke Onbe protocol that predates modern API standards. Clients must generate files conforming to this exact byte-position schema. Migrating clients to REST APIs (such as `manage-payment-rest-api`) requires a parallel-run strategy.

### 3. Coupling to Windows On-Premise Infrastructure
The service assumes:
- A Windows filesystem at `D:/c-base/config/...`
- Tomcat deployed as a Windows Service named `JSValidator`
- Named on-premise hosts (`d-na-app04`, `q-na-app09`)

This architecture cannot be containerised or cloud-deployed without significant refactoring.

### 4. No Horizontal Scalability
The JNDI connection pool and singleton `JSContext` / `IDGeneratorImpl` sequence manager create single-instance constraints. The ID generator uses database-based sequences — under concurrent multi-instance deployment, sequence contention would arise.

### 5. Absence of API Gateway / Auth Layer
The `JobValidatorServlet` accepts HTTP POSTs without visible authentication enforcement at the application layer (no JWT, no API key validation in the servlet). Security must be enforced entirely by network ACLs and the upstream infrastructure layer. This does not meet PCI DSS Requirement 6.3 (web-facing application security controls) if the endpoint is accessible beyond the trusted internal network.

## Integration Architecture

| Integration Point | Protocol | Direction | Data Sensitivity |
|---|---|---|---|
| Client file submission | HTTP POST / SFTP | Inbound | PII, Financial |
| jobsvc SQL Server | JDBC (jTDS) via JNDI | Outbound | PII, Financial |
| Redis cache | TCP (custom URL) | Outbound | Config only |
| jobservice_SVC | Database polling (shared DB) | Indirect | — |

The shared-database integration with `jobservice_SVC` is an anti-pattern under microservices architecture — it creates tight schema coupling and prevents independent deployment.

## Regulatory Architecture Alignment

| Requirement | Status | Notes |
|---|---|---|
| PCI DSS Req 6.3 (web app protection) | Partial | No WAF or app-level auth evident |
| PCI DSS Req 8 (access control) | Unknown | Depends on network/Tomcat config |
| PCI DSS Req 10 (audit logging) | Weak | Log4j 1.x, no structured audit trail |
| GLBA Safeguards Rule | Partial | PII processed but no field encryption |
| NACHA (ACH data) | Partial | Bank data in WithdrawRequest, no encryption |
| Reg E | Partial | Electronic fund transfer processing |

## Modernisation Roadmap Recommendations

1. **Short-term**: Upgrade Log4j to 2.x or Logback; upgrade commons-collections to 4.x; patch jTDS to mssql-jdbc; upgrade Spring to 5.x.
2. **Medium-term**: Replace JNDI/XML config with Spring Boot; externalise configuration from filesystem to a config server; add JWT/API-key authentication to `JobValidatorServlet`.
3. **Long-term**: Migrate clients from JS file format to `manage-payment-rest-api` REST endpoints; decommission this service as the new API reaches full feature parity.
4. **Containerisation**: Once config externalisation is complete, containerise with Docker and deploy to the existing Kubernetes/ECS infrastructure used by newer services.

## Architectural Fitness Functions

The following quality attributes should be formally measured:
- **Reliability**: File processing success rate and error rate per batch
- **Throughput**: Maximum records/second before DB saturation
- **Latency**: Time from file submission to `job_file` record insertion
- **Availability**: Uptime of the Tomcat Windows service
- **Security**: CVE count in dependency tree (currently high)
