# job_LIB — Data Architect View

## Data Stores

| Store | Type | Access Pattern |
|---|---|---|
| `jobsvc` (SQL Server) | Relational (Microsoft SQL Server) | JDBC via Spring `JdbcDaoSupport`; all writes via stored procedures |

The data source is injected as `JobSvcDataSource` via Spring XML context (`appCtx-job.xml`) and resolved at deployment time — no connection string is present in source code.

## Schema / Tables

### `job_account_map`
Direct SQL read: `SELECT partner_user_id, ecount_id, emember_id, is_encoded FROM job_account_map WHERE ecount_id = cast(? as varchar)`

| Column | Type | Notes |
|---|---|---|
| `partner_user_id` | VARCHAR | Client's external user identifier |
| `ecount_id` | VARCHAR | Internal ecount account identifier |
| `emember_id` | VARCHAR | Internal eMember identifier |
| `is_encoded` | TINYINT | 0 = plain, 1 = encoded/encrypted PUID |

### `job_statistics` (read-only view/table)
Read via: `SELECT * FROM job_statistics WHERE [job.job_id] = ?`

| Column | Mapped Field |
|---|---|
| `job.stats.action_failed` | actionFailed |
| `job.stats.action_processed` | actionProcessed |
| `job.stats.action_remaining` | actionRemaining |
| `job.stats.action_skipped` | actionSkipped |
| `job.stats.percent_complete` | percentComplete |

### `simplesolve_versionvalidation`
`SELECT validation_version FROM [simplesolve_versionvalidation] WHERE validation_id=?`

### Stored Procedures (all reside in the `jobsvc` database)
- `job_account_map_set2` — upsert JAM record
- `job_account_map_get2` — retrieve JAM record by PUID
- `job_account_map_delete_locked` — delete null lock entry
- `job_account_map_update2` — update PUID
- `dbo.job_account_map_getpuids` — bulk lookup
- `job_get_bulk_batch_id` — retrieve batch ID by ecount ID
- `instant_issue_card_get_status` — retrieve instant-issue card status

## Sensitive Data

| Field | Classification | Risk |
|---|---|---|
| `partner_user_id` | Cardholder-adjacent PII | Links to card programme participant; could be SSN-derived or email in some programmes |
| `ecount_id` | Internal account identifier | Ties to cardholder account in EcountCore |
| `emember_id` | Internal member identifier | Ties to cardholder registration record |
| `is_encoded` flag | Indicator of encoded PUID | Presence implies some PUIDs have been encrypted |

No PAN, CVV, or track data is stored or transmitted through this library.

## Encryption

- The `is_encoded` flag indicates that PUIDs may be stored in an encrypted/encoded form in the database. The encoding/decoding logic is handled inside stored procedures (`job_account_map_set2`, `job_account_map_get2`), not in Java code — meaning key management is DB-side.
- No application-layer encryption is present in this library's Java code.
- Transport encryption (TLS) depends on the JDBC driver and SQL Server configuration; it is not enforced in library code.

## Data Flow

```
[Caller Service]
      |
      v
[JobManagerImpl]
      |
      +--> [JdbcJobAccountMapDao]  --> SP: job_account_map_set2 / get2 / delete_locked / update2 / getpuids
      |                                    [jobsvc SQL Server database]
      +--> [JdbcJobDao]            --> Direct SQL on job_statistics, simplesolve_versionvalidation
      +--> [JdbcSymbolDao]         --> Symbol table lookup
      |
      v
[AgentCachingJobManagerClient] (optional JMS remoting path)
      |
      v
[JMS Destination: ${service.job.manager.jms.destination}]
      |
      v
[Remote JobManager service instance]
```

## Data Quality and Retention

- No data validation logic exists within the Java library for inputs (ecountId, PUID, programId). Validation is delegated to stored procedures which return numeric error codes.
- No TTL, archival, or purge policies are defined in this library; retention is entirely governed at the database layer.
- The `job_statistics` table is read-only from the library's perspective; population is handled by the job service itself.

## Compliance Gaps

1. **PCI DSS Req 3.4**: The encoding flag (`is_encoded`) implies PUIDs are sometimes stored obfuscated, but the encoding algorithm is opaque (inside stored procedures). No evidence of strong encryption (AES-256) in the Java code layer.
2. **PCI DSS Req 6.4 / OWASP**: Inline SQL in `JdbcJobDao` (`SELECT * FROM job_statistics WHERE [job.job_id] = ?`) uses parameterised queries — acceptable. However, the `getPuids` call passes a raw comma-delimited string `ecountIds` to `dbo.job_account_map_getpuids`; if the SP does not use parameterised SQL internally this is a SQL injection risk.
3. **Audit logging**: No audit trail for JAM mutations in the Java layer; relies on database-level triggers or logging if any.
4. **Data minimisation**: `writeCreateAccountAction` in `BatchFile.java` (in the integration libraries) accepts full name, address, and phone — but this is in the integration library, not job_LIB directly.
