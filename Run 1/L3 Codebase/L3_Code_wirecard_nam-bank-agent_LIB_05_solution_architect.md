# Solution Architect — wirecard_nam-bank-agent_LIB

## Clone Completeness Note
Partial clone — event-consumer, event-service, event-persistence, and config modules may have incomplete or missing files. Technical analysis is limited to batch module, SFTP configs, and available structural source.

## Technical Architecture
- **Framework**: Spring Boot 1.5.13.RELEASE, Java 8, Gradle 4.8
- **Batch framework**: Spring Batch (chunk-oriented, partitioned)
- **SFTP**: Spring Integration SFTP (`sftp-common-utilities` shared library); JSch under the hood
- **Persistence**: JPA/Hibernate + Liquibase (event-persistence module — partially available)
- **Messaging**: Wirecard EventHub client (ActiveMQ transport)
- **Email**: Spring Mail for batch failure notifications
- **Modules**: batch, config, data, db-app, docs, event-consumer, event-persistence, event-service, event-utility

## API Surface
No REST API exposed by this service. It is a batch/event-driven backend with no inbound HTTP endpoints beyond Spring Boot Actuator health.
- Actuator health: `/nam-bank-agent/monitoring/health` (assumed; consistent with platform pattern)

## Security Posture

### Authentication / Authorisation
- No REST API, so no inbound authentication surface
- Internal service — relies on network segmentation for access control
- EventHub consumption uses ActiveMQ credentials (not visible in source, expected in env config)

### SFTP Security
- Authentication: private key (`SunriseSftpConfig.privateKey` loaded from property)
- **Critical finding**: `setAllowUnknownKeys(true)` in `BatchCommonChannelConfig.java:38` — host key verification disabled for all SFTP connections
  - This means the service will connect to ANY server presenting as the configured hostname without verifying authenticity
  - Violates PCI DSS Requirement 4.2 and NACHA security requirements for protected file exchange

### Known CVEs (library-level risk)
| Library | Version | Risk |
|---|---|---|
| Spring Boot | 1.5.13.RELEASE | EOL Aug 2019; multiple high/critical CVEs; Apache Tomcat embedded version CVEs |
| Spring Batch | (from Spring Boot 1.5.13 BOM) | EOL equivalent |
| Spring Integration SFTP | (from BOM) | Old JSch version known for outdated cipher support |
| Oracle ojdbc8 | 12.2.0.1.0 | Old driver version; check Oracle CPU advisories |
| H2 Database | (from BOM) | 1.4.x known CVE-2021-42392 if console enabled |

## Technical Debt
1. Spring Boot 1.5.13 — most outdated in all 6 repos; highest CVE surface area
2. `setAllowUnknownKeys(true)` — deliberate disabling of SFTP host verification; should be replaced with known_hosts file management
3. Gradle `compile` dependency configuration (deprecated in Gradle 7, removed in Gradle 7+)
4. Jenkins sub-module (`jenkins-plugins/`) embedded within application repo — anti-pattern; CI/CD should be separate
5. `bootRepackage` Gradle task syntax — Spring Boot 1.x only; will not work with Spring Boot 2+
6. AsciiDoc documentation module (`nam-bank-agent-docs`) — suggests documentation is version-coupled to code; acceptable but aging toolchain
7. No circuit-breaker pattern observed for SFTP or EventHub operations — batch jobs may hang indefinitely on connection failures
8. BatchJobConstants.CHUNK_SIZE — single shared constant for all jobs; different job types may need different chunk sizes for performance

## Gen-3 Migration Requirements
1. Upgrade Spring Boot from 1.5.13 to 3.x (two major version jump — requires full testing cycle)
2. Replace SFTP host-key bypass with proper known_hosts management
3. Replace JSch/Spring Integration SFTP with modern SSHD-based client (Apache MINA SSHD, as used in sftp-common-utilities v2.0)
4. Replace EventHub/ActiveMQ with cloud-native messaging
5. Containerise: remove RPM/Ansible; create Dockerfile
6. Extract Jenkins plugins sub-module to separate CI repo
7. Implement circuit-breaker / retry with backoff for SFTP and EventHub operations
8. Replace Oracle with cloud-managed DB
9. Ensure all NACHA file processing logic is covered by integration tests before migration
10. Validate SFTP private key rotation procedure and integrate with secrets manager

## Code-Level Risks
| File | Line | Risk |
|---|---|---|
| `nam-bank-agent-batch/src/main/java/com/wirecard/nambankagent/batch/common/listener/StepExceptionEmailListener.java` | (available) | Sends exception detail via email — may include ACH account numbers in stack traces |
| `BatchCommonChannelConfig.java` (sftp-common-utilities dependency) | Line 38 | `setAllowUnknownKeys(true)` — SFTP host key verification disabled |
| `build.gradle` | Line 19 | HTTP (not HTTPS) Nexus URL — artifact download integrity not protected |
| `SunriseSftpConfig.java` | All | Private key loaded from property — no validation of key format or rotation hooks |
| `nam-bank-agent-batch/src/main/java/.../StepExceptionEmailListener.java` | (available) | Email-based alerting as sole failure notification — no integration with monitoring platform |
