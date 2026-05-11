# DS_DB_ecountbatchjobrepository — Business Analyst View

## Repository Overview

`DS_DB_ecountbatchjobrepository` is a SQL Server Database Project (`.sqlproj`, targeting SQL Server 2012 `Sql110DatabaseSchemaProvider`) that defines the schema for the `EcountBatchJobRepository` database. The project contains DDL for 9 tables and an extensive set of Security scripts covering role definitions and user grants. This database is the Spring Batch `JobRepository` for the Onbe prepaid card batch processing platform.

---

## Business Purpose

The `EcountBatchJobRepository` database serves as the **operational metadata store for Spring Batch job execution** across the Onbe EcountCore batch processing platform. It does not store financial, cardholder, or payment data itself, but it tracks the execution state of every batch job that processes cardholder data, payments, ACH transactions, card issuance, fee processing, and compliance operations.

In a Spring Batch architecture, the `JobRepository` is the central record of truth for:
- What jobs have run
- Whether they succeeded, failed, or were abandoned
- What parameters were passed to each job run
- How many records were read, written, filtered, and skipped at each step
- Step-level progress enabling restartability

This metadata is operationally critical for:
- **Restart and recovery** — if a batch job fails mid-run, Spring Batch can restart from the last checkpoint
- **Duplicate prevention** — Spring Batch uses the `JOB_KEY` (a hash of job parameters) to prevent duplicate job runs
- **Audit trail** — every job execution is recorded with timestamps, status, and exit messages, providing an audit log of batch operations

---

## Batch Jobs Tracked

While the batch job names themselves are not stored in this repository (they are defined in the Spring Batch application code in repos such as `ecore-batch_LIB`, `prepaid-batch-framework_LIB`, `auto-card-batch_LIB`), the database schema supports tracking of all batch job types deployed against EcountCore:

Based on the broader codebase context and the service accounts granted access (see Security section), the jobs tracked include:
- **ACH processing jobs** — NACHA file generation, settlement, returns
- **Card issuance jobs** — emboss extract, card shipping
- **Fee processing jobs** — dormancy fees, service fees, maintenance fees
- **Escheatment jobs** — identifying and processing dormant accounts
- **FDR file processing** — importing and posting First Data Resources files
- **Notification jobs** — balance notifications, card expiry notifications
- **Enrollment jobs** — new cardholder onboarding
- **Archival jobs** — moving processed data to archive

---

## Regulatory Relevance

### PCI DSS
Although the `EcountBatchJobRepository` does not store cardholder data, it is part of the system that processes cardholder data. Under PCI DSS v4.0.1, any system that can affect the security of cardholder data (e.g., by controlling when batch jobs run, enabling fraudulent re-runs, or disrupting fee processing) is in-scope. The service accounts granted access (e.g., `NAM\PPA_PRD_ECORESVC`, `NAM\PPA_PRD_ECAPSVC`) are production service accounts connected to the CDE.

### NACHA / Reg E
ACH-related Spring Batch jobs use this repository to track execution. If an ACH job fails mid-run, the restart capability enabled by this database is critical to ensuring NACHA file integrity and Reg E return processing timelines are met. A corrupted or inaccessible `JobRepository` could prevent ACH batch restart, resulting in missed settlement windows.

### SOX / Operational Audit
The job execution history tables (`BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION`) constitute an operational audit log of all batch processing activity. This log is relevant for financial controls audits and incident investigations.

---

## Service Accounts with Access

The following production service accounts are explicitly granted access to this database (from Security scripts):

| Account | Service | Significance |
|---|---|---|
| `NAM\PPA_PRD_ECORESVC` | EcountCore Service | Core card platform service — highest impact |
| `NAM\PPA_PRD_ECAPSVC` | ECAP Service | eCount Application Platform |
| `NAM\PPA_PRD_APISVC` | API Service | Card/account API |
| `NAM\PPA_PRD_CSASVC` | CSA Service | Customer Service API |
| `NAM\PPA_PRD_CSWSVC` | CSW Service | Customer Service Web |
| `NAM\PPA_PRD_CZSVC` | ClientZone Service | Client portal |
| `NAM\PPA_PRD_IVRWSVC` | IVR Web Service | IVR integration |
| `NAM\PPA_PRD_BMCSVC` | BMC Service | Operations monitoring |
| `NAM\PPA_PRD_NROLLSVC` | Enrollment Service | Cardholder enrollment |
| `NAM\PPA_PRD_OPSVC` | Operations Service | Operational batch |
| `NAM\PPA_PRD_ORDERSVC` | Order Service | Card ordering |
| `NAM\PPA_PRD_SCHSVC` | Scheduler Service | Job scheduling |
| `NAM\ppa_prd_ndm` | NDM/Connect:Direct | File transfer service |
| `NAM\ppa_prd_mon` | Monitoring | Operational monitoring |
| `NAM\PROD` | General PROD | Domain-level prod access |
| `NAM\PROD_CPP` | CPP Production | Card processing platform |
| `NAM\PROD_CPP_APAC` | CPP APAC | Asia-Pacific card processing |
| `NAM\PROD_ITOPS` | IT Operations | IT ops team |
| `NAM\UAT` | UAT environment | Test/UAT access |
| `b2c`, `b2c_1` | B2C application | Consumer-facing app |
| `NAM\GTS_MSSQL_DBA_RO` | GTS DBA read-only | Database administration |
| `NAM\ICG_DBA_Default` | ICG DBA | Infrastructure DBA |
| `NAM\ISA_SQL_SECADMIN` | Security Admin | SQL security admin |
| `FortiDBRptRole` | FortiDB | Database activity monitoring |
| `gers_role`, `gers_read` | GERS | Reporting/audit |
| `ifs_gidadb`, `ifs_infosec` | IFS Security | Information Security |
| `NAM_GTS_gpatmon` | GP AT Monitor | GP application monitoring |
| `scpardb` | SCPARdb | Storage/compute platform AR |
| Various `emer_*` accounts | Emergency access | DBA emergency break-glass |

---

## Key Observations for Business

1. This database enables **restartability** of failed batch jobs — loss of this database means failed batch jobs cannot be automatically restarted, requiring manual intervention.
2. The **job execution history** is a valuable audit resource — it shows the exact time, duration, and record counts of every batch processing run.
3. Access is granted to over 30 distinct service accounts and user logins, many with read/write capability — the access surface is very broad.
4. No data classification or data masking is needed for this database as it contains no cardholder data — however it is operationally critical to the systems that do.
