# Data Architect Report: scheduler_WAPP

## Data Models

The scheduler stores all job and trigger state in a SQL Server database (`jobsvc`) using the standard Quartz 2 JDBC schema under the `QRTZ2_` table prefix. Key tables include:

- `QRTZ2_JOB_DETAILS` — job definitions including `JOB_DATA` blob
- `QRTZ2_TRIGGERS` — trigger metadata (cron expressions, next fire times)
- `QRTZ2_SIMPLE_TRIGGERS` / `QRTZ2_CRON_TRIGGERS` — type-specific trigger details
- `QRTZ2_FIRED_TRIGGERS` — runtime execution tracking for cluster coordination
- `QRTZ2_LOCKS` — cluster-level pessimistic locking (SELECT ... ROWLOCK)
- `QRTZ2_SCHEDULER_STATE` — per-node heartbeat for cluster membership

The `ScheduleInfo` DTO carries: `applicationName`, `scheduleId`, `scheduleTime`, `scheduleType`, `cronExpression`, `callbackPath`, `callbackType`, `callbackInputText`, `callbackInputObject` (serialised binary object).

## Sensitive Data

The scheduler does not directly store PANs, CVV, SSN, DDA account numbers, or full cardholder PII. However:

- **`callbackInputObject`** is a serialised Java object passed as part of the schedule; if calling services embed sensitive payment references in this field, those values would be stored in the Quartz job data blob in the database without any application-layer encryption
- **`callbackInputText`** is a free-form string; similar risk applies
- **Database credentials** are currently committed in plaintext in `.env` and `.env-dev` (see `scheduler-service/.env` lines 7–14): usernames and passwords are identical (`b2cstage`) for four separate database connections — CbaseApp, JobSvc, RequestDB, EcountCore

## Encryption Status

- Database connections use TLS (`sslProtocol=TLSv1.2` in QA JDBC URL; `trustServerCertificate=true` in dev, which bypasses certificate validation)
- No application-level encryption of job data blobs
- Credentials in `.env` files are plaintext; they are not encrypted or managed by a vault system at the configuration layer
- The Quartz `JOB_DATA` BLOB is Java-serialised object data, not encrypted at rest at the application level (SQL Server TDE may apply at the infrastructure layer)

## Database Schemas and Data Flows

Four SQL Server databases are referenced:

| JNDI Name | Database | Purpose |
|---|---|---|
| `jdbc/JobSvcDataSource` | jobsvc | Quartz scheduler state (primary) |
| `jdbc/CbaseappDataSource` | cbaseapp | CBase application data (indirect) |
| `jdbc/EcountCoreDataSource` | EcountCore | Core card data |
| `jdbc/OrderSvcDataSource` | Ordersvc | Order management |

The Tomcat server.xml (`scheduler-service/config/server.xml`) exposes only `JobSvcDataSource` as a JNDI resource. The other three databases are referenced in `.env` files, suggesting they are consumed by downstream callback-target services rather than by the scheduler itself.

Data flow: Calling services → HTTP Invoker (POST to `/scheduler.service`) → Quartz job creation in `jobsvc` DB → Quartz fires at trigger time → HTTP Invoker callback POST to registered `callbackPath` URL.

## Retention Concerns

Quartz JDBC store retains fired trigger history until jobs are manually removed. There is no visible data retention policy or automated purge job for `QRTZ2_FIRED_TRIGGERS` or `QRTZ2_JOB_DETAILS`. In a long-running clustered deployment this can cause unbounded growth. If job data blobs contain payment references, this constitutes an uncontrolled retention of sensitive data references with no documented deletion process, creating a PCI DSS Requirement 3 exposure.

## PCI DSS Compliance Assessment

- **Req 2 (No defaults)**: Credentials `b2cstage`/`b2cstage` resemble stage defaults left in committed files — high risk
- **Req 3 (Protect stored data)**: `callbackInputObject` could hold payment references without encryption
- **Req 4 (Encrypt in transit)**: TLS in use for QA; `trustServerCertificate=true` in dev bypasses cert validation
- **Req 7 (Access control)**: No documented role-based access control on JDBC resources; connection credentials shared across four services
- **Req 8 (Identify and authenticate access)**: Single shared credentials for multiple services; no individual accountability
