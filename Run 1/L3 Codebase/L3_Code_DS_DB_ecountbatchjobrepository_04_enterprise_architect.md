# DS_DB_ecountbatchjobrepository — Enterprise Architect View

## Platform Generation

`EcountBatchJobRepository` is a **Spring Batch 2.x/3.x standard JobRepository implementation** on SQL Server 2012. The schema is the canonical Spring Batch schema for SQL Server (using sequence tables `BATCH_JOB_SEQ` and `BATCH_STEP_EXECUTION_SEQ` instead of SQL Server IDENTITY columns, indicating a cross-database-compatible design). The platform represents a **second-generation batch architecture** — more structured than pure SSIS/SQL Agent, using the Spring Batch framework for Java-based batch processing on top of SQL Server persistence.

The project targets `.NET Framework 4.6.1` as the toolchain target (SSDT project metadata), while the actual runtime consumers are **Java Spring Batch applications**.

---

## Role in the Payments Architecture

The `EcountBatchJobRepository` sits at the **Batch Orchestration tier** of the platform:

```
[Batch Service Layer - Java/Spring Batch]
  ecore-batch          ──uses──> EcountBatchJobRepository (job metadata)
  prepaid-batch-framework         "
  auto-card-batch                 "
  enrollment (batch steps)        "
  scheduler_SVC                   "
  job_LIB / job-scheduler_SVC     "
                                       ↓
                          [EcountCore DB] (actual cardholder data)
                          [Ecountcore_Process DB] (staging data)
```

The `EcountBatchJobRepository` is a **cross-cutting infrastructure concern** shared by multiple batch application modules. Every Spring Batch job, regardless of business domain (card issuance, ACH processing, fee posting, notification delivery), uses this single shared database to persist execution metadata.

---

## Dependencies

| Dependency | Type | Direction | Notes |
|---|---|---|---|
| Spring Batch framework (Java) | Runtime | Consumer → DB | All batch Java apps write to this DB |
| `ecore-batch_LIB` | Application | Consumer | Core batch processing |
| `prepaid-batch-framework_LIB` | Application | Consumer | Batch framework library |
| `auto-card-batch_LIB` | Application | Consumer | Automated card batch |
| `job-scheduler_SVC` | Application | Consumer | Job scheduling service |
| `jobservice_SVC` | Application | Consumer | Job service |
| SQL Server (host) | Infrastructure | Dependency | Database server |
| `NAM\PPA_PRD_SCHSVC` | Service Account | Consumer | Scheduler service account |
| `NAM\PPA_PRD_ECORESVC` | Service Account | Consumer | Core service account |

---

## Architectural Significance

1. **Single point of contention**: All batch services share a single `EcountBatchJobRepository` database. High-volume batch runs could cause lock contention on the sequence tables (`BATCH_JOB_SEQ`, `BATCH_STEP_EXECUTION_SEQ`), which use an update-based sequence pattern rather than SQL Server IDENTITY. This is a known Spring Batch performance concern at scale.

2. **Decoupled batch identity**: Using a dedicated `JobRepository` database rather than embedding metadata in `EcountCore` is a correct architectural decision — it separates operational metadata from financial data, simplifying backup, recovery, and access control.

3. **Shared schema across multiple applications**: The single `dbo` schema with no namespacing means all batch jobs from all applications are mixed together. In a microservices migration, each batch service would ideally have its own `JobRepository` schema or database.

4. **No business logic**: This database contains no stored procedures, views, functions, or triggers beyond the table DDL. All business logic resides in the Java Spring Batch application layer. This is architecturally clean.

---

## Migration Complexity

| Dimension | Assessment |
|---|---|
| Cloud migration readiness | High — schema is simple and cloud-native databases (Azure SQL, Amazon RDS) fully support this schema |
| Spring Batch version compatibility | Medium — Spring Batch 5.x changed the `JobRepository` schema; migration requires schema upgrade scripts |
| Data migration | Low — historical job execution data has limited long-term value; a clean-slate deployment is viable |
| Access model migration | Medium — 30+ AD-based users/groups need to be migrated to Azure AD or equivalent cloud identity |
| Secrets management | No credentials stored in this database; not a blocker |

---

## Modernisation Recommendations

1. **Upgrade Spring Batch target**: Spring Batch 5.x (Spring Boot 3.x) uses an updated schema with new columns. Plan schema migration alongside Java application upgrades.
2. **Implement per-service isolation**: In a microservices context, separate `JobRepository` schemas per service (or separate databases) reduce blast radius and enable independent scaling.
3. **Move to Azure SQL / managed service**: The schema is compatible with Azure SQL Database. Managed service eliminates DBA overhead for patching and backup.
4. **Implement automated purge**: Add a scheduled stored procedure or Azure Data Factory pipeline to archive and purge execution history older than 18 months.
5. **Replace sequence tables with IDENTITY**: In SQL Server-only deployments (abandoning cross-DB compatibility), replace the sequence table pattern with SQL Server IDENTITY for better performance under high concurrency.
