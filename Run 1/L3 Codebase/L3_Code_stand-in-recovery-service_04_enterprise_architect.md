# 04 Enterprise Architect — stand-in-recovery-service

## Platform Generation
Gen-3. Spring Boot 3.5.5, Java 21, Azure-native (Azure SQL, Azure Service Bus, Azure Key Vault, Azure API Management), containerised (Docker), GitHub Actions CI/CD. This is the most modern service in the analysed estate.

## Business Domain
Payments Infrastructure / Card Issuance Resilience. STIP stand-in recovery is a Visa/Mastercard network rule requirement for authorisation continuity; this service directly supports Onbe's obligations as a card programme manager and PCI DSS Level 1 service provider.

## Role
Singleton recovery orchestrator. Manages the complex state machine of switching the card and DDA number allocation authority back from STIP stand-in mode to the primary SASI/Legacy allocators after a network or system outage, ensuring no duplicate card or DDA numbers are issued across the boundary.

## Dependencies
| Dependency | Direction | Criticality |
|---|---|---|
| Azure Service Bus (session queue) | Inbound | Critical — recovery message source |
| sasi Azure SQL DB | Bidirectional | Critical — session/snapshot/message state |
| cbaseapp SQL Server (on-prem) | Bidirectional | Critical — card/DDA serial state |
| AccountManagementAPI (`3.1.7`) | Outbound | Critical — card activation replays during recovery |
| DebitAPI (`3.1.4`) | Outbound | Critical — debit transaction replays |
| CSAPI v3 (`3.1.13`) | Outbound | High — customer service operations |
| ecountcore SQL Server | Outbound | High — eCount core data |
| ordersvc SQL Server | Outbound | Medium — order data |
| Azure Key Vault | Outbound | Critical — all credentials |
| Azure APIM | Inbound | High — external API gateway |
| Wirecard internal PKI | Runtime | High — on-prem TLS |

## Integration Patterns
- **Event-driven (Azure Service Bus sessions)**: recovery messages are session-keyed, ensuring ordered processing per card/DDA number session
- **REST API**: `RecoveryServiceController` exposes session lifecycle management and status endpoints
- **Snapshot pattern**: captures point-in-time serial state before recovery begins; provides rollback reference
- **Saga / compensation**: session start/end orchestrates processor lifecycle across multiple Azure Service Bus consumers
- **Multi-database fan-out**: reads from and writes to 5 separate SQL Server databases across cloud and on-premises

## Strategic Status
**Active — strategic. Invest and maintain.** This service is a Gen-3 greenfield implementation addressing a genuine payment network resilience requirement. It is the bridge between the legacy Wirecard on-prem infrastructure and the modern Azure-hosted platform. Its stability is critical to Onbe's ability to meet network rules during infrastructure switchovers.

Key risks to strategic health:
- The remaining `@Deprecated` endpoints in the controller should be removed in a near-term release
- The on-premises SQL Server connections (`trustServerCertificate=true`) create a hybrid-cloud security gap; full migration to Azure SQL for all data stores is the target state
- The Gen-3 migration of cbaseapp and ecountcore (which this service depends on) is a prerequisite for fully retiring the Wirecard on-prem network dependency

## Migration Blockers
- cbaseapp and ecountcore on-premises SQL Server databases must be migrated or replicated to Azure SQL before the Wirecard network dependency can be eliminated
- AccountManagementAPI, DebitAPI, and CSAPI v3 must remain available at their current endpoints during any infrastructure migration
- The Azure Service Bus session-enabled queue configuration (session IDs, max concurrency = 75) must be validated and potentially reconfigured for any change in message volume
- The Wirecard CA certificate (`nam.wirecard.sys.crt`) bundled in the Docker image must be replaced when the Wirecard on-prem PKI is decommissioned
