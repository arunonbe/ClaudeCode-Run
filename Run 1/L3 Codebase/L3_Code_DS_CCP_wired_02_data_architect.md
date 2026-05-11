# Data Architect Report — DS_CCP_wired

## Database Objects Inventory

### Tables (17 total)

#### Subscription and Scheduling Tables
| Table | PK | Sensitive Fields | Notes |
|---|---|---|---|
| `report_requests` | `ID` SMALLINT IDENTITY | `DeliverySpecification` NVARCHAR(4000) — stores email addresses | Central subscription table; has `ComputedFileName` computed column |
| `report_requests_log` | (not read in full — referenced by procs) | None | Execution history per subscription |
| `report_schedule` | `ScheduleCode` VARCHAR(4) | None | Schedule code reference; `ScheduleDate` and `ScheduleMatch` computed columns |
| `report_timeslot` | `TimeSlotID` TINYINT | None | Delivery time windows |
| `report_parameter_lookup` | `ID` INT IDENTITY | None | Parameter name translation mapping |

#### Cache Tables (Active + Staging pairs)
| Table | Purpose | Sensitive Fields |
|---|---|---|
| `cache_pbr` | Programme Balance Report data | None — financial aggregates |
| `cache_pbr_STG` | Staging for `cache_pbr` | None |
| `cache_pbr_GP` | GP financials PBR data | None |
| `cache_AggSpend` | Aggregate spending data | None |
| `cache_AggSpend_STG` | Staging | None |
| `cache_CardShipDate` | Card shipment dates | None |
| `cache_CardShipDate_STG` | Staging | None |
| `cache_RapidUndeliverableCards` | Undeliverable card records | None |
| `cache_RapidUndeliverableCards_STG` | Staging | None |
| `cache_corp_client_brands` | Brand reference data | None |
| `cache_corp_client_brands_STG` | Staging | None |

### Stored Procedures (11 total)

| Procedure | Purpose |
|---|---|
| `rpt_ProgramBalanceReport` | Generates Programme Balance Report data from cache tables |
| `rpt_validate_reportrequests` | Validates report request parameters before execution |
| `usp_ReportCatalog_RPT` | Returns available reports from SSRS/Crystal Reports catalog |
| `usp_Wired_Cache_AggSpend_INS` | Loads `cache_AggSpend` from staging (stage-and-swap) |
| `usp_Wired_cache_CardShipDate_INS` | Loads `cache_CardShipDate` from staging |
| `usp_Wired_Cache_PBR_INS` | Loads `cache_pbr` from staging |
| `usp_WIred_Cache_RapidUndeliverable` | Loads `cache_RapidUndeliverableCards` from staging |
| `usp_Wired_CorpClientBrands_INS` | Loads `cache_corp_client_brands` from staging |
| `usp_Wired_InsertReportRequest_Manual_INS` | Inserts new report subscription (administrative/manual) |
| `usp_Wired_InsertReportRequest_UI_INS` | Inserts/updates/views report subscription (UI interface) — multi-mode |
| `usp_Wired_SubscriptionStatus_RPT` | Subscription status report with filtering |

### Triggers

| Trigger | Table | Event | Action |
|---|---|---|---|
| `updateModified` | (not specified — `dbo\Trigger\updateModified.sql`) | UPDATE | Updates `DateModified` and `ModifiedBy` columns on change |

### Views

| View | Purpose |
|---|---|
| `vw_param_Frequencies` | Exposes available frequency options for the report request UI; appears to cross-reference schedule codes |

## Sensitive Data Fields — CDE Assessment

### PCI DSS Assessment

**The WIRED database is NOT in PCI DSS CDE scope.** No tables in this database store PANs, CVV/CVCs, track data, PINs, SSNs, or bank account numbers. The cache tables contain programme-level financial aggregates (balances, quantities, amounts) and brand identifiers — not individual cardholder data.

### Privacy-Sensitive Fields

| Table | Column | Data Type | Classification |
|---|---|---|---|
| `report_requests` | `DeliverySpecification` | NVARCHAR(4000) | **Email addresses** — personal data under GDPR/CCPA |
| `report_requests` | `Requester` | VARCHAR(200) | **Username/identity** — `suser_sname()` default captures SQL login name |
| `report_requests` | `ModifiedBy` | VARCHAR(200) | Username |

The `DeliverySpecification` column stores the delivery destination: for Email delivery method, this contains email addresses (e.g., `patricia.zysk@wirecard.com;pattizysk@outlook.com` in seed data `insert_report_requests.sql`). For SFTP delivery, this may contain SFTP paths or connection strings. For WEP delivery, this may be empty.

**Personal email addresses in seed data**: The post-deployment script `post_deployment\insert_report_requests.sql` (seen in lines 22-48) contains `patricia.zysk@wirecard.com` and `pattizysk@outlook.com` as literal email address values committed to source control. These are personal email addresses and represent a **GDPR/CCPA data handling concern** — personal data committed to a Git repository.

## Schema Design Quality

### Strengths
1. **Computed column scheduling logic** (`report_schedule.ScheduleMatch`, `report_schedule.ScheduleDate`): Encoding schedule evaluation as computed columns is elegant and ensures consistency — schedule determination cannot diverge between the DB and application layers.
2. **Computed filename** (`report_requests.ComputedFileName`): Centralising filename generation in the database ensures consistent, collision-resistant output naming.
3. **Stage-and-swap cache pattern**: Each cache table has a `_STG` counterpart. The INSERT procedures load staging first, then swap — enabling near-atomic cache refresh without locking production queries.
4. **`updateModified` trigger**: Automatically maintains audit columns `DateModified` and `ModifiedBy` on UPDATE.
5. **SSDT project management**: Schema is managed as a deployable SSDT project, not raw scripts.

### Weaknesses
1. **`report_requests.ID` is SMALLINT**: Maximum value 32,767. If the system accumulates thousands of subscriptions and log entries, this could overflow. `report_requests_log` also references this ID. Should be INT or BIGINT.
2. **`DeliverySpecification` NVARCHAR(4000) is unbounded for email lists**: A large multi-recipient email list could approach the 4000 character limit.
3. **Dynamic SQL in `usp_Wired_SubscriptionStatus_RPT`** (lines 92–133): The procedure builds a `SELECT` statement by string concatenation of filter clauses. This is a SQL injection risk if any input parameter contains malicious SQL fragments (see Security section).
4. **`cache_pbr` has no unique constraint on meaningful business keys**: Multiple rows can exist for the same `brand_name` + `promotion_id` + `Date` combination. Data integrity depends entirely on SSIS load logic, not database constraints.
5. **No FK between `report_requests` and `report_schedule`**: `report_requests.DeliverySchedule` references `report_schedule.ScheduleCode` but without a FK constraint — orphaned schedule codes would silently produce no output.
6. **`usp_Wired_InsertReportRequest_UI_INS` is 27,311 bytes**: Extremely large stored procedure. It handles three modes (New, Update, View) with complex parameter mapping logic. This is difficult to test and maintain.

## Indexes

- `cache_pbr`: Clustered index `PK_cache_PBR` on `ID` ASC (no functional PK declared — using clustered index as surrogate)
- Other cache tables likely follow same pattern
- No obvious covering indexes visible for common query patterns (e.g., brand+date queries on cache tables)

## Security Roles and Permissions

From `Security\Permissions.sql` and `Security\RoleMemberships.sql`:
- `WIRED_Execute` role: GRANT EXECUTE on schema `dbo` — allows stored procedure execution
- `WIRECARD\GL_WDNAM-DEVQA` and `WIRECARD\GL_WDNAM-DS_Admin` groups have CONNECT grants
- These are Wirecard Active Directory group names — post-acquisition, these AD groups may no longer exist or map to Onbe identities

## Data Retention

- `report_requests` accumulates subscription records indefinitely; `RequestEnabled = 0` marks inactive subscriptions but does not delete them
- `report_requests_log` accumulates execution history indefinitely
- `cache_*` tables are refreshed (truncate-and-reload or stage-and-swap) on schedule
- No explicit purge policy for log or subscription history tables

## PCI DSS CDE Scope Assessment

**WIRED database is OUT of CDE scope.** No PAN or sensitive authentication data is stored or processed. However:
- GDPR/CCPA: Email addresses in `DeliverySpecification` and `Requester` columns are personal data requiring appropriate handling
- SOC 1: Report delivery accuracy and completeness are potentially in financial reporting control scope
- Committed personal email addresses in `insert_report_requests.sql` should be redacted from version control history
