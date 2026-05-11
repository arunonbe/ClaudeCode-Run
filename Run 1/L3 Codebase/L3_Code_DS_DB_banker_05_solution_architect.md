# Solution Architect Report — DS_DB_banker

## 1. Technical Architecture

`DS_DB_banker` is an **SSDT SQL Server Database Project** (`banker.sqlproj`) targeting SQL Server 2008 (`Sql100DatabaseSchemaProvider`) with compatibility level 90 (SQL Server 2005).

**Project identity:**
- Project GUID: `{25f40aa0-1918-45fa-b3e9-25454c440b7b}` (`banker.sqlproj` line 10)
- Active branch: `development`
- DSP: `Sql100DatabaseSchemaProvider`
- CompatibilityMode: `90` (SQL Server 2005)
- DefaultCollation: `SQL_Latin1_General_CP1_CI_AS`
- PageVerify: `CHECKSUM`
- TDE: disabled (`IsEncryptionOn=False`, line 51)
- Broker: disabled (`ServiceBrokerOption=DisableBroker`)
- Query Store: enabled (`QueryStoreCaptureMode=Auto`)
- `AnsiNulls=False`, `AnsiWarnings=False`, `ArithAbort=False`, `ConcatNullYieldsNull=False`, `QuotedIdentifier=False` — all non-ANSI settings

**Schema composition** (multi-schema):
- `dbo` schema: 20 tables, 50+ stored procedures, 5 functions, synonyms
- `so` schema: 17 tables, 50+ stored procedures, 3 views — Sales Order Automation subsystem
- `onus` schema: 2 tables, 1 stored procedure — OnUS processing
- `Storage`: partition function and scheme (2013–2016)

**Build artefact**: DACPAC deployed to the Banker SQL Server production instance.

---

## 2. API Surface

The `banker` database exposes its functionality through two categories of stored procedure API.

### 2.1 Core Banker API (dbo schema)

**Fund Reservation API:**
- `banker_get_unsettled_funds(@program_promo_id, @source_id, @source_amount, ... 9 OUTPUT params)` — primary fund settlement determination. Queries `BankerAllSOView` (external) to retrieve GP finance documents and calculate unsettled fund amounts. Returns `@can_settle BIT` and `@unsettled_funds BIGINT` as the key settlement decision outputs (`banker_get_unsettled_funds.sql` lines 1-80)
- `banker_get_payments(@program_id, @promo_id, ...)` — retrieves payment records by querying `BankerPayment` (external view)
- `banker_get_*` family: ~15 procedures for balance calculations, payment summaries, fund availability

**Reservation Management:**
- `banker_delete_reserved_source` / `banker_delete_reserved_sources` — remove fund reservations
- `banker_delete_multiple_sos` — delete multiple sales order reservations

**Balance Capture:**
- `PrepaidCaptureDailyBalances` (created 2017-01-11 by Greg Couto) — captures daily balances from all active Dynamics GP companies by querying GP system tables; populates `so.PrepaidCustomerBalanceHistory`
- `PrepaidCaptureDailyBalances_ForMovingCompany` — migration-specific variant
- `PrepaidCaptureDailyBalances_ForMovingCompany_International` — international variant
- `PrepaidCaptureDailyBalances_ForMovingCompany_International_CPGBP` — British pounds variant

### 2.2 Sales Order Automation API (so schema)

**Order lifecycle API:**
- `so.ordersvc_get_orders` / `so.jobsvc_get_orders` — order service data providers (called via synonyms from external systems)
- `so.aggregate_core` / `so.aggregate_items` — fee aggregation engine
- `so.fee_invoicing_*` family — GP invoice creation procedures
- `so.item_*` family — item processing (plastics, reloads, ACH, etc.)
- `so.order_status` / `so.order_detail` tables — state machine for order processing

**Key synonym chain** (data architect view):
```
External callers (SSIS packages)
    │
    ▼
dbo.na_ordersvc_get_orders (synonym)
    │  → [REPORTINGDBSERVER].[cf_report].[so].[ordersvc_get_orders]
    ▼
cf_report database (on REPORTINGDBSERVER)
    │
    ▼
so.order_status, so.order_detail (in banker — written back by SSIS)
```

### 2.3 Functions

| Function | Purpose |
|---|---|
| `banker_get_required_deposit_date(@current_date, @num_days_to_usable)` | Calculates required payment deposit date given payment type settlement days (check=3, ACH=2, cash=0); excludes weekends |
| `banker_get_sum_saved_credit_memos` | Sums credit memo amounts for program/promo |
| `banker_get_sum_saved_invoices_per_program_promo` | Sums saved invoice amounts |
| `banker_get_sum_saved_usable_payments` | Sums usable payment amounts |
| `banker_get_x_days_payments` | Sums payments within X-day window |

---

## 3. Security Posture

| Control | Status | Finding |
|---|---|---|
| TDE | Disabled | Data at rest unencrypted — fund reservation amounts and balance history are unprotected at rest |
| SQL 2005 compat mode (90) | Active | Modern query features unavailable; performance ceiling |
| `AnsiNulls=False` | Active | Non-ANSI NULL comparison semantics |
| `ArithAbort=False` | Active | Arithmetic overflows silently ignored — financial amount calculation errors may be masked |
| `BankerAllSOView` / `BankerPayment` | External undocumented views | Critical dependency on views not defined in this repo; CDE classification unknown |
| REPORTINGDBSERVER synonym chain | External server alias | All order service data routed via `REPORTINGDBSERVER` server alias; if alias points to wrong server in any environment, financial data is silently misrouted |
| `SSISConfigurations.ConfiguredValue` NVARCHAR(4000) | May contain connection strings | This field should be reviewed for plaintext credentials (PCI DSS Req 8.3) |
| SSIS Windows Auth (implied) | No SQL logins visible in banker Security scripts | Appropriate — service accounts use Windows authentication |
| FortiDB DAM | `FortiDBRptRole` present | Database activity monitoring configured |
| Partition function limited to 2013-2016 | `Storage/monthly_partition.sql` | Historical partition scheme covering only 2013–2016; new data may not be partitioned |

---

## 4. Technical Debt

| Item | File:Line | Impact |
|---|---|---|
| `BankerAllSOView` not defined in repo | `banker_get_unsettled_funds.sql:66-74` | Critical external view dependency — fund settlement breaks if this view is unavailable; ownership/definition unknown |
| `BankerPayment` not defined in repo | `banker_get_payments.sql:27-41` (implied) | Same risk — all payment retrieval depends on this undefined view |
| SQL 2005 compat mode | `banker.sqlproj:63` | All modern SQL Server features unavailable; performance ceiling |
| `AnsiNulls=False` / `ArithAbort=False` | `banker.sqlproj:65-69` | Non-ANSI settings; arithmetic errors silently swallowed — dangerous in financial amount calculations |
| Orphaned backup tables | `dbo.fee_aggregation_core_5_24_2018`, `dbo.fee_aggregation_items_5_24_2018`, `dbo.SSISJobConfigurations_backup`, `so.PrepaidCustomerBalanceHistory_Backup` | Deployed to production via DACPAC; unmanaged data accumulation |
| Developer debug tables in production | `dbo.Nick_Logging_JVC_Orders`, `dbo.Nick_Logging_JVC_Order_Details` | Personal developer debug tables are deployed to production; governance gap |
| Stale partition function | `Storage/monthly_partition.sql` | Partition boundaries end at 2016-12; no coverage for post-2016 data |
| `intl_*` synonyms unused | `dbo.intl_ordersvc_get_orders` etc. | Dead code; commented out in `ordersvc_get_orders.sql:69` but synonyms remain deployed |
| `PrepaidCaptureDailyBalances` reads under READ UNCOMMITTED | `PrepaidCaptureDailyBalances.sql:39` | `SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED` — balance snapshots may read dirty (uncommitted) GP data; daily balance history could be inaccurate |
| `so.gp_dbs` view queries `Atlys_E..vPrgPrefixes` | `so/Views/gp_dbs.sql` | Cross-database view dependency; schema change in Atlys_E breaks GP database routing |
| No TDE | `banker.sqlproj:51` | Fund reservation amounts and balance history unencrypted at rest |

---

## 5. Gen-3 Migration Requirements

| Requirement | Description |
|---|---|
| Resolve `BankerAllSOView` and `BankerPayment` first | These undefined external views are the foundation of fund settlement determination; they must be documented, owned, and replaced before `banker` can be migrated |
| Replace GP invoice creation | `so` schema procedures create GP invoices by inserting into GP tables via SSIS; Gen-3 requires a Dynamics 365 Business Central API or equivalent billing service |
| Replace GP customer model | `fee_invoicing_get_customers` uses dynamic SQL against `CitiPrepaidMapping`, `rm00101`, `SY40100` GP tables; this business knowledge must be extracted to a Gen-3 customer/billing service |
| Replace SSIS job configuration | `SSISConfigurations` and `SSISJobConfigurations` tables drive ETL batch jobs; Gen-3 replaces these with Azure Data Factory pipelines or similar |
| Migrate fund reservation service | `banker_reserved_source` is the core fund reservation ledger; Gen-3 equivalent is a Fund Management microservice with API-level reservation and settlement |
| Upgrade SQL compat mode | Must upgrade compat level 90 → 130+ and test all procedures under ANSI settings before Gen-3 migration |
| Data archival strategy | `PrepaidCustomerBalanceHistory` accumulates indefinitely; Gen-3 must include data retention and archival policy |
| Migrate active client funds data | `banker_reserved_source` contains live fund reservation state; migration requires zero-downtime cutover strategy |

---

## 6. Code-Level Risks

| Risk | File:Line | Notes |
|---|---|---|
| `BankerAllSOView` directly queried with no fallback | `banker_get_unsettled_funds.sql:66-67` (`FROM BankerAllSOView WHERE DOCTYPE IN (2,3,5)`) | If this view is unavailable, the `can_settle` output defaults to 0 and the fund settlement workflow fails silently |
| `ArithAbort=False` in financial amount calculations | `banker.sqlproj:69` | `action_amount BIGINT` and `NUMERIC(19,5)` financial fields computed without arithmetic overflow protection; overflow errors may produce incorrect fund totals |
| `TRANSACTION ISOLATION LEVEL READ UNCOMMITTED` for balance capture | `PrepaidCaptureDailyBalances.sql:39` | Daily balance history snapshots use dirty read — balances captured may reflect uncommitted GP transactions that are subsequently rolled back |
| `REPORTINGDBSERVER` server alias — no fallback | `dbo.na_ordersvc_get_orders` synonym | If `REPORTINGDBSERVER` alias is misconfigured, all NA order data silently disappears; no error monitoring |
| Developer tables deployed to production | `banker.sqlproj` (Nick_Logging_JVC_* build includes) | `Nick_Logging_JVC_Orders` and `Nick_Logging_JVC_Order_Details` are compiled into the DACPAC and deployed to production; any order processing state written to these tables is unmonitored and unretained |
| `ConcatNullYieldsNull=False` | `banker.sqlproj:70` | String concatenation with NULL produces the non-NULL string rather than NULL; dynamic SQL construction in procedures may behave unexpectedly if NULL program identifiers are concatenated |
