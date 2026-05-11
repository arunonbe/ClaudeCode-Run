# cicd-gala_SVC — Business Analyst View

## Business Purpose

cicd-gala_SVC (artifact `cicd-gala`, internal name `banker-parent`) is the **Banker Service**: a funds-authorization and reservation engine that controls disbursement spending against program budgets sourced from a Great Plains (GP) financial ERP database. It acts as the financial gatekeeper between the operational transaction layer (Job Service, Order Service) and the GP ledger, enforcing that no outgoing disbursement (card load, ACH, etc.) exceeds the available program funds. The README describes it only as "Galina's testing area", but the codebase is a complete, production-grade service.

The service name "cicd-gala" and the SCM URL
`scm:git:ssh://git@gitlab.com:northlane/development/application-development/application/cicd-gala.git`
confirm this is a Northlane (pre-Onbe) legacy service that has been mirrored into Onbe's GitLab as a CI/CD testing artefact while preserving the full operational source.

## Business Capabilities

| Capability | Key API Method | Notes |
|---|---|---|
| Single-source authorization | `auth(ClientSourceDTO)` | Checks available funds, reserves budget, returns pass/fail + required banker level |
| Bulk authorization | `authMultiple(ClientSourceDTO[])` | All-or-nothing; any failure rolls back entire list |
| Un-authorization | `unAuth(SourceDTO)` | Releases reserved funds for a program/promo/source |
| Available-funds query | `getAvailableFunds(BankerRequestDTO)` | Returns Free Funds − Unsettled + Credit Limit ± 321-day payments |
| Finance balance query | `getFinanceBalances(BankerRequestDTO)` | Returns GP-posted balance, free funds, credit components |
| Program info query | `getProgramInfo(BankerRequestDTO)` | GP program name, credit limit type, currency, posted balance |
| Preset-funds reservation | `reservePresetFunds(ClientSourceDTO)` | Reserves a calculated percentage of available funds |
| Preset-funds update | `updatePresetFunds(ClientSourceDTO)` | Reduce/settle/cancel a previously preset-reserved source |
| Settle reserved sources | `settleReservedSources(BankerRequestDTO)` | Marks reserved sources as settled against GP invoices |
| Cancel source | `cancelReservedSource(SourceDTO)` | Deletes reserved source, releases funds |
| Force settle | `forceSettleReservedSource(SourceDTO)` | Privileged operation; requires `bankersettleforce` role |
| Approval notification | `sendApprovalNotification(BankerNotificationDTO)` | Emails banker-level users when authorization requires escalation |
| Finance documents | `getFinanceDocumentsBySources / BySource` | Retrieves GP documents (invoices, sales orders, etc.) by source |
| Finance payments | `getFinancePaymentsBySources / BySource` | Retrieves non-voided GP payments by source |
| 321-day payments | `get321DaysPayments(BankerRequestDTO)` | Pending (3-, 2-, 1-day) payment sums affecting available funds |
| ACH delay days | `getACHDelayDays(BankerRequestDTO)` | Returns configured ACH settlement delay for a program/promo |
| Multiple sales orders | `getMultipleSalesOrders / delete / insert` | Manages GP multiple-original-sales-order exceptions |
| Program datasource management | `updateProgramExpressionsDatasourceNames / delete` | Hot-updates the GP database routing table without restart |
| Active promotions | `getActivePromotions(BankerRequestDTO)` | Returns all active GP promotion IDs for a program |
| Preset funds config | `getPresetFundsConfig / updatePresetFundsConfig` | Per-program-promo ratio/base-amount configuration |
| Authorization limit query | `getUserGroupAuthorizationAmountLimt(String)` | Returns the monetary ceiling for a banker role group |

## Business Entities

| Entity | DTO / Class | Description |
|---|---|---|
| Program | `BankerRequestDTO.programId` | Client program identifier (maps to a GP "program number") |
| Promotion | `BankerRequestDTO.promoId` | Sub-identifier within a program; `0` = parent/default promo |
| Source | `SourceDTO`, `ClientSourceDTO` | A specific transaction (job or order) with a `sourcePrefix + sourceId` finance key |
| Reserved Source | `ReservedSourceDTO`, stored in `banker_reserved_source` table | Banker's local lock on funds; fields: `action` (auth/unauth/settle/cancel/force settle), `sourceAmount`, `refSourceId` |
| Finance Balance | `FinanceBalancesDTO` | GP ledger snapshot: posted balance, free funds, credit memos, 321-day payments |
| Available Funds | `AvailableFundsDTO` | Derived: Free Funds − sum(Unsettled) + Credit Limit ± 321 |
| Preset Funds Config | `PresetFundsConfigDTO` | Configures automated fund reservation ratio and floor amount per program/promo |
| Program Datasource | `ProgramDatasourceDTO`, `banker_program_datasource` | Maps program regex expression to GP database name |
| Banker User | `BankerUserDTO` | Internal user with `userId`, `applicationId`, email, and `bankerGroups[]` |
| Banker Email | `BankerEmail` | Approval notification payload with program, source, currency, promotion amounts |
| Authorization Role | `BankerRoleSetting` | Defines role strings: `bankerlevelone`, `bankerleveltwo`, `bankerlevelthree`, `bankerauthforce`, `bankersettleforce`, `bankerupdatefinancedatasources` |

## Business Rules & Validations

1. **Available Funds Formula** (documented in `BankerServiceAPI.java` Javadoc and `Authorize.java`):
   - Free Funds = posted balance + sum(saved usable payments) + sum(saved credit memos) − sum(posted 321 payments) − sum(saved invoices)
   - Unsettled Funds (per source) = Original Sales Order amount − sum(posted invoices) − voided amounts
   - Available Funds = Free Funds − sum(Unsettled Funds) + Credit Limit

2. **Role-based authorization ceiling** (`Authorize.java`, `BankerRoleSetting.java`): A user can only authorize a source if `availableFunds − sourceAmount >= userGroupAuthAmountLimit`. The service checks the highest role held; Level 3 > Level 2 > Level 1 > force-auth (bypasses limits).

3. **Test source cap** (`Authorize.java` line 38): Test sources (`isTest = true`) cannot exceed `MAX_TEST_SOURCE_AMOUNT = 50000` (i.e., $500.00; amounts are in cents). Exceeding this throws `BankerAuthTestException`.

4. **Reference source integrity** (`BankerServiceAction.validateReferencedOriginalSourceExistence`): A reference source (exception file) can only be authorized if its parent original source already exists in `banker_reserved_source`.

5. **Multiple original sales orders** (`Authorize.findSalesOrderAndPopulateSourceAmount`): If a source maps to more than one active GP sales order, all are recorded in a multiple-SO tracking table and `BankerMultipleOriginalSalesOrdersException` is thrown.

6. **Single active promotion rule** (`BankerMultiplePromotionsException`): A source must map to exactly one active GP promotion unless the requesting user has `bankerauthforce` role, in which case the parent promotion is used.

7. **Preset funds update boundary** (`UpdatePresetFunds` action): If `sourceAmount > reservedAmount`, `BankerUpdatePresetFundsExceedAmountException` is thrown. If `sourceAmount <= 0`, the source is settled.

8. **Transaction isolation** (`banker-transaction.xml`): All `BankerServiceManager` operations run under SERIALIZABLE isolation with a 120-second timeout to prevent concurrent over-authorization.

9. **Program promotion parent resolution**: Parent promo defaults to `0`; exception programs (list in `banker_default_promo_exception` table) may use promo `1` as parent instead.

## Business Flows

### Authorization Flow
1. Caller supplies `ClientSourceDTO` (programId, promoId, userId, applicationId, sourceAmount, optional refSources).
2. Service validates inputs; looks up `BankerUserDTO` from cbaseapp DB.
3. Checks user has at least `bankerlevelone` role.
4. Resolves actual GP promotion (active promos, parent promo logic).
5. Settles any already-reserved sources against GP (reducing unsettled funds).
6. Retrieves free funds and credit limit from GP stored procedures.
7. Computes available funds; checks if user's role permits authorization at the resulting balance level.
8. If authorized: inserts/updates `banker_reserved_source` record with action = "auth".
9. Returns `AuthReturnStatusDTO` with `isAuthorized` flag, source amount, and (if denied) required banker level.

### Approval Notification Flow
1. Caller invokes `sendApprovalNotification(BankerNotificationDTO)` with target group level and source details.
2. Service fetches caller info and recipient list (users in that banker group level).
3. Looks up program/relationship manager labels from GP profile service.
4. Constructs `BankerEmailNotification` objects per recipient.
5. Delivers via `NotificationManagerImpl` (cbase notification system).
6. Updates `banker_approval_notification` counter in banker DB.

## Compliance & Regulatory Concerns

- **Fund control**: The service enforces program budget limits before any disbursement is authorized. This is directly relevant to Onbe's obligations as a prepaid card issuer/program manager to ensure client funds are not over-disbursed (Reg E, NACHA, program agreements).
- **Role-based access control**: Three banker levels + force-auth + force-settle roles gate authorization and settlement. No PAN or card data flows through this service.
- **Audit trail**: AOP interceptor `BankerAuditMethodInterceptor` (Spring AOP on all `BankerServiceManagerImpl` methods) logs all operations. The `banker_reserved_source` table records every auth/unauth/settle/cancel action with `updatedBy` userId.
- **No cardholder data**: The service deals in program/source IDs and monetary amounts only; no PAN, CVV, or account numbers are stored or transmitted here.
- **SERIALIZABLE transactions**: Prevents race conditions in fund reservation, important for financial integrity and audit.

## Business Risks

1. **Single singleton pattern** (`BankerServiceManagerImpl.getInstance()`): The service is a JVM singleton; in-memory state (`outstandingPaymentsProgramPromoMap`, `presetFundsConfig`, `bankerDefaultPromoExceptionPrograms`) is loaded at startup and not refreshed except via the `updateProgramExpressions*` API. Stale state risk exists if the database changes without a service restart or API call.
2. **All-or-nothing bulk auth**: `authMultiple` fails the entire batch on any single error. A single invalid source aborts all other valid authorizations.
3. **SERIALIZABLE isolation at scale**: Under high concurrency, SERIALIZABLE on the reserved sources table may cause significant lock contention and timeouts (120-second limit).
4. **No REST/modern API contract**: The service exposes a SOAP/Axis 1.4 interface. Any client breakage is silent unless WSDL is re-parsed.
5. **Approval notification dependency**: `sendApprovalNotification` has hard dependencies on cbase profile services and notification manager. A failure in either causes a `BankerServiceException` without partial-success handling.
6. **`System.out.println` in production code** (`SendApprovalNotification.java` line 274): Leaks internal label type IDs to stdout in the production service.
