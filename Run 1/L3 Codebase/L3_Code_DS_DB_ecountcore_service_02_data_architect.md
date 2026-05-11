# DS_DB_ecountcore_service — Data Architect View

## 1. Database Object Inventory

### 1.1 Tables
| Table | Columns | Purpose | Sensitive Data |
|-------|---------|---------|----------------|
| `dbo.TaskLog` | `id` (INT IDENTITY PK), `task_name` (VARCHAR 50), `task_msg` (TEXT), `task_return_code` (INT), `process_id` (INT), `created` (DATETIME, default getdate()), `updated` (DATETIME) | Audit log of all dispatched tasks, including error messages | `task_msg` may contain stored procedure parameter values including product/brand/affiliate identifiers. Does not contain PANs or account numbers. **Low sensitivity.** |

### 1.2 Stored Procedures
| Procedure | Location | Purpose | Dynamic SQL Risk |
|-----------|----------|---------|-----------------|
| `app_task_agent` | `dbo/Stored Procedures/app_task_agent.sql` | Service Broker activation proc: dequeues XML task messages and executes them via `sp_executesql` | **HIGH** — executes arbitrary SQL from queue message body (line 47: `exec sp_executesql @taskstr`) |
| `app_task_enqueue` | `dbo/Stored Procedures/app_task_enqueue.sql` | Enqueues an XML task message onto the Service Broker queue | Low — parameterised XML input |
| `app_task_log` | `dbo/Stored Procedures/app_task_log.sql` | Inserts a TaskLog start record | None |
| `app_task_log_update` | `dbo/Stored Procedures/app_task_log_update.sql` | Updates a TaskLog record with completion status | None |
| `app_task_manager_card_account_purge_request` | `dbo/Stored Procedures/` | Dispatches card account purge tasks per program | Constructs XML dynamically from integer parameters only |
| `app_task_manager_dormancy_fee` | `dbo/Stored Procedures/` | Dispatches dormancy fee tasks per program | Constructs XML with VARCHAR date values — low injection risk (date cast) |
| `app_task_manager_escheatment_commit` | `dbo/Stored Procedures/` | Dispatches escheatment commit tasks | Constructs XML with `@StateString varchar(4000)` — **MEDIUM** injection risk if caller does not sanitise state strings |
| `app_task_manager_escheatment_due_diligence` | `dbo/Stored Procedures/` | Dispatches escheatment due-diligence tasks | Same `@StateString` concern as commit |
| `app_task_manager_escheatment_enqueue` | `dbo/Stored Procedures/` | Dispatches escheatment enqueue tasks | Low |
| `app_task_manager_maintenance_fee` | `dbo/Stored Procedures/` | Dispatches maintenance fee tasks with DCAF open-auth exclusion | Constructs XML with integer and date parameters |

### 1.3 Functions
| Function | Type | Purpose |
|----------|------|---------|
| `escheatment_func_get_status` | Scalar UDF (T-SQL) | Given a DDA number and datetime, determines whether a card is in active (0) or pending-escheatment (1) status by calling cross-database functions in `ecountcore` |
| `getValidStringFromFrench` | Scalar UDF (T-SQL) | Character normalisation for French text (bilingual compliance for Canadian programs) |
| `programCount` | Scalar UDF (SQL-CLR) | Delegates to `EcountUtility.dll` assembly — `com.ecount.database.EcountSQLCLR.SQLUtility.programCount` |

### 1.4 Service Broker Objects
| Object | Type | Purpose |
|--------|------|---------|
| `TaskMessage` | Message Type | Carries XML task payloads |
| `TaskContract` | Contract | Defines message exchange pattern |
| `TaskQueue` | Queue | Worker queue; ACTIVATION ON, `app_task_agent` proc, MAX_QUEUE_READERS = 2, POISON_MESSAGE_HANDLING = OFF |
| `TaskManagerQueue` | Queue | Manager-side queue |
| `TaskAgentService` | Service | Agent endpoint (ON TaskQueue, TaskContract) |
| `TaskManagerService` | Service | Manager endpoint — sends to TaskAgentService |

### 1.5 Security Objects (in `Security/` folder)
- **Roles** (derived from file inventory): `Ecountcore_Service_Delete`, `Ecountcore_Service_execute`, `Ecountcore_Service_Schema_View`, `Ecountcore_Service_Select`, `Ecountcore_Service_Update`, `FortiDBRptRole`, `gers_read`, `gers_role`
- **Logins / Users**: `B2C`, `b2c_1`, `GENTRAN`, `ifs_gidadb`, `ifs_infosec`, `NAM_GTS_gpatmon`, `NAM_GTS_MSSQL_DBA_RO`, `NAM_ICG_DBA_Default`, `NAM_ISA_SQL_SECADMIN`, `NAM_PPA_DB_ACCESS`, `NAM_PPA_PRD_APISVC`, `NAM_PPA_PRD_BMCSVC`, `NAM_PPA_PRD_CSASVC`, `NAM_PPA_PRD_CSWSVC`, `NAM_PPA_PRD_CZSVC`, `NAM_PPA_PRD_ECAPSVC`, `NAM_PPA_PRD_ECORESVC`, `NAM_PPA_PRD_IVRWSVC`, `NAM_ppa_prd_mon`, `NAM_PPA_PRD_NROLLSVC`, `NAM_PPA_PRD_OPSVC`, `NAM_PPA_PRD_ORDERSVC`, `NAM_PPA_PRD_SCHSVC`, `NAM_PPA_PRD_SQL`, `NAM_PROD_CPP`, `NAM_PROD_CPP_APAC`, `NAM_PROD_ITOPS`, `NAM_UAT`, `scpardb`, `vascan`, plus ~17 `emer_*` individual SQL logins
- **Role Memberships** (`RoleMemberships.sql`): `NAM\PROD_CPP_APAC`, `NAM\ISA_SQL_SECADMIN`, `ifs_gidadb`, `scpardb`, `ifs_infosec` are members of `db_accessadmin` and `db_securityadmin` — **elevated privilege logins**. Individual `emer_*` accounts have `db_datareader` and `db_datawriter` membership.

### 1.6 Assemblies
| Assembly | File | CLR Permission Set | Notes |
|----------|------|--------------------|-------|
| `EcountUtility` | `Assemblies/EcountUtility.dll` | Not declared in DDL (inferred SAFE or EXTERNAL_ACCESS) | Backs `programCount` function. Binary blob committed to repo. No source code present. |

---

## 2. Sensitive Data Field Assessment

| Field / Context | Classification | PCI DSS Relevance |
|-----------------|---------------|-------------------|
| `TaskLog.task_msg` (TEXT) | Operational log — may contain program IDs, dates, error messages | Not a PAN/SAD field. Not in PCI CDE scope. However, error messages should be reviewed to ensure they never inadvertently capture account numbers. |
| Service Broker message body (XML `<task>` elements) | Contains stored procedure names and integer/date parameters. No account-number data by design. | Out of PCI CDE scope. |
| `dda_number` values referenced in SP logic | DDA numbers are 16-character program+sequence identifiers (e.g. `01020003XXXXXXX`). These are **program-level** identifiers, not individual PANs. However, the left-8 segment identifies a card program BIN range. | Not a full PAN. Monitor for inadvertent logging. |

**PCI DSS CDE Assessment**: This database is **out of direct CDE scope** because it stores no PANs, CVVs, track data, or PINs. However, it is a **connected system** that dispatches processes into the CDE (`ecountcore`) and is therefore subject to PCI DSS network segmentation and access-control requirements (Requirements 1, 7, 8).

---

## 3. Data Retention

No data-retention DDL (archiving, partitioning, or purge jobs) is defined within this repo. The `TaskLog` table uses a TEXT column (deprecated SQL Server data type) with no explicit row-count or age limits visible in the schema. Growth management is not addressed. A production instance with no purge job will grow unboundedly.

**Recommendation**: Define a retention policy (e.g. 90 days online, archive to cold storage) and implement a scheduled purge against `dbo.TaskLog`.

---

## 4. Encryption at Rest

- **Column-level encryption**: Not present. No `ENCRYPTBYKEY`, `ENCRYPTBYCERT`, or Always Encrypted definitions exist in any DDL.
- **TDE (Transparent Data Encryption)**: Not configured at the database level in this repo. TDE is typically set at instance/deployment level and would not appear in `.sqlproj` DDL unless explicitly scripted via `ALTER DATABASE ... SET ENCRYPTION ON`.
- **Service Broker encryption**: `WITH ENCRYPTION = OFF` is explicit in `app_task_enqueue.sql` (line 17) — Service Broker dialog encryption is disabled. For intra-instance communication this is standard; for cross-instance (linked server) scenarios this would be a gap.

---

## 5. Cross-Database Dependencies

| Referenced Database | Objects Used | Nature |
|---------------------|-------------|--------|
| `ecountcore` | `app_func_get_fee_programs`, `fdr_profile_class_property`, `fdr_profile_class`, `fdr_process_service_status`, `fdr_dda_account`, `fdr_dda_account_balance_status`, `app_profile_promotion_label`, `app_profile_global_label`, `app_process_escheatment_queue`, `app_profile_escheatment_rules`, `app_func_escheatment_get_rule_set`, `app_func_escheatment_dda_get_address_state`, `app_func_escheatment_get_expiration_date`, `app_func_dda_get_balance`, `fdr_profile_scope` | Read and write via three-part names |
| `ecountcore_process` | `fdr_process_dcaf_chd_data`, `fdr_process_dcaf_auth_data`, `fdr_process_dcaf_maint_fee_open_auth_accounts` | Read and write (TRUNCATE + INSERT) |

These hard-coded cross-database references mean the database cannot be moved to a different SQL Server instance without updating all procedure bodies or using synonyms.

---

## 6. Index and Clustering Notes
- `dbo.TaskLog`: Single clustered primary key on `id` (INT IDENTITY). No secondary indexes. Queries filtering by `task_name` or `created` range will require full scans on large tables.
