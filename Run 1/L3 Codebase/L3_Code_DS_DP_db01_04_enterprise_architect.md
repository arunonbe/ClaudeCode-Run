# DS_DP_db01 — Enterprise Architect Report

## Platform Generation and Technology Stack

| Attribute | Value |
|---|---|
| Database engine | Microsoft SQL Server 2012 (inferred from `MSSQL11` in path `G:\MSSQL11.DB01\MSSQL\Data\`) |
| Instance name | DB01 (named instance, port 2232 based on DB07 SSIS connection strings) |
| Connectivity protocol | TCP/IP, port 2232, SQLNCLI11 provider |
| HA mechanism | SQL Server Database Mirroring (evidence: "mirrored databases" in SQ-261 script) |
| Platform era | Legacy — SQL Server 2012 is end-of-life (EOL July 2022) |

**Critical finding:** SQL Server 2012 reached extended end-of-support on July 12, 2022. Running PCI DSS Level 1 payment infrastructure on an EOL database engine is a **critical compliance gap** under PCI DSS v4.0.1 Requirement 6.3.3 (all system components protected from known vulnerabilities). This applies to all DS_DP_db* nodes given the shared `MSSQL11` path pattern.

---

## Role in Payments Architecture

DB01 serves as one of the **lower-tier service database nodes** in the Onbe distributed prepaid card platform. Based on the databases it hosts:

```
                    ┌──────────────────────────────────────────┐
                    │        Onbe Payments Platform            │
                    │                                          │
  ┌─────────┐       │  ┌──────────┐    ┌──────────┐           │
  │ Client  │──────▶│  │ Ordersvc │    │ Jobsvc   │           │
  │ APIs    │       │  │ (DB01)   │    │ (DB01)   │           │
  └─────────┘       │  └────┬─────┘    └──────────┘           │
                    │       │                                  │
                    │  ┌────▼─────────┐                       │
                    │  │ Repositorysvc│                        │
                    │  │ (DB01)       │                        │
                    │  │ file storage │                        │
                    │  └──────────────┘                       │
                    │                                          │
                    │  ┌──────────────┐                       │
                    │  │ ACH Transfer │                        │
                    │  │ Processing   │                        │
                    │  │ (DB01/DB02)  │                        │
                    │  └──────────────┘                       │
                    └──────────────────────────────────────────┘
```

The `Repositorysvc` database on DB01 is the **document repository** for the broader platform — serving KYC documents, enrollment files, and card program assets for the programs hosted on this node.

---

## Dependencies

### Inbound (services that write to DB01)
- **Card enrollment APIs** — submit documents into `Repositorysvc`
- **Jobsvc consumers** — write job records to `Jobsvc`
- **Order management services** — write to `Ordersvc`

### Outbound (DB01 references other systems)
- `repositorysvc_rollback` — archive target on same instance
- `Repositorysvc..repo_file*` — cross-database references in prune job (same instance)

### Shared Infrastructure
- `DataServicesGroup-Operator` email operator — shared across all DB nodes (DB01–DB07)
- `NoReply@northlane.com` mail account — shared SMTP relay
- `ValidIPAddress` / `usernames_functional_accounts` tables in `master` — shared across all databases on the same SQL Server instance

---

## Architecture in Context of the DS_DP Shard Set

The DS_DP_db01–db07 nodes (with db03 absent) appear to be **function-differentiated** rather than pure horizontal shards:

| Node | Primary Function (inferred) |
|---|---|
| DB01 | Repositorysvc (documents), Ordersvc, Jobsvc — general application services |
| DB02 | EcountCore (card account), ACH processing, KYC tracking — core card engine |
| DB04 | Cbaseapp (content/portal), partition processing — UI content and cardholder portal |
| DB05 | Index maintenance only visible — lowest-activity node, possibly legacy or standby |
| DB06 | cf_report (compliance/finance reporting), BINBANK (BIN management), NACHA extract, IVR call logs — reporting layer |
| DB07 | SSIS orchestration server, SSISDB catalog, ETL/Finance/Warehouse package execution — integration/ETL host |

This is **not a pure horizontal sharding model** (same schema on N nodes). It is a **functional decomposition** model where different workloads are segregated onto different server instances. This has implications for migration complexity (each node requires separate, bespoke migration planning).

---

## Migration Complexity

| Factor | Assessment |
|---|---|
| Schema complexity | LOW for DB01 (few DDL objects in this repo) |
| Cross-instance dependencies | MEDIUM (references to same-instance databases; disrupting one affects others) |
| EOL platform risk | CRITICAL (SQL Server 2012 EOL) |
| HA migration | HIGH (database mirroring to Always On AG is a non-trivial migration path) |
| Downtime tolerance | LOW (payment systems require near-zero downtime) |
| Rollback complexity | MEDIUM (archive pattern in `_rollback` databases aids recovery but is not automated) |

---

## Corporate Transition Evidence

The scripts span the **Wirecard-to-NorthLane-to-Onbe** corporate transition:
- Pre-August 2020: Email addresses contain `wirecard.com`, operator name `NAMSupport@wirecard.com`
- November 2020 (SQ-1114): Migrated to `northlane.com` domain
- Ticket prefixes shift from `NATS/NAMDATASVC/WDNAMCBTS` to `SQ-` format

This transition represents a significant operational risk period — security controls, access grants, and email routing were all in flux simultaneously.

---

## Strategic Recommendations

1. **Urgent: Upgrade SQL Server** from 2012 to a supported version (2019 or 2022). DB01 is running EOL software in a PCI-regulated environment.
2. **Standardize job ownership** away from `sa` to a dedicated service account.
3. **Introduce migration tooling** (Flyway, Liquibase, or SSDT) to enforce script ordering and environment-aware deployments.
4. **Validate audit log retention** — confirm 90-day database cleanup is supplemented by 12-month SIEM or log archive to meet PCI DSS Req 10.7.
5. **Review `encryption_code` storage** in `repo_file` — key references in application tables should reference a key management vault, not store identifiers in plaintext table rows.
