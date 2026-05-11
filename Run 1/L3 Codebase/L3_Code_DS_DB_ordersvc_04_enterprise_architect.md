# Enterprise Architect View — DS_DB_ordersvc

## 1. Platform Generation

**Gen-1/Gen-2 boundary** — The ordersvc database follows a structured action/request/order command pattern that shows Gen-2 design thinking (GUID primary keys, status/log tables, custom execution roles, filegroup isolation). However, it carries Gen-1 artefacts: WebLogic JMS tables, `SET ROWCOUNT` usage, no CI/CD, plaintext SSN storage, and a `CodeArchive` legacy object.

---

## 2. Business Domain

**Order Lifecycle / Card Issuance Operations**. ordersvc is the persistence store for the Order Service — the system that manages every card issuance, fund loading, registration, and account management operation from initial request through fulfillment. It is the **operational command store** for all cardholder lifecycle events in the prepaid card platform.

---

## 3. Role in the Enterprise Architecture

```
Partner System / Client Zone
        |
        | order creation, card issuance requests
        v
Order Service API (Java application)
        |
        | reads/writes
        v
ordersvc (this database)
        |
        +--- ecount_id ---> EcountCore (cardholder creation/update)
        |
        +--- sales_order ---> ECNT GP (program financial billing)
        |
        +--- card_package_id / location_code ---> Fulfillment systems
        |
        +--- WebLogic JMS ---> Async processing (legacy)
```

ordersvc is a **write-heavy operational database** in the CDE. It receives all card order and cardholder registration events and is the source of truth for order status and action history.

---

## 4. Dependencies

### Upstream (depends on ordersvc)
| Dependency | Type | Notes |
|---|---|---|
| EcountCore database | Write-through | Cardholder records created in EcountCore via ecount_id linkage |
| ECNT GP | Write-through | Sales orders posted to GP via `order_billing_info.sales_order` |
| Fulfillment systems | Write-through | Card package issuance via delivery_code, location_code |
| DS_DB_dbadmin | Read | Index monitoring cross-database |

### Downstream (depends on ordersvc)
| Dependency | Type | Notes |
|---|---|---|
| Order Service (Java app) | Primary consumer | All order CRUD operations |
| B2C / Client Zone | Consumer | Order status queries via ordersvc_read / b2c roles |
| Reporting | Consumer | `report`, `report_full`, `report_readonly` roles |
| GERS tool | Consumer | Third-party tool with `gers_role` access |
| WebLogic JMS | Integrated | `WLJMS` login for JMS datastore |

---

## 5. Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| Command/action pattern | order_detail -> request_detail -> action_detail -> specific action tables | Immutable command log; each action creates a record chain |
| Status machine | `*_status_log` tables | All status transitions are logged with timestamp |
| Keyset pagination | `order_summary` and `request_inquiry` procedures | Dynamic SQL with temp table key sets for efficient paging |
| GUID primary keys | All entity tables use UNIQUEIDENTIFIER | Distributed-safe identity generation |
| Filegroup isolation | `Ordersvc_FG_1` | All application data on dedicated filegroup for I/O isolation |
| WebLogic JMS datastore | `jms*WLStore` tables | Legacy WebLogic JDBC persistence for async messaging |

---

## 6. Strategic Status

**Active production system — Gen-3 migration target (medium priority).**

ordersvc is an actively used operational database for a core business function (card issuance). It requires:
1. SSN/DOB encryption remediation (critical security gap)
2. Migration of WebLogic JMS to modern messaging infrastructure
3. Data retention/purge policy implementation for PII tables
4. CI/CD pipeline introduction
5. Long-term: consideration of whether the command-pattern database design should be migrated to an event sourcing or CQRS pattern in a Gen-3 platform

---

## 7. Migration Complexity and Blockers

**Complexity: HIGH**

| Factor | Assessment |
|---|---|
| SSN/DOB encryption | Must be remediated in-place; adding Always Encrypted requires application changes in Order Service |
| EcountCore coupling | `ecount_id` linkage means ordersvc cannot be migrated independently of EcountCore |
| ECNT GP coupling | `order_billing_info.sales_order` links to GP; must be migrated with GP replacement |
| WebLogic JMS | Legacy WebLogic dependency must be replaced with modern messaging (Azure Service Bus, Kafka) before app server modernisation |
| Action definition view SSN exposure | Any migration must ensure SSN masking is applied before replicating view definitions to new environment |
| Data volume | Active write-heavy system; migration requires minimal downtime strategy |
| Reporting consumers | Multiple downstream roles (report, b2c, gers_role) have direct DB access; must be preserved or redirected |
