# DS_DB_nexpay_claimable — DevOps & Operations Report

## 1. Project Structure

| Attribute | Value |
|-----------|-------|
| Total source files | 5 (1 README + 4 SQL views) |
| Project file | None — no `.sqlproj` or `.sln` present |
| Deployment method | Manual SQL execution (`:r` syntax per README) |
| Prerequisites | SQL Server 2019+ or Azure SQL; EcountCore DB access |
| Documented | YES — README.md is comprehensive |

Unlike all other databases in this analysis set, `DS_DB_nexpay_claimable` has **no SSDT project file** (`.sqlproj`). Deployment is manual script execution as documented in the README:

```sql
:r dbo\Views\claimable_payment.sql
:r dbo\Views\claimable_payment_modality.sql
:r dbo\Views\claimable_payment_status.sql
:r dbo\Views\recipient_registration.sql
```

## 2. CI/CD Pipeline Assessment

**No CI/CD pipeline configuration is committed.** The absence of a `.sqlproj` means SSDT DACPAC-based deployment does not apply. Options available:
- **Manual SQL execution** (current documented approach) — high human-error risk
- **flyway/liquibase migration** — could be adopted given the small schema size
- **Azure DevOps / GitLab CI** with `sqlcmd` execution — straightforward for 4 view scripts
- **SSDT project creation** — could be introduced to bring this database into the same DACPAC pipeline as other databases

Given the database contains only 4 views and changes rarely, a simple CI pipeline that validates and deploys view scripts is appropriate and low-effort.

## 3. Deployment Dependencies

**Critical operational dependency**: This database's views are entirely dependent on `EcountCore` being deployed and accessible on the same SQL Server instance. The deployment runbook must include:
1. Confirm `EcountCore` database is accessible before deploying views
2. Test cross-database connectivity: `SELECT TOP 1 * FROM EcountCore..claimable_payment`
3. Validate all 4 views return data (not errors) post-deployment
4. Verify that `nexpay-claim-code-svc` connection string points to `nexpay_claimable` database (not directly to EcountCore)

## 4. Change Management

The repository has **no DeltaSql folder** and no migration history. Because the schema is only 4 views with no tables or stored procedures:
- Schema changes are CREATE OR ALTER VIEW statements
- No data migration is ever required
- Rollback is straightforward: `DROP VIEW` and recreate from the previous git commit

The README provides clear deployment instructions, making this the most operationally transparent database in the set.

## 5. Environment Considerations

The README notes:
- **SQL Server 2019+ or Azure SQL** required — more modern target than GP databases
- **EcountCore cross-database reference** — both databases must reside on the same SQL Server instance (or Azure SQL managed instance with elastic queries)
- `WITH (NOLOCK)` hints used throughout — indicates this is intended for production read workloads where blocking is unacceptable

**Multi-environment concern**: If `EcountCore` is on a different server in lower environments (DEV, QA, UAT), the views will fail to resolve. Environment-specific deploy targets must be managed carefully.

## 6. Operational Risks

| Risk | Severity | Description |
|------|----------|-------------|
| `SELECT p.*` wildcard in `claimable_payment` | **HIGH** | Silent PII/CDE exposure if EcountCore adds sensitive columns |
| No schema validation in CI pipeline | **HIGH** | Breaking EcountCore changes won't be caught until runtime |
| Cross-database dependency | **MEDIUM** | EcountCore outage cascades to nexpay-claim-code-svc |
| No `.sqlproj` file | **MEDIUM** | Cannot participate in DACPAC-based deployment pipeline |
| NOLOCK dirty read risk | **MEDIUM** | Dirty reads on claimable_payment status fields could display incorrect status |
| No monitoring on view health | **MEDIUM** | View errors only surfaced at application query time |
| `SELECT *` in modality/status views | **LOW** | Future-proofed but uncontrolled schema exposure |

## 7. Monitoring Recommendations

Since the database has no tables, traditional SQL Server monitoring metrics (row counts, table sizes, index fragmentation) do not apply. Recommended monitoring:
1. **Query plan cache monitoring**: Alert if query plans for `nexpay_claimable` views become invalid (EcountCore schema change)
2. **View execution health**: Check `sys.dm_exec_query_stats` for view-related query errors
3. **EcountCore dependency monitoring**: Alert if `EcountCore` database is offline or inaccessible from `nexpay_claimable`'s connection context
4. **Application-level alerting**: `nexpay-claim-code-svc` should expose health check metrics for database query success rate

## 8. Backup and Recovery

No backup strategy is needed for this database's schema — it contains only view definitions which are fully in source control. In the event of disaster:
1. Create new `nexpay_claimable` database
2. Execute 4 SQL scripts from GitLab repository
3. Total recovery time: < 5 minutes

The critical dependency is `EcountCore` recovery — if EcountCore is lost, these views return no data regardless.

## 9. Security Configuration

No `Security/` folder exists in this repository. The security model is simple:
- Grant `SELECT` on the 4 views to the `nexpay-claim-code-svc` service account
- No other access should be granted (no DML permissions — views are read-only)
- The service account's access to `EcountCore` tables is indirect through the view (cross-database VIEW access does not grant direct table access)

This is architecturally sound — the view layer provides a controlled access boundary between the microservice and EcountCore's internal tables.
