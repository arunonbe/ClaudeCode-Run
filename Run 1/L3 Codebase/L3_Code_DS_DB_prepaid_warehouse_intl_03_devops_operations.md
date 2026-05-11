# DS_DB_prepaid_warehouse_intl — DevOps and Operations Assessment

## 1. Build and Deployment Pipeline

### 1.1 Project Type and Target
The repository is a Visual Studio SSDT project targeting **SQL Server 2012** (`DSP: Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider`). The build target is .NET Framework 4.0 — two major framework generations behind the US warehouse (which targets .NET 4.6.1). This indicates the international warehouse was not updated in lockstep with the US warehouse.

### 1.2 CI/CD
**No CI/CD pipeline configuration files are present in this repository.** The same gap exists as in the US warehouse. Deployments are presumed manual (DACPAC deployment or DBA script execution) with no automated validation.

### 1.3 Legacy SQL Compatibility Settings
The sqlproj file (`database.Prepaid_Warehouse_Intl.sqlproj`, lines 28–29) sets:
- `<AnsiNulls>False</AnsiNulls>`
- `<QuotedIdentifier>False</QuotedIdentifier>`

These settings force SQL Server to compile all procedures in legacy compatibility mode. If these procedures are ever migrated or executed in a modern SQL Server session context that has `SET ANSI_NULLS ON` (the SQL Server 2016+ default), behaviour may differ from the design intent.

### 1.4 Change Tracking Configuration
The sqlproj explicitly configures Change Tracking:
```xml
<IsChangeTrackingOn>False</IsChangeTrackingOn>
<IsChangeTrackingAutoCleanupOn>True</IsChangeTrackingAutoCleanupOn>
<ChangeTrackingRetentionPeriod>2</ChangeTrackingRetentionPeriod>
<ChangeTrackingRetentionUnit>Days</ChangeTrackingRetentionUnit>
```
Change tracking is disabled. This is consistent with a read-heavy analytical database where change tracking is not needed, but it confirms that no incremental synchronisation uses the SQL Server Change Tracking feature (relying instead on CDC or custom ETL watermarks).

---

## 2. Storage and Infrastructure Settings (from sqlproj)

| Setting | Value | Implication |
|---|---|---|
| `PageVerify` | `CHECKSUM` | Page-level integrity checking enabled — positive |
| `VardecimalStorageFormatOn` | `True` | Legacy storage optimization (SQL 2005 era) — minor concern |
| `AllowSnapshotIsolation` | `False` | Snapshot isolation disabled — long-running reads may block writers |
| `ReadCommittedSnapshot` | `False` | RCSI disabled — risk of read-write locking contention |
| `ServiceBrokerOption` | `DisableBroker` | Service Broker disabled — no internal message queuing |
| `Parameterization` | `SIMPLE` | Simple parameterisation — standard for OLTP; warehouses sometimes use FORCED |
| `Trustworthy` | `False` | Database trustworthy setting off — correct security posture |

The absence of `ReadCommittedSnapshot` isolation on a reporting database is a concern: long-running analytical queries will block ETL writes, and ETL writes will block reporting reads. This was a known limitation of older SQL Server warehouse designs.

---

## 3. Backup and Recovery

No backup configuration is in the repository. Same limitations as the US warehouse apply. The `PageVerify = CHECKSUM` setting is a positive indicator that page corruption can be detected during backup restoration.

---

## 4. Operational Differences From US Warehouse

| Aspect | US Warehouse | International Warehouse |
|---|---|---|
| ETL procedure count | ~120 stored procedures | Fewer — subset of US patterns |
| Rollback capability | Full rollback procedures | Partial (sprocInc_* rollback present) |
| Risk reporting procedures | `Rpt_Risk_*` family present | Not observed in file listing |
| DDA verification | Full DDA verification flow | `sprocInc_Capture_Incremental_DDAs` only |
| Report coverage | ~40 reporting procedures | ~5 reporting procedures |

The international warehouse appears to be a **lighter-weight** warehouse compared to the US one — fewer reporting procedures and less ETL complexity. This may reflect smaller portfolio volume in international markets or a less mature reporting function.

---

## 5. Security Operations

### 5.1 Security Folder
The `Security/` folder mirrors the US warehouse structure with:
- Role definitions (inferred from file structure)
- NAM production service account grants
- Emergency access accounts (`emer_*`)
- FortiDB reporting role
- Vulnerability scanning account

### 5.2 Compliance Notes
- No evidence of GDPR-specific data governance controls (e.g., data classification tags, access request workflows)
- No data residency controls (e.g., database restricted to EU-region servers)

---

## 6. Key Operational Risks

1. **SQL Server 2012 End of Life** — If deployed to a SQL Server 2012 instance, the database runs on an unsupported engine version. Security vulnerabilities in SQL Server 2012 are no longer patched by Microsoft. This is a PCI DSS Requirement 6.3 (patching) and NIST CSF identify/protect concern.
2. **No read-committed snapshot isolation** — ETL and reporting operations will block each other, potentially causing missed ETL windows during peak reporting periods.
3. **Legacy compatibility settings** — `AnsiNulls = False` and `QuotedIdentifier = False` create portability and correctness risks if procedures are executed in modern session contexts.
4. **No CI/CD** — Same deployment risk as US warehouse.
5. **Fewer rollback procedures** — If an international ETL load partially fails, recovery procedures may be less robust than the US warehouse.
