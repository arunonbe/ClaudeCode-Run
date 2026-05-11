# Data Architect View — inventory-mgmt_LIB

## Data Stores
| Store | Type | Database Reference |
|-------|------|--------------------|
| JobSvc SQL Server | Relational RDBMS | `jobsvc` database (Director-resolved) |
| ecountCore SQL Server | Relational RDBMS | `ecountcore` database (Director-resolved) |
| C-Base App SQL Server | Relational RDBMS | `cbaseapp` database (Director-resolved) |

Connection strings are resolved at runtime via the Director service registry (no connection strings are hardcoded in this library).

## Schema / Tables
Based on stored procedure names and DAO code in `InventoryManagementJDBCDao`:

**jobsvc database** (primary inventory store):

| Table / SP | Key Columns | Description |
|-----------|-------------|-------------|
| instant_issue_card | instant_issue_card_id, program_id, delivery_site_id, partner_user_id (puid), ecount_id, status, used_date, parent_dda, parent_puid, card_number, used_member_id, payable, facility, ship_date, tracking_number, shipping_data_date | Core card inventory |
| instant_issue_notification | affiliate_id, delivery_site_id, low_inventory | Low inventory flag per location |
| instant_issue_inv_email_log | program_id, delivery_site_id, email_address, type_of_email | Email notification audit log |
| instant_issue_inv_email_queue | program_id, delivery_site_id, request_file_id, num_of_cards_order, date_received, type_of_email | Pending email queue |
| instant_issue_inv_card_expiry_notification_log | program_id, delivery_site_id, minpackageid, maxpackageid, email_notification | Expiry alert log |
| instant_issue_order | order_id, program_id, delivery_site_id, size, facility_desc, username, address fields, file_name, request_file_id | Card orders |
| id_sequence | (resolved via stored procedures) | ID sequence blocks |

Stored procedures referenced:
- `instant_issue_create_order`, `instant_issue_current_inventory`, `instant_issue_order_history`, `get_instant_issue_order_history`, `instant_issue_get_card_by_ecount_id`, `instant_issue_use_card`, `instant_issue_new_card`, `instant_issue_unreserved_card`, `instant_issue_inventory_by_order_status`, `instant_issue_use_card_by_ecount_id_xml`, `instant_issue_card_inquiry`, `instant_issue_card_upd_inventory`, `instant_issue_is_card_reserved`, `instant_issue_card_expiry_batch`, `upd_instant_issue_order_with_request_file_id`, `upd_instant_issue_order_with_request_file_id_xml`, `get_instant_issue_unshipped_details`

## Sensitive Data Classification
| Field | Classification | PCI DSS Relevance |
|-------|---------------|-------------------|
| card_number | Cardholder Data — PAN | PCI DSS Req 3 — must be protected at rest (truncation or encryption) |
| partner_user_id (puid) | Payment card identifier | Maps to a payment card |
| ecount_id | Payment card identifier | Legacy card reference |
| parent_dda / parent_puid | Payment card identifiers | Parent card linkage |
| used_member_id | Internal member ID | Low sensitivity |
| delivery_site_id | Location identifier | Internal |

## Encryption
- No column-level encryption is visible in this library's code.
- card_number is stored and retrieved in plaintext via the `instant_issue_card_inquiry` stored procedure.
- Transport encryption depends on the JDBC DataSource configuration provided by the Director-configured DBCP factory.
- The xsecurity dependency provides a security framework but no encryption of card fields is observed in this library.

## Data Flow
1. Card inventory is populated externally (card ordering pipeline) into `instant_issue_card`.
2. `InventoryManagementManagerImpl` reads and updates inventory via JDBC stored procedure calls.
3. Auto-reorder writes XML request files to filesystem → Repository Service → external card production.
4. Card usage: `updateInventory()` calls `instant_issue_card_upd_inventory` SP to mark card as USED.
5. Email notifications written to `instant_issue_inv_email_log` and `instant_issue_inv_email_queue`.

## Data Quality / Retention
- No data retention or archival policy is implemented in this library.
- Batch update of shipping info uses a batch size of 100 rows.
- Query timeouts are configurable via `queryTimeoutValue` (setter injection), defaulting to the values declared in each inner class.
- `instant_issue_card_inquiry` SP uses a 5-minute query timeout (300,000 ms).

## Compliance Gaps
1. `card_number` is stored and retrieved in plaintext — PCI DSS Requirement 3.4 requires PANs to be rendered unreadable (truncation, hashing, or encryption). This is a critical gap if card_number contains a full PAN.
2. DEBUG logging logs ecountIds and PUIDs which are card identifiers — PCI DSS Requirement 3 applies if these map 1:1 to PANs.
3. No audit log of who queried or updated card_number values.
4. No evidence of PAN masking before logging (first 6 / last 4 rule).
5. Email queue and log tables retain email addresses and program/location data — retention policy needed.
