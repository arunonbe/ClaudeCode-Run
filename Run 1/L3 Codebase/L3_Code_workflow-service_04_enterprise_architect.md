# workflow-service — Enterprise Architect View

## Platform Generation
**Gen-2** — Transitional generation with mixed signals.

Evidence for Gen-2 (modernized but not cloud-native):
- Java 21 compilation target (modern)
- Spring framework (spring-context, spring-webmvc, spring-jms) from `prepaid-parent:6.0.13`
- Jakarta EE namespace (`jakarta.transaction`, `jakarta.servlet`) — post-Java EE 8 migration
- AspectJ used for AOP (reasonable, non-legacy)
- XML-RPC transport layer is legacy but the service implementation itself is modern Spring

Evidence of legacy roots (Gen-1 inheritance):
- XML-RPC remote procedure call protocol — not REST, not gRPC
- JMS queue-based agent dispatch using IBM MQ (enterprise messaging bus typical of mid-2000s J2EE)
- Custom Dictionary-based context serialization (XML format)
- Jenkinsfile references `JDK1.8` tool and `D:\\c-base\\JDK-AWS-8` — legacy deployment infrastructure
- Parent POM namespace `com.parents:prepaid-parent` and client namespaces `com.citi.prepaid.*` — Citi/Wirecard era

## Business Domain
**Core Platform — Batch Processing Orchestration**

The workflow service sits at the center of Onbe's batch payment processing pipeline. It coordinates:
- Job load workflows (file ingestion, structure validation, content validation)
- Job preparation workflows
- Job processed workflows (order creation, payment award, notification)

This is a **platform infrastructure service**, not a business-facing capability in isolation.

## Role in Platform
- **Workflow orchestration hub**: All batch file processing passes through this service's state machine
- **Integration point**: Receives commands via XML-RPC from Workbench (operator overrides) and from batch job services
- **JMS consumer/producer**: Writes to and reads from the workflow agent JMS queue
- **Director client**: Reads runtime configuration from the Director service
- Consumed by: `workbench_WAPP` (operator control), batch job services (automated progression)

## Dependencies
**Inbound consumers:**
| Consumer | Interface |
|----------|-----------|
| workbench_WAPP | XML-RPC (WorkflowService.WorkflowManager.*) |
| Batch job services | XML-RPC (WorkflowService.WorkflowAgent.ExecuteTask) |
| Scheduler service | XML-RPC (TurnZombies, StartProcess) |

**Outbound calls:**
| Dependency | Type |
|-----------|------|
| SQL Server (JobSvcDataSource) | JDBC stored procedures |
| IBM MQ / TIBCO / ActiveMQ | JMS (agent queue) |
| Director Service | Remote config (`getAgentSetting`) |
| Profile Service (`profile-client`) | Remote |
| Repository Service (`repository-client`) | Remote |
| ecount-core (`ecount-core-client`) | Remote |
| Event Service (`eventserviceclient`) | Remote |
| Order XML-RPC (`orderxmlrpcclient`) | XML-RPC |
| Notification Service (via `INotificationServiceDelegate`) | Remote |

## Integration Patterns
- **XML-RPC**: Primary inbound/outbound integration protocol; custom Spring-based XML-RPC framework (`com.citi.prepaid.service.core:xmlrpc`)
- **JMS (IBM MQ, TIBCO, WebLogic, ActiveMQ)**: Async agent execution; Spring `DefaultMessageListenerContainer` with transacted session
- **Spring stored procedure abstraction**: All persistence through annotated stored procedure wrappers
- **Director pattern**: Runtime configuration loaded from central Director service — enables environment-specific tuning without redeployment
- **State machine pattern**: Workflow process definitions stored in database; transitions validated at runtime via `work_process_get_state_machine`

## Strategic Status
**Maintain / Partial Migration Candidate**

- The service has been partially modernized (Java 21, Jakarta EE namespaces) indicating active investment
- XML-RPC transport is legacy and limits interoperability with modern HTTP/REST clients
- JMS messaging infrastructure with IBM MQ is robust but heavy; migration to lighter messaging (Azure Service Bus, RabbitMQ) may be desirable
- The workflow pattern itself could be replaced with a managed workflow service (Azure Durable Functions, Temporal, Camunda) for Gen-3
- Core workflow logic in `workflowmanager-svc` and `workflowagent-svc` could be extracted and re-exposed via REST

## Migration Blockers
1. **XML-RPC protocol**: All callers (Workbench, batch services) use XML-RPC; migration requires updating all consumers simultaneously or building an adapter layer
2. **IBM MQ coupling**: All four JMS profiles reference IBM-specific classes for the default (IBMMQ) profile; migration to cloud-native messaging requires queue migration and consumer re-testing
3. **Director service dependency**: Runtime config resolution from Director is not replaceable without understanding the Director service's config schema and availability
4. **Custom XML context serialization**: `WorkflowInstanceContextDictionaryParser` / `WorkflowInstanceContextXMLParser` — bespoke serialization format; no schema documentation visible
5. **Database stored procedures**: All data access is via SQL Server stored procedures — tightly coupled to SQL Server; migration to another RDBMS or cloud data store requires procedure rewrite
6. **Distributed transactional model**: JMS session is transacted (`sessionTransacted=true`) with SQL Server operations — XA or local transaction coordination; cloud-native equivalent requires careful design
