# Enterprise Architect — wirecard_nam-bank-agent_LIB

## Clone Completeness Note
Partial clone — some modules may have missing files. Enterprise architecture assessment is based on available source.

## Platform Generation
**Gen-2 (Wirecard/Northlane)** — Spring Boot 1.5.13 (older than FTC sibling at 2.0.7), Java 8, Gradle 4.8, Nexus, Ansible/RPM. The older Spring Boot version suggests this component pre-dates the FTC service and may be among the earliest Gen-2 NAM microservices.

## Business Domain
**Banking Integration / Payment Rail Connectivity** — NAM Bank Agent is the primary integration adapter between the Wirecard/Northlane internal platform and the North American banking system (Sunrise Bank). It is the ACH originator, wire transfer initiator, and check issuance file generator for the NAM prepaid card programme.

## Role in the Wirecard Platform
- **The banking gateway for NAM**: all ACH, wire, and check communications with the bank partner flow through this service
- Downstream consumer of: FTC (wire drawdown events), platform EventHub (check/ACH/customer events)
- Upstream provider to: CCP/platform (ACH returns, direct deposit postings, check status, wire transfer in updates)
- Peer to: wire-transfer-agen_LIB (which handles the internal wire transfer coordination side); NAM-bank-agent handles the external bank file side

## System Dependencies
### Inbound (consumes from)
| System | Protocol | Data |
|---|---|---|
| EventHub (ActiveMQ) | JMS | Wire transfer out, check, ACH origination, customer sync events |
| Sunrise Bank SFTP | SFTP (private key auth) | ACH direct deposit files, ACH return files, client fund posting files |
| PDS SFTP | SFTP | Undelivered check files |

### Outbound (publishes to)
| System | Protocol | Data |
|---|---|---|
| EventHub (ActiveMQ) | JMS | ACH posting events, check status updates, wire transfer in events, customer updates |
| Sunrise Bank SFTP | SFTP | ACH origination files, wire drawdown files, DD reject files, check files |
| PDS SFTP | SFTP | Check-related files |
| SMTP | Email | Batch failure alerts |

## Integration Patterns
- **File-based batch**: NACHA ACH files, wire drawdown files, check issuance files (SFTP-in/SFTP-out pattern)
- **Event-driven**: EventHub (ActiveMQ) for inbound triggers and outbound status updates
- **Spring Batch**: Partitioned multi-file, multi-brand processing with Chunk-oriented steps
- **SFTP gateway**: sftp-common-utilities library for download/upload tasklets (with retry)
- **Dependency injection**: All batch configs wired via Spring `@ConfigurationProperties`

## Strategic Status
- **Current**: Active production service — the only banking file exchange gateway for NAM ACH/wire/check
- **Critical path**: Cannot be decommissioned without a replacement banking integration layer
- **High complexity**: Handles multiple NACHA subtypes (PPD, CCD, CTX implied), wire drawdown, check MICR — significant domain expertise required for migration
- **Spring Boot 1.5.13**: The oldest Spring Boot version observed across these 6 repos — highest technical debt

## Migration Blockers
1. NACHA file format compliance is complex and deeply embedded in batch DTOs and factory classes — requires full ACH domain knowledge for migration
2. Sunrise Bank SFTP integration — any replacement must negotiate new connection parameters with the banking partner
3. Spring Boot 1.5.13 → 3.x is a two-major-version jump; no direct upgrade path
4. EventHub/ActiveMQ proprietary client — must be replaced with cloud-native messaging
5. Oracle DB (two-schema pattern) — same as FTC
6. RPM/Ansible deployment model
7. `setAllowUnknownKeys(true)` in SFTP — migration to known-host verification requires operational coordination with bank partner
8. Jenkins sub-module (`jenkins-plugins`) embedded in repo — CI/CD tightly coupled to Jenkins
9. PDS as a second SFTP bank partner — dual-bank integration complexity
