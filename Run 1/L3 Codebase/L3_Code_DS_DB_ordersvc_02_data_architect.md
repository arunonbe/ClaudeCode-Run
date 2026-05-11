# Data Architect View — DS_DB_ordersvc

## 1. Repository Structure and Build System

`DS_DB_ordersvc` is an **SSDT SQL Server Database Project** (`ordersvc.sqlproj`).

**Key project properties:**
- **DSP**: `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` — SQL Server 2012 compatible
- **DefaultCollation**: `1033, CI` (SQL_Latin1_General_CP1_CI_AS equivalent)
- **Filegroup**: `Ordersvc_FG_1` — dedicated filegroup for all application tables (I/O isolation)
- **TDE**: Not specified in project file — TDE configuration managed at the instance level
- **`SqlServerVerification=False`**

---

## 2. Schema Composition

Single schema: `dbo`. Three functional layers:

**Layer 1 — Order/Request/Action model**: A hierarchical command pattern:
- `order_detail` (1) → `request_detail` (many) → `action_detail` (many) → specific action tables (1:1)

**Layer 2 — Inventory**: Card inventory tracking separate from order model

**Layer 3 — WebLogic JMS**: WebLogic JMS datastore tables for legacy messaging infrastructure

---

## 3. Key Table Inventory

### Order Model
| Table | Key Columns | Notes |
|---|---|---|
| `order_detail` | id GUID, program_id, type, status, ref_id, order_number IDENTITY | `order_number` is sequential IDENTITY; CHECK constraint on active sweep count |
| `order_status` | | Order status reference |
| `order_status_log` | | Order status change audit trail |
| `order_type` | | Order type reference |
| `order_activity` | | Order-level activity log |
| `order_file` | | File association for orders (job_id, file_id) |
| `order_billing_info` | | sales_order reference (links to ECNT GP) |
| `order_sweep` | | Sweep order for cross-program fund movements |
| `order_memo` | | Order-level memos (used for CZ_QUICK_ORDER_TYPE) |

### Request/Action Model
| Table | Key Columns | Notes |
|---|---|---|
| `request_detail` | id GUID, program_id, ref_id, ecount_id, partner_user_id | ecount_id links to EcountCore cardholder |
| `request_status_log` | | Request status audit trail |
| `action_detail` | id GUID, request GUID, pos, type, status, secure_ref | PK on Ordersvc_FG_1; ordered by pos within request |
| `action_register_user` | id GUID + full cardholder PII (name, address, phone, email) | **HIGH PII — cardholder registration data** |
| `action_issue_card` | delivery_code, location_code, card_package_id | Card issuance parameters |
| `action_issue_card_secondary` | full cardholder PII + card package | **HIGH PII — secondary cardholder** |
| `action_update_user_secure_profile` | ssn VARCHAR(32), dob DATETIME | **CRITICAL — SSN and date of birth** |
| `action_add_funds` | amount, currency, claimable, taxable, payment_ref | Fund addition |
| `action_claimable_add_funds` | | Claimable fund variant |
| `action_instant_issue_add_funds` | | Instant issue add-funds |
| `action_stop_payment` | | Stop payment parameters |
| `action_update_account_status` | | Account block/status change |
| `action_update_member_addenda` / `_value` | | Supplementary cardholder data |
| `action_update_user_registration` | | User registration update |
| `action_update_user_secure_profile` | ssn, dob | SSN + DOB — most sensitive table in schema |
| `action_notification` / `_result` | | Notification dispatch |
| `action_send_notification` / `_result` | | External notification |
| `action_memo` | | Action-level memo |
| `action_status` / `_log` | | Action status reference and history |
| `action_type` | | Action type reference |
| `action_bulk_order` / `_result` | | Bulk card order |
| `action_withdraw` / `_result` | | Withdrawal action |
| `action_link_card` / `_result` | | Card link action |

### Inventory
| Table | Key Columns | Notes |
|---|---|---|
| `inventory_program_location_activity_journal` | | Card inventory movements by program/facility |
| `inventory_account_identifier_type` | | Identifier type reference |
| `inventory_activity_type` | | Activity type reference |
| `inventory_facility_type` | | Facility type reference |

### WebLogic JMS
| Table | Notes |
|---|---|
| `ecountJmsDataStore1WLStore`, `ecountJmsDataStore2WLStore`, `ecountJmsDataStore3WLStore` | WebLogic JMS JDBC data stores |
| `jms1WLStore`, `jms2WLStore`, `jms3WLStore` | WL JMS stores |
| `jms2WLStore_Backup`, `jms2WLStore_backup_1` | Backup copies committed to source |

### Administrative
| Table | Notes |
|---|---|
| `CodeArchive` | Legacy code archive table |
| `ddl_log` | DDL change log |

---

## 4. Sensitive Data Assessment

| Data Element | Table | Classification | PCI DSS Req |
|---|---|---|---|
| SSN | `action_update_user_secure_profile.ssn` VARCHAR(32) | CRITICAL — government ID | Req 3.3.1 masking; GLBA NPI |
| Date of Birth | `action_update_user_secure_profile.dob` DATETIME | HIGH — sensitive personal data | GLBA, CCPA, GDPR |
| Full name (first/middle/last) | `action_register_user`, `action_issue_card_secondary` | HIGH — PII | GLBA NPI, GDPR |
| Physical address | `action_register_user`, `action_issue_card_secondary` | HIGH — PII | GLBA NPI, GDPR |
| Phone numbers (home/business/mobile) | `action_register_user`, `action_issue_card_secondary` | HIGH — PII | GLBA NPI |
| Email addresses | `action_register_user`, `action_issue_card_secondary` | MEDIUM — PII | GLBA NPI |
| Fund amounts | `action_add_funds.amount` | MEDIUM — financial | Reg E |
| card_package_id | `action_issue_card`, `action_issue_card_secondary` | MEDIUM — card program data | PCI DSS Req 3 |
| ecount_id | `request_detail.ecount_id` | MEDIUM — internal cardholder ID | CDE reference |
| partner_user_id | `request_detail.partner_user_id` | MEDIUM — partner cardholder ID | |

**`action_update_user_secure_profile.ssn`**: SSN is stored as VARCHAR(32) — not masked or encrypted at the column level. This is the most sensitive field in the database. PCI DSS Req 3.3.1 prohibits storing sensitive authentication data post-authorisation; SSN is GLBA NPI and must be protected under GLBA.

**`action_definition` view**: This view joins `action_update_user_secure_profile` and exposes `auusp.ssn` and `auusp.dob` directly — any application or report role with SELECT on this view has unmasked SSN visibility.

---

## 5. Encryption

| Control | Status | Notes |
|---|---|---|
| TDE | Not configured in SSDT project | Must verify at instance level |
| Column-level encryption | None visible | SSN and DOB stored in plaintext columns |
| `action_detail.secure_ref` | VARCHAR(40) | A reference identifier — not encrypted payload |
| Filegroup isolation | `Ordersvc_FG_1` | I/O isolation; does not provide encryption |

**Critical gap**: `action_update_user_secure_profile.ssn` and `.dob` are stored as plaintext VARCHAR/DATETIME. Applying Always Encrypted or column-level encryption to these fields would provide protection even from DBA-level access.

---

## 6. Data Flow

```
Partner / Client Zone
    |
    | HTTP request to Order Service API
    v
Order Service (Java application)
    |
    | INSERT into ordersvc SQL Server
    v
order_detail --> request_detail --> action_detail --> action_register_user / action_issue_card / action_update_user_secure_profile / etc.
                                                               |
                                              action_definition VIEW (exposes SSN, DOB, PII)
                                                               |
                                         EcountCore (cardholder creation via ecount_id)
                                                               |
                                     ECNT GP (sales order via order_billing_info.sales_order)
```

---

## 7. Compliance Gaps

| Gap | Location | Regulation |
|---|---|---|
| SSN stored as plaintext VARCHAR | `action_update_user_secure_profile.ssn` | GLBA NPI; PCI DSS adjacent |
| DOB stored as plaintext DATETIME | `action_update_user_secure_profile.dob` | GLBA NPI; CCPA; GDPR |
| `action_definition` view exposes SSN/DOB unmasked | `dbo\Views\action_definition.sql:39` | GLBA; PCI DSS Req 3.3.1 |
| JMS backup tables in production schema | `jms2WLStore_Backup`, `jms2WLStore_backup_1` | Data governance |
| No purge policy visible for most tables | Schema-level | PCI DSS Req 3.2 (data retention minimisation) |
| `usp_Table_Purge_action_notification_result` only purges notification results | Schema-level | Incomplete retention coverage |
| `CodeArchive` table in production schema | `CodeArchive.sql` | Legacy object; data governance |
