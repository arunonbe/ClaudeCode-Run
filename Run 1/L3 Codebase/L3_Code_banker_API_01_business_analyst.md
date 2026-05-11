# banker_API — Business Analyst View

## Business Purpose

Banker is a funds-authorization and financial-control service that sits between Onbe's B2C disbursement platform (referred to internally as BMC / eCount) and Microsoft Great Plains (GP), the general-ledger / ERP system. Its primary job is to prevent over-commitment of program funds before a disbursement job or order is executed.

From the README: *"Banker verifies funds availability for Job Service and Order Service (ClientZone and API) and provides a snapshot of a program/promotion's financial situation for file processing or API add-fund-request approval. It also serves as a control mechanism to flag over-the-limit approvals."*

## Business Capabilities

| Capability | Primary Method(s) | Notes |
|---|---|---|
| Funds authorization | `auth()`, `authMultiple()` | Reserves funds before disbursement; supports single and batch |
| Un-authorization (reversal) | `unAuth()` | Releases reserved funds without settlement |
| Fund cancellation | `cancelReservedSource()` | Deletes reservation; logs action |
| Force settlement | `forceSettleReservedSource()` | Privileged role required (`bankersettleforce`) |
| Preset funds reservation | `reservePresetFunds()` | Reserves a calculated percentage or minimum base amount |
| Preset funds update/reduction | `updatePresetFunds()` | Reduces or settles a preset-reserved source |
| Available-funds query | `getAvailableFunds()` | Returns full calculation breakdown |
| Program financial balance query | `getFinanceBalances()`, `getProgramInfo()` | Reads from Great Plains |
| Finance document query | `getFinanceDocumentsBySource()`, `getFinanceDocumentsBySources()` | Sales orders, invoices, credit memos |
| Finance payment query | `getFinancePaymentsBySource()`, `getFinancePaymentsBySources()` | Non-voided payments |
| 3/2/1-day payment query | `get321DaysPayments()` | Outstanding ACH-style payments not yet cleared |
| ACH delay query | `getACHDelayDays()` | Returns configured ACH delay days per program/promo |
| Approval notification | `sendApprovalNotification()` | Emails banker-level users when authorization requires escalation |
| Approval counter | `getApprovalNotificationCounter()` | Tracks how many times notification was sent for a source |
| Promotion discovery | `getActivePromotions()` | Returns active GP promotions for a program |
| Multiple sales order management | `getMultipleSalesOrders()`, `insertMultipleSalesOrder()`, `deleteMultipleSalesOrders()` | Handles edge cases where GP has multiple original sales orders |
| Program datasource management | `updateProgramExpressionsDatasourceNames()`, `deleteProgramExpressionsDatasourceNames()` | Live reconfiguration of GP database routing per program regex |

## Business Entities

- **Program** (`programId`: String) — A client incentive/disbursement program; maps to a GP customer account.
- **Promotion** (`promoId`: Integer) — Sub-period or sub-product within a program. Parent promotion is always `0`; exception programs may use `1`.
- **Reserved Source** (`ReservedSourceDTO`) — The core transactional entity. Represents a financial hold (auth, unauth, cancel) for a specific job/order source against a program-promotion.
- **Client Source** (`ClientSourceDTO`) — Input from calling services (Job Service, Order Service) including source amount, source prefix, source ID and optional reference sub-sources.
- **Preset Funds Config** (`PresetFundsConfigDTO`) — Per-program-promo configuration holding a ratio percent and base amount used to calculate preset hold amounts.
- **Finance Document** (`FinanceDocumentDTO`) — GP-side document (sales order, invoice, credit memo, back order).
- **Finance Payment** (`FinancePaymentDTO`) — GP-side payment record.
- **Banker User** (`BankerUserDTO`) — Internal user with assigned banker role levels; used for authorization and email notifications.
- **Banker Email** (`BankerEmail`) — Notification payload sent to role-level recipients when escalation is required.
- **Program Datasource** — A mapping of a regular expression for a program ID to a named GP SQL Server datasource, stored in `banker_program_datasource` table.

## Business Rules & Validations

1. **Available-funds formula** (documented in `BankerServiceAPI.java` line 39–45):
   - Free Funds = Posted Balance + Sum(Saved Usable Payments) + Sum(Saved Credit Memos) − Sum(Posted 321 Payments)
   - Unsettled Funds = Original Sales Order Amount − Sum(Posted Invoices) − Voided Back Order Amount − Voided Sales Order Amount
   - Available Funds = Free Funds − Sum(Unsettled Funds) + Credit Limit

2. **Test source cap**: Test sources (`isTest=true`) are authorized automatically only if `sourceAmount <= MAX_TEST_SOURCE_AMOUNT` (50,000 cents / $500.00), adjusted by a currency multiplier (`Authorize.java` lines 37, 342).

3. **Role-based authorization levels**: Three tiers (`bankerlevelone`, `bankerleveltwo`, `bankerlevelthree`) map to amount thresholds. If funds would fall below the user's permitted `downToAmount`, authorization is denied (`BankerRoleSetting.java`). If `downToAmount < 0`, a `BankerInsufficientFundsException` is thrown (`Authorize.java` lines 432–446).

4. **Force authorization** (`bankerauthforce`): Bypasses available-funds check entirely; still inserts reserved sources.

5. **Multiple original sales orders**: If GP returns more than one active original sales order for a source, the order numbers are logged to a `banker_multiple_sales_order` table and a `BankerMultipleOriginalSalesOrdersException` is thrown (`Authorize.java` lines 577–593).

6. **Reference source parent existence**: A reference (exception) source must have its parent original source already in the reserved-sources table before it can be authorized, unless the user has force-auth privileges (`BankerServiceAction.java` lines 575–605).

7. **Authorization amount guard**: Re-authorizing an existing source cannot increase the reserved amount beyond what already exists (`BankerServiceAction.java` lines 545–572).

8. **Promotion resolution**: If a program has only promotion `1` active and is flagged as a "default promo exception program," promo `1` is treated as the parent; otherwise promo `0` is the parent (`BankerServiceAction.java` lines 515–543).

9. **Preset funds defaults**: If no config is found in DB for a program-promo, defaults of 50% ratio and $1,000 base amount are applied (`PresetFundsConfig.java` lines 80–86).

10. **Serializable transaction isolation**: All banker manager calls execute under `SERIALIZABLE` isolation with a 120-second timeout (`banker-transaction.xml` line 24), ensuring no phantom reads during concurrent fund checks.

## Business Flows

### Authorization Flow (auth)
1. Validate `ClientSourceDTO` inputs.
2. Look up calling user's banker role (`banker_get_user_info`).
3. Check user has minimum `bankerlevelone` access.
4. Resolve actual active promotion from GP (`banker_get_active_promotions`).
5. Settle existing reserved sources (calculate unsettled amounts from GP).
6. Calculate total auth amount by finding original sales order in GP.
7. Check available funds against user's level amount limit.
8. If authorized, upsert reserved source records (`banker_update_reserved_source`).
9. Return `AuthReturnStatusDTO` with `hasEnoughFunds` flag and actual amount.

### Preset Funds Flow
1. Validate input.
2. Resolve promotion.
3. Look up `PresetFundsConfigDTO` (ratio and base amount).
4. Calculate `max(baseAmount, availableFunds * ratio%)`.
5. Insert reservation record.

### Approval Notification Flow
1. Validate notification DTO.
2. Retrieve group-level recipient users.
3. Fetch currency symbol and program/relationship manager labels from eCountCore profile service.
4. Build `BankerEmail` and dispatch via `NotificationManagerImpl`.
5. Increment approval notification counter in DB (`banker_approval_notification` table).

## Compliance & Regulatory Concerns

- **PCI DSS**: Banker does not handle PANs, CVVs or card numbers directly. All amounts are in cents (long integer). No card data flows through Banker. However, Banker's authorization decisions gate fund releases that ultimately load prepaid cards, making it part of the CDE boundary control chain.
- **Reg E / NACHA**: The `getACHDelayDays()` method indicates ACH payments are tracked with settlement delay periods (3, 2, 1 day windows). The `get321DaysPayments()` method explicitly tracks pre-settlement ACH amounts for inclusion in available-funds calculations, reflecting awareness of settlement timing obligations.
- **GLBA / Data minimization**: Banker stores user IDs, group memberships, and source descriptions in the `banker_reserved_sources` table. No cardholder PII is stored beyond internal numeric IDs.
- **Audit trail**: All writes to `banker_reserved_sources` include an `updated_by` (userId) field. The stored procedure `banker_update_reserved_source` returns `-1` on log-insert failure, indicating a separate audit log table is maintained in the banker DB.
- **Separation of duties**: Role levels (1/2/3) and the `bankerauthforce` / `bankersettleforce` roles enforce financial controls over who can authorize what amount or settle/cancel reservations.

## Business Risks

1. **Great Plains single point of failure**: All funds-availability calculations depend on live GP queries. If GP is unavailable, `BankerNoActivePromotionsException` or `BankerServiceException` will prevent any authorization, blocking all disbursement processing.

2. **Static singleton state**: `BankerServiceManagerImpl` is a static singleton (`BankerServiceManagerImpl.java` line 69). In-memory caches (`outstandingPaymentsProgramPromoMap`, `userGroupCodeAuthorizationAmountLimitsMap`, `bankerDefaultPromoExceptionPrograms`, `presetFundsConfigsMap`) are loaded at startup. Stale cache data could cause incorrect available-funds decisions.

3. **Serializable isolation contention**: Using `SERIALIZABLE` transaction isolation on all banker manager operations ensures correctness but creates a potential bottleneck under high concurrency. This is intentional but will degrade throughput as volume scales.

4. **Force-authorize bypass**: Users with `bankerauthforce` role bypass all available-funds checks. Misconfigured role assignments could result in unlimited fund disbursements without financial guard rails.

5. **No API authentication**: The SOAP service endpoint (Apache Axis, `/Banker/*`) has no visible authentication layer in the code or web.xml. Authorization is purely based on the `userId` + `applicationId` passed in the request body.

6. **Multiple sales order exception is a hard block**: When GP returns multiple original sales orders, the flow throws an exception and must be manually resolved. This creates operational risk if GP data inconsistencies are frequent.
