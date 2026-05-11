# DevOps and Operations Report: DS_DB_banker

## Build System

| Attribute | Detail |
|---|---|
| Project type | SQL Server Data Tools (SSDT) `.sqlproj` (MSBuild) |
| Project file | `banker.sqlproj` |
| Target SQL Server | SQL Server 2016 (`Sql130DatabaseSchemaProvider`) inferred from family pattern |
| Build output | DACPAC + deployment script |
| Schemas | `dbo`, `so`, `onus`, `Storage` (partition objects) |
| Object count | ~20 dbo tables, ~50 dbo SPs, ~10 so tables, ~50 so SPs, 1 so view, 2 onus tables, 1 onus SP, 10 synonyms, partition function + scheme |

The project spans four schemas (`dbo`, `so`, `onus`, `Storage`) plus a `Security` folder. The `so` schema houses the Sales Order Automation subsystem as a logical namespace within the same database. This is a common Gen-1 pattern that collocates related objects in schemas rather than separating them into microservices.

---

## CI/CD Pipelines

**No CI/CD pipeline files exist in this repository.** No Jenkinsfile, Azure DevOps YAML, or GitLab CI configuration is present.

- Branch: `development` (single tracked branch)
- Shallow clone: `.git/shallow` present
- Remote: `origin/HEAD` → `development`

This is consistent with the pattern observed across the Atlys database family. Given that `banker` drives automated GP invoice creation and fund settlement determination — both financially significant automated processes — the absence of a CI/CD pipeline is a critical gap. Any schema change to `so.order_status`, `banker_reserved_source`, or `fee_invoicing_*` tables deployed incorrectly could corrupt active order processing batches.

---

## Deployment Approach

Based on the SSDT project structure, the inferred manual deployment process:

1. `msbuild banker.sqlproj /p:Configuration=Release` → produces `banker.dacpac`
2. `SqlPackage.exe /Action:Publish /SourceFile:banker.dacpac /TargetConnectionString:"..."` → differential deployment script
3. DBA reviews and executes against target SQL Server instance

**Critical deployment considerations specific to banker:**

- **`so.order_status` and `so.order_detail` contain active processing state**: These tables hold in-flight sales order processing data. Schema changes during an active SOA batch run could corrupt processing state. Deployments to these tables must be coordinated with the SSIS SOA job schedule.
- **`cpp_loop_process_status` is a FK parent**: Any deployment that truncates or rebuilds `cpp_loop_process_status` will violate the FK from `so.order_status.process_id`. Deployment scripts must preserve active process rows.
- **`SSISConfigurations` drives SSIS behavior**: Changes to this table's structure require coordination with all SSIS packages that read from it. SSIS packages referencing this table by column name will break if columns are added, renamed, or removed.
- **Synonyms require `REPORTINGDBSERVER` to be defined**: The 10 synonyms in the `dbo` schema all reference `REPORTINGDBSERVER`. This server alias must exist on the target SQL Server instance before deployment. Deployment on a new instance without this alias will fail.
- **Partition function is static (2013–2016)**: The `monthly_partition` function (`Storage/monthly_partition.sql`) has boundaries only through 2016. If any table uses this partition scheme, it must be reviewed before deployment to a current production instance.
- **Triggers**: Both `SSISConfigurations_timestamp_trigger` and `so.order_status_timestamp_trigger` are defined inline with their tables. SSDT handles trigger deployment atomically with the table, but if these tables already exist, SSDT will ALTER TABLE to add/replace the triggers.

---

## Environments

The Security folder defines access for multiple environments and access tiers:

| File / Group | Environment | Access Level |
|---|---|---|
| `NAM_PROD.sql`, `NAM_PROD_1.sql` | Production | Standard production access |
| `NAM_UAT.sql`, `NAM_UAT_1.sql` | UAT | Test environment access |
| `NAM_PPA_PRD_ATLYS.sql` | Production | Atlys application service account |
| `NAM_ppa_prd_ABAT.sql` | Production | Automated batch service account |
| `NAM_PPA_PRD_FinSVC.sql` | Production | Finance service account |
| `NAM_PPA_PRD_MON.sql` | Production | Monitoring service account |
| `Banker.sql`, `Banker_1.sql` | All | Banker application role |
| `Banker_Delete.sql` | All | DELETE permission role |
| `Banker_Select.sql` | All | SELECT permission role |
| `Banker_execute.sql` | All | EXECUTE permission role |
| `Banker_update.sql` | All | UPDATE permission role |
| `PPA_FinSVC_GRP.sql` | Production | Finance service group |
| `Prod_Support_execute.sql`, `Prod_Support_Select.sql`, `Prod_Support_Update.sql`, `Prod_Support_Schema_View.sql` | Production | Production support tiers |
| `FortiDBRptRole.sql` | All | FortiDB DAM reporting |
| `ifs_infosec.sql`, `ifs_gidadb.sql` | All | Information security monitoring |
| `NAM_GTS_gpatmon.sql`, `NAM_GTS_MSSQL_DBA_RO.sql` | All | DBA monitoring |
| `NAM_ICG_DBA_Default.sql`, `NAM_ISA_SQL_SECADMIN.sql` | All | DBA and security admin |
| `report.sql`, `report_full.sql` | All | Report access |
| `scpardb.sql` | All | Additional service account |
| `onus.sql`, `so.sql` | All | Schema-level security |
| `gers_read.sql`, `gers_role.sql` | All | GERS reporting |
| `RoleMemberships.sql` | All | Consolidated role membership assignments |

The Banker-specific roles (`Banker_Delete`, `Banker_Select`, `Banker_execute`, `Banker_update`) implement a four-tier RBAC model for this database. Combined with the `Prod_Support_*` roles, there are at least 8 distinct access tiers.

---

## Backup and Recovery

No backup scripts present. Key recovery considerations:

- **`banker_reserved_source`**: Loss of fund reservation data would require manual reconciliation against GP sales orders to reconstruct settled vs. unsettled state. This is operationally critical data.
- **`so.order_status` + `so.order_detail`**: Loss of in-flight order processing state would require reprocessing from source orders, potentially creating duplicate GP invoices if not carefully managed.
- **`so.PrepaidCustomerBalanceHistory`**: Historical daily balance snapshots are not reproducible from other systems once lost.
- **`SSISConfigurations`**: Loss of SSIS configuration data would halt all ETL jobs until the table is repopulated. This table should be backed up and version-controlled separately.

---

## Operational Risks

### Risk 1: No CI/CD Pipeline — CRITICAL
For a database that drives automated GP invoice creation and fund settlement determination, the absence of an automated deployment pipeline is a critical compliance and operational gap.

### Risk 2: `BankerAllSOView` and `BankerPayment` are Undocumented External Dependencies
The `banker_get_unsettled_funds` and `banker_get_payments` procedures depend on `BankerAllSOView` and `BankerPayment` views that are **not defined anywhere in this repository**. These are external views, presumably defined in a Great Plains-linked view layer or another database. If these views become unavailable or change their schema, all fund settlement determination will fail or return incorrect results. There is no documentation of where these views are defined or what their schema is.

### Risk 3: `REPORTINGDBSERVER` Alias Dependency
All 10 synonyms in the `dbo` schema reference `REPORTINGDBSERVER` as a server alias. If this alias is not correctly configured on a target SQL Server instance (e.g., a new environment, a DR failover instance), all synonym-dependent procedures will fail. The alias configuration is external to this repository and undocumented within it.

### Risk 4: Debug Tables in Production Schema
`Nick_Logging_JVC_Orders` and `Nick_Logging_JVC_Order_Details` are debug/logging tables named after a developer and committed to the production database project. `ordersvc_get_orders.sql` previously wrote to these tables (referenced in the conversation context as containing an OUTPUT clause). These tables represent a data retention and PII risk — order processing details and `customer_id` values written to debug tables with no documented retention or access policy.

### Risk 5: Date-Stamped Backup Tables in Production Schema
`fee_aggregation_core_5_24_2018`, `fee_aggregation_items_5_24_2018`, and `SSISJobConfigurations_backup` are backup/snapshot tables committed to the production SSDT project. They will be deployed to production, consuming storage and potentially creating confusion about which table is authoritative.

### Risk 6: Static Partition Function (2013–2016)
The `monthly_partition` function covers only 2013-01 through 2016-12. If any table currently uses this partition scheme, data since 2017 is in an unpartitioned overflow partition, defeating the purpose of partitioning and potentially impacting query performance on large historical tables.

### Risk 7: SSIS Configuration in SQL Table
`SSISConfigurations` stores SSIS package parameters in the database. SSIS package configurations in SQL Server tables can contain server names, file paths, and potentially connection string fragments. Access to this table should be restricted to SSIS service accounts only. Confirm that no plaintext credentials are stored in `ConfiguredValue` fields.

### Risk 8: Cursor Usage in Fee Invoicing
`so.fee_invoicing_get_customers` uses two cursors (`countries` over `so.gp_dbs` and `program_promos` over fee aggregation data). For large numbers of GP databases or programs, this cursor-based processing will scale poorly. Monitor execution time and blocking during fee invoicing runs.

### Risk 9: FortiDB Monitoring
`FortiDBRptRole.sql` confirms FortiDB DAM is deployed. Monitoring coverage should include the `banker_reserved_source` table (all DML), `SSISConfigurations` (all DML), and `so.PrepaidCustomerBalanceHistory` (INSERT/UPDATE). Confirm alert thresholds are set appropriately.
