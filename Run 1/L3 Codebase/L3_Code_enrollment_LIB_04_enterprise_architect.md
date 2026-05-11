# Enterprise Architect Analysis — enrollment_LIB

## Repository Overview

**Repo:** `enrollment_LIB`
**Artifact:** `com.ecount.processes.enrollment:enrollment:2.0.3-SNAPSHOT`
**Platform generation:** Gen-1 (Legacy eCount / Citi Prepaid batch infrastructure)
**Package namespace:** `com.citi.processes.enrollment` — confirms Citi Prepaid heritage, predating the Wirecard/North Lane/Onbe brand transitions.

---

## Platform Generation Assessment

`enrollment_LIB` is a **Gen-1 batch library** built on the original eCount platform architecture:

| Dimension | Gen-1 (this repo) | Gen-2 (enrollment_WAPP) | Gen-3 (exemplar services) |
|-----------|-------------------|------------------------|--------------------------|
| Java | 1.6 | 1.8 | 11+ |
| Spring | 2.0.8 (XML config) | 2.0.3 (XML config) | Spring Boot 2.4–2.5 |
| Build | Maven + assembly | Maven + WAR | Maven multi-module |
| Database | SQL Server via jTDS | SQL Server via jTDS/mssql-jdbc | SQL Server via mssql-jdbc |
| Config | cBase config server + Spring XML | cBase / Tomcat context | Spring Cloud Config / YAML |
| Deployment | Shell script / scheduled job | Tomcat WAR | Docker / Kubernetes |
| Messaging | File + FTP | N/A | Dapr pub/sub (MQTT) |
| Testing | None | Integration tests | JUnit 5 + Cucumber BDD |
| Security scanning | CodeQL (added later) | N/A | CodeQL + Dependabot |

---

## Enterprise Architecture Position

### Application Landscape Role

`enrollment_LIB` represents the **cardholder enrollment extract subsystem** within Onbe's prepaid card operations. It is part of the data-delivery infrastructure that feeds issuers, partners, and internal systems with records of which cardholders have enrolled or unenrolled.

### Integration Points

```
[SQL Server Database]
    -- program profiles (batch control)
    -- enrollment records (extract source)
    -- report status (processing outcome)
         |
         v
[enrollment_LIB batch process]
         |
         |-- StrongBox (XML-RPC: sensitive data retrieval)
         |-- Director service (DB connection routing)
         |-- cBase config server (property resolution)
         v
[Fixed-width flat file]
         |
         v
[FTP server -> Partner / Issuer]
```

This is a classic **batch ETL** integration pattern: Extract from database, Transform into fixed-width format (with StrongBox enrichment), Load via file transfer.

### Organisational Heritage

The package name `com.citi.processes.enrollment` reveals that this code was originally developed under Citi Prepaid. The references to `ecount` throughout (`ecountId` field, `ecount.processes.enrollment` groupId, `com.ecount.service.Core2` dependencies) reflect the eCount platform that Wirecard acquired and that later became North Lane / Onbe. This code has survived multiple corporate acquisitions and brand changes with minimal modernisation.

---

## Strategic Architecture Concerns

### 1. Platform Extinction Risk

The library depends on:
- **Director service** — an internal eCount/cBase service for database connection routing. This service may not exist in Onbe's future cloud-native infrastructure.
- **StrongBox** — a legacy secure data store using XML-RPC. This is not a cloud-native secrets management solution (contrast with HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault).
- **cBase config server** — a legacy configuration server. Gen-3 services use Spring Cloud Config or Kubernetes ConfigMaps.

If any of these infrastructure components is decommissioned, `enrollment_LIB` will stop functioning.

### 2. Data Classification Boundary

The flat files produced by this library contain **Category 1 PII** (SSN, DOB) and **regulated financial data** (ACH routing/account numbers). This creates enterprise-wide obligations:
- Files must be encrypted at rest and in transit (GLBA, PCI DSS Req 3.4, NIST CSF PR.DS-1).
- File access must be logged (PCI DSS Req 10.2).
- Retention policies must be enforced (CCPA, GLBA).

There is no evidence in this repo that these controls are implemented at the library level.

### 3. Legacy Dependency Supply Chain

The dependency tree includes components that are no longer maintained:
- `org.springframework:spring:2.0.8` (2007)
- `net.sourceforge.jtds:jtds:1.2` (2012)
- `commons-lang:commons-lang:2.1` (2005)
- Internal `com.ecount.service.Core2` dependencies (no public CVE tracking possible)

This represents a significant supply chain security risk under PCI DSS v4.0.1 Req 6.3 and NIST CSF ID.SC.

### 4. Regulatory Change Exposure

As Reg E, CCPA, and state privacy laws evolve, the fields collected in `ExtractInfo` (particularly `ssn`, `dob`, `accountNumber`) may require additional consent tracking, data minimisation, or right-to-erasure handling. The current batch extract architecture has no mechanism for:
- Excluding cardholders who have exercised CCPA deletion rights.
- Masking SSN in outputs that do not strictly require it.
- Consent-aware filtering.

---

## Enterprise Architecture Recommendations

1. **Inventory and document** all downstream consumers of the enrollment flat files. Determine which partners still require this exact format vs. which could receive an API-based notification.
2. **Evaluate migration** to a Spring Batch / Spring Boot implementation with direct `mssql-jdbc` connectivity, Vault/AWS Secrets Manager for sensitive data, and Azure Blob Storage or SFTP with PGP encryption for file delivery.
3. **Decommission StrongBox and Director** dependencies as part of a platform modernisation programme; replace with cloud-native equivalents.
4. **Implement data minimisation** — review whether SSN and DOB are actually required in the extract files delivered to partners; if not, remove from `ExtractInfo` and the stored procedure.
5. **Establish a sunset date** — given the EOL dependencies and Gen-1 architecture, this library should have a documented sunset date aligned with the Gen-3 migration roadmap.
