# Enterprise Architect — wirecard_wire-transfer-agen_LIB

## Platform Generation
**Gen-2 (Wirecard/Northlane)** — Spring Boot 1.5.13, Java 8, Gradle 4.8, Nexus, Ansible/RPM. Shares the same Spring Boot 1.5.13 version as NAM-bank-agent, placing it in the older half of the Gen-2 platform.

## Business Domain
**Wire Transfer Processing / Payment Rail Coordination** — The Wire Transfer Agent is the internal coordination layer for wire transfers. It sits between the CCP platform (business rules and account management) and the NAM Bank Agent (external banking file exchange), translating platform events into bank-processable formats and vice versa.

## Role in the Wirecard Platform
```
CCP / EventHub
     │
     ▼
Wire Transfer Agent (WTA) ◄──── file exchange ────► NAM Bank Agent ──── SFTP ────► Sunrise Bank
     │
     ▼
Oracle DB (wire transfer state)
     │
     ▼
EventHub (status events → CCP)
```

- WTA is the **orchestration node** for wire transfers: receives events from CCP, processes inbound bank files from NAM bank agent, publishes status events back to CCP
- NAM Bank Agent is the **banking gateway**: handles SFTP file exchange with Sunrise; WTA feeds it outbound file content

## System Dependencies
### Inbound (consumes from)
| System | Protocol | Data |
|---|---|---|
| EventHub (ActiveMQ) | JMS | WireTransferOutStatusUpdatedEvent, WireTransferOutCancellationStatusEvent, WireTransferOutNotificationOfChangeEvent |
| Local filesystem | File | JSON prototype files from NAM bank agent (import jobs) |

### Outbound (publishes to)
| System | Protocol | Data |
|---|---|---|
| EventHub (ActiveMQ) | JMS | NewWireTransferOutEvent, CancelWireTransferOutEvent, IncomingWireTransferStatusUpdatedEvent |
| Oracle DB | JDBC | Wire transfer state persistence |
| SMTP | Email | Operational notifications |
| Local filesystem | File | Output files for NAM bank agent pickup |

## Integration Patterns
- **Event-driven (EventHub)**: Publishes and consumes wire transfer lifecycle events
- **File-based batch**: JSON line files for bank-sourced data; partitioned, parallel Spring Batch processing
- **Database-per-service**: Oracle schema with two-schema pattern
- **JSON serialisation**: Jackson; `JsonLineMapper` / `JsonLineAggregator` for batch files
- **XML serialisation**: JAXB for EventHub event objects (`NewWireTransferOutEvent`, etc.)

## Strategic Status
- **Current**: Active production service for NAM wire transfer processing
- **Critical path**: Cannot be decommissioned without simultaneous replacement of both wire transfer event processing and the bank-file coordination with NAM bank agent
- **Tight coupling**: WTA ↔ NAM-bank-agent file exchange via shared filesystem — must be migrated as a pair
- **Data sensitivity**: This service handles the most sensitive financial data in the batch (bank routing numbers, bank account numbers) — migration must include enhanced data protection

## Migration Blockers
1. Spring Boot 1.5.13 → 3.x — two major version jump with extensive API changes (javax → jakarta namespace, etc.)
2. JAXB XML serialisation (`javax.xml.bind`) removed in Java 11+ — requires replacement with Jakarta XML Bind or alternative
3. EventHub/ActiveMQ proprietary client — must be replaced
4. Shared filesystem coupling with NAM-bank-agent — requires agreed migration to message-based or object-storage-based file exchange
5. Oracle DB two-schema pattern
6. `com.wirecard.ccpclient` dependency — tight coupling to Gen-2 CCP client library
7. Ansible/RPM deployment model
8. Jenkins sub-module embedded in repo
9. Bank account number handling in XML events — Gen-3 replacement must implement field-level encryption or tokenisation for these values
