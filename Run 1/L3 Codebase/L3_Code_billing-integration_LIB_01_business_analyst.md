# billing-integration_LIB — Business Analyst View

## Business Purpose

billing-integration_LIB (artifact `billingIntegration`, version `1.0.0-SNAPSHOT`) is a shared Java library that acts as a **service facade over Microsoft Dynamics Great Plains (GP)**. Its stated description is: *"Provides a service facade over Great Plains."*

The library's core job is to translate an Onbe (ecount) internal prepaid-card order into a **GP Sales Order**, compute the correct billing fee owed by the client, and persist that sales order record so that downstream GP-side invoicing can proceed. It also supports cancellation of previously created GP sales orders.

---

## Business Capabilities

| Capability | Entry Point |
|---|---|
| Create a GP Sales Order for a qualifying prepaid-card order | `BIService.createSalesOrder(Order)` / `SalesOrderManagerImpl.createSalesOrder()` |
| Cancel a GP Sales Order | `BIService.cancelSalesOrder(Order)` / `SalesOrderManagerImpl.cancelSalesOrder()` |
| Determine whether a client program is configured at the promotion level in GP | `BIService.isCustomerSetAtPromo(String progId)` |
| Retrieve all GP customer numbers for a given program ID | `BIService.getGPCustomersByProgramId(String progId)` |
| Assess billing fees based on configurable fee schemes | `FeeStrategy` implementations (six schemes) |
| Calculate shipping fees for special delivery orders | `ShippingFeeHelper.calculateShippingCost()` |

---

## Business Entities

| Entity | Class | Table / Source | Notes |
|---|---|---|---|
| Sales Order | `SalesOrder` | `sales_order` | GP sales order staging record; holds order number, customer number, job number, file name, status, action, product code |
| Sales Order Item | `SalesOrderItem` | `sales_order_item` | Line item within a sales order; item number, quantity, unit price |
| Fee Scheme | `FeeScheme` | `fee_scheme` | Named billing scheme (e.g., `iss-fee-percent`, `rate-card`) |
| Fee Scheme Item | `FeeSchemeItem` | `fee_scheme_item` | Item codes belonging to a fee scheme |
| Fee Structure Item | `FeeStructureItem` | GP `contractpricing` table (JDBC) | Customer-specific price list sourced from Great Plains |
| Billing Exception Customer | `BillingExceptionCustomer` | `billing_customer_exception_list` | Customers excluded from auto GP sales-order creation |
| Shipping Fee | `ShippingFee` | `shipping_fee` | Banded shipping cost matrix (lower/upper card count limits) |
| Inventory Item | `InventoryItem` | GP `inventory` table (JDBC) | Card kit items with access levels; used to differentiate plastic fee lines |
| Rate Card Data | `RateCardData` | Stored proc `dbo.rate_card_data_summary` | Face-value category buckets for rate-card billing |
| Sales Order Status | `SalesOrderStatus` | Enum-style Symbol | NONE, CREATED, CREATE_FAILED, MANUAL_CREATE, CANCELLED, CANCEL_FAILED, MANUAL_CANCEL |

---

## Business Rules & Validations

1. **Order validity gate** (`SalesOrderManagerImpl.isValidOrder()`): an order must have a non-null, non-empty `programId`; otherwise processing silently returns.

2. **Customer promo detection** (`isCustomerSetAtPromo()`): if any GP customer number for the program is longer than 8 characters, has a hyphen at position 8, and is *not* a "-P" suffix entry, the customer is flagged as "set at promotion level." At promo level the fee structure lookup appends a zero-padded `promotionId` suffix to the program ID key (e.g., `04018194-00001`). If no GP customers are found at all, a `BIServiceException` is thrown with the message "Customer does not exist in Great Plains."

3. **Fee structure validity gate** (`isValidFeeStructure()`): if GP returns no pricing rows for the derived customer key, processing returns silently.

4. **Exception list gate** (`isCustomerInExceptionList()`): the `billing_customer_exception_list` table is checked; customers with `activity_type = 'sales_order'` are excluded from auto billing. Processing returns silently for matched customers.

5. **Fee scheme resolution** (`FeeSchemeHelper.getScheme()`): a fee structure must map to *exactly one* scheme. If item codes from the customer's fee structure match items across multiple different fee schemes, the result is `null` and no sales order is written.

6. **Rate card reconciliation** (`RateCardStrategy.assessFee()`): the total add-funds count in the order must exactly match the total subcount returned by the stored procedure `dbo.rate_card_data_summary`. A mismatch throws `BIServiceException("RateCard Data does not match")`.

7. **Reload fee deduction** (`ReloadFeeStrategy`, `CommonReloadFee`): reload fees subtract `issuedPlasticCount` from `addFundsCount` to avoid double-billing new card issuances.

8. **Special delivery flag** (`OrderItemsHelper.hasSpecialDelivery()`): shipping fee is only added if an order item of type `PLASTIC_SHIPPING` carries the memo key `delivery-code`.

9. **Amount scaling**: order monetary amounts are stored in cents (long); they are divided by 100 when placed into `SalesOrderItem.quantity` (`OrderItemsHelper.convertOrderAmtToSalesOrderAmt()`).

10. **Sales order persistence only when items exist**: `salesOrderDao.saveOrUpdate()` is called only if the items list is non-empty (`soItems.size() > 0`).

---

## Business Flows

### Create Sales Order Flow

```
Caller -> BIService.createSalesOrder(Order)
  -> SalesOrderManagerImpl.createSalesOrder()
      1. Validate order (programId present)
      2. Determine promo flag -> look up fee structure from GP contractpricing
      3. Validate fee structure is non-empty
      4. Check billing exception list
      5. Resolve fee scheme name (FeeSchemeHelper)
      6. Look up FeeStrategy from map (6 strategies)
      7. Build SalesOrder header (createSalesOrderHeader):
           - OrderType.FILE  -> jobNumber = FileOrder.jobId
           - OrderType.BILLINGSUB -> jobNumber via OrderDao lookup of parent billing order
           - Other -> jobNumber = order.mapOrderNumberForBilling()
      8. Fee.assessFee() -> delegates to FeeStrategy
      9. If items produced -> SalesOrderDao.saveOrUpdate()
```

### Cancel Sales Order Flow

```
Caller -> BIService.cancelSalesOrder(Order)
  -> SalesOrderManagerImpl.cancelSalesOrder()
      1. Find SalesOrder by orderNumber
      2. If salesOrderNumber already assigned -> set action = SALES_ORDER_CANCEL (1)
      3. Else -> set status = CANCELLED
      4. SalesOrderDao.saveOrUpdate()
```

### Fee Strategies (six schemes wired in `appContext-bisvc.xml`)

| Scheme Name | Strategy Class | Basis |
|---|---|---|
| `iss-fee-percent` | `IssuanceFeePercentStrategy` | Add-funds dollar total (item `1000`) |
| `iss-disc-percent` | `IssuanceFeePercentStrategy` | Add-funds discount dollar total (item `8500`) |
| `iss-fee-fixed` | `IssuanceFeeFixedStrategy` | Add-funds count (item `1010`) |
| `iss-disc-fixed` | `IssuanceFeeFixedStrategy` | Add-funds discount count (item `8501`) |
| `reload` | `ReloadFeeStrategy` | Add-funds count minus issuances (item `1031`) |
| `rate-card` | `RateCardStrategy` | Face-value category buckets from stored proc (items `10100`-`10140`) |

All strategies delegate to `CommonFeeAssessor` for shared fee lines: issuance (`0100`), issuance payment (`0101`), data entry (`5600`/`5610`), plastic fees (generic `2000`, affinity `2010`, custom `2020`, or kit items by access level), and shipping (`5700`).

---

## Compliance & Regulatory Concerns

- **PCI DSS**: The library processes prepaid card issuance and reload transaction volumes. No PANs, CVVs, or track data appear in source code. However, the `contractpricing` and `sales_order` tables hold customer program IDs and financial settlement amounts that may be considered cardholder-environment-adjacent data requiring access controls and audit logging per PCI DSS v4.0.1 Requirements 7, 8, and 10.
- **NACHA / Reg E**: Reload and issuance counts drive financial settlement entries into Great Plains. Errors in fee computation (especially the rate-card mismatch exception) could result in incorrect billing that materially affects fund disbursement, implicating Reg E accuracy obligations.
- **GLBA / Data Minimization**: The library stores `customerNumber`, `orderNumber`, `jobNumber`, and `fileName` in the `sales_order` table. These should be reviewed for GLBA NPI classification.
- **Audit Trail**: No explicit audit-log mechanism is implemented. `created_by` is hardcoded to the string `"BillingIntegration"` in `SalesOrderManagerImpl.createSalesOrderHeader()` (line 233); `modified_by` is never set by this service.
- **Error Handling**: `BIServiceException` is an unchecked `RuntimeException`. Silent `return` on invalid order or missing fee structure means failures produce no audit record or alert.

---

## Business Risks

1. **Silent failures on missing data**: If `programId` is missing, the fee structure is empty, or the customer is on the exception list, processing silently aborts with no notification to the caller or downstream system. Orders that should be billed may be silently skipped.
2. **Rate-card exception throws unchecked exception**: A data discrepancy in `dbo.rate_card_data_summary` vs. order items causes an unhandled `BIServiceException` that propagates to the EJB boundary — this could roll back the entire order processing transaction.
3. **Hardcoded `created_by` string**: `salesOrder.setCreatedBy("BillingIntegration")` in `SalesOrderManagerImpl` (line 233) provides no user-level audit trail, which is a compliance concern.
4. **No idempotency guard**: There is no check before `salesOrderDao.saveOrUpdate()` for whether a sales order for the same `orderNumber` already exists; this could create duplicate GP sales orders.
5. **SNAPSHOT versioning in production**: `version 1.0.0-SNAPSHOT` indicates this artifact has never been formally released, raising reproducibility concerns.
6. **EJB module commented out**: The parent `pom.xml` comments out `<module>billingIntegration-ejb</module>`, meaning the EJB layer (`BIServiceBean`) is not part of the standard build, yet the EJB source is still in the repository.
