# Solution Architect View — DS_DB_ordersvc

## 1. Technical Architecture

| Attribute | Value |
|---|---|
| Project type | SSDT SQL Server Database Project (`ordersvc.sqlproj`) |
| Target DSP | `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` (SQL Server 2012) |
| Schema | Single `dbo` schema |
| Primary keys | UNIQUEIDENTIFIER (GUID) throughout |
| Filegroup | `Ordersvc_FG_1` — dedicated for all application tables |
| DSP (compatibility) | SQL Server 2012 schema provider |
| TDE | Not configured in SSDT project |
| Security model | Granular custom roles: `OrderSvc_Execute`, `OrderSvc_SELECT`, `OrderSvc_Update`, `OrderSvc_Delete` |

---

## 2. Object Inventory

| Category | Count | Notes |
|---|---|---|
| Tables | ~80 | Order model, action model, inventory, JMS, reference data |
| Views | 14 | action_definition, order_summary_view, request_activity_definition, etc. |
| Stored procedures | 11 | order_summary, request_inquiry, create_sweep_order, inventory_inquiry, etc. |
| Functions | 7 | app_func_get_financial_count/total, count_active_sweep_orders, get_next_action_pos, etc. |
| Security scripts | 40+ | Service accounts, named individual logins, role memberships |
| Storage | 1 | Ordersvc_FG_1 filegroup definition |

---

## 3. Security Posture

### 3.1 Authentication and Authorisation
- **Application service accounts**: `ordersvc` uses granular custom roles — this is a best-practice access control pattern compared to `db_owner`
- **Role separation**: `OrderSvc_Execute` (stored procedures), `OrderSvc_SELECT` (tables/views), `OrderSvc_Update` (DML), `OrderSvc_Delete` (purge) — principle of least privilege applied
- **B2C service account**: `b2c` has its own login — correct isolation of cardholder portal access
- **`WLJMS` login**: WebLogic JMS requires direct table access — this is a legacy pattern; modern messaging infrastructure should not require a SQL database login
- **FortiDB DAM**: `FortiDBRptRole` confirms database activity monitoring is deployed — detective control for suspicious access

### 3.2 Critical Security Findings

| Finding | File | Severity |
|---|---|---|
| SSN stored as plaintext VARCHAR(32) | `action_update_user_secure_profile.sql:3` | CRITICAL |
| DOB stored as plaintext DATETIME | `action_update_user_secure_profile.sql:4` | HIGH |
| `action_definition` view exposes SSN/DOB | `action_definition.sql:39` — `auusp.ssn`, `auusp.dob` | HIGH |
| No column-level encryption on any PII fields | Schema-wide | HIGH |
| No data purge policy for PII tables | `action_register_user`, `action_issue_card_secondary` | HIGH |
| WebLogic JMS backup tables in production schema | `jms2WLStore_Backup.sql`, `jms2WLStore_backup_1.sql` | MEDIUM |

### 3.3 SSN Exposure in `action_definition` View
The `action_definition` view (line 39) joins `action_update_user_secure_profile` and aliases `auusp.ssn as ausp_ssn` and `auusp.dob as ausp_dob`. This view is accessible to any principal granted the `OrderSvc_SELECT` role. The Order Service application reads this view to get full action context — meaning the application tier has direct access to plaintext SSN values.

**Mitigation options** (in order of preference):
1. Apply SQL Server Always Encrypted on `action_update_user_secure_profile.ssn` and `.dob` — requires application-layer key management change
2. Apply dynamic data masking as an interim control: `MASKED WITH (FUNCTION = 'default()')` — provides masking to non-privileged users without application changes
3. Split `action_definition` into two views: a sanitised version (no SSN/DOB) for general use and a privileged version for identity verification use cases

---

## 4. API Surface

ordersvc has no REST or HTTP API surface. Access patterns:

| Pattern | Consumers | Description |
|---|---|---|
| Stored procedures | Order Service Java app | `order_summary`, `request_inquiry`, `create_sweep_order`, `inventory_inquiry`, etc. |
| Direct table DML | Order Service Java app via `ordersvc` role | INSERT/UPDATE/DELETE on action/order tables |
| Views | Order Service, reporting | `action_definition`, `order_summary_view`, `request_activity_definition` |
| `OrderSvc_SELECT` role | B2C portal, reporting tools | Read access to tables and views including `action_definition` |
| `WLJMS` direct access | WebLogic app server | JMS datastore table access |

---

## 5. Technical Debt

| Item | File:Line | Severity | Notes |
|---|---|---|---|
| SSN plaintext storage | `action_update_user_secure_profile.sql:3` | CRITICAL | GLBA NPI; column-level encryption required |
| DOB plaintext storage | `action_update_user_secure_profile.sql:4` | HIGH | GLBA NPI; CCPA; GDPR if EU cardholders present |
| `action_definition` view exposes unmasked SSN/DOB | `action_definition.sql:39` | HIGH | Broad read access to SSN via standard app role |
| No PII purge policy for `action_register_user` | Schema-level | HIGH | Cardholder PII retained indefinitely |
| WebLogic JMS tables in production schema | `jms*WLStore*.sql` | HIGH | Legacy messaging; prevents clean schema evolution |
| `SET ROWCOUNT` in `order_summary` | `order_summary.sql:125-126` | MEDIUM | Deprecated; removed in SQL Server 2022 |
| `SET ROWCOUNT` in `request_inquiry` | `request_inquiry.sql` | MEDIUM | Same issue |
| JMS backup tables committed to source | `jms2WLStore_Backup.sql` | MEDIUM | Production backup artifact in source control |
| `CodeArchive` table in production schema | `CodeArchive.sql` | MEDIUM | Legacy object; should be removed |
| No CI/CD pipeline | Repo level | MEDIUM | Manual deployment without automation |
| No TDE configuration in SSDT project | `ordersvc.sqlproj` | MEDIUM | Must verify TDE status at instance level |

---

## 6. Gen-3 Migration Requirements

1. **Encrypt SSN and DOB at rest** — apply Always Encrypted or column-level encryption on `action_update_user_secure_profile.ssn` and `.dob`; update Order Service application to handle encrypted column access
2. **Apply dynamic data masking as interim control** on `action_update_user_secure_profile.ssn` and `action_definition` view while Always Encrypted migration is planned
3. **Implement data retention and purge** for all PII-containing tables: `action_register_user`, `action_issue_card_secondary`, `action_update_user_secure_profile` — define retention periods by jurisdiction (GLBA: 5+ years for account records; CCPA: minimise retention)
4. **Migrate WebLogic JMS** to Azure Service Bus or Apache Kafka; remove `jms*WLStore` tables from ordersvc schema
5. **Fix `SET ROWCOUNT` usage** in `order_summary` and `request_inquiry` — replace with `TOP n` equivalents before SQL Server 2022 upgrade
6. **Add CI/CD pipeline** — GitHub Actions dacpac build + deploy to staging + schema drift detection
7. **Remove `CodeArchive` and JMS backup tables** from production schema
8. **Add SSN masking to `action_definition` view** — split into privileged and unprivileged variants; restrict privileged variant to identity verification use cases only
9. **Implement data lineage tracking** — add audit logging for SSN/DOB access to support PCI DSS Req 10.2 (logging of access to cardholder data)
10. **ECNT GP decoupling** — `order_billing_info.sales_order` creates a hard coupling between ordersvc and the GP ERP; introduce an async event-driven billing integration for Gen-3
