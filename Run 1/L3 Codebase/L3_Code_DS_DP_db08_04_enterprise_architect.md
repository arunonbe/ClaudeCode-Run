# Enterprise Architect Report — DS_DP_db08

## Repository Identity

**Repository:** DS_DP_db08  
**Platform Generation:** Legacy monolithic SQL Server data platform (Generation 1)  
**Role in Architecture:** Core transaction-processing shard — one of at least eight numbered DP database instances (db01 through db08 are visible in the repos directory)

---

## Platform Generation and Architectural Context

DS_DP_db08 belongs to the **first-generation Onbe data platform**, built on Microsoft SQL Server with a sharded, multi-database architecture predating any microservices decomposition. The SQL Server version in use supports `ONLINE = ON` index creation and `SET SINGLE_USER WITH ROLLBACK IMMEDIATE`, consistent with SQL Server 2012 or later; the SSIS version referenced (`11.0.7001.0` in sister ETL repos) confirms **SQL Server 2012 (SSIS 11)** as the base installation, though the database engine may have been upgraded independently.

This generation predates:
- Containerisation (no Docker/Kubernetes references)
- Infrastructure-as-Code (no Terraform, ARM, or Bicep)
- Event-driven architectures (no Kafka, Service Bus, or message queue references)
- Modern CI/CD pipelines (no YAML, no GitOps)

---

## Role in the Data Architecture

DB08 sits in the **operational data layer** of a layered architecture:

```
[Card Networks / Processors / Partners]
           ↓ ETL pipelines (DS_ETL_*)
[Processing Shards — DS_DP_db01..db08]
           ↓ Replication
[Reporting / Atlys databases on same shard]
           ↓ Linked servers
[Warehouse — DS_WH_ecount-warehouse]
           ↓
[Reporting — DS_RPT_*]
```

DB08's specific role within the shard fleet is not formally documented, but evidence from scripts indicates it hosts:
- **US and Canadian prepaid card accounting** (ECNT, ECAN)
- **Back-office automation** configuration (Banker)
- **Revenue/forecast reporting aggregates** (ATLYS_* family)
- **GP financial integration** (DYNAMICS, ECNT GP tables)

---

## System Dependencies

### Upstream Dependencies (systems feeding DB08)
| System | Integration Method | Evidence |
|---|---|---|
| Microsoft Dynamics GP | Direct SQL write (journal entries, batch records) | GP table references throughout scripts |
| CCP (Card/Client Processing Platform) | Transactional replication (subscriber) | `20210513_SQ-3032` adds tables to replication |
| SO Automation (Job Service / Order Service) | SQL Agent job driven via `Banker.SSISJobConfigurations` | Job names in multiple scripts |
| FDR (First Data Resources) DD441 report | Direct SQL import to custom table | `20210907_NATS12149` references FDR DD441 |
| Finance Web Service | Certificate-authenticated HTTPS | `<FinanceWSURL>` in job parameters; cert thumbprint updates |

### Downstream Dependencies (systems reading from DB08)
| System | Integration Method | Evidence |
|---|---|---|
| Atlys Reporting Application | Direct SQL / linked server | ATLYS_* databases on the same instance |
| Accounting Workflow (AcctgWf) | Direct SQL | AcctgWf database co-hosted on shard |
| Microsoft GP (finance) | Bidirectional — reads ledger data | DYNAMICS database co-hosted |
| BakerTilly Audit | Read-only `db_datareader` Windows group | `20200731` grant scripts |
| DR Replica (log shipping) | Log shipping to `_R` suffix databases | DR scripts reference `ECNT_R`, `ATLYS_E_R` etc. |

---

## Corporate Identity Layers

Three corporate identity layers are embedded in the repository, reflecting the Wirecard → North Lane → Onbe ownership progression:

| Period | Identity | Evidence |
|---|---|---|
| Pre-2020 | Wirecard NAM | Ticket prefix `NAMDATASVC`, domain `@wirecard.com` |
| 2020–2021 | North Lane Technologies | Domain change to `@northlane.com` in `SQ-124`, entity rename in `SQ-137` |
| 2021+ | Onbe | Ticket prefix `US-` style; `ATM Cardtronics` renamed to `OnbeATM` in DB15 |

---

## Architectural Gaps and Technical Observations

### 1. Shard Cohesion vs. Single-Responsibility
The shard hosts 11+ logically independent databases on a single SQL Server instance. This violates modern single-responsibility principles and creates:
- Resource contention risk between OLTP (GP transactions) and OLAP (Atlys reporting)
- Blast radius risk: a single SQL Server failure takes down GP accounting, card processing, and reporting simultaneously
- Complex permission management across databases (evidenced by the multi-database audit access scripts)

### 2. IP Allowlist as Primary Access Control
The `TR_check_ip_address_functional_user` LOGON trigger is a **compensating control** for what should be network-level segmentation. Relying on a database trigger for network access control is brittle — if `sa` access is available (which the trigger itself uses), this control can be bypassed.

### 3. Replication Complexity
Adding tables to transactional replication (`SQ-3032`) as a script suggests the replication topology is not managed declaratively. Changes to the publication article list require manual intervention and do not appear to be tested in a lower environment before production.

### 4. Corporate Rebrand Incompleteness
The entity rebrand from North Lane to Onbe is not fully completed in all email/configuration references visible in this repository as of the last commit (March 2022). Residual `@northlane.com` addresses in `SSISJobConfigurations` may cause confusion but are not a security risk.

---

## Migration Complexity Assessment

| Migration Concern | Complexity | Notes |
|---|---|---|
| Extracting ECNT/ECAN to independent instances | HIGH | Deep cross-database query dependencies expected |
| Migrating GP integration to modern ERP | VERY HIGH | GP (Dynamics) is legacy; replacement requires full financial data migration |
| Replacing SSIS job configuration with modern orchestration | MEDIUM | `SSISJobConfigurations` pattern can be replaced by modern pipeline parameters (ADF, Airflow) |
| Introducing migration-tracked schema changes | LOW | Add Flyway/Liquibase; no schema DDL to migrate, only data patches |
| Decomposing Atlys reporting databases | HIGH | Seven Atlys variants suggest complex reporting model; dimensional redesign required |
