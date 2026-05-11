# DS_DB_CBTS — DevOps and Operations View

## 1. Build and Release System

Unlike cbaseapp (which uses SSDT/DACPAC), CBTS uses **Liquibase** for schema migrations. The `DATABASECHANGELOG` and `DATABASECHANGELOGLOCK` tables are the runtime artefacts of Liquibase execution. This means:

- Schema changes are defined as Liquibase changesets (XML, YAML, or SQL format) in the application repository (not this database-DDL repository).
- The DDL files in this repository (`Database Objects/Tables/*.sql`) are **snapshots** of the current schema state, not the change scripts themselves.
- Deployment is driven by the Java application startup or a CI/CD pipeline step that runs `liquibase update`.

**Implication for Change Management**: Schema migrations for CBTS are owned by the application team, not the DBA team. This is a modern, developer-owned database-migration pattern appropriate for microservices.

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Application framework | Java Spring Batch |
| ORM / query | Spring Data JPA (inferred from Spring Batch metadata pattern) |
| Schema migration | Liquibase |
| Database | SQL Server (Unicode-encoded DDL, SQL Server constraint syntax) |
| Job orchestration | Spring Batch (`BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION` tables) |

---

## 3. CI/CD Assessment

No CI/CD workflow files were found in the CBTS repository. The `README.md` is empty (12 bytes). This suggests:
- The CBTS application repository (containing the Java source code and Liquibase changesets) is a separate repository not included in this analysis batch.
- Schema-change CI/CD is managed from that application repository.

**Gap**: The SQL DDL repository has no workflow files for validation or deployment. Any schema review process relies on manual inspection.

---

## 4. Environments

The security scripts provide evidence of environment-specific access grants:

- `Security/NAM UAT_admins.sql` — UAT environment admin grants
- `Security/NAM Brenda.Pereira.sql`, `Security/NAM TCS_L2.sql` — individual/team named grants (suggests manual access provisioning)
- `Security/NAM SitescopeSQL.sql` — SiteScope monitoring access
- `Security/cbts_data.sql` — data role
- `Security/cbts_user.sql` — `cbts_user` login with `db_datareader` + `db_datawriter` roles

The presence of a UAT-specific admin grant suggests at least two environments (UAT and Production) are maintained.

---

## 5. Security Configuration

From `Security/cbts_user.sql`:
```sql
CREATE USER [cbts_user] FOR LOGIN [cbts_user] WITH DEFAULT_SCHEMA=[dbo]
ALTER ROLE [db_datareader] ADD MEMBER [cbts_user]
ALTER ROLE [db_datawriter] ADD MEMBER [cbts_user]
```
The `cbts_user` service account has `db_datareader` + `db_datawriter` — appropriate principle of least privilege for an application service account (no `db_owner`, no DDL permissions).

`cbts_data.sql` defines a separate data role (contents truncated in listing — 448 bytes).

---

## 6. Monitoring

- `Security/NAM SitescopeSQL.sql` — SiteScope monitoring account, consistent with the broader Onbe SiteScope monitoring infrastructure referenced in cbaseapp's `SiteScopeLog` table.
- Spring Batch `BATCH_JOB_EXECUTION` table provides operational observability: start time, end time, exit code, exit message, and failure exception message per job run.
- `BATCH_STEP_EXECUTION` provides step-level read/write/skip/rollback counts for detailed job diagnostics.
- **Gap**: No custom monitoring stored procedures or alerting scripts were found in this repository.

---

## 7. Backup and Recovery

No backup configuration is present in this repository. CBTS backup relies on the server-level maintenance jobs in `DS_DB_database_maintenance`.

Key recovery considerations:
- Spring Batch jobs that fail mid-run can be restarted from the last committed step (Spring Batch restart capability). The `BATCH_JOB_EXECUTION_CONTEXT` and `BATCH_STEP_EXECUTION_CONTEXT` tables store the restart checkpoint.
- Transfer records in `TRANSFER` have `INSERTED_AT`/`UPDATED_AT` audit timestamps to support point-in-time recovery validation.

---

## 8. Operational Risks

### Risk 1: Empty README (LOW-MEDIUM)
The `README.md` is 12 bytes (effectively empty). There is no runbook, deployment guide, or operational documentation in the repository. This creates knowledge-dependency risk.

### Risk 2: Named Individual Access Grants in Security Scripts (MEDIUM)
`Security/NAM Brenda.Pereira.sql` and `Security/NAM TCS_L2.sql` are individual/team access grants stored in source control. If these individuals leave the organisation, the scripts remain in version history with their names. More critically, if the grants are not revoked when personnel change, access may persist beyond the period of legitimate need — a PCI DSS Req 7 (access control) violation risk.

### Risk 3: Liquibase Lock Contention (LOW-MEDIUM)
`DATABASECHANGELOGLOCK` is a single-row lock table. If a deployment fails mid-migration, the lock row remains set, blocking subsequent migrations until manually cleared. This requires a DBA intervention procedure.

### Risk 4: Plaintext Foreign Bank Account Data (HIGH)
`BENEFICIARY.ACCOUNT_NUMBER` and `ROUTING_CODE` are stored without encryption. A SQL injection attack or misconfigured access control on the CBTS database would expose foreign bank account numbers that could be used for fraudulent wire transfers.

### Risk 5: No Automated Schema Validation Pipeline (MEDIUM)
No GitHub Actions or equivalent workflow validates schema changes before merge. Liquibase changesets in the application repo could introduce breaking changes without DBA review.
