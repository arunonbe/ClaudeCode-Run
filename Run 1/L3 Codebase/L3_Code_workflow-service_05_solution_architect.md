# workflow-service — Solution Architect View

## Technical Architecture
- **Module structure**: 4-module Maven project
  - `workflow-common`: Domain model (value objects, service interfaces, exception hierarchy, result codes)
  - `workflowmanager-svc`: Manager implementation, JDBC DAO, stored procedure adapters, JMS producer
  - `workflowagent-svc`: Agent implementation, JMS consumer, step execution definitions, delegate interfaces
  - `workflow-xmlrpc`: XML-RPC endpoint layer, Spring MVC controllers, proxy beans for inbound calls
- **Java version**: 21 (POM); Jenkinsfile references JDK 8 — version mismatch
- **Spring**: Inherited from `prepaid-parent:6.0.13`; uses `spring-context`, `spring-webmvc`, `spring-jms`, `jakarta.transaction`
- **Persistence**: Spring JDBC `JdbcTemplate` with custom `AnnotatedStoredProcedureImpl` wrapper; all SQL via stored procedures
- **Messaging**: JMS via Spring `DefaultMessageListenerContainer` + `JmsTemplate`; primary broker is IBM MQ (`com.ibm.mq.jms.MQQueueConnectionFactory`)
- **Remote protocol**: XML-RPC for both inbound (exposing service operations) and outbound (orderxmlrpcclient)
- **AOP**: AspectJ (`aspectjrt`, `aspectjweaver`) — likely used for transaction demarcation or logging

## API Surface

### Inbound XML-RPC Methods (via `WorkflowManagerServiceXMLRPC.xml` and `WorkflowAgentServiceXMLRPC.xml`)
| RPC Method | Implementation |
|-----------|----------------|
| `WorkflowService.WorkflowManager.StartProcess` | `WorkflowManagerServiceProxy.startProcess()` |
| `WorkflowService.WorkflowManager.SetWorkInstanceState` | `WorkflowManagerServiceProxy.workInstanceSetState()` |
| `WorkflowService.WorkflowManager.TurnZombies` | `WorkflowManagerServiceProxy.turnZombies()` |
| `WorkflowService.WorkflowManager.GetWorkProcessList` | `WorkflowManagerServiceProxy.getWorkProcessList()` |
| `WorkflowService.WorkflowManager.GetWorkProcessStepList` | `WorkflowManagerServiceProxy.getWorkProcessStepList()` |
| `WorkflowService.WorkflowManager.GetWorkProcessStateMachine` | `WorkflowManagerServiceProxy.getWorkProcessStateMachine()` |
| `WorkflowService.WorkflowManager.GetWorkInstanceDefinition` | `WorkflowManagerServiceProxy.getWorkInstanceDefinition()` |
| `WorkflowService.WorkflowManager.GetWorkInstanceLog` | `WorkflowManagerServiceProxy.getWorkInstanceLog()` |
| `WorkflowService.WorkflowManager.FreeWorkInstance` | `WorkflowManagerServiceProxy.freeWorkInstance()` |
| `WorkflowService.WorkflowAgent.ExecuteTask` | `WorkflowAgentServiceProxy.executeTask()` |

### Outbound
- JMS queue write via `JmsTemplate` → `workflowAgentDestination`
- JMS consume via `DefaultMessageListenerContainer` → `workflowAgentListenerAdapter`
- SQL Server via `JdbcTemplate` → stored procedures

## Security Posture

### Authentication
- No authentication/authorization configuration is visible in this repository for the XML-RPC endpoint
- The service likely relies on network-level controls (firewall, VPN) for access restriction
- JMS connection uses `UserCredentialsConnectionFactoryAdapter` with property-injected username/password — credentials must be secured in the runtime environment

### Authorisation
- No role-based access control defined at the service layer
- All callers that can reach the XML-RPC endpoint can invoke any operation

### Crypto
- No encryption configured at the application layer
- XML-RPC traffic presumed to travel over internal network; no TLS enforcement visible
- JMS connection credentials passed in plaintext properties

### Secrets Management
- IBM MQ credentials (`workflow.agent.queue.username`, `workflow.agent.queue.password`) are injected via property files — file must be secured at OS level
- No vault, Kubernetes secret, or Azure Key Vault integration visible

### Known CVE Risks
| Component | Risk |
|-----------|------|
| jtds (SQL Server JDBC driver) | Older driver; may have known CVEs depending on version pinned in `prepaid-parent` |
| commons-dbcp | Older version likely; connection pool with potential DoS/resource leak CVEs |
| IBM MQ client | Version not visible; may have security patches pending |

## Technical Debt
1. **XML-RPC protocol**: Non-standard, not REST/gRPC; limited tooling, no OpenAPI spec, no contract testing
2. **Java version mismatch**: POM says Java 21 but Jenkinsfile deploys with JDK 8 — produces incorrect bytecode
3. **Tests skipped in CI**: All stages use `-Dmaven.test.skip=true`
4. **No input validation** visible in XML-RPC input DTOs — risk of malformed input causing SQL/runtime errors
5. **Custom stored procedure wrapper** (`AnnotatedStoredProcedureImpl`): Proprietary abstraction with no standard support
6. **`Dictionary` type in API** (`IWorkflowManager.startProcess` uses `java.util.Dictionary`) — deprecated Java type since Java 1.2; indicates very old API design
7. **Author attribution**: `@author OFSS` (Oracle Financial Software Services) — offshore development origin; code comment date Nov 2010
8. **IBM MQ-specific classes at default profile**: Tight coupling to IBM proprietary JMS classes; no abstraction behind `javax.jms` interface
9. **No health or readiness endpoint** for the service

## Gen-3 Migration Requirements
1. Replace XML-RPC transport with REST API (Spring Boot 3.x, OpenAPI 3.0 spec)
2. Replace IBM MQ with cloud-native messaging (Azure Service Bus or EventGrid) with standard JMS or SDK
3. Replace `Dictionary` context with typed POJO/JSON payload
4. Replace SQL Server stored procedures with JPA repository or JDBC query methods with schema ownership
5. Implement OAuth2/JWT authentication for all inbound service calls
6. Inject secrets via Azure Key Vault or Kubernetes secrets instead of property files
7. Implement structured logging with correlation IDs (OpenTelemetry)
8. Add health/readiness/liveness endpoints (Spring Actuator)
9. Containerize with Docker; define resource limits and readiness probes
10. Consider replacing bespoke state machine with a managed workflow engine (Temporal, Azure Durable Functions)

## Code-Level Risks (file:line references)
| Risk | File | Line |
|------|------|------|
| `Dictionary` context type (deprecated since Java 1.2) | `workflow-common/src/main/java/com/ecount/workflow/service/IWorkflowManager.java` | 42 |
| No caller identity in `freeWorkInstance` — audit gap | `workflow-common/src/main/java/com/ecount/workflow/service/IWorkflowManager.java` | 115 |
| JDK8 reference in Jenkinsfile | `Jenkinsfile` | 7–10 |
| IBM MQ plaintext credentials via property injection | `workflowagent-svc/src/main/filters/ibmmq/resources/queue/WorkflowAgentListener.xml` | 25–26 |
| `sessionTransacted=true` without visible XA config | `workflowagent-svc/src/main/filters/ibmmq/resources/queue/WorkflowAgentListener.xml` | 42 |
