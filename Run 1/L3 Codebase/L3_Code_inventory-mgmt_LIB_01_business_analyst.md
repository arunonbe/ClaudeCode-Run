# Business Analyst View — inventory-mgmt_LIB

## Business Purpose
A core Gen-1/Gen-2 Java library that manages instant-issue prepaid card inventory for the ecount/C-Base platform. It tracks physical card stock at distribution locations, handles automated and manual reorder workflows, manages card expiration alerts, and records card usage (mark-as-used). This library is a critical component in Onbe's prepaid card issuance operations, directly supporting card programs at retail and distribution sites.

## Capabilities
- Query current inventory levels (count and detail) per program and delivery site.
- Check for low inventory and trigger automatic reorder or manual-reorder notifications.
- Place automated reorder requests by generating XML request files and submitting them via the Repository Service.
- Place ad-hoc (manual) reorder requests from ClientZone.
- Send email notifications for low inventory (automatic, manual, or neither mode), card expiration alerts, and program administrator alerts.
- Track order history per program and location.
- Mark instant-issue cards as used (remove from inventory) by ecount ID or XML batch.
- Get new unassigned cards (PUID or ecount ID) for a program.
- Update card inventory status (USED, RESERVED, etc.) with facility tracking.
- Query card details by PUID or ecountId.
- ID generation service (IDGeneratorMgr/IDGeneratorImpl) for sequential ID allocation from a database sequence table.

## Entities
| Entity | Description |
|--------|-------------|
| InstantIssueCard | A physical prepaid card in inventory; fields: programId, puid, ecountId, locationCode, cardStatus, cardFacility, parentPUID, usedMemberID, cardNumber, dateUsed |
| InstantIssueOrder | A reorder transaction; fields: programId, location, size, facility, username, address fields, shipping info, orderStatus |
| InventoryDetail | Summary of in-stock and on-order counts for a program/location |
| InstantIssueNotificationProfile | Notification preferences per program |
| IDSequence | Database sequence block for ID generation |
| ShippingInfo | Ship date, tracking number, shipment count |

## Business Rules
- Reorder is triggered when current inventory falls at or below the `autoReorderThreshold` for a location.
- Auto reorder creates an XML request file and submits it to the Repository Service via `processJobFile`.
- Manual reorder mode sends a low-inventory email notification rather than automatically placing an order.
- Card expiration alerts are sent when `expirationAlertDays` is reached; for values < 28 days, alerts fire only on the corresponding day before month end.
- Cards are marked as used via stored procedure `instant_issue_use_card_by_ecount_id_xml` (batch XML input).
- PUID (Partner User ID) is the primary card identifier; ecountId is the secondary/legacy identifier.
- Card status values: USED, UNUSED, RESERVED (CardStatus enum), with facility tracking (AUTOMATIC, CLIENTZONE, etc.).
- ID sequences have exhaustion handling: `IDsExhaustedException` and `NoSuchIDSequenceException`.

## Process Flows
1. **Inventory Check (batch)**: Batch job calls `checkInventory()` → evaluates each low-inventory location → triggers auto or manual reorder or expiration alert.
2. **Auto Reorder**: `placeReorder()` → builds XML request file → `RepositoryManager.processJobFile()` → updates order IDs in database.
3. **Manual Reorder (ClientZone)**: `placeAdHocReorder()` → same XML/file path → email notification sent.
4. **Card Issuance**: Caller calls `getNewCard()` → returns PUID → later calls `updateInventory()` to mark card as used.
5. **Expiration Alert**: `sendExpirationAlertNotification()` → looks up min/max package IDs approaching expiry → emails users with ROLE_INVENTORY_VIEW privilege.

## Compliance Considerations
- `InstantIssueCard.getCardNumber()` exists on the interface; card numbers stored or logged are in scope for PCI DSS Requirement 3 (protection of stored cardholder data). The DAO maps `card_number` from the `instant_issue_card_inquiry` stored procedure result set.
- Card data (puid, ecountId, cardNumber) passes through in-memory objects; logging at DEBUG level in InventoryManagementManagerImpl logs ecountIds and PUIDs.
- Email notifications to users contain program/location information and card count ranges; no card numbers observed in email paths.
- xSecurity (privilege framework) controls access to inventory view via ROLE_INVENTORY_VIEW privilege — role-based access control is present.
- The library uses Spring 2.5 / Struts via `prepaid-parent` BOM, all of which are end-of-life.

## Risks
- Card numbers (`card_number`) are handled in DAO layer; any logger that captures SQL parameters or result sets could inadvertently log PANs.
- DEBUG-level logging logs ecountIds and PUIDs (identifiers that map to payment cards) — log sanitisation is not evident in this library.
- Dependency on legacy `cbase` and `xplatform` frameworks makes isolation or replacement difficult.
- XML request files are written to a local filesystem path (`filePath`); file security and access controls are external to this library.
- No unit tests observed for the core `InventoryManagementManagerImpl`.
