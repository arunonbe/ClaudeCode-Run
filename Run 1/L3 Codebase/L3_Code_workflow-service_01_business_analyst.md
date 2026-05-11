# workflow-service — Business Analyst View

## Business Purpose
The Workflow Service is an internal business process orchestration engine for Onbe's prepaid payment platform. It manages the lifecycle of payment-related batch jobs through a state-machine-driven workflow, coordinating the sequential execution of processing steps (job load, preparation, processing) across distributed systems. It is the automation backbone for batch file operations — including payment card load, disbursement file processing, and order creation workflows.

## Capabilities
- **Process Initiation**: Start a named workflow process at a specified step for a given execution agent
- **State Management**: Advance or update the state of a workflow instance through defined transitions
- **Zombie Recovery**: Identify and reprocess workflow instances that have stalled (turned idle/"zombie") beyond a timeout threshold
- **Agent Dispatch**: Enqueue agent execution commands to a JMS message queue (IBM MQ, TIBCO, WebLogic, or ActiveMQ)
- **Process Introspection**: Query available work processes, their step lists, and state machine transition maps
- **Instance Tracking**: Retrieve instance definitions, execution logs, and free locked instances
- **Notifications**: Send email/notification on workflow events (content failed, structure failed, file receipt, pending finance)
- **Job Steps** (inferred from workflowagent-svc step definitions): Assign record IDs, award spin payments, create job orders, create notifications, create status reports (content failed, structure failed, file receipt, pending finance)

## Key Entities
| Entity | Description |
|--------|-------------|
| WorkProcess | Named workflow process definition (e.g., job load, job preparation, job processed) |
| WorkProcessDefinition | Metadata definition of a work process |
| WorkProcessStepDefinition | A single step within a process, with ordering |
| WorkProcessStateMachine | Set of valid state transitions for a process |
| WorkProcessStateMachineEntry / EntryDefinition | A single valid transition rule |
| WorkInstance | A running instance of a workflow process (identified by `instance_id`) |
| WorkInstanceDefinition | Full definition of a running instance including context, current step, owner |
| WorkInstanceLog | Audit log of a workflow instance (process, step, agent, status, result code, timestamps) |
| WorkInstanceOwner | The controlling job/queue that owns a running instance (`control_queue_name`, `control_job_id`) |
| WorkflowMember | Member (cardholder/account) associated with a workflow step |
| SubmissionChannelCodes | Enumeration of channels through which work is submitted |

## Business Rules
- Workflow execution is agent-based: an `execAgent` string identifies the processing agent that will claim and execute a workflow step
- State transitions are governed by the `WorkProcessStateMachine`; only valid transitions (as defined in `dbo.work_process_get_state_machine`) are allowed
- Zombie timeout: instances idle beyond a configurable timeout are re-queued via `turnZombies(timeout, execAgent)`
- Instances must be explicitly freed (`freeWorkInstance`) to be made available for other processes — prevents concurrent execution conflicts
- Notification emails originate from a configurable `notification.from.email.id`
- Workflow configurations (process keys, agent keys) are retrieved from a Director service at runtime — dynamic configuration, not hardcoded

## Key Flows
1. **Normal Execution**: External caller → `startProcess(process, step, execAgent, context)` → `dbo.work_process_initiate` → instance created → JMS message enqueued → `WorkflowAgent.executeTask()` → step logic executed → `workInstanceSetState()` → next step or completion
2. **Zombie Recovery**: Scheduler/caller → `turnZombies(timeout, execAgent)` → `dbo.work_get_zombie_count` → stale instances identified → re-enqueued to agent queue
3. **Manual Override (from Workbench)**: Operator → Workbench `WorkflowInstanceStatusUpdateAction` → XML-RPC call → `WorkflowService.WorkflowManager.SetWorkInstanceState` → `dbo.work_instance_set_state`
4. **Instance Rollback (from Workbench)**: Operator → `WorkflowInstanceRollbackAction` → XML-RPC → state set to rollback state
5. **Free Instance**: Operator or system → `FreeWorkInstance` XML-RPC call → `dbo.work_instance_free` → instance released

## Compliance Considerations
- Workflow instance logs (`dbo.work_instance_get_log`) record `process_step_id`, `workflow_status`, `result_code`, `result_message`, `last_modified`, `failed` — provides an audit trail for batch processing actions
- The `control_job_id` and `control_queue_name` in `WorkInstanceOwner` link workflow instances back to the originating batch job, enabling traceability
- Email notifications from `notification.from.email.id` should comply with corporate communications policies

## Business Risks
- **Zombie processing**: If zombie recovery is not scheduled regularly, stale instances accumulate and processing backlogs grow
- **Single-queue design**: The workflow agent queue is a single named queue; failures in queue connectivity will halt all workflow execution
- **No SLA enforcement visible**: No timeout escalation or SLA breach alerting is defined in the codebase
- **Notification-on-failure only**: Notifications are triggered on failure states (content failed, structure failed) — no success notification observable
