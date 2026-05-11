# Solution Architect Report — DS_CCP_wired

## Technical Debt Inventory

| Item | Severity | Location |
|---|---|---|
| `report_requests.ID` is SMALLINT (max 32,767) | HIGH | `report_requests.sql` — column definition |
| SQL injection risk in `usp_Wired_SubscriptionStatus_RPT` | HIGH | `usp_Wired_SubscriptionStatus_RPT.sql` lines 71–89, 133 |
| Personal email addresses committed to version control | HIGH | `post_deployment\insert_report_requests.sql` lines 22–48 |
| Wirecard AD group names in security definitions | HIGH | `Security\WIRECARD_GL_WDNAM-DEVQA.sql`, `Security\WIRECARD_GL_WDNAM-DS_Admin.sql` |
| No FK between `report_requests.DeliverySchedule` and `report_schedule.ScheduleCode` | MEDIUM | `report_requests.sql` |
| No unique constraint on cache tables business keys | MEDIUM | All `cache_*` tables |
| `usp_Wired_InsertReportRequest_UI_INS` is 27KB — overly complex | MEDIUM | `usp_Wired_InsertReportRequest_UI_INS.sql` |
| Post-deployment seed scripts not idempotent (`insert_report_requests.sql`) | MEDIUM | `post_deployment\insert_report_requests.sql` |
| Hardcoded SSISDB ENVREFERENCE integers in SQL Agent job scripts | MEDIUM | `SQL Agent Scripts\wired_cache_refresh.sql` line 42 |
| Hardcoded production server name in SQL Agent job scripts | MEDIUM | `SQL Agent Scripts\wired_cache_refresh.sql` line 42 |
| `sa` ownership on SQL Agent jobs | MEDIUM | `SQL Agent Scripts\*.sql` — all jobs |
| No FK between `report_requests_log` and `report_requests` | LOW | Referenced in `usp_Wired_SubscriptionStatus_RPT` |
| No index on `cache_pbr(brand_name, promotion_id, Date)` | LOW | `cache_pbr.sql` |
| Dead Confluence runbook URLs in job descriptions | LOW | `SQL Agent Scripts\wired_cache_refresh.sql` line 26 |

## Security Vulnerabilities Found

### 1. SQL Injection Risk in `usp_Wired_SubscriptionStatus_RPT` (HIGH)
File `usp_Wired_SubscriptionStatus_RPT.sql`, lines 71–89, 133:

The procedure builds a dynamic SQL `SELECT` statement by directly concatenating parameter values:
```sql
IF @Report IS NOT NULL 
    SET @sql_WHERE_Report = ' and EXISTS (SELECT 1 FROM dbo.report_requests rr1 WHERE rr1.ID in (' + @Report + ') ...)'
IF @Brand IS NOT NULL SET @sql_WHERE_Brand = ' and cb.ID in (' + @Brand + ')'
...
EXEC (@sql_SELECT + @sql_WHERE_Report + @sql_WHERE_Brand + ...)
```

`@Report` and `@Brand` are derived from input parameters `@P_Report` and `@P_Brand` with only a single-quote stripping: `SET @Report = REPLACE(@P_Report, '''', '')`. This removes single quotes but does NOT prevent injection via other SQL metacharacters. An input like `1) OR 1=1--` (no single quotes) would bypass the stripping and inject into the WHERE clause.

If this procedure is called from a web-based UI (as implied by `usp_Wired_InsertReportRequest_UI_INS` naming), this represents a SQL injection vulnerability accessible from the application layer.

**Remediation**: Use parameterised queries or `sp_executesql` with explicit parameter binding. Replace string concatenation with `CHARINDEX` + `IN` logic using table-valued parameters, or validate inputs are strictly numeric/comma-separated numbers before concatenation.

### 2. Personal Email Addresses in Version Control (HIGH — GDPR/CCPA)
File `post_deployment\insert_report_requests.sql`, lines 22–48: Multiple rows contain personal email addresses as literal string values:
- `patricia.zysk@wirecard.com`
- `pattizysk@outlook.com` (personal email)

These are personal data under GDPR Article 4. Committing personal data to a Git repository means:
- The data is accessible to everyone with repository access
- It may have been exported to any developer workstation that cloned the repo
- Removal requires a git history rewrite (not just a new commit)

**Remediation**: Replace personal email addresses in seed data with role-based email addresses (e.g., `reports@northlane.com`). Initiate a git history rewrite to remove historical commits containing personal emails.

### 3. Wirecard AD Groups in Security Objects (HIGH — Broken Access Control)
Files `Security\WIRECARD_GL_WDNAM-DEVQA.sql` and `Security\WIRECARD_GL_WDNAM-DS_Admin.sql` create or reference Windows logins for `WIRECARD\GL_WDNAM-DEVQA` and `WIRECARD\GL_WDNAM-DS_Admin` Active Directory groups. Post-Northlane acquisition:
- These AD groups likely no longer exist in the current domain
- If deployed to an Onbe SQL Server, `GRANT CONNECT` would fail with an AD lookup error
- If the groups still resolve to a renamed AD group, unexpected users might have access

**Remediation**: Remove Wirecard AD group references from security scripts. Replace with current Onbe AD groups/service accounts with documented access justification.

### 4. No Delivery Specification Encryption (MEDIUM)
`report_requests.DeliverySpecification` NVARCHAR(4000) stores email addresses and potentially SFTP credentials for client report delivery. This column is stored in plaintext. SFTP passwords or access tokens could be embedded here.

**Remediation**: If SFTP credentials are stored in `DeliverySpecification`, they should be encrypted at rest using SQL Server Always Encrypted or moved to a dedicated credential store.

## Stored Procedure Summary

| Procedure | Purpose |
|---|---|
| `rpt_ProgramBalanceReport` | Returns PBR data from `cache_pbr` for report rendering |
| `rpt_validate_reportrequests` | Pre-execution validation of subscription parameters (date ranges, brand existence, etc.) |
| `usp_ReportCatalog_RPT` | Returns available reports from SSRS report server catalog |
| `usp_Wired_Cache_AggSpend_INS` | Stage-and-swap load of `cache_AggSpend` — truncates STG, loads from source, swaps to production |
| `usp_Wired_cache_CardShipDate_INS` | Stage-and-swap load of `cache_CardShipDate` |
| `usp_Wired_Cache_PBR_INS` | Stage-and-swap load of `cache_pbr` |
| `usp_WIred_Cache_RapidUndeliverable` | Stage-and-swap load of `cache_RapidUndeliverableCards` — note mixed case in procedure name (`usp_WIred_`) |
| `usp_Wired_CorpClientBrands_INS` | Stage-and-swap load of `cache_corp_client_brands` |
| `usp_Wired_InsertReportRequest_Manual_INS` | Administrative INSERT of new report subscription with full parameter list |
| `usp_Wired_InsertReportRequest_UI_INS` | Multi-mode (New/Update/View) subscription management via UI; largest procedure in the database at 27KB |
| `usp_Wired_SubscriptionStatus_RPT` | Filtered subscription status report with dynamic SQL construction — SQL injection risk |

## Code Quality Issues

1. **Mixed case procedure name**: `usp_WIred_Cache_RapidUndeliverable` — capital 'I' after 'W'. Minor inconsistency but indicates lack of naming convention review.
2. **Multi-mode procedures**: Both `usp_Wired_InsertReportRequest_UI_INS` and `usp_Wired_SubscriptionStatus_RPT` serve multiple functional roles in a single procedure, making unit testing complex.
3. **Sample execution blocks in procedures**: `usp_Wired_InsertReportRequest_UI_INS` and `usp_Wired_InsertReportRequest_Manual_INS` contain extensive example `EXEC` calls in comments — useful for documentation but inflates procedure size.
4. **`vw_param_Frequencies`** (3,577 bytes) is unusually large for a reference view — it likely contains complex CASE logic or UNION statements that should be evaluated for simplification.

## Recommended Remediation Priority

| Priority | Action |
|---|---|
| P1 — Immediate | Fix SQL injection in `usp_Wired_SubscriptionStatus_RPT` — use `sp_executesql` with typed parameters |
| P1 — Immediate | Remove personal email addresses from `insert_report_requests.sql` and initiate git history rewrite |
| P1 — Immediate | Replace Wirecard AD group references with Onbe-equivalent AD groups in Security scripts |
| P2 — Short-term | Alter `report_requests.ID` from SMALLINT to INT (with `report_requests_log` FK update) |
| P2 — Short-term | Add FK constraint from `report_requests.DeliverySchedule` to `report_schedule.ScheduleCode` |
| P2 — Short-term | Add unique constraint on `cache_pbr(brand_name, promotion_id, Date)` |
| P2 — Short-term | Refactor `usp_Wired_InsertReportRequest_UI_INS` into separate New/Update/View procedures |
| P2 — Short-term | Make `insert_report_requests.sql` idempotent (use MERGE or INSERT-IF-NOT-EXISTS pattern) |
| P3 — Medium-term | Refactor `usp_Wired_SubscriptionStatus_RPT` into a view + application-layer filtering |
| P3 — Medium-term | Add covering index on `cache_pbr` for brand+date queries |
| P3 — Medium-term | Add CI/CD pipeline for dacpac build and deployment |
