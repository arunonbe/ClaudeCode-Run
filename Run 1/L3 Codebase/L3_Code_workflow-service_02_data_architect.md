# workflow-service — Data Architect View

## Data Stores
| Store | Type | Bean ID | Purpose |
|-------|------|---------|---------|
| JobSvcDataSource | SQL Server (JNDI) | `JobSvcDataSource` | Primary workflow state database; all workflow instance, process, step, and log data |
| IBM MQ (primary profile) | JMS Queue | `workflowAgentDestination` | Async agent dispatch; workflow task execution queue |
| Director Service | Remote config service | `Director` bean | Runtime configuration retrieval (workflow keys, agent settings) |

## Schema / Tables (via Stored Procedures)
All data access goes through SQL Server stored procedures in the `dbo` schema:

| Stored Procedure | Operation | Input | Output |
|-----------------|-----------|-------|--------|
| `dbo.work_process_initiate` | Create workflow instance | `WorkProcessInitiateInput` | `WorkInstance` (instance_id) |
| `dbo.work_instance_set_state` | Update instance state | `WorkInstanceSetStateInput` | none |
| `dbo.work_get_zombie_count` | Count/identify stale instances | `WorkGetZombieCountInput` | `WorkGetZombieCountInput` result |
| `dbo.work_process_list` | List all work processes | none | `WorkProcessDefinition[]` |
| `dbo.work_process_step_list` | List steps for a process | `WorkProcess` | `WorkProcessStepDefinition[]` |
| `dbo.work_process_get_state_machine` | Get state transitions | `WorkProcess` | `WorkProcessStateMachineEntryDefinition[]` |
| `dbo.work_instance_get` | Retrieve instance definition | `WorkInstance` | `WorkInstanceDefinition` (with context XML) |
| `dbo.work_instance_get_log` | Retrieve instance log | `WorkInstance` | `WorkInstanceDefinition` (log fields) |
| `dbo.work_instance_free` | Release instance lock | `WorkInstanceDefinition` (instance_id, caller) | none |

**Log fields returned by `dbo.work_instance_get_log`:**
- `process.process_id`, `current_step.process_step_id`, `exec_agent`, `workflow_status`, `result_message`, `result_code`, `owner.control_queue_name`, `owner.control_job_id`, `last_modified`, `failed`

## Sensitive Data
- **Workflow context**: Stored as serialised XML (LONGVARCHAR) in the `work_instance` table — context may carry business-sensitive job parameters
- **`WorkflowMember`** entity exists in `workflow-common`; member data may include cardholder or account identifiers passed through workflow context — exact fields require deeper analysis of runtime context payloads
- `result_message` in workflow log may contain error details including partial data values
- Queue credentials (`workflow.agent.queue.username`, `workflow.agent.queue.password`) passed as runtime properties — external secrets required

## Encryption
- **At-rest**: No application-level field encryption configured; relies on SQL Server and MQ infrastructure-level encryption
- **In-transit**: XML-RPC over HTTP — no TLS enforcement visible at the application layer; relies on network/infrastructure controls
- **Queue credentials**: Passed via `UserCredentialsConnectionFactoryAdapter` using property-injected username/password — plaintext in properties files unless an external vault is used

## Data Flow
```
Caller (Workbench / other service)
  → XML-RPC (HTTP) 
  → WorkflowManagerServiceProxy / WorkflowAgentServiceProxy
  → WorkflowManagerImpl / WorkflowAgentDAOJDBCImpl
  → SQL Server (JobSvcDataSource) — stored procedures
  
WorkflowManager.enqueueAgent()
  → JmsTemplate
  → IBM MQ (workflowAgentQueue)
  → WorkflowAgentListenerAdapter (DefaultMessageListenerContainer)
  → WorkflowAgentImpl.executeTask()
  → WorkflowAgentDAOJDBCImpl (get next step, update state)
  → SQL Server (JobSvcDataSource)
```

Workflow context (XML dictionary) round-trips through:
```
startProcess() → LongVarcharInputConverter → stored in DB as LONGVARCHAR
work_instance_get → LongVarcharOutputConverter → deserialized as Dictionary
```

## Data Quality / Retention
- Workflow instance log entries are append-style (`work_instance_get_log`) — provides temporal audit trail
- No data retention policy is defined in the repository
- `failed` flag on instance log indicates terminal failure state for monitoring
- `last_modified` timestamp provides temporal ordering of state transitions
- The `workflowInstanceContextDictionaryParser` and `workflowInstanceContextXMLParser` suggest context serialization/deserialization — XML format; schema not enforced at application level

## Compliance Gaps
1. **Audit completeness**: Workflow logs record state transitions but not the identity of the calling user/system initiating each state change — `caller` is only in the `free` operation
2. **Queue credentials in properties files**: No secrets vault integration visible; credentials likely stored on server filesystem
3. **XML-RPC without TLS enforcement**: Data in transit including workflow context payloads is not cryptographically protected at the application layer
4. **Workflow context content**: If `WorkflowMember` carries cardholder identifiers, context XML stored in `JobSvcDataSource` may constitute CHD storage requiring PCI DSS Req 3 controls
5. **No data classification marking**: Context data schema is not documented or classified
