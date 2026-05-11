# Enterprise Architect Report — wirecard_sg-bank-agent_LIB

## Platform Generation

**Gen-2 (Wirecard/Northlane)**. Evidence:
- Spring Boot 1.5.13.RELEASE (released 2018, EOL 2019) — characteristic Gen-2 era.
- Spring Cloud Finchley (2018) — Gen-2 microservices cloud layer.
- Gradle build (Wirecard used Gradle; Gen-1 used Maven exclusively, Gen-3 migrated back to Maven).
- Ansible RPM deployment to on-premises Linux servers — Gen-2 deployment pattern.
- Jenkins CI (`Jenkinsfile`) — Gen-2 CI/CD.
- Internal Wirecard Nexus server (`d-issrepo-app01.wirecard.sys`, `q-issrepo-app01.wirecard.sys`).
- Package namespace `com.wirecard.sgbankagent`.
- Brand server client URL `q-brands-app01.wirecard.sys:9000` — Wirecard internal.

## Integration Patterns

- **Event-driven (ActiveMQ)**: Asynchronous event exchange with CCP via the `eventhub` client library (Wirecard proprietary). Modes: `producer.activemq` and `consumer.activemq`.
- **SFTP batch file exchange**: Scheduled Spring Batch jobs polling SFTP server at CIMB for status files; uploading wire transfer instructions.
- **PGP encryption**: Files exchanged with CIMB are PGP-encrypted (mandatory bank security requirement).
- **XSLT transformation**: Wire transfer transaction data is transformed to CIMB-required XML format via XSLT templates.
- **Spring Batch partitioned processing**: Customer and wire transfer processing uses Spring Batch's `FilesInDirectoryPartitioner` and `CustomerBrandPartitioner` for parallel processing.
- **Liquibase database migrations**: Schema versioning via Liquibase, targeting Oracle in production.

## External Dependencies

- **CIMB Bank Singapore**: Primary external bank partner; SFTP-based file exchange.
- **Wirecard CCP (Central Card Platform)**: Internal event source/sink via ActiveMQ.
- **Wirecard Brand Server** (`q-brands-app01.wirecard.sys:9000`): Financial institution data.
- **Oracle OJDBC6**: Oracle database.
- **Nexus repositories** (`d-issrepo-app01.wirecard.sys`, `q-issrepo-app01.wirecard.sys`): Artifact hosting.
- **AWS** (`[REDACTED — rotate immediately]`): AWS access — likely for an AWS-hosted Nexus or artifact storage.
- **BouncyCastle**: PGP cryptography library.
- **JSch (jcraft)**: SFTP client library.

## Position in the Broader Platform

The SG bank agent is the **only payment rail to CIMB Bank Singapore**, making it a critical single point of failure for Singapore-market wire transfer disbursements. It sits between the Wirecard CCP (internal orchestration) and CIMB (external bank), a position that is:
- In scope for PCI DSS as a component that processes payment instructions.
- In scope for MAS TRM (Technology Risk Management) guidelines for Singapore financial institutions.
- A critical integration for cardholder fund access in the Singapore market.

## Migration Blockers

1. **Spring Boot 1.5.x → 3.x migration**: Major breaking changes (Spring namespace, javax → jakarta, configuration property binding). Estimated high effort.
2. **Gradle → Maven migration**: If following Onbe's Gen-3 standard of Maven.
3. **Ansible/RPM → container/AKS migration**: Significant infrastructure change.
4. **ActiveMQ → Azure Service Bus**: If following Onbe Gen-3 messaging patterns.
5. **SFTP credential rotation**: The CIMB SFTP private key must be rotated and removed from source code before any migration.
6. **Oracle → SQL Server or Azure SQL**: If following Onbe database platform consolidation.

## Strategic Status

**High criticality — urgent security remediation required.** The hardcoded SFTP private key, PGP private key, and AWS credentials in source code represent active security incidents, not technical debt. This repository's secrets must be rotated immediately and the credentials removed from Git history. The service itself requires a Spring Boot upgrade and containerization before it can be considered for Gen-3 migration planning.
