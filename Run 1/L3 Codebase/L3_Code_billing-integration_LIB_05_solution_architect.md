# billing-integration_LIB — Solution Architect View

## Technical Architecture

### Module Structure

```
billingIntegration (root POM, pom packaging)
├── billingIntegration-pojo  (JAR — active, the core library)
│   ├── com.ecount.service.bi.bs           — service interfaces + strategy interfaces
│   ├── com.ecount.service.bi.bs.impl      — service + strategy implementations
│   ├── com.ecount.service.bi.bo           — domain/value objects (Hibernate entities)
│   ├── com.ecount.service.bi.dao          — DAO interfaces
│   ├── com.ecount.service.bi.dao.hibernate — Hibernate DAO implementations
│   ├── com.ecount.service.bi.dao.jdbc     — JDBC / StoredProcedure DAO implementations
│   └── com.ecount.service.bi.startup      — BIAppContext singleton
└── billingIntegration-ejb   (EJB JAR — commented out of build)
    └── com.ecount.service.bi.bs.ejb       — BIServiceBean (JBoss SLSB)
```

### Layer Responsibilities

| Layer | Classes | Responsibility |
|---|---|---|
| Service interface | `BIService` | Public API contract |
| Service impl | `BIServiceImpl` | Delegates to `SalesOrderManager` |
| EJB facade | `BIServiceBean` | JBoss SLSB; delegates to Spring bean via `AbstractGenericEJB3` |
| Order management | `SalesOrderManagerImpl` | Orchestrates fee assessment flow; owns create/cancel logic |
| Fee context | `Fee` | Strategy pattern context; holds `FeeStrategy`, `feeStructure`, `Order`, `SalesOrder` |
| Fee strategies | `IssuanceFeePercentStrategy`, `IssuanceFeeFixedStrategy`, `ReloadFeeStrategy`, `RateCardStrategy` | Scheme-specific fee computation |
| Common fee | `CommonFeeAssessor` (decoratee), `CommonReloadFee` (decorator), `CommonFeeDecorator` (abstract) | Shared fee lines for all schemes |
| Helper | `FeeSchemeHelper`, `FeeStructureHelper`, `OrderItemsHelper`, `ShippingFeeHelper` | Utility logic |
| Domain objects | `SalesOrder`, `SalesOrderItem`, `FeeScheme`, `FeeSchemeItem`, `FeeStructureItem`, `BillingExceptionCustomer`, `ShippingFee`, `InventoryItem`, `RateCardData`, `SalesOrderStatus`, `Symbol` | Data carriers |
| DAO interfaces | `SalesOrderDao`, `FeeSchemeDao`, `BillingCustomerExceptionDao`, `ShippingFeeDao`, `GPCustomersDao`, `GPInventoryDao`, `RateCardDataDao` | Data access contracts |
| Hibernate DAOs | `HibernateSalesOrderDao`, `HibernateFeeSchemeDao`, `HibernateBillingCustomerExceptionDao`, `HibernateShippingFeeDao` | Hibernate 3 / `HibernateDaoSupport` |
| JDBC DAOs | `JdbcGPCustomersDao`, `JdbcGPInventoryDao`, `JdbcRateCardDataDao` | Spring `JdbcDaoSupport` + `StoredProcedure` |
| Spring config | `appContext-bisvc.xml`, `appContext-hibernate.xml`, `appContext-jdbc.xml` | Bean wiring |

### Design Patterns Identified

- **Strategy**: `FeeStrategy` interface with four concrete implementations; selected at runtime from a `Map<String, FeeStrategy>` keyed by scheme name (wired in `appContext-bisvc.xml`)
- **Decorator**: `CommonFeeDecorator` (abstract) → `CommonReloadFee` wraps `CommonFeeAssessor` to chain reload-specific common fees before standard common fees in `IssuanceFeePercentStrategy`
- **Facade**: `BIService` / `BIServiceImpl` thin facade; `BIServiceBean` EJB facade over Spring bean
- **DAO**: Clean interface/implementation separation with separate Hibernate and JDBC implementations
- **Singleton**: `BIAppContext` — manual singleton pattern (not Spring-managed); problematic for testing

---

## API Surface

### Public Java Interface
`com.ecount.service.bi.bs.BIService` (4 methods):

```java
void createSalesOrder(Order order)
void cancelSalesOrder(Order order)
boolean isCustomerSetAtPromo(String progId)
List<String> getGPCustomersByProgramId(String progId)
```

All parameters use `com.ecount.service.order.domain.Order` (from `order-pojo:1.0.1`) — a tight JAR-level coupling.

### EJB Bindings (when EJB module is built and deployed)
- Local: `BIService/local` (JNDI)
- Remote: `BIService/remote` (JNDI)

### Database Procedures Invoked
- `dbo.rate_card_data_summary(job_id BIGINT)` — active (JobSvc DB)
- `dbo.get_contract_pricing(program_id VARCHAR, promotion_Id VARCHAR)` — present in code (`CallGetContractPricing`) but commented out; replaced by inline JDBC `SELECT`

### SQL Queries (inline JDBC)
- `SELECT DISTINCT ProgramID FROM contractpricing WHERE ProgramID LIKE ?` — GP DB
- `SELECT c.ProgramID, c.UnitPrice, c.ItemNumber, c.ItemDescript FROM contractpricing c WHERE c.ProgramID = ?` — GP DB
- `SELECT ItemNumber, ItemDescript, AccessLevel, ItemType, ItemClass FROM inventory WHERE ItemType = 3` — GP DB

### HQL Queries (Hibernate)
- `from com.ecount.service.bi.bo.FeeScheme` — find all fee schemes
- `from com.ecount.service.bi.bo.FeeScheme fs where fs.name ='?'` — find by name (**bug: literal `?` not parameterized** — see Code-Level Risks)
- `from com.ecount.service.bi.bo.SalesOrder so where so.orderNumber =?` — find by order number
- `from com.ecount.service.bi.bo.BillingExceptionCustomer bc where bc.activityType='sales_order'` — exception list

---

## Security Posture

### Authentication & Authorization
- **None implemented in the library itself.** The library assumes it is called from within a trusted JEE context (same JBoss JVM or trusted EJB remote caller).
- No role-based access control, no method-level security annotations.

### Credential Exposure
- **`jboss-bisvc-beans.xml`** (test resource, committed to source): GP database password `$1ii1nt3grat3` for user `bintegrate` on `cbaseapp` database. Plaintext. This file is in the Git history.
- **`.mvn/wrapper/settings.xml`**: Maven server passwords `dwil15?` (nexus-qa), `d3v0nly` (ecount release/snapshot), `acmng/acmng` (Wirecard proxy). Committed to Git.
- Both sets of credentials must be treated as **compromised** and rotated regardless of whether the hosts are still accessible.

### Input Validation
- `programId` null/empty check in `isValidOrder()` — minimal.
- No length validation, no character whitelist validation on any input.
- The `leadPad()` method in `SalesOrderManagerImpl` (line 325) is called on `order.getPromotionId()` without a null-check; if `promotionId` is null, `String.length()` will throw a `NullPointerException`.

### SQL Injection
- JDBC queries use parameterized `?` placeholders — no direct string concatenation in active query code.
- However, `HibernateFeeSchemeDao.findByName()` uses HQL with a literal `'?'` (quoted) in the query string `"from com.ecount.service.bi.bo.FeeScheme fs where fs.name ='?'"` — this is not a parameter placeholder; the method passes a `new Object[] {name}` second argument to `getHibernateTemplate().find()`, but Hibernate's `find()` with a literal `'?'` in HQL would not bind it correctly. This query likely never returns results by name; `findByName()` is not called in production paths, so this is a dormant bug rather than an active injection risk.

### Transport Security
- No TLS enforcement in any datasource configuration.
- The JTDS driver URLs in test configs are plain `jdbc:jtds:sqlserver://` without `ssl=require`.

### Logging of Sensitive Data
- `hibernate.show_sql=true` in `appContext-hibernate.xml` (production): SQL statements with bind parameter values will appear in application server logs.
- No log sanitization.

---

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| Java 5 bytecode target | Both `pom.xml` files | Critical |
| Spring 2.0, Hibernate 3.2.0.cr4 | `billingIntegration-pojo/pom.xml` | Critical |
| `double` for financial amounts | `FeeStructureItem`, `SalesOrderItem`, `ShippingFee` | High |
| Hardcoded item code magic strings | `IssuanceFeePercentStrategy`, `IssuanceFeeFixedStrategy`, `ReloadFeeStrategy`, `RateCardStrategy`, `CommonFeeAssessor` | High |
| `BIAppContext` missing `appContext-jdbc.xml` | `BIAppContext.java:22-25` | High — runtime NPE when using standalone context |
| `HibernateFeeSchemeDao.findByName()` broken HQL | `HibernateFeeSchemeDao.java:18` — `"from ... where fs.name ='?'"` | Medium |
| `SalesOrderManagerImpl.cancelSalesOrder()`: null dereference before null check | Lines 179-180: `salesOrder.getSalesOrderNumber()` called before `if (salesOrder != null)` | High — NPE if no sales order found |
| `promotionId` null-check missing in `createSalesOrder` | `SalesOrderManagerImpl.java:117` — `leadPad(order.getPromotionId())` | Medium — NPE if promotionId is null |
| `modified_date` / `modified_by` never populated | `SalesOrderManagerImpl` | Medium |
| EJB module commented out but code present | Root `pom.xml:41` | Medium — dead code / confusing |
| All substantive tests commented out | `BIServiceTest`, `BIServiceBeanTest` | High — no reliable test coverage |
| Credentials in source control | `jboss-bisvc-beans.xml`, `.mvn/wrapper/settings.xml` | Critical |
| `hibernate.show_sql=true` in production config | `appContext-hibernate.xml` | High |
| `eternal=true` EhCache for FeeScheme, ShippingFee | `ehcache.xml` | Medium — stale config without restart |
| Legacy Wirecard Nexus mirror | `.mvn/wrapper/settings.xml` | Medium — build breakage |
| No idempotency guard on `createSalesOrder` | `SalesOrderManagerImpl` | High — duplicate GP sales orders |
| `CascadeType.ALL` on `SalesOrder.items` | `SalesOrder.java:92` | Medium — delete cascades could be unintentional |
| `@SuppressWarnings("unchecked")` throughout | All Hibernate/JDBC DAOs | Low — pre-generics Hibernate API; expected but should be migrated |
| `new Integer(accessLevel)` boxing | `CommonFeeAssessor.java:103` | Low — deprecated constructor |

---

## Gen-3 Migration Requirements

To migrate this library to a Gen-3 platform (Spring Boot, containerized microservice, modern Java), the following are required:

1. **Upgrade runtime**: Java 17+, Spring Boot 3.x, Hibernate 6.x (or Spring Data JPA)
2. **Replace EJB with REST**: Expose `BIService` operations as REST endpoints (`POST /sales-orders`, `DELETE /sales-orders/{orderNumber}`) with JWT/OAuth2 authorization
3. **Decouple Order domain**: Replace `order-pojo` JAR dependency with an API contract (OpenAPI schema or event schema); consume `Order` data via REST call or event (Kafka/SNS)
4. **Replace GP direct-JDBC**: Implement a GP integration via an API gateway or message-based integration (e.g., webhook, MuleSoft, or GP REST API if available); remove `GreatPlainsDataSource` JDBC dependency
5. **Externalize fee configuration**: Move hardcoded item codes to a configuration database or feature flag service; implement cache refresh without restart
6. **Use `BigDecimal` for money**: Replace all `double` financial fields
7. **Add idempotency**: Unique constraint on `order_number` in `sales_order`; check-before-insert logic in the service
8. **Implement audit fields**: Populate `modified_by` and `modified_date` via Spring Data auditing
9. **Schema migration**: Add Flyway or Liquibase for `sales_order`, `fee_scheme`, `fee_scheme_item`, `billing_customer_exception_list`, `shipping_fee`
10. **Secrets management**: Remove all credentials from source; use Vault, AWS Secrets Manager, or equivalent
11. **Structured logging**: Replace Log4j `log.debug()` with SLF4J + JSON appender; add correlation IDs; disable `show_sql` in all environments
12. **Test coverage**: Replace commented-out integration tests with unit tests using mocks + embedded database tests; target >80% line coverage
13. **Observability**: Add Micrometer metrics, Spring Actuator health checks, distributed tracing (OpenTelemetry)

---

## Code-Level Risks

### Critical Bug: Null dereference before null check in `cancelSalesOrder`
**File**: `billingIntegration-pojo/src/main/java/com/ecount/service/bi/bs/impl/SalesOrderManagerImpl.java`, lines 178–180

```java
SalesOrder salesOrder = salesOrderDao.findByOrderNumber(order.getOrderNumber());
log.debug("Cancel SalesOrder Number: " + salesOrder.getSalesOrderNumber()); // NPE if salesOrder is null
if (salesOrder != null){
```

`salesOrder.getSalesOrderNumber()` is called unconditionally on line 179, but `findByOrderNumber()` returns `null` when no record is found. The null check appears on line 180 — too late. This will throw `NullPointerException` for any cancel request where no staging sales order was previously created.

### High Bug: `BIAppContext` missing JDBC context
**File**: `billingIntegration-pojo/src/main/java/com/ecount/service/bi/startup/BIAppContext.java`, lines 22–25

Only three XML files are loaded; `appContext-jdbc.xml` is absent. The standalone context will fail to wire `GPCustomersDao`, `GPInventoryDao`, and `RateCardDataDao`, causing `NullPointerException` in `SalesOrderManagerImpl` at any GP data access point.

### High Bug: HQL parameterization in `HibernateFeeSchemeDao.findByName()`
**File**: `billingIntegration-pojo/src/main/java/com/ecount/service/bi/dao/hibernate/HibernateFeeSchemeDao.java`, line 18

```java
private final String findByNameSQL = "from com.ecount.service.bi.bo.FeeScheme fs where fs.name ='?'";
```

The `?` is inside single quotes, making it a string literal, not a Hibernate positional parameter. The `find(hql, new Object[]{name})` call will not substitute the value. This method always returns `null` or an empty list regardless of input. This method is not called in the production code path (scheme lookup goes through `findAll()` in `FeeSchemeHelper`), so it is a dormant bug — but it is broken.

### Medium Bug: Potential NPE on null `promotionId`
**File**: `SalesOrderManagerImpl.java`, line 117

```java
String promoId = leadPad(order.getPromotionId());
```

`leadPad()` calls `orig.length()` at line 329. If `order.getPromotionId()` returns `null`, this throws `NullPointerException`. The `Order` interface does not document whether `promotionId` can be null.

### Medium: `double` arithmetic on financial values
All monetary fields (`unitPrice`, `quantity`, `standardFee`) use Java primitive `double`. Floating-point binary representation can introduce rounding errors in financial calculations. For example, `0.1 + 0.2 != 0.3` in IEEE 754. Any billing amounts computed through these fields may be slightly off and could cause reconciliation discrepancies with GP.

### Medium: `RateCardStrategy` validation is single-equality check
**File**: `RateCardStrategy.java`, line 62

```java
if(this.getTotalCount(rateCardDataList) == oiHelper.getAddFundsCountAll()){
```

An exact integer equality check between a stored-procedure result set sum and an in-memory order count is brittle. Any timing issue, partial data delivery, or rounding discrepancy throws an unchecked exception and abandons the entire order billing. This should be handled more gracefully.

### Low: `StandardShipping.calulateShippingCost()` — typo in method name
**File**: `StandardShipping.java` / `ShippingStrategy.java`

```java
public double calulateShippingCost(double sChrg)  // "calulatate" — missing 'c'
```

This is a public interface method name. Correcting it would be a breaking API change.
