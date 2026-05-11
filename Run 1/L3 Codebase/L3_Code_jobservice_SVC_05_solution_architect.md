# Solution Architect View — jobservice_SVC

## Technical Architecture

`jobservice_SVC` is a **multi-module Maven project** producing two deployable WARs and a shared client library:

```
jobservice_SVC/
├── jobmanager-svc/       ← Service implementation (business logic, no web layer)
├── jobmanager-war/       ← WAR: includes jobmanager-svc + web.xml + Spring XML configs + Workflow embedded
├── jobmanager-client/    ← XmlRPC client library for callers
├── jobagent-svc/         ← Agent service implementation
└── jobagent-war/         ← WAR: includes jobagent-svc + action handlers + web.xml
```

### Runtime Architecture (Two-Tier)

**JobManager** (`service.war`) — Control plane:
- Spring XML-configured (no Spring Boot, no annotations-based config)
- Exposes XmlRPC endpoints via `JobManagerServiceXMLRPC`, `JobFileManagerServiceXMLRPC`, `JobProfileManagerServiceXMLRPC`
- Embeds WorkflowManager and WorkflowAgent services in the same JVM
- Reads configuration from filesystem (`CBASE_HOME_URL`) via `PropertySourcesPlaceholderConfigurer`
- Connected to: Director service, Repository service, Order service, Event service, jobsvc DB, TIBCO JMS

**JobAgent** (`JobAgentService.war`) — Data plane:
- Spring XML-configured
- Polls TIBCO JMS queue for job execution commands
- Dispatches to typed action handlers (AccountService, PaymentService, SecurityService)
- All actual cardholder/card operations delegated to downstream services via XmlRPC
- Connected to: Account service, Payment service, Security service, Director service, jobsvc DB

## API Surface

### XmlRPC Endpoints (JobManager)
- `JobManagerService` — job lifecycle: runJob, authorizeJob, endJob, resetJob, cancelJob, archiveJob, etc.
- `JobFileManagerService` — file management: loadJobFileChecker, jobValidateContent, jobCreateNotifications, etc.
- `JobProfileManagerService` — job profiles and fee calculation

XmlRPC is exposed via Apache XmlRPC server servlet. All clients use the `jobmanager-client` library which generates XmlRPC calls over HTTP. There is no REST or SOAP — only XmlRPC.

### JMS Interface (JobAgent)
- Consumes from TIBCO JMS `JOB_EXECUTION_QUEUE` (queue name inferred from configuration)
- Job execution messages contain job ID and execution parameters
- The agent processes one action at a time (checked out from `job_action` table with optimistic locking)

## Security Posture

### Authentication
- XmlRPC calls use `Member caller` objects (session/authentication token) validated by the security service. The authentication model is legacy (pre-OAuth) — session-based tokens.
- No TLS termination visible at the application layer (handled by Tomcat `server.xml` — QA cert imported into JVM truststore).
- Dual-authorization for high-value jobs: the `authorizeJob()` path requires a Banker role check before execution.

### Credential Management (Critical Gap)
Database passwords and JMS broker credentials are stored in filesystem property files at `CBASE_HOME_URL/config/`. There is no Azure Key Vault integration, no Vault, no environment variable injection for secrets. This is a **PCI DSS Requirement 8.3 finding** — hardcoded or file-stored credentials.

### Java Module System
The Dockerfile applies multiple `--add-opens` to the JVM, indicating use of internal JDK APIs by legacy libraries (XmlRPC, SOAP, JMS). This is a known risk with Java 9+ strong encapsulation and suggests some libraries are performing illegal reflective access.

## Technical Debt

| Item | Severity | Description |
|---|---|---|
| XmlRPC protocol | Critical | Apache XmlRPC is EOL since 2010. All inter-service communication uses this protocol. |
| Spring XML configuration | High | Zero annotation-based or Spring Boot configuration. All beans defined in 15+ XML context files per WAR. |
| No secrets manager | Critical | Database and JMS passwords in filesystem config files — PCI DSS non-compliant. |
| JobManager runs as root in Docker | High | No USER instruction in `jobmanager-war/Dockerfile`. |
| Tomcat version mismatch | Medium | JobAgent: 10.1.28; JobManager: 10.1.19. |
| Embedded Workflow Service | Medium | Workflow Manager and Agent embedded in JobManager WAR — tight coupling, shared JVM, harder to scale independently. |
| Java 8/21 dual-version deployment | Medium | CI/CD supports both Java 8 and 21 targets, indicating the migration is incomplete. |
| 4.0.7-SNAPSHOT version | Low | Service is SNAPSHOT — not a release artifact — in a production system. |
| `ignoreUnresolvablePlaceholders: true` | Medium | Missing configuration properties fail silently rather than preventing startup. |
| SQL timeout at 600 seconds | Low | 10-minute query timeout acceptable for batch but masks performance regressions. |
| Download Tomcat at Docker build time | Medium | `curl https://archive.apache.org/...` at build time creates network dependency and reproducibility issues. |

## Gen-3 Migration Considerations

`jobservice_SVC` has **no direct Gen-3 migration path** in the near term because:

1. Gen-3 (NexPay) is built for real-time, API-initiated payments. It has no bulk file processing capability.
2. The XmlRPC-based client library (`jobmanager-client`) is embedded in dozens of consuming services — a portfolio-wide API change.
3. The JMS execution model requires a broker migration (TIBCO → Azure Service Bus or similar).

**Recommended incremental approach**:
- **Step 1**: Replace filesystem credential management with Azure Key Vault injection (immediate PCI DSS compliance gain).
- **Step 2**: Decouple embedded Workflow Service from JobManager WAR.
- **Step 3**: Add OpenTelemetry instrumentation for observability.
- **Step 4**: Replace XmlRPC with REST/OpenAPI in a non-breaking manner (parallel deployment with adapter layer).
- **Step 5**: Migrate JMS from TIBCO to Azure Service Bus.
- **Step 6 (long-term)**: Evaluate whether the batch processing use case should be served by a Gen-3 event-driven architecture or maintained as a legacy service under an SLA-governed support contract.

## Code-Level Risks

1. **`XStream` in `manage-payment-rest-api`** dependency (`xstream:1.4.21`) — XStream has a well-documented history of CVEs related to XML deserialization. In the context of the job service XmlRPC payloads (which use XML), XStream usage must be audited.
2. **`jtds` JDBC driver** (from README) — the jTDS driver is EOL. Microsoft's `mssql-jdbc` (`12.8.2.jre11` in `manage-payment-rest-api`) should be used instead. The job service pom.xml does not specify the JDBC driver directly (resolved via `prepaid-parent`), but the README mentions jTDS.
3. **Commented-out AOP advice** in `JobConfiguration.xml` — extensive commented-out audit and tracing AOP configuration suggests these capabilities were removed. The absence of method-level audit trail is a compliance gap.
