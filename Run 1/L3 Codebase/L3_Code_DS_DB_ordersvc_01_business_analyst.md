# Business Analyst View — DS_DB_ordersvc

## 1. Repository Identity

| Attribute | Value |
|---|---|
| Repo name | DS_DB_ordersvc |
| Project file | `ordersvc.sqlproj` (SSDT, DSP Sql110 = SQL Server 2012) |
| Solution file | `ordersvc.sln` |
| README | "ordersvc" |
| Database name | ordersvc — Order Service operational database |

---

## 2. Business Purpose

`DS_DB_ordersvc` is the **Order Service operational database** for the Onbe prepaid card platform. It is the persistence layer for the Order Service microservice, which orchestrates the card issuance lifecycle: creating and managing card orders, processing cardholder registration, issuing cards, adding funds, managing card inventory, and tracking order status from creation through fulfillment.

This database is in the **Cardholder Data Environment (CDE)** perimeter because it stores:
- Cardholder PII (name, address, phone, email) in `action_register_user` and `action_issue_card_secondary`
- SSN and date of birth in `action_update_user_secure_profile`
- Card package identifiers in `action_issue_card`

---

## 3. Capabilities

1. **Order lifecycle management**: Creates, tracks, and closes prepaid card orders (`order_detail`, `order_status`, `order_activity`)
2. **Cardholder registration**: Captures cardholder PII for new card registrations (`action_register_user`)
3. **Card issuance**: Issues primary and secondary cards (`action_issue_card`, `action_issue_card_secondary`)
4. **Fund management**: Handles add-funds requests, claimable funds, and instant issue (`action_add_funds`, `action_claimable_add_funds`, `action_instant_issue_add_funds`)
5. **Sweep order management**: Manages fund sweep operations across programs (`order_sweep`, `create_sweep_order`, `cleanup_sweep_orders`)
6. **Card inventory tracking**: Tracks card inventory by program and facility (`inventory_program_location_activity_journal`)
7. **Stop payment processing**: Manages stop payment actions (`action_stop_payment`)
8. **Account status management**: Updates and tracks account status (`action_update_account_status`)
9. **Member addenda management**: Updates member addenda (supplementary cardholder data) (`action_update_member_addenda`)
10. **Secure profile management**: Manages SSN/DOB for identity verification (`action_update_user_secure_profile`)
11. **WebLogic JMS persistence**: Hosts WebLogic JMS datastore tables (`ecountJmsDataStore*WLStore`, `jms*WLStore`) for message queuing

---

## 4. Key Entities

| Entity | Table | Description |
|---|---|---|
| Order | `order_detail` | Card order header: program_id, type, status, ref_id, order_number |
| Request | `request_detail` | Individual action request within an order: program_id, ecount_id, partner_user_id |
| Action | `action_detail` | Atomic action within a request (issue card, add funds, register, etc.) |
| Register User | `action_register_user` | Cardholder PII: name, address, phone, email, country, state |
| Issue Card | `action_issue_card` | Card issuance parameters: delivery_code, location_code, card_package_id |
| Issue Card Secondary | `action_issue_card_secondary` | Secondary card with full cardholder PII |
| Add Funds | `action_add_funds` | Fund addition: amount, currency, taxable, claimable |
| Update Secure Profile | `action_update_user_secure_profile` | SSN (VARCHAR 32) and DOB (DATETIME) |
| Stop Payment | `action_stop_payment` | Stop payment action parameters |
| Account Status | `action_update_account_status` | Block code, status change |
| Member Addenda | `action_update_member_addenda_value` | Supplementary cardholder data key-value pairs |
| Order Sweep | `order_sweep` | Sweep order for cross-program fund movements |
| Inventory | `inventory_program_location_activity_journal` | Card inventory movements by program/facility |

---

## 5. Business Rules

- Each `order_detail` is uniquely identified by the combination of `program_id` + `ref_id`
- `order_detail` has a CHECK constraint: `count_active_sweep_orders(program_id, promotion_id, created) < 2` — no more than 1 active sweep order per program/promotion at a time
- `order_summary` procedure generates paginated order summaries with dynamic SQL (keyset pagination)
- Order types 4 and 5 are excluded from standard summary queries (internal sweep types)
- `request_detail` uniquely keyed by `program_id` + `ref_id` (two unique constraints)
- `action_detail` ordered within a request by position (`pos`) — action sequence within a request matters
- `action_detail` uses a dedicated filegroup `Ordersvc_FG_1` for I/O isolation
- `usp_Table_Purge_action_notification_result` — scheduled purge for the `action_notification_result` table

---

## 6. Process Flows

### Card Order Lifecycle
1. Client Zone / Partner system creates order → `order_detail` + `request_detail` records created
2. Order Service processes actions: `action_detail` rows created for each action type (issue card, add funds, register user, etc.)
3. Specific action tables populated based on action type
4. Order status progresses through states; logged in `order_status_log`
5. On completion: `post_clean_sweep_orders` cleans up sweep-related records; sales order posted to ECNT GP via `order_activity_post_sales_order`

### Cardholder Registration
1. Partner submits registration request with cardholder PII
2. `action_register_user` record created with full name/address/contact
3. Registration processed; cardholder created in EcountCore
4. Result returned via `action_register_user_result`

### Sweep Orders
1. `create_sweep_order` creates a sweep order for cross-program fund movement
2. `count_active_sweep_orders` function enforces at-most-1 active sweep constraint
3. `count_harford_daily_created_sweep_orders` tracks Harford-sourced daily sweep volume
4. `find_inactive_sweep_orders` + `cleanup_sweep_orders` purge completed sweeps

---

## 7. Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | Stores cardholder PII (name, address, SSN, DOB); in-scope for PCI DSS Req 3, 7, 8, 10 |
| **GLBA** | `action_update_user_secure_profile.ssn` is financial account-associated PII |
| **CCPA / GLBA** | Cardholder PII in `action_register_user` and `action_issue_card_secondary` |
| **Reg E (EFTA)** | Fund addition and stop payment actions are electronic fund transfer events |
| **NACHA** | Fund movements via sweep orders may involve ACH |
| **GDPR** | If EU cardholder data is present in `action_register_user` |
