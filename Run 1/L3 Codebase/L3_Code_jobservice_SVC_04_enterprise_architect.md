# Enterprise Architect View — jobservice_SVC

## Platform Generation

**Generation 1/2 — Core Legacy Batch Platform**

`jobservice_SVC` is the central batch processing engine of Onbe's Generation 1/2 legacy prepaid disbursement platform. It predates the Gen-3 NexPay architecture by over a decade. The service's Spring XML configuration, XmlRPC inter-service communication, JNDI/Director data source resolution, and TIBCO JMS messaging are all hallmarks of early-2010s Java EE architecture.

The Java 21 upgrade (in progress, as evidenced by the dual Java 8/21 deployment workflow) and Tomcat 10.x containers represent modernisation steps within the Gen-2 constraint — not a migration to Gen-3.

## Business Domain

**Batch Disbursements — Core Payment Processing**

This service owns the `batch disbursement` subdomain within Onbe's payments business. It is the operational backbone for every dollar disbursed via file-based batch (insurance claims, rebates, incentives, payroll supplements). This domain is distinct from the Gen-3 real-time NexPay domain — it will coexist with Gen-3 until Onbe's client portfolio migrates from file-based to API-based disbursements.

## Position in the Architecture

```
[Client SFTP / Banker Web Portal]
         │ file upload
         ▼
[Repository Service] ←────────── reply files (out)
         │ loadJobFileChecker()
         ▼
[JobManager WAR] ←───── JobManager Client (used by Banker API, ClientZone, etc.)
  │ validate, authorize, runJob()
  │ state transitions in jobsvc DB
  │ JMS publish (TIBCO)
  ▼
[TIBCO JMS Queue]
  │
  ▼
[JobAgent WAR] ×2 (parallel workers on q-app08, q-app09)
  │ action handlers
  ├──→ [Account Service] → cbaseapp DB (register, issue card, add funds)
  ├──→ [Payment Service] → payment DB (create certificate)
  └──→ [Security Service] → (user management)
         │
         ▼
  [Director Service] ← all services route through Director for data source resolution
```

## Dependencies

### Inbound (Consumers of JobService)
| Service | Interface | Usage |
|---|---|---|
| `banker_API` | `jobmanager-client` (XmlRPC) | Batch file management, job lifecycle control |
| `clientapi_API` | `jobmanager-client` | Client-facing job management |
| `autofile_SVC` | `autofile-common` | Automated file ingestion via SFTP |
| `js-import_SVC` | Job creation API | Import-based job initiation |

### Outbound (Dependencies)
| Service | Interface | Purpose |
|---|---|---|
| Director Service | HTTP/XmlRPC | Data source resolution, system config |
| Account Service | XmlRPC | All card/account operations |
| Payment Service | XmlRPC | Certificate/payment creation |
| Security Service | XmlRPC | User management actions |
| Repository Service | XmlRPC | File storage/retrieval |
| Order Service | XmlRPC | Order orchestration |
| Profile Service | XmlRPC | Cardholder profile |
| Event Service | XmlRPC | Event publication |
| Workflow Service | Embedded (same WAR) | Workflow management |
| TIBCO JMS | JMS | Job execution queue |
| jobsvc DB | JDBC (stored procs) | Job state persistence |
| cbaseapp DB | JDBC (via Account Svc) | Cardholder data |

## Integration Patterns

- **XmlRPC**: All inter-service communication uses Apache XmlRPC over HTTP — a 2003-era RPC protocol. No REST, no gRPC, no message streaming.
- **JMS fan-out**: Job execution uses JMS for worker-level parallelism across multiple JobAgent instances.
- **Directory Service**: The `director-client` acts as a service registry and data source resolver — a proprietary alternative to Kubernetes service discovery or Consul.
- **Workflow co-deployment**: The JobManager WAR embeds the Workflow Service, creating a monolithic deployment where job management and workflow management share a JVM.

## Strategic Status

**Stable / Maintenance — Not on Gen-3 Migration Path (Near Term)**

The service is actively maintained (recent updates: Spring 6.2.11, Java 21, Tomcat 10.x, Jakarta EE namespace dependencies). This is a production-critical service processing all client batch disbursements.

There is no Gen-3 equivalent for bulk file processing. The `manage-payment-rest-api` provides real-time API equivalents for some operations (createAccount, addFunds) but does not replace the bulk file processing pipeline. A Gen-3 batch capability would require substantial new development.

The service is therefore a **long-lived legacy service** that will remain in operation for the foreseeable future alongside Gen-3 services.

## Migration Blockers

| Blocker | Impact | Path |
|---|---|---|
| XmlRPC inter-service protocol | High | All dependent services (banker_API, clientapi_API, and others) must migrate off XmlRPC simultaneously — a portfolio-wide coordination effort |
| TIBCO JMS broker dependency | High | Requires replacement with cloud-native messaging (Azure Service Bus, Event Hubs) |
| Director Service coupling | High | Data source resolution via Director must be replaced with direct connection string / Key Vault injection |
| Embedded Workflow Service | Medium | Workflow Manager and Agent should be decoupled from the JobManager WAR before any modernisation |
| File-based client integration | Medium | Client programs using SFTP-based file submission must be migrated to API-based submissions |
| Dual Java 8/21 infrastructure | Medium | Resolution of the Java 8 → Java 21 migration must complete before any further modernisation |

## Compliance Architecture

- **PCI DSS Req 6 (Security development)**: Spring 6.2.11 and Java 21 upgrade reduces CVE exposure. However, remaining Axis/XStream/legacy library dependencies carry unpatched CVEs.
- **PCI DSS Req 8 (Access control)**: Credentials stored in filesystem configuration files (`CBASE_HOME_URL/config/`) — not in a secrets manager. This is a PCI DSS Req 8.3 finding.
- **PCI DSS Req 10 (Audit logging)**: No structured, queryable audit log for job lifecycle events. Log4j2 file logging is not equivalent to a compliance-grade audit trail.
- **Reg E**: The job action audit trail in `job_action` provides a transaction record for each disbursement. Failed actions with `job_action_error` records provide the error resolution basis.
- **NACHA**: All ACH-equivalent operations (fund loads, withdrawals) are channelled through this service. The service's reliability directly affects NACHA settlement obligations.
