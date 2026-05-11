# Business Analyst View — inventory-mgmt-batch-client_LIB

## Business Purpose
A Gen-1 Java batch client library that runs scheduled/on-demand batch jobs against the inventory-mgmt_LIB to synchronise instant-issue card states with the core ecount platform, process card expiration alerts, and manage email notification queues. It is the batch execution layer that sits above inventory-mgmt_LIB and drives the actual scheduled operations.

## Capabilities
- **AutoReorder / CoreSync**: Queries ecount core for DDA (Demand Deposit Account) card lists in various states (assigned, blocked, loaded, expired) as XML, then drives the inventory management auto-reorder workflow.
- **Card Expiry Alert Batch**: Standalone Java main class (`CardExpiryAlertNotificatonClient`) that iterates all active instant-issue programs, checks expiration alert configuration, and triggers expiration notification via inventory management.
- **Shipping Info Population**: `PopulateShippingInfoBatch` reads unshipped inventory cards and populates shipping date, tracking number, and card number from external shipping data.
- **Email Notification**: DAO-backed email notification queue reader/writer (`EmailNotificationDao`).

## Entities
| Entity | Description |
|--------|-------------|
| CoreSyncCard (interface) | Card state query interface against ecountcore DB: assigned/blocked/loaded/expired DDA number lists |
| DDA_Number | Demand Deposit Account number domain object |
| InventoryEmailNotification | Email notification record for inventory events |

## Business Rules
- The card expiry batch checks `expirationAlertDays`; for values < 28 the alert fires only when remaining days in the month equals the configured value.
- Auto-reorder batch processes all programs configured in `AppProfileInstantIssue` and delegates to `InventoryManagementManager.checkInventory()`.
- Shipping info is populated in bulk (batch updates via `PopulateShippingInfoBatch`).
- Config is loaded from filesystem properties files at fixed paths: `D:/c-base/config/inventoryMgmt/inventoryMgmtBatchClient.properties` and `D:/c-base/config/director-client.properties`.

## Process Flows
1. **Card Expiry Alert**: OS scheduler/cron → `CardExpiryAlertNotificatonClient.main()` → Spring context load → iterate programs → check expiry config → call `cardExpiryClientDao.sendExpirationAlertNotification()`.
2. **Auto Reorder Sync**: Batch trigger → `AutoReorderCardExpirationNotification` → query core DDA card lists → `inventoryManagementManager.checkInventory()`.
3. **Shipping Info**: Batch trigger → `PopulateShippingInfoBatch` → read unshipped cards → update ship_date/tracking_number/card_number.

## Compliance Considerations
- `PopulateShippingInfoBatch` writes `card_number` values into the `instant_issue_card` table — card numbers at rest require PCI DSS Requirement 3 controls (truncation or encryption).
- The batch runs as an OS-level Java process reading credentials from `D:/c-base/config`; access to that directory must be restricted per PCI DSS Requirement 7.
- DDA numbers represent bank account identifiers; their handling in lists and XML strings may trigger GLBA data protection obligations.
- No TLS or channel encryption is configured for database connections in the Spring XML; the DBCP pool connects using Director-configured connection strings.

## Risks
- Hardcoded filesystem paths (`D:/c-base/config/...`) make the batch non-portable and environment-specific.
- Java compiler target is 1.6 (Java 6), which is severely end-of-life with no security support.
- Dependencies: log4j 1.2.14 (affected by legacy CVEs; note: not log4shell-vulnerable in 1.x, but still EOL), Spring 2.5.4, Commons DBCP 1.4 — all EOL.
- No containerisation or orchestration; batch runs as a raw Java process requiring a Windows/Linux host with the C-Base directory structure.
- `System.exit()` calls scattered in main methods make the batch difficult to integrate or test.
