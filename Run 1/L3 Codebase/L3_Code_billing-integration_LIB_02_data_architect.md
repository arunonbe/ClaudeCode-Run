# billing-integration_LIB — Data Architect View

## Data Stores

The library interacts with **three distinct SQL Server databases**, resolved via JNDI at runtime:

| JNDI Name | Bean ID | Purpose | Access Method |
|---|---|---|---|
| `java:jdbc/OrderDataSource` | `OrderDataSource` | Staging database for GP sales orders, fee schemes, shipping fees, exception lists | Hibernate 3 (annotation-based) |
| `java:jdbc/GreatPlainsDataSource` | `GreatPlainsDataSource` | Microsoft Dynamics GP / "cbaseapp" | Spring JDBC (`JdbcTemplate`) |
| `java:jdbc/JobSvcDataSource` | `JobSvcDataSource` | Job service database; supplies rate-card data | Spring JDBC via stored procedure |

Test configs (`datasourceTestContext.xml`, `jboss-bisvc-beans.xml`) reveal the dev server as `ecsqldev1` with database names `ordersvc_test`, `jobsvc_test`, `cbaseapp` / `ETEST`.

---

## Schema & Tables

### OrderDataSource (managed by this service via Hibernate)

#### `sales_order`
| Column | Java Field | Notes |
|---|---|---|
| `id` | `SalesOrder.id` (long) | Auto-generated PK |
| `create_date` | `createDate` | Set to `new Date()` at creation; `modified_date` is never set by this service |
| `created_by` | `createdBy` | Hardcoded to `"BillingIntegration"` |
| `modified_by` | `modifiedBy` | Never populated by this service |
| `order_number` | `orderNumber` (long) | FK to Order Service order |
| `customer_number` | `customerNumber` | GP customer number (e.g., `04018194`) |
| `job_number` | `jobNumber` | GP job / file identifier |
| `file_name` | `fileName` | Source file name |
| `status` | `status` (int) | Maps to `SalesOrderStatus` symbol (1=NONE, 2=CREATED, 3=CREATE_FAILED, etc.) |
| `sales_order_number` | `salesOrderNumber` | Assigned by GP after processing; null until GP processes the record |
| `action` | `action` (int) | 1 = SALES_ORDER_CANCEL |
| `product` | `product` | First 2 characters of customerNumber |

#### `sales_order_item`
| Column | Java Field | Notes |
|---|---|---|
| `id` | `id` (long) | Auto-generated PK |
| `item_number` | `itemNumber` | GP item code string |
| `quantity` | `quantity` (double) | Transaction count or dollar amount (scaled from cents) |
| `unit_price` | `unitPrice` (double) | From `contractpricing.UnitPrice` |
| `sales_order_id` | `salesOrder` | FK to `sales_order.id` (cascade ALL) |

#### `fee_scheme`
| Column | Java Field | Notes |
|---|---|---|
| `id` | `id` (int) | Auto-generated PK |
| `name` | `name` | Scheme name (e.g., `iss-fee-percent`, `rate-card`) |

Annotated with `@Cache(READ_ONLY)` — cached indefinitely in EhCache (`eternal=true`).

#### `fee_scheme_item`
| Column | Java Field | Notes |
|---|---|---|
| `id` | `id` (int) | Auto-generated PK |
| `item_code` | `itemNumber` | GP inventory item code |
| `fee_scheme_id` | `feeScheme` | FK to `fee_scheme.id` |

#### `billing_customer_exception_list`
| Column | Java Field | Notes |
|---|---|---|
| `id` | `id` (long) | Auto-generated PK |
| `customer_number` | `customerNum` | GP customer number |
| `activity_type` | `activityType` | Service only queries where `activity_type='sales_order'` |

#### `shipping_fee`
| Column | Java Field | Notes |
|---|---|---|
| `id` | `id` (long) | Auto-generated PK |
| `lower_limit` | `lower` (int) | Lower bound of card count range |
| `upper_limit` | `upper` (int) | Upper bound of card count range |
| `standard_fee` | `standardFee` (double) | Fee dollar amount for this band |

Annotated with `@Cache(READ_ONLY)` — cached indefinitely in EhCache (`eternal=true`).

### GreatPlainsDataSource (read-only JDBC queries; "cbaseapp" database)

#### `contractpricing` (GP table, queried via `JdbcGPCustomersDao`)

Columns read: `ProgramID`, `UnitPrice`, `ItemNumber`, `ItemDescript`

Two queries:
- `SELECT DISTINCT ProgramID FROM contractpricing WHERE ProgramID LIKE ?` — customer discovery (uses `progId%` wildcard)
- `SELECT c.ProgramID, c.UnitPrice, c.ItemNumber, c.ItemDescript FROM contractpricing c WHERE c.ProgramID = ?` — fee structure retrieval

A commented-out stored procedure call (`dbo.get_contract_pricing`) is also present in `CallGetContractPricing.java` with parameters `program_id` and `promotion_Id`.

#### `inventory` (GP table, queried via `JdbcGPInventoryDao`)

Columns read: `ItemNumber`, `ItemDescript`, `AccessLevel`, `ItemType`, `ItemClass`

Query: `SELECT ... FROM inventory WHERE ItemType = 3` (ItemType 3 = kit items)

### JobSvcDataSource (stored procedure)

#### Stored Procedure: `dbo.rate_card_data_summary` (called via `CallRateCardDataSummary`)

Input: `job_id` (BIGINT)
Output result set columns: `category`, `subtotal`, `subcount`

Maps to `RateCardData` (faceValueCategory, subTotal, subCount).

---

## Sensitive Data Handling

- **Customer / Program IDs**: `ProgramID` / `customerNumber` values like `04018194` appear to be client program identifiers. They are stored in plain text in `sales_order`, `fee_structure_item` (in-memory), and queried from GP. No masking is applied.
- **Financial amounts**: `UnitPrice` (contract price per item) and `quantity` (billing volume) are stored as plain `double` in `sales_order_item`. These constitute financial settlement data.
- **No PAN, CVV, or account numbers** are present in any source file.
- **Test credentials exposed in source**: `jboss-bisvc-beans.xml` contains hardcoded credentials:
  - User `bintegrate`, password `$1ii1nt3grat3` for the GP datasource (`cbaseapp`)
  - User `andrewc`, password `andrewc` for `jobsvc_test` and `ordersvc` databases
  - `settings.xml` contains Maven repository credentials: `dwil15?` (nexus-qa), `d3v0nly` (ecount.release/snapshot), and `acmng/acmng` (wirecard proxy)
  These are committed to source control and constitute a **critical credential exposure risk**.

---

## Encryption & Protection

- **No encryption at rest** is implemented within the library. All data is written to SQL Server tables without application-layer encryption.
- **No field-level encryption** on any sensitive columns (`customer_number`, `unit_price`, financial amounts).
- **Transport**: Data access is over JDBC; no TLS/SSL enforcement is specified in any datasource configuration. The JTDS driver URLs in test configs use plain `jdbc:jtds:sqlserver://` without `ssl=require`.
- **EhCache**: The `diskStore path="java.io.tmpdir"` means cache overflow could write fee scheme and shipping fee data to a temp directory on disk without any encryption (`diskPersistent=false` but `overflowToDisk=true` on default cache).
- **Hibernate**: `hibernate.show_sql=true` is enabled in **all** session factory configurations including production (`appContext-hibernate.xml`), which means SQL statements containing financial data values will be emitted to application logs.

---

## Data Flow

```
Order Service (Order domain object)
        |
        v
SalesOrderManagerImpl
        |
        +--[JDBC READ]--> GP contractpricing (GreatPlainsDataSource)
        |                     -> FeeStructureItem map
        +--[Hibernate READ]--> billing_customer_exception_list (OrderDataSource)
        |
        +--[Hibernate READ]--> fee_scheme / fee_scheme_item (OrderDataSource, cached)
        |
        +--[JDBC READ]--> GP inventory (GreatPlainsDataSource)
        |                     -> InventoryItem list (kit items)
        +--[JDBC SPROC]--> dbo.rate_card_data_summary (JobSvcDataSource) [rate-card only]
        |                     -> RateCardData list
        |
        +--[Hibernate READ]--> shipping_fee (OrderDataSource, cached) [shipping only]
        |
        v
     SalesOrder + SalesOrderItems assembled in memory
        |
        v
     [Hibernate WRITE]--> sales_order + sales_order_item (OrderDataSource)
```

---

## Data Quality & Retention

- **No retention policy** is defined within the library. The `sales_order` table has no `deleted_at` or archival flag.
- **Duplicate risk**: No unique constraint logic is enforced in `HibernateSalesOrderDao.saveOrUpdate()`. If `createSalesOrder` is called twice for the same `orderNumber`, two `sales_order` rows will be created. `findByOrderNumber()` throws `BIServiceException("Multiple sales orders for this order")` if this occurs, indicating the schema has no unique constraint on `order_number`.
- **`modified_date` never set**: `SalesOrder.modifiedDate` field exists in the entity but is never assigned by any code in the library, leaving it permanently null after create.
- **`double` for money**: `FeeStructureItem.unitPrice`, `SalesOrderItem.unitPrice`, and `SalesOrderItem.quantity` all use Java `double`. Floating-point arithmetic on financial amounts is a data quality risk; `BigDecimal` should be used instead.
- **Amount scaling**: Order item estimates are stored in cents (long) and divided by 100 in `OrderItemsHelper.convertOrderAmtToSalesOrderAmt()`. This conversion is applied inconsistently: `getAddFundsTotalAll()` divides, but `getAddFundsCountAll()` (count, not amount) does not. If the wrong quantity method is selected by a strategy, the sales order item quantity will be off by a factor of 100.

---

## Compliance Gaps

| Gap | Detail | Applicable Standard |
|---|---|---|
| Credentials in source control | `jboss-bisvc-beans.xml` contains plaintext DB password `$1ii1nt3grat3` and Maven `settings.xml` contains `dwil15?`, `d3v0nly`, `acmng` | PCI DSS Req 8.2, GLBA Safeguards Rule |
| No TLS enforcement on JDBC connections | All datasource configs use plain JDBC URLs without SSL flags | PCI DSS Req 4.2 (data in transit) |
| `hibernate.show_sql=true` in production config | Financial data values written to application logs | PCI DSS Req 10, GLBA |
| `double` for financial amounts | Floating-point precision loss on monetary values | General accounting integrity; GAAP |
| No audit trail for modified_by / timestamps | `modified_by` and `modified_date` never populated | PCI DSS Req 10.3 |
| EhCache disk overflow to unencrypted temp | Default cache `overflowToDisk=true` pointing to `java.io.tmpdir` | PCI DSS Req 3.5 (protect stored data) |
| No schema migration tooling | No Flyway / Liquibase present; schema changes are manual | Operational risk, change management |
