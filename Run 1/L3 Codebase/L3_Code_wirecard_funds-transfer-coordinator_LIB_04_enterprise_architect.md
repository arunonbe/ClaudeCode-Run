# Enterprise Architect — wirecard_funds-transfer-coordinator_LIB

## Platform Generation
**Gen-2 (Wirecard/Northlane)** — Spring Boot 2.0.7, Java 8, Gradle 4.8, Nexus, Ansible/RPM deployment, Oracle DB, ActiveMQ EventHub, on-premises bare-metal/VM target.

## Business Domain
**Payments Orchestration / Disbursements** — The FTC sits within the funds-flow domain, coordinating disbursements from corporate funding accounts to card-holders or bank accounts. It is the rules-engine layer between internal event sources (CCP, card processing) and external payment rails (ACH, wire, check).

## Role in the Wirecard Platform
- Central coordinator for automated fund sweeps and scheduled disbursements
- Downstream consumer of: CCP account events, card authorisation events, incoming wire-transfer events, overdraft events, client-file events
- Upstream trigger for: check-agent, NAM-bank-agent (wire drawdown), A2A transfers (via CCP), money-remittance orders

## System Dependencies
### Inbound
| System | Protocol | Event Types |
|---|---|---|
| EventHub (ActiveMQ) | JMS/ActiveMQ | AccountStateEvent, CardAuthorizationEvent, IncomingWireTransferEvent, OverdraftUpdatedEvent, TransactionEvent, StandaloneAccountCreatedEvent, ClientFileReceivedEvent |

### Outbound
| System | Protocol | Operations |
|---|---|---|
| CCP API | REST (Feign) | reserve-money, confirm-reserve-money, cancel-reserve-money, A2A transfer, validate-s2c, create-note |
| Check-Agent API | REST (Feign) | create-check |
| Brand-Server API | REST (Feign) | brand financial institution lookup |
| EventHub (ActiveMQ) | JMS | Publishes NewDrawdownEvent, SalesOrderUpdateEvent |
| SMTP | Mail | Past-due invoice notifications |

## Integration Patterns
- **Event-Driven Architecture**: Consumes EventHub messages; publishes results back to EventHub
- **Request/Reply (sync)**: REST calls to CCP and check-agent via Feign clients with Resilience4j circuit-breaker
- **Scheduler**: Quartz clustered JDBC-backed scheduler for time-based triggers
- **Database-per-service**: Dedicated Oracle schema with two-schema pattern (data owner + app user)
- **Idempotency**: TRANSFER_REQUEST_LOG unique constraint on TRANSFER_TRIGGER_PLACEHOLDER prevents duplicate execution
- **Audit trail**: Hibernate Envers revision tables; all business tables carry audit columns

## Strategic Status
- **Current**: Active Gen-2 service in production for NAM/Northlane platform
- **Strategic fit**: The orchestration logic (configurable triggers, multi-rail) is a Gen-3 migration candidate for a cloud-native event-driven rules engine
- **Risk**: Spring Boot 2.0.7 EOL; Java 8 scheduled for sunsetting within Onbe

## Migration Blockers
1. Oracle DB with synonym/two-schema pattern — requires re-platforming to cloud-managed RDBMS or maintained Oracle Cloud
2. ActiveMQ/EventHub proprietary client (`com.wirecard.eventhub:eventhub-client:2.1.188`) — must be replaced with cloud-native messaging (Kafka, Azure Service Bus)
3. CCP client dependency (`com.wirecard.issuing:ccp-client:1.0.18`) — tight coupling to Gen-2 CCP API
4. Quartz JDBC cluster — must be replaced with cloud-native scheduler (Quartz on RDS, or Azure Scheduler)
5. Ansible/RPM deploy model — must migrate to containerised deployment (Docker/Kubernetes or ECS)
6. ISS Auth Server OAuth2 JWT key-set endpoint — must migrate to cloud-native identity provider (Azure AD B2C or equivalent)
7. Nexus artifact repo at `d-issrepo-app01.wirecard.sys` — internal hostname; not reachable from cloud
