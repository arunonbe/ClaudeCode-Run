# DevOps / Operations View — DS_DB_ordersvc

## 1. Build System

| Property | Value |
|---|---|
| Project type | SSDT SQL Server Database Project (`ordersvc.sqlproj`) |
| Build tool | MSBuild with SSDT targets |
| Output | DACPAC (`ordersvc.dacpac`) |
| Target DSP | `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` (SQL Server 2012) |
| Build configurations | `Debug` and `Release` |
| Project GUID | `{caf05e4c-b3ad-4228-96a5-7f89b85b5201}` |
| `SqlServerVerification` | `False` |
| `IncludeCompositeObjects` | `True` |

---

## 2. Deployment

No CI/CD pipeline configuration is visible in this repository. No Jenkinsfile, Azure DevOps YAML, GitHub Actions, or equivalent pipeline files are present.

**Filegroup dependency**: All application tables are placed on `Ordersvc_FG_1` (defined in `Storage\Ordersvc_FG_1.sql`). Any DACPAC deployment to a new database instance must pre-create this filegroup before the schema can be applied, or the deployment will fail.

**Security scripts**: `Security\` contains principal creation and role membership scripts including `b2c`, `ordersvc`, `ordersvc_read`, `report`, `report_full`, `report_readonly`, `FortiDBRptRole`, `gers_role`, and named individual and service account logins. These must be deployed separately — DACPAC deploy applies schema; security principals require pre-existing SQL instance logins.

---

## 3. Configuration Management

- No environment-specific configuration files (`.sqlcmdvars`, publish profiles) present
- `Ordersvc_FG_1` filegroup name is hardcoded in all table DDL — not parameterised
- No SQLCMD variable substitution in table or view DDL

---

## 4. Observability

| Signal | Mechanism | Notes |
|---|---|---|
| DDL changes | `ddl_log` table | DDL trigger log; tracks schema changes in production |
| Order/request/action status | `*_status_log` tables | Application-level audit trail for all state changes |
| Index maintenance | DS_DB_dbadmin (`indexstats`) | DBAdmin monitors ordersvc indexes cross-database |
| FortiDB DAM | `FortiDBRptRole` | Database activity monitoring configured |

No distributed tracing, metrics endpoint, or application-level logging is implemented at the database layer.

---

## 5. Service Account and User Access

| Account | Role | Notes |
|---|---|---|
| `ordersvc` | `OrderSvc_Execute`, `OrderSvc_SELECT`, `OrderSvc_Update`, `OrderSvc_Delete` | Application service account — scoped access |
| `ordersvc_read` | `OrderSvc_SELECT` | Read-only variant |
| `b2c` | Defined role | B2C (cardholder portal) service account |
| `report` / `report_full` / `report_readonly` | Report roles | Reporting access |
| `NAM_PPA_PRD_ORDERSVC` | Service account | NAM production Order Service |
| `NAM_PPA_PRD_APISVC` through `SCHSVC` | Various | ~10 NAM service accounts |
| `FortiDBRptRole` | Monitoring | FortiDB DAM role |
| `gers_role` | Third-party | GERS tool role |
| `WLJMS` | WebLogic JMS | WebLogic JMS datastore access |
| Named individual logins (`emer_*`) | Emergency access | Emergency DBA/support access |

**Least privilege**: `ordersvc` uses granular custom roles (`OrderSvc_Execute`, `OrderSvc_SELECT`, etc.) — better access control than `db_owner`.

---

## 6. Infrastructure Dependencies

| Dependency | Notes |
|---|---|
| SQL Server 2012+ | Minimum target SQL Server version |
| `Ordersvc_FG_1` filegroup | Must pre-exist before DACPAC deploy |
| WebLogic JMS | WebLogic JDBC JMS datastore tables in schema — legacy messaging infrastructure |
| EcountCore database | `request_detail.ecount_id` links to EcountCore cardholder |
| ECNT GP database | `order_billing_info.sales_order` links to GP sales orders |
| DS_DB_dbadmin | Index stats and blocking monitoring |
| FortiDB | Database activity monitoring |

---

## 7. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| SSN stored as plaintext | CRITICAL | `action_update_user_secure_profile.ssn` unencrypted |
| `action_definition` view exposes SSN/DOB | HIGH | Any SELECT grant exposes unmasked SSN |
| JMS backup tables in production schema | HIGH | `jms2WLStore_Backup` tables are production backup artifacts |
| No data purge for most PII tables | HIGH | Only `action_notification_result` has a purge proc; `action_register_user` et al. have no purge policy |
| WebLogic JMS dependency | MEDIUM | Legacy dependency suggests WebLogic app server still in use |
| `SET ROWCOUNT` deprecated in `order_summary` | MEDIUM | `set rowcount @rcks` at line 125 — removed in SQL Server 2022 |
| No CI/CD pipeline | MEDIUM | Manual deployments with no automated validation |

---

## 8. CI/CD Assessment

No CI/CD pipeline is present. Recommended approach:
1. GitHub Actions workflow for dacpac build on every commit
2. Automated deploy to staging before production
3. SSDT schema comparison for drift detection
4. Security scanning (Snyk or equivalent) for SQL schema vulnerabilities
