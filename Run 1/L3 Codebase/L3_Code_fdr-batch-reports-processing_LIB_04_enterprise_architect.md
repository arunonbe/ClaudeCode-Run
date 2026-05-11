# Enterprise Architect View — fdr-batch-reports-processing_LIB

## Platform Generation and Role

**Platform Generation**: Gen-1 (legacy on-premises batch processing)  
**Integration Partner**: FDR / First Data Resources (now Fiserv) — Onbe's primary debit card processor  
**Role in Architecture**: Financial reconciliation bridge between FDR card processing reports and Onbe's internal job service

This library is a **Gen-1 Fiserv integration component**. It was built during the ecount era (package prefix `com.ecount.batch.fdr`) and represents the original prepaid card processor integration at Onbe. Its architectural role is to close the data loop between what FDR has processed (batch card creations and fund loads) and what Onbe's internal systems need to know to complete disbursement workflows.

## Position in the Fiserv Integration Architecture

```
[Fiserv / FDR Card Processor]
    |
    | Batch file delivery (RMS28 format or equivalent)
    | (handled by separate import jobs, not in this library)
    v
[EcountCore DB: Staging Tables]
  - fdr_batch_creation_report
  - fdr_dda_account_journal
  - fdr_batch_add_funds_queue
    |
    | fdr-batch-reports-processing_LIB (this library)
    v
[JobSvc DB: Job Processing Tables]
  - job_fdr_batch_creation_report
  - job_member_recent_commited_transfers
    |
    | Stored procedures (job_fdr_batch_creation_report_process, etc.)
    v
[CBaseApp DB: Core Application]
  - batch_message_status
    |
    v
[Downstream: Notification, Card Management, Reconciliation]
```

## Integration Pattern Classification

This library implements a **database-to-database ETL** (Extract, Transform, Load) pattern, which is characteristic of Gen-1 architectures:
- No message queues.
- No REST APIs.
- No event streaming.
- All integration is via direct JDBC connections to multiple databases.
- Coordination is via database tables and stored procedures.

This is in stark contrast to the Gen-3 pattern demonstrated in `exemplar-theater-service_WAPP`, which uses Dapr pub/sub, REST APIs, and JPA.

## FDR Integration Context

FDR (First Data Resources, acquired by Fiserv in 2019) is a card processor that delivers batch report files (typically fixed-width flat files in formats like RMS28) to its clients. The `FDRReports_LIB` repository handles the initial parsing of those files. This library (`fdr-batch-reports-processing_LIB`) handles the **secondary processing** — reading the already-imported data from staging tables and routing it into Onbe's job processing pipeline.

The pre-processing stored procedures (`fdr_batch_creation_report_import`, `fdr_batch_creation_report_process`) that this library calls represent the interface between the file-parsing layer and the report-reading layer.

## Migration Complexity Assessment

**Migration Complexity: HIGH**

This library is deeply integrated into Onbe's Gen-1 data architecture:

1. **Database coupling**: Four databases, multiple stored procedures. Any migration requires simultaneous changes to EcountCore, JobSvc, and CBaseApp databases.

2. **Stored procedure dependencies**: Pre- and post-processing stored procedures (`fdr_batch_creation_report_import`, `fdr_batch_creation_report_process`, `job_member_recent_commited_transfers_process`, `job_fail_lingering_batch_actions`, `batch_messages_status_process`, `job_mark_batch_job_complete`) contain business logic that is not in this repository. These must be inventoried and refactored as part of any migration.

3. **FDR contract coupling**: The data structures (field names, DDA journal schema, add-funds queue schema) are dictated by Fiserv's reporting format. Any platform migration must maintain compatibility with Fiserv's delivery format.

4. **No abstraction layer**: The library directly references specific database table and column names via configuration properties. There is no domain abstraction or anti-corruption layer between the FDR data model and Onbe's internal model.

5. **Java 1.5 compilation target**: Cannot run on modern JVM without recompilation. Requires modernization before containerization.

## Recommended Migration Path

For a Gen-1 to Gen-3 migration:

1. **Phase 1**: Lift-and-shift with dependency upgrades (Java 17, Log4j 2.x, replace jTDS with Microsoft JDBC Driver, remove credential logging). Run on existing infrastructure.

2. **Phase 2**: Extract stored procedure logic into Java/Spring Batch service code. Replace direct DB calls with service API calls or events.

3. **Phase 3**: Implement as a Spring Batch job (using Spring Batch framework) with proper job repository, retry semantics, and monitoring.

4. **Phase 4**: Replace database-to-database integration with event-driven integration via Dapr pub/sub (consistent with Gen-3 pattern). FDR file delivery triggers an event; consumers update their own databases.

## Dependency Map

| Dependency | Version | Status |
|-----------|---------|--------|
| `log4j:log4j` | 1.2.14 | EOL, Critical CVEs |
| `net.sourceforge.jtds:jtds` | 1.2.2 | EOL, superseded by `com.microsoft.sqlserver:mssql-jdbc` |
| Java target | 1.5 | EOL since 2009 |

## Compliance Position

For a PCI DSS Level 1 service provider, this library's current state presents multiple compliance risks:
- Password logging (Requirement 3 — protect stored account data; Requirement 8 — authenticate access).
- EOL dependencies with known CVEs (Requirement 6 — develop and maintain secure systems).
- Hardcoded default config path (Requirement 6 — secure configuration management).
- No access control or authentication on database connections beyond username/password in plaintext config (Requirement 7/8).
