# DevOps & Operations Report — DS_DP_db15

## Repository Identity

**Repository:** DS_DP_db15  
**Deployment Model:** Manual ad-hoc SQL script execution  
**CI/CD Pipeline:** None detected  
**Change Frequency:** Low (9 scripts over ~24 months)

---

## Build and Deployment Model

DS_DP_db15 mirrors the same manual-script deployment pattern as DS_DP_db08. There is no CI/CD pipeline, no migration framework, and no deployment tooling of any kind. Scripts are manually executed by a DBA or data engineer against the `RiskDB` SQL Server instance.

The repository's 9 scripts represent a low-frequency, high-impact change profile — each script modifies core reporting queries or fundamental configuration data affecting ATM cash management, emboss inventory, and client program parameters.

---

## Report Deployment Mechanism

A distinctive operational pattern in this shard is the use of a **stored procedure to deploy report queries**:

```sql
EXECUTE [dbo].[rpt_qryReports_QRY_Insert]
@qryStatus = 'RunD'
,@qryName = 'OnbeATM_CashForecastDetail'
,@qryTxt = "... (long T-SQL query) ..."
```

This pattern (file `20210503_SQ-3028_CREATE - OnbeATM_CashForecastDetail.sql`, lines 7–12) stores the entire T-SQL query body as a string in the `RiskDB.dbo.qryReports` table. The reporting engine retrieves the query text at runtime and executes it dynamically.

**Operational implications:**
- Report logic is stored in a database table, not in source control as a first-class SQL file
- The `qryReports` table is the single source of truth for report behaviour — it must be included in backup/DR planning
- `UPDATE qryReports SET QRYTXT = "..."` pattern (used in `20210315_SQ-1820_ALTER - 131`) replaces the entire query text; there is no versioning within the table
- Report changes are invisible to standard code review until the script file is reviewed

---

## Linked Server Dependency and Operational Risk

The `OnbeATM_CashForecastDetail` report depends on `reportingdbserver2008` via linked server. Operationally:

- If `reportingdbserver2008` is unavailable, the ATM cash forecast report will fail
- `OPENQUERY` executes the remote SQL on the linked server; any performance issues on the remote server degrade the local report
- No timeout or retry logic is visible in the query text
- The linked server name hard-codes the server reference — changing the server name requires a SQL script deployment and coordinated cutover

---

## SQL Agent and Scheduling

No SQL Agent jobs are created or modified in this repository. The reports stored in `qryReports` are likely scheduled via a separate job or application layer not visible here. The `@qryStatus = 'RunD'` parameter in the `rpt_qryReports_QRY_Insert` call suggests a status flag that may control scheduling behaviour within the reporting application.

---

## Environment Differentiation

As with DB08, no environment-specific deployment configuration is present. The same scripts are presumably applied to production directly. No staging environment validation is documented.

---

## Backup and Recovery Considerations

The `qryReports` table is a critical operational asset for DB15 — it contains the deployed report logic. Standard SQL Server backup procedures should include `RiskDB` and specifically `qryReports` in:
- Full database backups
- Log backups (for point-in-time recovery)
- DR replication (if `RiskDB` is log-shipped to a DR instance)

The fact that report query text is stored in a database table rather than as `.sql` files means that a database restore is required to recover report logic, not a simple Git checkout.

---

## Monitoring and Alerting

No monitoring configuration is present in this repository. The Stock reconciliation report (`Report 131`) has built-in thresholds (90% emboss accountability, 50-unit minimum, 21-day period) that define alert conditions in the business logic, but the mechanism for surfacing these alerts to operations teams is not visible in the scripts.

---

## Deployment Risk Assessment

| Risk | Severity | Description |
|---|---|---|
| Report logic in database table (not source-controlled as first-class) | HIGH | `qryReports` contents not versioned independently of script files |
| Linked server to potentially EOL SQL Server 2008 instance | HIGH | PCI DSS patch compliance risk; single point of failure for ATM forecast |
| No rollback capability | HIGH | `UPDATE qryReports SET QRYTXT` overwrites the prior query; no previous version is retained |
| Dynamic SQL execution pattern | MEDIUM | Queries stored and executed as strings; harder to analyse for SQL injection |
| No automated deployment or testing | MEDIUM | Manual execution errors possible |
| `OPENQUERY` with no error handling | MEDIUM | Remote query failures not gracefully handled |
| `spamap_update_query.sql` has no transaction wrapper | MEDIUM | Insert into DMT_SPAMAP_DATA with no BEGIN TRANSACTION/ROLLBACK |
